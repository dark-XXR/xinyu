"""管理员商品审批、退款回收、对账和权益调整 PostgreSQL 集成测试。"""

import os
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from love_reply_api.application.commerce import CommerceService
from love_reply_api.application.commerce_admin import CommerceAdminService
from love_reply_api.application.errors import ApiError
from love_reply_api.application.payment_adapters import (
    EpayCheckout,
    EpayPaymentState,
    EpayRefundState,
    EpayVerifiedCallback,
)
from love_reply_api.application.provider_runtime import ResolvedProvider
from love_reply_api.infrastructure.commerce_records import (
    AdminCommerceAuditRecord,
    CommerceGrantRecord,
    CommerceOrderRecord,
    EntitlementAdjustmentRecord,
    PaymentAttemptRecord,
    PaymentEventRecord,
    PaymentReconciliationRecord,
    ProductVersionRecord,
    RefundRecord,
    SubscriptionRecord,
)
from love_reply_api.infrastructure.database import engine, session_factory
from love_reply_api.infrastructure.generation_records import (
    EntitlementRecord,
    WalletAccountRecord,
    WalletLedgerRecord,
)
from love_reply_api.infrastructure.identity_records import UserRecord
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_INTEGRATION_TESTS") != "1", reason="requires PostgreSQL"
)


class FakePaymentTransport:
    def __init__(self) -> None:
        self.query_succeeds = False
        self.refund_calls = 0

    def create_checkout(self, **values: object) -> EpayCheckout:
        del values
        return EpayCheckout(checkout_url="https://pay.example.test/checkout")

    def verify_callback(
        self,
        *,
        configuration: dict[str, object],
        credentials: dict[str, str],
        form: dict[str, str],
    ) -> EpayVerifiedCallback:
        del configuration, credentials
        return EpayVerifiedCallback(
            merchant_id="merchant",
            provider_transaction_id=form["trade_no"],
            order_id=form["out_trade_no"],
            payment_method="ALIPAY",
            product_name=form.get("name", "Energy 50"),
            amount_minor=int(form["amount_minor"]),
            occurred_at=datetime.now(UTC),
        )

    async def query(self, **values: object) -> EpayPaymentState:
        order_id = str(values["order_id"])
        return EpayPaymentState(
            status="SUCCEEDED" if self.query_succeeds else "PENDING",
            order_id=order_id,
            amount_minor=600,
            payment_method="ALIPAY",
            provider_transaction_id=f"trade_{order_id}",
        )

    async def refund(self, **values: object) -> EpayRefundState:
        del values
        self.refund_calls += 1
        return EpayRefundState(succeeded=True, provider_refund_id="provider_refund_1")


class FakeGateway:
    def __init__(self) -> None:
        self.transport = FakePaymentTransport()
        self.provider = ResolvedProvider(
            provider_id="prv_epay",
            kind="PAYMENT",
            configuration={
                "paymentTypes": ["ALIPAY"],
                "checkoutTtlSeconds": 900,
                "callbackAckText": "success",
            },
            credentials={"merchantKey": "fixture-secret"},
            resource_version=1,
            retry_limit=0,
        )

    async def resolve(self, *, routing_key: str) -> ResolvedProvider:
        del routing_key
        return self.provider

    async def resolve_by_id(self, *, provider_id: str, routing_key: str) -> ResolvedProvider:
        del routing_key
        assert provider_id == self.provider.provider_id
        return self.provider


@pytest_asyncio.fixture(autouse=True)
async def clean_database() -> AsyncIterator[None]:
    async with session_factory() as session:
        await _delete(session)
    yield
    async with session_factory() as session:
        await _delete(session)
    await engine.dispose()


async def _delete(session: AsyncSession) -> None:
    for model in (
        AdminCommerceAuditRecord,
        EntitlementAdjustmentRecord,
        PaymentReconciliationRecord,
        RefundRecord,
        SubscriptionRecord,
        CommerceGrantRecord,
        PaymentEventRecord,
        PaymentAttemptRecord,
        CommerceOrderRecord,
        ProductVersionRecord,
        WalletLedgerRecord,
        WalletAccountRecord,
        EntitlementRecord,
        UserRecord,
    ):
        await session.execute(delete(model))
    await session.commit()


