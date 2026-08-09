"""管理员商品、订单、退款、对账和权益调整业务服务。

商品使用不可变版本与创建/审批分离；退款先持久化执行状态再调用支付网关，避免进程中断后
重复退款。权益仅在能够证明未消费时自动回收，其余情况明确进入人工复核。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from json import dumps
from typing import Any, Generic, TypeVar
from uuid import uuid4

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from love_reply_api.application.commerce import CommerceService
from love_reply_api.application.errors import ApiError
from love_reply_api.application.provider_runtime import RegistryPaymentGateway
from love_reply_api.application.referrals import ReferralService
from love_reply_api.infrastructure.commerce_records import (
    AdminCommerceAuditRecord,
    CommerceGrantRecord,
    CommerceOrderRecord,
    EntitlementAdjustmentRecord,
    PaymentAttemptRecord,
    PaymentReconciliationRecord,
    ProductVersionRecord,
    RefundRecord,
    SubscriptionRecord,
)
from love_reply_api.infrastructure.generation_records import (
    EntitlementRecord,
    WalletAccountRecord,
    WalletLedgerRecord,
)

RecordT = TypeVar("RecordT")


@dataclass(frozen=True, slots=True)
class Page(Generic[RecordT]):
    items: list[RecordT]
    next_cursor: str | None
    has_more: bool


class CommerceAdminService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        gateway: RegistryPaymentGateway,
        referrals: ReferralService | None = None,
    ) -> None:
        self._session = session
        self._gateway = gateway
        self._commerce = CommerceService(session=session, gateway=gateway, referrals=referrals)

    async def list_products(self, *, cursor: str | None, limit: int) -> Page[ProductVersionRecord]:
        statement = select(ProductVersionRecord).order_by(ProductVersionRecord.product_version_id)
        if cursor is not None:
            statement = statement.where(ProductVersionRecord.product_version_id > cursor)
        rows = list((await self._session.scalars(statement.limit(limit + 1))).all())
        return self._page(rows, limit, lambda item: item.product_version_id)

    async def get_product(self, *, product_version_id: str) -> ProductVersionRecord:
        record = await self._session.get(ProductVersionRecord, product_version_id)
        if record is None:
            raise self._not_found("PRODUCT_NOT_FOUND", "Product version")
        return record

    async def create_product(
        self, *, admin_id: str, audit_reason: str, values: dict[str, Any]
    ) -> ProductVersionRecord:
        self._validate_product(values)
        product_code = str(values["product_code"])
        latest = await self._session.scalar(
            select(func.max(ProductVersionRecord.version)).where(
                ProductVersionRecord.product_code == product_code
            )
        )
        now = datetime.now(UTC)
        record = self._new_product(
            values=values,
            version=int(latest or 0) + 1,
            admin_id=admin_id,
            now=now,
        )
        self._session.add(record)
        self._audit(
            resource_type="PRODUCT",
            resource_id=record.product_version_id,
            admin_id=admin_id,
            action="PRODUCT_DRAFT_CREATED",
            audit_reason=audit_reason,
            metadata={"productCode": product_code, "version": record.version},
            now=now,
        )
        await self._session.commit()
        return record

    async def update_product(
        self,
        *,
        product_version_id: str,
        expected_version: int,
        admin_id: str,
        audit_reason: str,
        values: dict[str, Any],
    ) -> ProductVersionRecord:
        self._validate_product(values)
        source = await self._locked_product(product_version_id)
        self._assert_version(source.resource_version, expected_version)
        if source.status != "DRAFT":
            raise ApiError(
                status_code=409,
                code="PRODUCT_VERSION_IMMUTABLE",
                message="Published products are immutable.",
            )
        if source.product_code != values["product_code"]:
            raise ApiError(
                status_code=409,
                code="PRODUCT_CODE_IMMUTABLE",
                message="Product code cannot be changed.",
            )
        now = datetime.now(UTC)
        latest = await self._session.scalar(
            select(func.max(ProductVersionRecord.version)).where(
                ProductVersionRecord.product_code == source.product_code
            )
        )
        source.status = "RETIRED"
        source.resource_version += 1
        source.updated_at = now
        record = self._new_product(
            values=values,
            version=int(latest or source.version) + 1,
            admin_id=admin_id,
            now=now,
        )
        self._session.add(record)
        self._audit(
            resource_type="PRODUCT",
            resource_id=record.product_version_id,
            admin_id=admin_id,
            action="PRODUCT_DRAFT_REPLACED",
            audit_reason=audit_reason,
            metadata={"replacedProductVersionId": source.product_version_id},
            now=now,
        )
        await self._session.commit()
        return record

    async def publish_product(
        self,
        *,
        product_version_id: str,
        expected_version: int,
        admin_id: str,
        effective_at: datetime,
        expires_at: datetime | None,
        audit_reason: str,
    ) -> ProductVersionRecord:
        record = await self._locked_product(product_version_id)
        self._assert_version(record.resource_version, expected_version)
        if record.status != "DRAFT":
            raise ApiError(
                status_code=409,
                code="PRODUCT_NOT_DRAFT",
                message="Only a draft product can be published.",
            )
        if record.created_by_admin_id == admin_id:
            raise ApiError(
                status_code=409,
                code="PRODUCT_SELF_APPROVAL_FORBIDDEN",
                message="The draft creator cannot approve the same product version.",
            )
        if expires_at is not None and expires_at <= effective_at:
            raise ApiError(
                status_code=400,
                code="PRODUCT_WINDOW_INVALID",
                message="Product expiry must follow activation.",
            )
        now = datetime.now(UTC)
        await self._expire_active_versions(
            product_code=record.product_code,
            region=record.region,
            replacement_at=effective_at,
            excluded_id=record.product_version_id,
            now=now,
        )
        record.status = "ACTIVE"
        record.effective_at = effective_at
        record.expires_at = expires_at
        record.published_by_admin_id = admin_id
        record.published_at = now
        record.was_published = True
        record.resource_version += 1
        record.updated_at = now
        self._audit(
            resource_type="PRODUCT",
            resource_id=record.product_version_id,
            admin_id=admin_id,
            action="PRODUCT_PUBLISHED",
            audit_reason=audit_reason,
            metadata={"effectiveAt": effective_at.isoformat(), "version": record.version},
            now=now,
        )
        await self._session.commit()
        return record

    async def rollback_product(
        self,
        *,
        product_code: str,
        target_product_version_id: str,
        effective_at: datetime,
        admin_id: str,
        audit_reason: str,
    ) -> ProductVersionRecord:
        target = await self._locked_product(target_product_version_id)
        if target.product_code != product_code or not target.was_published:
            raise ApiError(
                status_code=409,
                code="PRODUCT_ROLLBACK_TARGET_INVALID",
                message="Rollback target was not published.",
            )
        latest = await self._session.scalar(
            select(func.max(ProductVersionRecord.version)).where(
                ProductVersionRecord.product_code == product_code
            )
        )
        now = datetime.now(UTC)
        await self._expire_active_versions(
            product_code=product_code,
            region=target.region,
            replacement_at=effective_at,
            excluded_id="",
            now=now,
        )
        values = self._product_values(target)
        record = self._new_product(
            values=values,
            version=int(latest or 0) + 1,
            admin_id=target.created_by_admin_id,
            now=now,
        )
        record.status = "ACTIVE"
        record.effective_at = effective_at
        record.published_by_admin_id = admin_id
        record.published_at = now
        record.was_published = True
        self._session.add(record)
        self._audit(
            resource_type="PRODUCT",
            resource_id=record.product_version_id,
            admin_id=admin_id,
            action="PRODUCT_ROLLED_BACK",
            audit_reason=audit_reason,
            metadata={"targetProductVersionId": target_product_version_id},
            now=now,
        )
        await self._session.commit()
        return record

    async def list_orders(self, *, cursor: str | None, limit: int) -> Page[CommerceOrderRecord]:
        statement = select(CommerceOrderRecord).order_by(CommerceOrderRecord.order_id)
        if cursor is not None:
            statement = statement.where(CommerceOrderRecord.order_id > cursor)
        rows = list((await self._session.scalars(statement.limit(limit + 1))).all())
        return self._page(rows, limit, lambda item: item.order_id)

    async def get_order(self, *, order_id: str) -> CommerceOrderRecord:
        record = await self._session.get(CommerceOrderRecord, order_id)
        if record is None:
            raise self._not_found("ORDER_NOT_FOUND", "Order")
        return record

    async def attempts(self, *, order_id: str) -> list[PaymentAttemptRecord]:
        return await self._commerce.attempts(order_id)

    async def list_refunds(self, *, cursor: str | None, limit: int) -> Page[RefundRecord]:
        statement = select(RefundRecord).order_by(RefundRecord.refund_id)
        if cursor is not None:
            statement = statement.where(RefundRecord.refund_id > cursor)
        rows = list((await self._session.scalars(statement.limit(limit + 1))).all())
        return self._page(rows, limit, lambda item: item.refund_id)

    async def get_refund(self, *, refund_id: str) -> RefundRecord:
        record = await self._session.get(RefundRecord, refund_id)
        if record is None:
            raise self._not_found("REFUND_NOT_FOUND", "Refund")
        return record

    async def decide_refund(
        self,
        *,
        refund_id: str,
        expected_version: int,
        admin_id: str,
        decision: str,
        rejection_reason_code: str | None,
        audit_reason: str,
    ) -> RefundRecord:
        record = await self._locked_refund(refund_id)
        self._assert_version(record.resource_version, expected_version)
        if record.status != "REVIEWING":
            raise ApiError(
                status_code=409,
                code="REFUND_NOT_REVIEWABLE",
                message="Refund is not awaiting review.",
            )
        if decision == "REJECT" and rejection_reason_code is None:
            raise ApiError(
                status_code=400,
                code="REJECTION_REASON_REQUIRED",
                message="A rejection reason is required.",
            )
        now = datetime.now(UTC)
        record.status = "APPROVED" if decision == "APPROVE" else "REJECTED"
        record.rejection_reason_code = rejection_reason_code if decision == "REJECT" else None
        record.reviewed_by_admin_id = admin_id
        record.resource_version += 1
        record.updated_at = now
        self._audit(
            resource_type="REFUND",
            resource_id=refund_id,
            admin_id=admin_id,
            action=f"REFUND_{record.status}",
            audit_reason=audit_reason,
            metadata={"orderId": record.order_id},
            now=now,
        )
        await self._session.commit()
        return record

    async def execute_refund(
        self,
        *,
        refund_id: str,
        expected_version: int,
        admin_id: str,
        audit_reason: str,
    ) -> RefundRecord:
        record = await self._locked_refund(refund_id)
        self._assert_version(record.resource_version, expected_version)
        if record.status == "SUCCEEDED":
            return record
        if record.status not in {"APPROVED", "FAILED"}:
            raise ApiError(
                status_code=409,
                code="REFUND_NOT_EXECUTABLE",
                message="Refund is not approved for execution.",
            )
        order = await self._locked_order(record.order_id)
        attempt = await self._successful_attempt(order.order_id)
        record.status = "PROCESSING"
        record.executed_by_admin_id = admin_id
        record.resource_version += 1
        record.updated_at = datetime.now(UTC)
        # 先提交 PROCESSING，若进程在网关成功后中断，后续人员能看到待人工核对状态，
        # 而不会因数据库回滚把同一退款当作从未执行再次发起。
        await self._session.commit()
        try:
            provider = await self._gateway.resolve_by_id(
                provider_id=attempt.provider_id, routing_key=record.refund_id
            )
            result = await self._gateway.transport.refund(
                configuration=provider.configuration,
                credentials=provider.credentials,
                order_id=order.order_id,
                provider_transaction_id=str(attempt.provider_transaction_id),
                amount_minor=record.requested_amount_minor,
                currency=record.currency,
            )
        except ApiError:
            failed = await self._locked_refund(refund_id)
            failed.status = "FAILED"
            failed.resource_version += 1
            failed.updated_at = datetime.now(UTC)
            await self._session.commit()
            raise
        record = await self._locked_refund(refund_id)
        order = await self._locked_order(record.order_id)
        now = datetime.now(UTC)
        record.status = "SUCCEEDED"
        record.refunded_amount_minor = record.requested_amount_minor
        record.provider_refund_id = result.provider_refund_id
        succeeded_total = await self._session.scalar(
            select(func.coalesce(func.sum(RefundRecord.refunded_amount_minor), 0)).where(
                RefundRecord.order_id == order.order_id,
                RefundRecord.status == "SUCCEEDED",
            )
        )
        record.entitlement_recovery_status = await self._recover_benefits(
            refund=record,
            order=order,
            total_refunded_minor=int(succeeded_total or 0),
            now=now,
        )
        record.resource_version += 1
        record.updated_at = now
        order.status = (
            "REFUNDED"
            if int(succeeded_total or 0) >= order.paid_amount_minor
            else "PARTIALLY_REFUNDED"
        )
        order.resource_version += 1
        order.updated_at = now
        self._audit(
            resource_type="REFUND",
            resource_id=refund_id,
            admin_id=admin_id,
            action="REFUND_EXECUTED",
            audit_reason=audit_reason,
            metadata={
                "providerRefundId": result.provider_refund_id,
                "entitlementRecoveryStatus": record.entitlement_recovery_status,
            },
            now=now,
        )
        await self._session.commit()
        return record

    async def run_reconciliation(
        self,
        *,
        admin_id: str,
        stale_before: datetime,
        max_orders: int,
        audit_reason: str,
    ) -> PaymentReconciliationRecord:
        started_at = datetime.now(UTC)
        candidates = list(
            (
                await self._session.scalars(
                    select(CommerceOrderRecord)
                    .outerjoin(
                        PaymentAttemptRecord,
                        PaymentAttemptRecord.order_id == CommerceOrderRecord.order_id,
                    )
                    .where(
                        or_(
                            (
                                CommerceOrderRecord.status.in_(["PAID", "PARTIALLY_REFUNDED"])
                                & (CommerceOrderRecord.entitlement_granted.is_(False))
                            ),
                            (
                                CommerceOrderRecord.status.in_(
                                    ["CREATED", "PENDING_PAYMENT", "FAILED"]
                                )
                                & (
                                    (PaymentAttemptRecord.last_synced_at.is_(None))
                                    | (PaymentAttemptRecord.last_synced_at < stale_before)
                                )
                            ),
                        )
                    )
                    .order_by(CommerceOrderRecord.updated_at)
                    .with_for_update(skip_locked=True, of=CommerceOrderRecord)
                    .limit(max_orders)
                )
            ).unique()
        )
        settled = recovered = conflicts = 0
        for order in candidates:
            try:
                async with self._session.begin_nested():
                    outcome = await self._commerce.reconcile_order(order=order)
            except ApiError:
                conflicts += 1
                continue
            settled += int(outcome == "SETTLED")
            recovered += int(outcome == "RECOVERED")
        completed_at = datetime.now(UTC)
        record = PaymentReconciliationRecord(
            reconciliation_id=f"rec_{uuid4().hex}",
            stale_before=stale_before,
            max_orders=max_orders,
            scanned_count=len(candidates),
            settled_count=settled,
            recovered_count=recovered,
            conflict_count=conflicts,
            created_by_admin_id=admin_id,
            started_at=started_at,
            completed_at=completed_at,
        )
        self._session.add(record)
        self._audit(
            resource_type="RECONCILIATION",
            resource_id=record.reconciliation_id,
            admin_id=admin_id,
            action="PAYMENT_RECONCILIATION_RUN",
            audit_reason=audit_reason,
            metadata={
                "scannedCount": len(candidates),
                "settledCount": settled,
                "recoveredCount": recovered,
                "conflictCount": conflicts,
            },
            now=completed_at,
        )
        await self._session.commit()
        return record

    async def adjust_entitlement(
        self,
        *,
        idempotency_key: str,
        admin_id: str,
        user_id: str,
        unit: str,
        delta: int,
        reason_code: str,
        audit_reason: str,
    ) -> EntitlementAdjustmentRecord:
        fingerprint = sha256(
            dumps(
                {"userId": user_id, "unit": unit, "delta": delta, "reasonCode": reason_code},
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()
        existing = await self._session.scalar(
            select(EntitlementAdjustmentRecord).where(
                EntitlementAdjustmentRecord.idempotency_key == idempotency_key
            )
        )
        if existing is not None:
            if existing.request_fingerprint != fingerprint:
                raise ApiError(
                    status_code=409,
                    code="IDEMPOTENCY_KEY_REUSED",
                    message="Idempotency key was used with different adjustment facts.",
                )
            return existing
        entitlement = await self._session.scalar(
            select(EntitlementRecord).where(EntitlementRecord.user_id == user_id).with_for_update()
        )
        wallet = await self._session.scalar(
            select(WalletAccountRecord)
            .where(WalletAccountRecord.user_id == user_id)
            .with_for_update()
        )
        if entitlement is None or wallet is None:
            raise self._not_found("USER_ENTITLEMENT_NOT_FOUND", "User entitlement")
        now = datetime.now(UTC)
        ledger_id: str | None = None
        if unit == "ENERGY":
            if wallet.energy_balance + delta < wallet.energy_reserved:
                raise ApiError(
                    status_code=409,
                    code="ADJUSTMENT_BALANCE_INVALID",
                    message="Adjustment would make available energy negative.",
                )
            wallet.energy_balance += delta
            wallet.resource_version += 1
            wallet.updated_at = now
            ledger_id = f"wle_{uuid4().hex}"
            self._session.add(
                WalletLedgerRecord(
                    ledger_entry_id=ledger_id,
                    user_id=user_id,
                    generation_id=None,
                    entry_type="ADJUSTMENT",
                    energy_delta=delta,
                    reserved_delta=0,
                    balance_after=wallet.energy_balance,
                    reserved_after=wallet.energy_reserved,
                    reason_code=reason_code,
                    created_at=now,
                )
            )
        elif unit == "TEXT_QUOTA":
            if entitlement.text_remaining + delta < entitlement.text_reserved:
                raise ApiError(
                    status_code=409,
                    code="ADJUSTMENT_BALANCE_INVALID",
                    message="Text quota cannot be negative.",
                )
            entitlement.text_remaining += delta
        elif unit == "VISION_QUOTA":
            if entitlement.vision_remaining + delta < 0:
                raise ApiError(
                    status_code=409,
                    code="ADJUSTMENT_BALANCE_INVALID",
                    message="Vision quota cannot be negative.",
                )
            entitlement.vision_remaining += delta
        elif unit == "PLAN_DAYS":
            base = entitlement.plan_expires_at or now
            adjusted = base + timedelta(days=delta)
            if adjusted < now:
                raise ApiError(
                    status_code=409,
                    code="ADJUSTMENT_BALANCE_INVALID",
                    message="Plan expiry cannot be past.",
                )
            entitlement.plan_expires_at = adjusted
        else:
            raise ApiError(
                status_code=400,
                code="ADJUSTMENT_UNIT_INVALID",
                message="Adjustment unit is unsupported.",
            )
        if unit != "ENERGY":
            entitlement.resource_version += 1
            entitlement.updated_at = now
        record = EntitlementAdjustmentRecord(
            adjustment_id=f"adj_{uuid4().hex}",
            idempotency_key=idempotency_key,
            request_fingerprint=fingerprint,
            user_id=user_id,
            unit=unit,
            delta=delta,
            reason_code=reason_code,
            created_by_admin_id=admin_id,
            wallet_ledger_entry_id=ledger_id,
            created_at=now,
        )
        self._session.add(record)
        self._audit(
            resource_type="ENTITLEMENT",
            resource_id=record.adjustment_id,
            admin_id=admin_id,
            action="ENTITLEMENT_ADJUSTED",
            audit_reason=audit_reason,
            metadata={"userId": user_id, "unit": unit, "delta": delta},
            now=now,
        )
        await self._session.commit()
        return record

    async def _recover_benefits(
        self,
        *,
        refund: RefundRecord,
        order: CommerceOrderRecord,
        total_refunded_minor: int,
        now: datetime,
    ) -> str:
        if total_refunded_minor < order.paid_amount_minor:
            return "MANUAL_REVIEW"
        grant = await self._session.scalar(
            select(CommerceGrantRecord)
            .where(CommerceGrantRecord.order_id == order.order_id)
            .with_for_update()
        )
        if grant is None or grant.recovery_status != "AVAILABLE":
            return "MANUAL_REVIEW"
        if grant.product_type == "ENERGY_PACK":
            wallet = await self._session.scalar(
                select(WalletAccountRecord)
                .where(WalletAccountRecord.user_id == order.user_id)
                .with_for_update()
            )
            assert wallet is not None
            amount = int(grant.grant_snapshot["amount"])
            if wallet.energy_balance - amount < wallet.energy_reserved:
                return "MANUAL_REVIEW"
            wallet.energy_balance -= amount
            wallet.resource_version += 1
            wallet.updated_at = now
            self._session.add(
                WalletLedgerRecord(
                    ledger_entry_id=f"wle_{uuid4().hex}",
                    user_id=order.user_id,
                    generation_id=None,
                    entry_type="REFUND",
                    energy_delta=-amount,
                    reserved_delta=0,
                    balance_after=wallet.energy_balance,
                    reserved_after=wallet.energy_reserved,
                    reason_code=f"REFUND_{refund.refund_id}",
                    created_at=now,
                )
            )
        else:
            entitlement = await self._session.scalar(
                select(EntitlementRecord)
                .where(EntitlementRecord.user_id == order.user_id)
                .with_for_update()
            )
            subscription = await self._session.scalar(
                select(SubscriptionRecord)
                .where(SubscriptionRecord.order_id == order.order_id)
                .with_for_update()
            )
            assert entitlement is not None
            after = dict(grant.grant_snapshot["after"])
            # 只有当前权益仍与发放后快照完全一致，才能证明其间没有消费、续费或人工调整。
            current = {
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
            if current != after or subscription is None or subscription.status != "ACTIVE":
                return "MANUAL_REVIEW"
            before = dict(grant.grant_snapshot["before"])
            entitlement.plan_code = str(before["planCode"])
            expiry = before["planExpiresAt"]
            entitlement.plan_expires_at = datetime.fromisoformat(expiry) if expiry else None
            entitlement.text_remaining = int(before["textRemaining"])
            entitlement.vision_remaining = int(before["visionRemaining"])
            entitlement.allowed_model_ids = list(before["allowedModelIds"])
            entitlement.allowed_style_ids = list(before["allowedStyleIds"])
            entitlement.resource_version += 1
            entitlement.updated_at = now
            subscription.status = "CANCELLED"
            subscription.auto_renew = False
            subscription.cancel_at_period_end = False
            subscription.resource_version += 1
            subscription.updated_at = now
        grant.recovery_status = "RECOVERED"
        grant.recovered_at = now
        return "COMPLETED"

    async def _expire_active_versions(
        self,
        *,
        product_code: str,
        region: str,
        replacement_at: datetime,
        excluded_id: str,
        now: datetime,
    ) -> None:
        rows = list(
            (
                await self._session.scalars(
                    select(ProductVersionRecord)
                    .where(
                        ProductVersionRecord.product_code == product_code,
                        ProductVersionRecord.region == region,
                        ProductVersionRecord.status == "ACTIVE",
                        ProductVersionRecord.product_version_id != excluded_id,
                    )
                    .with_for_update()
                )
            ).all()
        )
        for row in rows:
            if row.expires_at is None or row.expires_at > replacement_at:
                row.expires_at = replacement_at
            if replacement_at <= now:
                row.status = "RETIRED"
            row.resource_version += 1
            row.updated_at = now

    @staticmethod
    def _new_product(
        *, values: dict[str, Any], version: int, admin_id: str, now: datetime
    ) -> ProductVersionRecord:
        return ProductVersionRecord(
            product_version_id=f"prd_{uuid4().hex}",
            version=version,
            status="DRAFT",
            effective_at=now,
            expires_at=None,
            resource_version=1,
            created_by_admin_id=admin_id,
            published_by_admin_id=None,
            published_at=None,
            was_published=False,
            created_at=now,
            updated_at=now,
            **values,
        )

    @staticmethod
    def _product_values(record: ProductVersionRecord) -> dict[str, Any]:
        return {
            "product_code": record.product_code,
            "product_type": record.product_type,
            "display_name": record.display_name,
            "description": record.description,
            "currency": record.currency,
            "amount_minor": record.amount_minor,
            "region": record.region,
            "sales_channels": list(record.sales_channels),
            "renewal_type": record.renewal_type,
            "term_days": record.term_days,
            "benefit_window_days": record.benefit_window_days,
            "benefits": dict(record.benefits),
        }

    @staticmethod
    def _validate_product(values: dict[str, Any]) -> None:
        product_type = values["product_type"]
        benefits = dict(values["benefits"])
        if product_type == "PLAN" and values.get("term_days") is None:
            raise ApiError(
                status_code=400,
                code="PRODUCT_TERM_REQUIRED",
                message="Plan term days are required.",
            )
        if product_type == "ENERGY_PACK":
            if values.get("renewal_type") != "NONE" or int(benefits["energyAmount"]) < 1:
                raise ApiError(
                    status_code=400,
                    code="PRODUCT_BENEFITS_INVALID",
                    message="Energy packs require a positive energy amount and no renewal mandate.",
                )

    async def _locked_product(self, product_version_id: str) -> ProductVersionRecord:
        record = await self._session.scalar(
            select(ProductVersionRecord)
            .where(ProductVersionRecord.product_version_id == product_version_id)
            .with_for_update()
        )
        if record is None:
            raise self._not_found("PRODUCT_NOT_FOUND", "Product version")
        return record

    async def _locked_refund(self, refund_id: str) -> RefundRecord:
        record = await self._session.scalar(
            select(RefundRecord).where(RefundRecord.refund_id == refund_id).with_for_update()
        )
        if record is None:
            raise self._not_found("REFUND_NOT_FOUND", "Refund")
        return record

    async def _locked_order(self, order_id: str) -> CommerceOrderRecord:
        record = await self._session.scalar(
            select(CommerceOrderRecord)
            .where(CommerceOrderRecord.order_id == order_id)
            .with_for_update()
        )
        if record is None:
            raise self._not_found("ORDER_NOT_FOUND", "Order")
        return record

    async def _successful_attempt(self, order_id: str) -> PaymentAttemptRecord:
        record = await self._session.scalar(
            select(PaymentAttemptRecord)
            .where(
                PaymentAttemptRecord.order_id == order_id,
                PaymentAttemptRecord.status == "SUCCEEDED",
                PaymentAttemptRecord.provider_transaction_id.is_not(None),
            )
            .order_by(PaymentAttemptRecord.updated_at.desc())
        )
        if record is None:
            raise ApiError(
                status_code=409,
                code="PAYMENT_FACTS_MISSING",
                message="Successful payment facts are missing.",
            )
        return record

    def _audit(
        self,
        *,
        resource_type: str,
        resource_id: str,
        admin_id: str,
        action: str,
        audit_reason: str,
        metadata: dict[str, Any],
        now: datetime,
    ) -> None:
        self._session.add(
            AdminCommerceAuditRecord(
                audit_id=f"caud_{uuid4().hex}",
                resource_type=resource_type,
                resource_id=resource_id,
                admin_id=admin_id,
                action=action,
                audit_reason=audit_reason,
                metadata_json=metadata,
                created_at=now,
            )
        )

    @staticmethod
    def _assert_version(current: int, expected: int) -> None:
        if current != expected:
            raise ApiError(
                status_code=409,
                code="RESOURCE_VERSION_CONFLICT",
                message="Resource version does not match.",
                details={"currentVersion": current},
            )

    @staticmethod
    def _page(rows: list[RecordT], limit: int, key: Any) -> Page[RecordT]:
        visible = rows[:limit]
        has_more = len(rows) > limit
        return Page(
            items=visible,
            next_cursor=key(visible[-1]) if has_more and visible else None,
            has_more=has_more,
        )

    @staticmethod
    def _not_found(code: str, label: str) -> ApiError:
        return ApiError(status_code=404, code=code, message=f"{label} was not found.")
