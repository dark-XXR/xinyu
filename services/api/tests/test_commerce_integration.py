"""订单快照、易支付回调和权益幂等发放集成测试。"""

import os
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from hashlib import md5

import pytest
import pytest_asyncio
from love_reply_api.application.commerce import CommerceService
from love_reply_api.application.errors import ApiError
from love_reply_api.application.payment_adapters import EpayTransport
from love_reply_api.application.provider_runtime import ResolvedProvider
from love_reply_api.infrastructure.commerce_records import (
    CommerceOrderRecord,
    PaymentAttemptRecord,
    PaymentEventRecord,
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


CONFIG = {
    "adapterType": "EPAY_COMPAT",
    "gatewayBaseUrl": "https://pay.example.test",
    "submitPath": "/submit",
    "queryPath": "/query",
    "refundPath": "/refund",
    "merchantId": "merchant",
    "applicationId": None,
    "paymentTypes": ["ALIPAY"],
    "signingPreset": "EPAY_MD5_CANONICAL",
    "callbackAckText": "success",
    "notifyUrl": "https://api.example.test/webhooks/v1/payments/epay/prv_epay",
    "returnUrl": "https://app.example.test/result",
    "callbackTimeWindowSeconds": 600,
    "checkoutTtlSeconds": 900,
    "timeoutMs": 10000,
}


class FakeGateway:
    def __init__(self) -> None:
        self.transport = EpayTransport(now_factory=lambda: datetime(2026, 8, 9, 12, 30, tzinfo=UTC))
        self.provider = ResolvedProvider(
            provider_id="prv_epay",
            kind="PAYMENT",
            configuration=CONFIG,
            credentials={"merchantKey": "secret"},
            resource_version=1,
            retry_limit=0,
        )

    async def resolve(self, *, routing_key: str) -> ResolvedProvider:
        del routing_key
        return self.provider

    async def resolve_by_id(self, *, provider_id: str, routing_key: str) -> ResolvedProvider:
        del routing_key
        assert provider_id == "prv_epay"
        return self.provider


@pytest_asyncio.fixture(autouse=True)
async def clean() -> AsyncIterator[None]:
    async with session_factory() as session:
        await _delete(session)
    yield
    async with session_factory() as session:
        await _delete(session)
    await engine.dispose()


async def _delete(session: AsyncSession) -> None:
    for model in (
        RefundRecord,
        SubscriptionRecord,
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


def _callback(order_id: str, money: str = "19.90") -> dict[str, str]:
    form = {
        "pid": "merchant",
        "trade_no": "trade-1",
        "out_trade_no": order_id,
        "type": "alipay",
        "name": "VIP Standard",
        "money": money,
        "trade_status": "TRADE_SUCCESS",
        "timestamp": str(int(datetime(2026, 8, 9, 12, 30, tzinfo=UTC).timestamp())),
        "sign_type": "MD5",
    }
    canonical = "&".join(f"{k}={v}" for k, v in sorted(form.items()) if k != "sign_type")
    form["sign"] = md5(f"{canonical}secret".encode()).hexdigest()  # noqa: S324
    return form


@pytest.mark.asyncio
async def test_verified_callback_grants_once_and_conflicts_fail() -> None:
    now = datetime(2026, 8, 9, 12, 0, tzinfo=UTC)
    async with session_factory() as session:
        session.add(
            UserRecord(
                user_id="usr_commerce",
                phone_e164=None,
                email_normalized="pay@example.com",
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
                user_id="usr_commerce",
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
                user_id="usr_commerce",
                energy_balance=0,
                energy_reserved=0,
                resource_version=1,
                updated_at=now,
            )
        )
        session.add(
            ProductVersionRecord(
                product_version_id="prod_vip_1",
                product_code="VIP_STANDARD",
                version=1,
                product_type="PLAN",
                display_name="VIP Standard",
                description=None,
                currency="CNY",
                amount_minor=1990,
                region="CN",
                sales_channels=["ANDROID"],
                renewal_type="NONE",
                term_days=30,
                benefit_window_days=30,
                benefits={
                    "textQuota": 300,
                    "visionQuota": 30,
                    "energyAmount": 0,
                    "allowedModelIds": ["quality"],
                    "allowedStyleIds": ["warm", "direct"],
                },
                status="ACTIVE",
                effective_at=now,
                expires_at=None,
                created_at=now,
            )
        )
        await session.commit()
        service = CommerceService(session=session, gateway=FakeGateway())  # type: ignore[arg-type]
        order = await service.create_order(
            user_id="usr_commerce", product_version_id="prod_vip_1", payment_method="ALIPAY"
        )
        assert (
            await service.receive_callback(provider_id="prv_epay", form=_callback(order.order_id))
            == "success"
        )
        assert (
            await service.receive_callback(provider_id="prv_epay", form=_callback(order.order_id))
            == "success"
        )
        entitlement = await session.get(EntitlementRecord, "usr_commerce")
        assert entitlement is not None and entitlement.text_remaining == 305
        assert len(await service.list_subscriptions(user_id="usr_commerce")) == 1
        with pytest.raises(ApiError) as captured:
            await service.receive_callback(
                provider_id="prv_epay", form=_callback(order.order_id, "18.90")
            )
        assert captured.value.code in {"PAYMENT_SIGNATURE_INVALID", "PAYMENT_CALLBACK_CONFLICT"}