async def _seed_user(session: AsyncSession, *, user_id: str = "usr_admin_commerce") -> None:
    now = datetime.now(UTC)
    session.add(
        UserRecord(
            user_id=user_id,
            phone_e164=None,
            email_normalized="commerce@example.test",
            status="ACTIVE",
            locale="zh-CN",
            time_zone="UTC",
            resource_version=1,
            created_at=now,
            updated_at=now,
        )
    )
    await session.flush()
    session.add(
        EntitlementRecord(
            user_id=user_id,
            plan_code="FREE",
            plan_expires_at=None,
            text_remaining=5,
            text_reserved=0,
            vision_remaining=0,
            allowed_model_ids=["basic"],
            allowed_style_ids=["warm"],
            resource_version=1,
            updated_at=now,
        )
    )
    session.add(
        WalletAccountRecord(
            user_id=user_id,
            energy_balance=0,
            energy_reserved=0,
            resource_version=1,
            updated_at=now,
        )
    )
    await session.commit()


def _energy_values() -> dict[str, object]:
    return {
        "product_code": "ENERGY_50",
        "product_type": "ENERGY_PACK",
        "display_name": "Energy 50",
        "description": "Fixture pack",
        "currency": "CNY",
        "amount_minor": 600,
        "region": "CN",
        "sales_channels": ["ANDROID"],
        "renewal_type": "NONE",
        "term_days": None,
        "benefit_window_days": 30,
        "benefits": {
            "textQuota": 0,
            "visionQuota": 0,
            "energyAmount": 50,
            "allowedModelIds": [],
            "allowedStyleIds": [],
            "deepAnalysisEnabled": False,
        },
    }


@pytest.mark.asyncio
async def test_product_publish_requires_another_admin_and_rollback_creates_version() -> None:
    async with session_factory() as session:
        gateway = FakeGateway()
        service = CommerceAdminService(session=session, gateway=gateway)  # type: ignore[arg-type]
        draft = await service.create_product(
            admin_id="adm_maker", audit_reason="Create energy pack", values=_energy_values()
        )
        with pytest.raises(ApiError) as captured:
            await service.publish_product(
                product_version_id=draft.product_version_id,
                expected_version=1,
                admin_id="adm_maker",
                effective_at=datetime.now(UTC),
                expires_at=None,
                audit_reason="Attempt self approval",
            )
        assert captured.value.code == "PRODUCT_SELF_APPROVAL_FORBIDDEN"
        published = await service.publish_product(
            product_version_id=draft.product_version_id,
            expected_version=1,
            admin_id="adm_checker",
            effective_at=datetime.now(UTC),
            expires_at=None,
            audit_reason="Approve reviewed product",
        )
        assert published.status == "ACTIVE" and published.version == 1
        rolled_back = await service.rollback_product(
            product_code="ENERGY_50",
            target_product_version_id=published.product_version_id,
            effective_at=datetime.now(UTC),
            admin_id="adm_operator",
            audit_reason="Restore prior price version",
        )
        assert rolled_back.version == 2 and rolled_back.was_published


