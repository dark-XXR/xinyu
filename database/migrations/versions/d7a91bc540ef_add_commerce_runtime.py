"""add commerce runtime

Revision ID: d7a91bc540ef
Revises: c1f5a803d2e4
Create Date: 2026-08-09 21:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d7a91bc540ef"
down_revision: str | None = "c1f5a803d2e4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 商品版本一经下单即复制到订单快照，后续调价不会改变历史交易事实。
    op.create_table(
        "product_versions",
        sa.Column("product_version_id", sa.String(64), primary_key=True),
        sa.Column("product_code", sa.String(64), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("product_type", sa.String(32), nullable=False),
        sa.Column("display_name", sa.String(128), nullable=False),
        sa.Column("description", sa.String(500)),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("amount_minor", sa.BigInteger(), nullable=False),
        sa.Column("region", sa.String(16), nullable=False),
        sa.Column("sales_channels", sa.JSON(), nullable=False),
        sa.Column("renewal_type", sa.String(32), nullable=False),
        sa.Column("term_days", sa.Integer()),
        sa.Column("benefit_window_days", sa.Integer(), nullable=False),
        sa.Column("benefits", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_product_versions_product_code", "product_versions", ["product_code"])
    op.create_index("ix_product_versions_region", "product_versions", ["region"])
    op.create_index("ix_product_versions_status", "product_versions", ["status"])
    op.create_table(
        "commerce_orders",
        sa.Column("order_id", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("product_snapshot", sa.JSON(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("amount_minor", sa.BigInteger(), nullable=False),
        sa.Column("paid_amount_minor", sa.BigInteger(), nullable=False),
        sa.Column("entitlement_granted", sa.Boolean(), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True)),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resource_version", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], ondelete="CASCADE"),
    )
    op.create_index("ix_commerce_orders_user_id", "commerce_orders", ["user_id"])
    op.create_index("ix_commerce_orders_status", "commerce_orders", ["status"])
    op.create_table(
        "payment_attempts",
        sa.Column("payment_attempt_id", sa.String(64), primary_key=True),
        sa.Column("order_id", sa.String(64), nullable=False),
        sa.Column("provider_id", sa.String(64), nullable=False),
        sa.Column("provider_resource_version", sa.BigInteger(), nullable=False),
        sa.Column("payment_method", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("amount_minor", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("checkout_action", sa.JSON()),
        sa.Column("provider_transaction_id", sa.String(128), unique=True),
        sa.Column("failure_code", sa.String(64)),
        sa.Column("last_synced_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["commerce_orders.order_id"], ondelete="CASCADE"),
    )
    op.create_index("ix_payment_attempts_order_id", "payment_attempts", ["order_id"])
    op.create_index("ix_payment_attempts_status", "payment_attempts", ["status"])
    op.create_table(
        "payment_events",
        sa.Column("payment_event_id", sa.String(64), primary_key=True),
        sa.Column("provider_id", sa.String(64), nullable=False),
        sa.Column("provider_transaction_id", sa.String(128), nullable=False, unique=True),
        sa.Column("order_id", sa.String(64), nullable=False),
        sa.Column("event_fingerprint", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_payment_events_provider_id", "payment_events", ["provider_id"])
    op.create_index("ix_payment_events_order_id", "payment_events", ["order_id"])
    op.create_table(
        "subscriptions",
        sa.Column("subscription_id", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.String(64), nullable=False),
        sa.Column("order_id", sa.String(64), nullable=False, unique=True),
        sa.Column("product_code", sa.String(64), nullable=False),
        sa.Column("product_version_id", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("renewal_type", sa.String(32), nullable=False),
        sa.Column("current_period_starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("current_period_ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("auto_renew", sa.Boolean(), nullable=False),
        sa.Column("cancel_at_period_end", sa.Boolean(), nullable=False),
        sa.Column("resource_version", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], ondelete="CASCADE"),
    )
    op.create_index("ix_subscriptions_user_id", "subscriptions", ["user_id"])
    op.create_index("ix_subscriptions_status", "subscriptions", ["status"])
    op.create_table(
        "refunds",
        sa.Column("refund_id", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.String(64), nullable=False),
        sa.Column("order_id", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("requested_amount_minor", sa.BigInteger(), nullable=False),
        sa.Column("refunded_amount_minor", sa.BigInteger(), nullable=False),
        sa.Column("reason_code", sa.String(64), nullable=False),
        sa.Column("comment", sa.Text()),
        sa.Column("entitlement_recovery_status", sa.String(32), nullable=False),
        sa.Column("rejection_reason_code", sa.String(64)),
        sa.Column("provider_refund_id", sa.String(128)),
        sa.Column("resource_version", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], ondelete="CASCADE"),
    )
    op.create_index("ix_refunds_user_id", "refunds", ["user_id"])
    op.create_index("ix_refunds_order_id", "refunds", ["order_id"])
    op.create_index("ix_refunds_status", "refunds", ["status"])


def downgrade() -> None:
    op.drop_table("refunds")
    op.drop_table("subscriptions")
    op.drop_table("payment_events")
    op.drop_table("payment_attempts")
    op.drop_table("commerce_orders")
    op.drop_table("product_versions")
