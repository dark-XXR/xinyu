"""商品、订单、支付、订阅和退款的数据表映射。"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from love_reply_api.infrastructure.database import Base


class ProductVersionRecord(Base):
    __tablename__ = "product_versions"
    __table_args__ = (
        UniqueConstraint("product_code", "version", name="uq_product_version_number"),
    )

    product_version_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    product_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    product_type: Mapped[str] = mapped_column(String(32), nullable=False)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500))
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    region: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    sales_channels: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    renewal_type: Mapped[str] = mapped_column(String(32), nullable=False)
    term_days: Mapped[int | None] = mapped_column(Integer)
    benefit_window_days: Mapped[int] = mapped_column(Integer, nullable=False)
    benefits: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    effective_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resource_version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_by_admin_id: Mapped[str] = mapped_column(
        String(64), nullable=False, default="SYSTEM_MIGRATION"
    )
    published_by_admin_id: Mapped[str | None] = mapped_column(String(64))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    was_published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )


class CommerceOrderRecord(Base):
    __tablename__ = "commerce_orders"

    order_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    product_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    paid_amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    entitlement_granted: Mapped[bool] = mapped_column(Boolean, nullable=False)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resource_version: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PaymentAttemptRecord(Base):
    __tablename__ = "payment_attempts"

    payment_attempt_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    order_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("commerce_orders.order_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider_id: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_resource_version: Mapped[int] = mapped_column(BigInteger, nullable=False)
    payment_method: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    checkout_action: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    provider_transaction_id: Mapped[str | None] = mapped_column(String(128), unique=True)
    failure_code: Mapped[str | None] = mapped_column(String(64))
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PaymentEventRecord(Base):
    __tablename__ = "payment_events"

    payment_event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    provider_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    provider_transaction_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    order_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    event_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SubscriptionRecord(Base):
    __tablename__ = "subscriptions"

    subscription_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True
    )
    order_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    product_code: Mapped[str] = mapped_column(String(64), nullable=False)
    product_version_id: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    renewal_type: Mapped[str] = mapped_column(String(32), nullable=False)
    current_period_starts_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    current_period_ends_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    auto_renew: Mapped[bool] = mapped_column(Boolean, nullable=False)
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, nullable=False)
    resource_version: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RefundRecord(Base):
    __tablename__ = "refunds"

    refund_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True
    )
    order_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    requested_amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    refunded_amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    reason_code: Mapped[str] = mapped_column(String(64), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text)
    entitlement_recovery_status: Mapped[str] = mapped_column(String(32), nullable=False)
    rejection_reason_code: Mapped[str | None] = mapped_column(String(64))
    provider_refund_id: Mapped[str | None] = mapped_column(String(128))
    reviewed_by_admin_id: Mapped[str | None] = mapped_column(String(64))
    executed_by_admin_id: Mapped[str | None] = mapped_column(String(64))
    resource_version: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CommerceGrantRecord(Base):
    """记录订单发放前后快照，退款时只回收能够证明尚未消费的权益。"""

    __tablename__ = "commerce_entitlement_grants"

    grant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    order_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("commerce_orders.order_id", ondelete="CASCADE"), unique=True
    )
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    product_type: Mapped[str] = mapped_column(String(32), nullable=False)
    grant_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    recovery_status: Mapped[str] = mapped_column(String(32), nullable=False)
    recovered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AdminCommerceAuditRecord(Base):
    """商品、退款、对账与人工权益变更的统一不可变审计记录。"""

    __tablename__ = "admin_commerce_audit_records"

    audit_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    resource_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    resource_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    admin_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    audit_reason: Mapped[str] = mapped_column(String(500), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class EntitlementAdjustmentRecord(Base):
    __tablename__ = "admin_entitlement_adjustments"

    adjustment_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    delta: Mapped[int] = mapped_column(BigInteger, nullable=False)
    reason_code: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by_admin_id: Mapped[str] = mapped_column(String(64), nullable=False)
    wallet_ledger_entry_id: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PaymentReconciliationRecord(Base):
    __tablename__ = "payment_reconciliations"

    reconciliation_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    stale_before: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    max_orders: Mapped[int] = mapped_column(Integer, nullable=False)
    scanned_count: Mapped[int] = mapped_column(Integer, nullable=False)
    settled_count: Mapped[int] = mapped_column(Integer, nullable=False)
    recovered_count: Mapped[int] = mapped_column(Integer, nullable=False)
    conflict_count: Mapped[int] = mapped_column(Integer, nullable=False)
    created_by_admin_id: Mapped[str] = mapped_column(String(64), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