@pytest.mark.asyncio
async def test_full_refund_recovers_unspent_energy_once() -> None:
    async with session_factory() as session:
        await _seed_user(session)
        gateway = FakeGateway()
        admin = CommerceAdminService(session=session, gateway=gateway)  # type: ignore[arg-type]
        draft = await admin.create_product(
            admin_id="adm_maker", audit_reason="Create refundable pack", values=_energy_values()
        )
        product = await admin.publish_product(
            product_version_id=draft.product_version_id,
            expected_version=1,
            admin_id="adm_checker",
            effective_at=datetime.now(UTC) - timedelta(seconds=1),
            expires_at=None,
            audit_reason="Approve refundable pack",
        )
        commerce = CommerceService(session=session, gateway=gateway)  # type: ignore[arg-type]
        order = await commerce.create_order(
            user_id="usr_admin_commerce",
            product_version_id=product.product_version_id,
            payment_method="ALIPAY",
        )
        await commerce.receive_callback(
            provider_id="prv_epay",
            form={
                "trade_no": "trade_refund",
                "out_trade_no": order.order_id,
                "amount_minor": "600",
                "name": "Energy 50",
            },
        )
        refund = await commerce.create_refund(
            user_id="usr_admin_commerce",
            order_id=order.order_id,
            amount_minor=600,
            reason_code="USER_REQUEST",
            comment=None,
        )
        approved = await admin.decide_refund(
            refund_id=refund.refund_id,
            expected_version=1,
            admin_id="adm_refund",
            decision="APPROVE",
            rejection_reason_code=None,
            audit_reason="Approve eligible refund",
        )
        completed = await admin.execute_refund(
            refund_id=refund.refund_id,
            expected_version=approved.resource_version,
            admin_id="adm_executor",
            audit_reason="Execute approved refund",
        )
        wallet = await session.get(WalletAccountRecord, "usr_admin_commerce")
        assert completed.status == "SUCCEEDED"
        assert completed.entitlement_recovery_status == "COMPLETED"
        assert wallet is not None and wallet.energy_balance == 0
        assert gateway.transport.refund_calls == 1


@pytest.mark.asyncio
async def test_entitlement_adjustment_replay_is_idempotent_and_conflict_is_rejected() -> None:
    async with session_factory() as session:
        await _seed_user(session)
        service = CommerceAdminService(session=session, gateway=FakeGateway())  # type: ignore[arg-type]
        first = await service.adjust_entitlement(
            idempotency_key="idem-adjustment-1",
            admin_id="adm_support",
            user_id="usr_admin_commerce",
            unit="ENERGY",
            delta=20,
            reason_code="SUPPORT_CORRECTION",
            audit_reason="Correct verified support case",
        )
        replay = await service.adjust_entitlement(
            idempotency_key="idem-adjustment-1",
            admin_id="adm_support",
            user_id="usr_admin_commerce",
            unit="ENERGY",
            delta=20,
            reason_code="SUPPORT_CORRECTION",
            audit_reason="Correct verified support case",
        )
        assert replay.adjustment_id == first.adjustment_id
        wallet = await session.get(WalletAccountRecord, "usr_admin_commerce")
        assert wallet is not None and wallet.energy_balance == 20
        with pytest.raises(ApiError) as captured:
            await service.adjust_entitlement(
                idempotency_key="idem-adjustment-1",
                admin_id="adm_support",
                user_id="usr_admin_commerce",
                unit="ENERGY",
                delta=30,
                reason_code="SUPPORT_CORRECTION",
                audit_reason="Conflicting support correction",
            )
        assert captured.value.code == "IDEMPOTENCY_KEY_REUSED"


@pytest.mark.asyncio
async def test_reconciliation_queries_only_selected_stale_batch_and_settles() -> None:
    async with session_factory() as session:
        await _seed_user(session)
        gateway = FakeGateway()
        admin = CommerceAdminService(session=session, gateway=gateway)  # type: ignore[arg-type]
        draft = await admin.create_product(
            admin_id="adm_maker", audit_reason="Create reconciliation pack", values=_energy_values()
        )
        product = await admin.publish_product(
            product_version_id=draft.product_version_id,
            expected_version=1,
            admin_id="adm_checker",
            effective_at=datetime.now(UTC) - timedelta(seconds=1),
            expires_at=None,
            audit_reason="Approve reconciliation pack",
        )
        commerce = CommerceService(session=session, gateway=gateway)  # type: ignore[arg-type]
        order = await commerce.create_order(
            user_id="usr_admin_commerce",
            product_version_id=product.product_version_id,
            payment_method="ALIPAY",
        )
        gateway.transport.query_succeeds = True
        result = await admin.run_reconciliation(
            admin_id="adm_finance",
            stale_before=datetime.now(UTC) + timedelta(seconds=1),
            max_orders=10,
            audit_reason="Run scheduled payment reconciliation",
        )
        await session.refresh(order)
        wallet = await session.get(WalletAccountRecord, "usr_admin_commerce")
        assert result.scanned_count == 1 and result.settled_count == 1
        assert order.status == "PAID" and order.entitlement_granted
        assert wallet is not None and wallet.energy_balance == 50
