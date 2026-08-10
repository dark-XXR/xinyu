"""商品目录、订单、支付结算、订阅和退款业务服务。

订单保存不可变商品快照；只有验签回调或主动查询能结算。结算与权益发放在同一数据库事务中，
并通过订单标记和支付事件唯一键保证重复回调不会重复增加次数、会员天数或能量。
"""

from datetime import UTC, datetime, timedelta
from hashlib import sha256
from json import dumps
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from love_reply_api.application.audit import ComplianceAuditService
from love_reply_api.application.errors import ApiError
from love_reply_api.application.payment_adapters import EpayVerifiedCallback
from love_reply_api.application.provider_runtime import RegistryPaymentGateway
from love_reply_api.application.referrals import ReferralService
from love_reply_api.infrastructure.commerce_records import (
    CommerceGrantRecord,
    CommerceOrderRecord,
    PaymentAttemptRecord,
    PaymentEventRecord,
    ProductVersionRecord,
    RefundRecord,
    SubscriptionRecord,
)
from love_reply_api.infrastructure.generation_records import (
    EntitlementRecord,
    WalletAccountRecord,
    WalletLedgerRecord,
)


class CommerceService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        gateway: RegistryPaymentGateway,
        referrals: ReferralService | None = None,
        audit: ComplianceAuditService | None = None,
    ) -> None:
        self._session = session
        self._gateway = gateway
        self._referrals = referrals
        self._audit = audit

    async def list_products(self, *, region: str, channel: str) -> list[ProductVersionRecord]:
        now = datetime.now(UTC)
        rows = list(
            (
                await self._session.scalars(
                    select(ProductVersionRecord)
                    .where(
                        ProductVersionRecord.region == region,
                        ProductVersionRecord.status == "ACTIVE",
                        ProductVersionRecord.effective_at <= now,
                        (ProductVersionRecord.expires_at.is_(None))
                        | (ProductVersionRecord.expires_at > now),
                    )
                    .order_by(
                        ProductVersionRecord.product_code, ProductVersionRecord.version.desc()
                    )
                )
            ).all()
        )
        return [row for row in rows if channel in row.sales_channels]

    async def get_product(self, *, product_version_id: str) -> ProductVersionRecord:
        product = await self._session.get(ProductVersionRecord, product_version_id)
        now = datetime.now(UTC)
        if (
            product is None
            or product.status != "ACTIVE"
            or product.effective_at > now
            or (product.expires_at is not None and product.expires_at <= now)
        ):
            raise ApiError(
                status_code=404, code="PRODUCT_NOT_FOUND", message="Product was not found."
            )
        return product

    async def create_order(
        self, *, user_id: str, product_version_id: str, payment_method: str
    ) -> CommerceOrderRecord:
        product = await self.get_product(product_version_id=product_version_id)
        provider = await self._gateway.resolve(routing_key=user_id)
        if payment_method not in provider.configuration["paymentTypes"]:
            raise ApiError(
                status_code=400,
                code="PAYMENT_METHOD_UNAVAILABLE",
                message="Payment method is unavailable.",
            )
        now = datetime.now(UTC)
        order_id = f"ord_{uuid4().hex}"
        ttl = int(provider.configuration["checkoutTtlSeconds"])
        order = CommerceOrderRecord(
            order_id=order_id,
            user_id=user_id,
            status="PENDING_PAYMENT",
            product_snapshot=self._product_snapshot(product),
            currency=product.currency,
            amount_minor=product.amount_minor,
            paid_amount_minor=0,
            entitlement_granted=False,
            paid_at=None,
            expires_at=now + timedelta(seconds=ttl),
            resource_version=1,
            created_at=now,
            updated_at=now,
        )
        self._session.add(order)
        await self._session.flush()
        await self._create_attempt(
            order=order, provider=provider, payment_method=payment_method, now=now
        )
        if self._audit is not None:
            await self._audit.record_event(
                category="PAYMENT",
                event_type="ORDER_CREATED",
                outcome="SUCCEEDED",
                severity="INFO",
                actor_type="USER",
                actor_id=user_id,
                user_id=user_id,
                resource_type="ORDER",
                resource_id=order_id,
                order_id=order_id,
                provider_id=provider.provider_id,
                summary="用户创建充值或订阅订单",
                metadata={
                    "productVersionId": product_version_id,
                    "productCode": product.product_code,
                    "productType": product.product_type,
                    "paymentMethod": payment_method,
                    "currency": product.currency,
                    "amountMinor": product.amount_minor,
                },
            )
        await self._session.commit()
        return order

    async def create_payment_attempt(
        self, *, user_id: str, order_id: str, expected_version: int, payment_method: str
    ) -> CommerceOrderRecord:
        order = await self._owned_order_locked(user_id, order_id)
        self._assert_version(order, expected_version)
        if order.status not in {"CREATED", "PENDING_PAYMENT", "FAILED"}:
            raise ApiError(
                status_code=409,
                code="ORDER_NOT_PAYABLE",
                message="Order cannot accept another payment attempt.",
            )
        provider = await self._gateway.resolve(routing_key=user_id)
        now = datetime.now(UTC)
        await self._create_attempt(
            order=order, provider=provider, payment_method=payment_method, now=now
        )
        order.status = "PENDING_PAYMENT"
        order.resource_version += 1
        order.updated_at = now
        if self._audit is not None:
            await self._audit.record_event(
                category="PAYMENT",
                event_type="PAYMENT_ATTEMPT_CREATED",
                outcome="SUCCEEDED",
                severity="INFO",
                actor_type="USER",
                actor_id=user_id,
                user_id=user_id,
                resource_type="ORDER",
                resource_id=order_id,
                order_id=order_id,
                provider_id=provider.provider_id,
                summary="用户为订单重新创建支付尝试",
                metadata={"paymentMethod": payment_method},
            )
        await self._session.commit()
        return order

    async def get_order(self, *, user_id: str, order_id: str) -> CommerceOrderRecord:
        order = await self._session.get(CommerceOrderRecord, order_id)
        if order is None or order.user_id != user_id:
            raise ApiError(status_code=404, code="ORDER_NOT_FOUND", message="Order was not found.")
        return order

    async def attempts(self, order_id: str) -> list[PaymentAttemptRecord]:
        return list(
            (
                await self._session.scalars(
                    select(PaymentAttemptRecord)
                    .where(PaymentAttemptRecord.order_id == order_id)
                    .order_by(PaymentAttemptRecord.created_at)
                )
            ).all()
        )

    async def sync_payment(
        self, *, user_id: str, order_id: str, expected_version: int
    ) -> CommerceOrderRecord:
        order = await self._owned_order_locked(user_id, order_id)
        self._assert_version(order, expected_version)
        if order.status == "PAID":
            return order
        attempt = await self._latest_attempt(order_id)
        provider = await self._gateway.resolve_by_id(
            provider_id=attempt.provider_id, routing_key=order_id
        )
        state = await self._gateway.transport.query(
            configuration=provider.configuration,
            credentials=provider.credentials,
            order_id=order_id,
        )
        attempt.last_synced_at = datetime.now(UTC)
        if state.status == "SUCCEEDED":
            if (
                state.amount_minor != order.amount_minor
                or state.payment_method != attempt.payment_method
            ):
                raise ApiError(
                    status_code=409,
                    code="PAYMENT_QUERY_CONFLICT",
                    message="Provider payment facts do not match the order.",
                )
            await self._settle(
                order=order,
                attempt=attempt,
                provider_id=provider.provider_id,
                provider_transaction_id=state.provider_transaction_id or f"query_{order_id}",
                fingerprint=self._fingerprint(
                    {"source": "QUERY", "orderId": order_id, "amount": state.amount_minor}
                ),
            )
        await self._session.commit()
        return order

    async def reconcile_order(self, *, order: CommerceOrderRecord) -> str:
        """在管理员限定的批次内核对单笔订单，不自行提交外层事务。"""

        now = datetime.now(UTC)
        if order.status in {"PAID", "PARTIALLY_REFUNDED"} and not order.entitlement_granted:
            # 支付事实已经由回调或查询确认时，只恢复被中断的本地权益事务。
            await self._grant(order=order, now=now)
            order.entitlement_granted = True
            order.resource_version += 1
            order.updated_at = now
            return "RECOVERED"
        if order.status not in {"CREATED", "PENDING_PAYMENT", "FAILED"}:
            return "SKIPPED"
        attempt = await self._latest_attempt(order.order_id)
        provider = await self._gateway.resolve_by_id(
            provider_id=attempt.provider_id, routing_key=order.order_id
        )
        state = await self._gateway.transport.query(
            configuration=provider.configuration,
            credentials=provider.credentials,
            order_id=order.order_id,
        )
        attempt.last_synced_at = now
        attempt.updated_at = now
        if state.status != "SUCCEEDED":
            return "PENDING"
        if (
            state.amount_minor != order.amount_minor
            or state.payment_method != attempt.payment_method
        ):
            raise ApiError(
                status_code=409,
                code="PAYMENT_QUERY_CONFLICT",
                message="Provider payment facts do not match the order.",
            )
        await self._settle(
            order=order,
            attempt=attempt,
            provider_id=provider.provider_id,
            provider_transaction_id=state.provider_transaction_id or f"query_{order.order_id}",
            fingerprint=self._fingerprint(
                {
                    "source": "ADMIN_RECONCILIATION",
                    "orderId": order.order_id,
                    "amount": state.amount_minor,
                }
            ),
        )
        return "SETTLED"

    async def receive_callback(self, *, provider_id: str, form: dict[str, str]) -> str:
        provider = await self._gateway.resolve_by_id(
            provider_id=provider_id, routing_key=form.get("out_trade_no", "callback")
        )
        callback = self._gateway.transport.verify_callback(
            configuration=provider.configuration, credentials=provider.credentials, form=form
        )
        order = await self._session.scalar(
            select(CommerceOrderRecord)
            .where(CommerceOrderRecord.order_id == callback.order_id)
            .with_for_update()
        )
        if order is None:
            raise ApiError(status_code=404, code="ORDER_NOT_FOUND", message="Order was not found.")
        fingerprint = self._fingerprint(
            {
                "providerId": provider_id,
                "tradeNo": callback.provider_transaction_id,
                "orderId": callback.order_id,
                "amount": callback.amount_minor,
                "method": callback.payment_method,
            }
        )
        existing = await self._session.scalar(
            select(PaymentEventRecord).where(
                PaymentEventRecord.provider_transaction_id == callback.provider_transaction_id
            )
        )
        if existing is not None:
            if existing.event_fingerprint != fingerprint:
                raise ApiError(
                    status_code=409,
                    code="PAYMENT_CALLBACK_CONFLICT",
                    message="Callback conflicts with recorded payment facts.",
                )
            return str(provider.configuration["callbackAckText"])
        self._assert_callback_facts(order, callback)
        attempt = await self._matching_attempt(order.order_id, callback.payment_method)
        await self._settle(
            order=order,
            attempt=attempt,
            provider_id=provider_id,
            provider_transaction_id=callback.provider_transaction_id,
            fingerprint=fingerprint,
            payment_identity_hash=(
                self._referrals.hash_payment_identity(
                    provider_id=provider_id,
                    payer_reference=callback.payer_reference,
                )
                if self._referrals is not None and callback.payer_reference is not None
                else None
            ),
        )
        await self._session.commit()
        return str(provider.configuration["callbackAckText"])

    async def list_subscriptions(self, *, user_id: str) -> list[SubscriptionRecord]:
        return list(
            (
                await self._session.scalars(
                    select(SubscriptionRecord)
                    .where(SubscriptionRecord.user_id == user_id)
                    .order_by(SubscriptionRecord.created_at.desc())
                )
            ).all()
        )

    async def cancel_subscription(
        self,
        *,
        user_id: str,
        subscription_id: str,
        expected_version: int,
        cancel_at_period_end: bool,
    ) -> SubscriptionRecord:
        record = await self._session.scalar(
            select(SubscriptionRecord)
            .where(
                SubscriptionRecord.subscription_id == subscription_id,
                SubscriptionRecord.user_id == user_id,
            )
            .with_for_update()
        )
        if record is None:
            raise ApiError(
                status_code=404,
                code="SUBSCRIPTION_NOT_FOUND",
                message="Subscription was not found.",
            )
        if record.resource_version != expected_version:
            raise self._version_error(record.resource_version)
        now = datetime.now(UTC)
        if record.renewal_type == "NONE":
            # 预付费非续费套餐没有可撤销的扣款授权，购买权益必须保留到已购周期结束。
            record.auto_renew = False
            record.cancel_at_period_end = False
            record.status = "ACTIVE"
            return record
        record.cancel_at_period_end = cancel_at_period_end
        record.auto_renew = False
        record.status = "CANCELLATION_SCHEDULED" if cancel_at_period_end else "CANCELLED"
        record.resource_version += 1
        record.updated_at = now
        if self._audit is not None:
            await self._audit.record_event(
                category="PAYMENT",
                event_type="SUBSCRIPTION_CANCEL_CHANGED",
                outcome="SUCCEEDED",
                severity="INFO",
                actor_type="USER",
                actor_id=user_id,
                user_id=user_id,
                resource_type="SUBSCRIPTION",
                resource_id=subscription_id,
                order_id=record.order_id,
                summary="用户变更订阅取消状态",
                metadata={
                    "cancelAtPeriodEnd": cancel_at_period_end,
                    "status": record.status,
                },
            )
        await self._session.commit()
        return record

    async def create_refund(
        self,
        *,
        user_id: str,
        order_id: str,
        amount_minor: int,
        reason_code: str,
        comment: str | None,
    ) -> RefundRecord:
        order = await self.get_order(user_id=user_id, order_id=order_id)
        existing_total = sum(
            (
                await self._session.scalars(
                    select(RefundRecord.requested_amount_minor).where(
                        RefundRecord.order_id == order_id,
                        RefundRecord.status.not_in(["REJECTED", "FAILED"]),
                    )
                )
            ).all()
        )
        if (
            order.status not in {"PAID", "PARTIALLY_REFUNDED"}
            or amount_minor + existing_total > order.paid_amount_minor
        ):
            raise ApiError(
                status_code=409,
                code="REFUND_AMOUNT_INVALID",
                message="Refund amount exceeds the refundable order amount.",
            )
        now = datetime.now(UTC)
        record = RefundRecord(
            refund_id=f"ref_{uuid4().hex}",
            user_id=user_id,
            order_id=order_id,
            status="REVIEWING",
            currency=order.currency,
            requested_amount_minor=amount_minor,
            refunded_amount_minor=0,
            reason_code=reason_code,
            comment=comment,
            entitlement_recovery_status="PENDING",
            rejection_reason_code=None,
            provider_refund_id=None,
            resource_version=1,
            created_at=now,
            updated_at=now,
        )
        self._session.add(record)
        if self._audit is not None:
            await self._audit.record_event(
                category="PAYMENT",
                event_type="REFUND_REQUESTED",
                outcome="SUCCEEDED",
                severity="INFO",
                actor_type="USER",
                actor_id=user_id,
                user_id=user_id,
                resource_type="REFUND",
                resource_id=record.refund_id,
                order_id=order_id,
                summary="用户提交退款申请",
                metadata={
                    "amountMinor": amount_minor,
                    "currency": order.currency,
                    "reasonCode": reason_code,
                },
                sensitive_payload={"comment": comment} if comment else None,
            )
        await self._session.commit()
        return record

    async def get_refund(self, *, user_id: str, refund_id: str) -> RefundRecord:
        record = await self._session.get(RefundRecord, refund_id)
        if record is None or record.user_id != user_id:
            raise ApiError(
                status_code=404, code="REFUND_NOT_FOUND", message="Refund was not found."
            )
        return record

    async def _create_attempt(
        self, *, order: CommerceOrderRecord, provider: Any, payment_method: str, now: datetime
    ) -> PaymentAttemptRecord:
        checkout = self._gateway.transport.create_checkout(
            configuration=provider.configuration,
            credentials=provider.credentials,
            order_id=order.order_id,
            product_name=str(order.product_snapshot["displayName"]),
            amount_minor=order.amount_minor,
            currency=order.currency,
            payment_method=payment_method,
        )
        attempt = PaymentAttemptRecord(
            payment_attempt_id=f"pay_{uuid4().hex}",
            order_id=order.order_id,
            provider_id=provider.provider_id,
            provider_resource_version=provider.resource_version,
            payment_method=payment_method,
            status="PENDING",
            amount_minor=order.amount_minor,
            currency=order.currency,
            checkout_action={
                "actionType": "REDIRECT_URL",
                "value": checkout.checkout_url,
                "expiresAt": order.expires_at.isoformat(),
            },
            provider_transaction_id=None,
            failure_code=None,
            last_synced_at=None,
            created_at=now,
            updated_at=now,
        )
        self._session.add(attempt)
        return attempt

    async def _settle(
        self,
        *,
        order: CommerceOrderRecord,
        attempt: PaymentAttemptRecord,
        provider_id: str,
        provider_transaction_id: str,
        fingerprint: str,
        payment_identity_hash: str | None = None,
    ) -> None:
        if order.entitlement_granted:
            return
        now = datetime.now(UTC)
        order.status = "PAID"
        order.paid_amount_minor = order.amount_minor
        order.entitlement_granted = True
        order.paid_at = now
        order.resource_version += 1
        order.updated_at = now
        attempt.status = "SUCCEEDED"
        attempt.provider_transaction_id = provider_transaction_id
        attempt.updated_at = now
        self._session.add(
            PaymentEventRecord(
                payment_event_id=f"pevt_{uuid4().hex}",
                provider_id=provider_id,
                provider_transaction_id=provider_transaction_id,
                order_id=order.order_id,
                event_fingerprint=fingerprint,
                status="SETTLED",
                received_at=now,
            )
        )
        if self._audit is not None:
            await self._audit.record_event(
                category="PAYMENT",
                event_type="PAYMENT_SETTLED",
                outcome="SUCCEEDED",
                severity="INFO",
                actor_type="SYSTEM",
                user_id=order.user_id,
                resource_type="ORDER",
                resource_id=order.order_id,
                order_id=order.order_id,
                provider_id=provider_id,
                summary="支付到账并完成权益发放",
                metadata={
                    "paymentAttemptId": attempt.payment_attempt_id,
                    "providerTransactionId": provider_transaction_id,
                    "paymentMethod": attempt.payment_method,
                    "amountMinor": order.amount_minor,
                    "currency": order.currency,
                    "entitlementGranted": True,
                },
            )
        await self._grant(order=order, now=now)
        if self._referrals is not None:
            await self._referrals.record_milestone(
                invitee_user_id=order.user_id,
                milestone_code="FIRST_PURCHASE",
                payment_identity_hash=payment_identity_hash,
            )

    async def _grant(self, *, order: CommerceOrderRecord, now: datetime) -> None:
        product = order.product_snapshot
        benefits = dict(product["benefits"])
        entitlement = await self._session.scalar(
            select(EntitlementRecord)
            .where(EntitlementRecord.user_id == order.user_id)
            .with_for_update()
        )
        wallet = await self._session.scalar(
            select(WalletAccountRecord)
            .where(WalletAccountRecord.user_id == order.user_id)
            .with_for_update()
        )
        assert entitlement is not None and wallet is not None
        if product["productType"] == "ENERGY_PACK":
            amount = int(benefits["energyAmount"])
            before_balance = wallet.energy_balance
            wallet.energy_balance += amount
            wallet.resource_version += 1
            wallet.updated_at = now
            self._session.add(
                WalletLedgerRecord(
                    ledger_entry_id=f"wle_{uuid4().hex}",
                    user_id=order.user_id,
                    generation_id=None,
                    entry_type="CREDIT",
                    energy_delta=amount,
                    reserved_delta=0,
                    balance_after=wallet.energy_balance,
                    reserved_after=wallet.energy_reserved,
                    reason_code=f"ORDER_{order.order_id}",
                    created_at=now,
                )
            )
            self._session.add(
                CommerceGrantRecord(
                    grant_id=f"cgr_{uuid4().hex}",
                    order_id=order.order_id,
                    user_id=order.user_id,
                    product_type="ENERGY_PACK",
                    grant_snapshot={
                        "amount": amount,
                        "beforeBalance": before_balance,
                        "afterBalance": wallet.energy_balance,
                    },
                    recovery_status="AVAILABLE",
                    recovered_at=None,
                    created_at=now,
                )
            )
            return
        before = {
            "planCode": entitlement.plan_code,
            "planExpiresAt": (
                entitlement.plan_expires_at.isoformat()
                if entitlement.plan_expires_at is not None
                else None
            ),
            "textRemaining": entitlement.text_remaining,
            "visionRemaining": entitlement.vision_remaining,
            "allowedModelIds": list(entitlement.allowed_model_ids),
            "allowedStyleIds": list(entitlement.allowed_style_ids),
        }
        term_days = int(product["termDays"])
        start = max(now, entitlement.plan_expires_at or now)
        end = start + timedelta(days=term_days)
        entitlement.plan_code = str(product["productCode"])
        entitlement.plan_expires_at = end
        entitlement.text_remaining += int(benefits["textQuota"])
        entitlement.vision_remaining += int(benefits["visionQuota"])
        entitlement.allowed_model_ids = sorted(
            set(entitlement.allowed_model_ids) | set(benefits["allowedModelIds"])
        )
        entitlement.allowed_style_ids = sorted(
            set(entitlement.allowed_style_ids) | set(benefits["allowedStyleIds"])
        )
        entitlement.resource_version += 1
        entitlement.updated_at = now
        after = {
            "planCode": entitlement.plan_code,
            "planExpiresAt": end.isoformat(),
            "textRemaining": entitlement.text_remaining,
            "visionRemaining": entitlement.vision_remaining,
            "allowedModelIds": list(entitlement.allowed_model_ids),
            "allowedStyleIds": list(entitlement.allowed_style_ids),
        }
        self._session.add(
            SubscriptionRecord(
                subscription_id=f"sub_{uuid4().hex}",
                user_id=order.user_id,
                order_id=order.order_id,
                product_code=str(product["productCode"]),
                product_version_id=str(product["productVersionId"]),
                status="ACTIVE",
                renewal_type=str(product["renewalType"]),
                current_period_starts_at=start,
                current_period_ends_at=end,
                auto_renew=product["renewalType"] == "PROVIDER_MANDATE",
                cancel_at_period_end=False,
                resource_version=1,
                created_at=now,
                updated_at=now,
            )
        )
        self._session.add(
            CommerceGrantRecord(
                grant_id=f"cgr_{uuid4().hex}",
                order_id=order.order_id,
                user_id=order.user_id,
                product_type="PLAN",
                grant_snapshot={"before": before, "after": after},
                recovery_status="AVAILABLE",
                recovered_at=None,
                created_at=now,
            )
        )

    async def _owned_order_locked(self, user_id: str, order_id: str) -> CommerceOrderRecord:
        order = await self._session.scalar(
            select(CommerceOrderRecord)
            .where(CommerceOrderRecord.order_id == order_id, CommerceOrderRecord.user_id == user_id)
            .with_for_update()
        )
        if order is None:
            raise ApiError(status_code=404, code="ORDER_NOT_FOUND", message="Order was not found.")
        return order

    async def _latest_attempt(self, order_id: str) -> PaymentAttemptRecord:
        attempt = await self._session.scalar(
            select(PaymentAttemptRecord)
            .where(PaymentAttemptRecord.order_id == order_id)
            .order_by(PaymentAttemptRecord.created_at.desc())
            .limit(1)
        )
        if attempt is None:
            raise ApiError(
                status_code=409,
                code="PAYMENT_ATTEMPT_MISSING",
                message="Order has no payment attempt.",
            )
        return attempt

    async def _matching_attempt(self, order_id: str, method: str) -> PaymentAttemptRecord:
        attempt = await self._session.scalar(
            select(PaymentAttemptRecord)
            .where(
                PaymentAttemptRecord.order_id == order_id,
                PaymentAttemptRecord.payment_method == method,
            )
            .order_by(PaymentAttemptRecord.created_at.desc())
            .limit(1)
        )
        if attempt is None:
            raise ApiError(
                status_code=409,
                code="PAYMENT_CALLBACK_CONFLICT",
                message="Callback has no matching payment attempt.",
            )
        return attempt

    @staticmethod
    def _product_snapshot(product: ProductVersionRecord) -> dict[str, Any]:
        return {
            "productVersionId": product.product_version_id,
            "productCode": product.product_code,
            "version": product.version,
            "productType": product.product_type,
            "displayName": product.display_name,
            "currency": product.currency,
            "amountMinor": product.amount_minor,
            "renewalType": product.renewal_type,
            "termDays": product.term_days,
            "benefitWindowDays": product.benefit_window_days,
            "benefits": product.benefits,
        }

    @staticmethod
    def _assert_callback_facts(order: CommerceOrderRecord, callback: EpayVerifiedCallback) -> None:
        if (
            callback.amount_minor != order.amount_minor
            or callback.product_name != order.product_snapshot["displayName"]
        ):
            raise ApiError(
                status_code=409,
                code="PAYMENT_CALLBACK_CONFLICT",
                message="Callback conflicts with immutable order facts.",
            )

    @staticmethod
    def _fingerprint(value: dict[str, Any]) -> str:
        return sha256(dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    @staticmethod
    def _assert_version(order: CommerceOrderRecord, expected: int) -> None:
        if order.resource_version != expected:
            raise CommerceService._version_error(order.resource_version)

    @staticmethod
    def _version_error(current: int) -> ApiError:
        return ApiError(
            status_code=409,
            code="RESOURCE_VERSION_CONFLICT",
            message="Resource version does not match If-Match.",
            details={"currentResourceVersion": current},
        )
