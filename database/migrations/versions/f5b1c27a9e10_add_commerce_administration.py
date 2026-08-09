"""add commerce administration

Revision ID: f5b1c27a9e10
Revises: d7a91bc540ef
Create Date: 2026-08-09 23:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f5b1c27a9e10"
down_revision: str | None = "d7a91bc540ef"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 旧商品仍可售和回滚；新增字段让后续草稿具备创建者、审批者和乐观锁信息。
    op.add_column(
        "product_versions",
        sa.Column("resource_version", sa.BigInteger(), nullable=False, server_default="1"),
    )
    op.add_column(
        "product_versions",
        sa.Column(
            "created_by_admin_id",
            sa.String(64),
            nullable=False,
            server_default="SYSTEM_MIGRATION",
        ),
    )
    op.add_column("product_versions", sa.Column("published_by_admin_id", sa.String(64)))
    op.add_column("product_versions", sa.Column("published_at", sa.DateTime(timezone=True)))
    op.add_column(
        "product_versions",
        sa.Column("was_published", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("product_versions", sa.Column("updated_at", sa.DateTime(timezone=True)))
    op.execute(
        "UPDATE product_versions SET was_published = true, published_at = created_at, "
        "updated_at = created_at WHERE status = 'ACTIVE'"
    )
    op.execute("UPDATE product_versions SET updated_at = created_at WHERE updated_at IS NULL")
    op.alter_column("product_versions", "updated_at", nullable=False)
    op.create_unique_constraint(
        "uq_product_version_number", "product_versions", ["product_code", "version"]
    )
    op.add_column("refunds", sa.Column("reviewed_by_admin_id", sa.String(64)))
    op.add_column("refunds", sa.Column("executed_by_admin_id", sa.String(64)))

    op.create_table(
        "commerce_entitlement_grants",
        sa.Column("grant_id", sa.String(64), primary_key=True),
        sa.Column("order_id", sa.String(64), nullable=False, unique=True),
        sa.Column("user_id", sa.String(64), nullable=False),
        sa.Column("product_type", sa.String(32), nullable=False),
        sa.Column("grant_snapshot", sa.JSON(), nullable=False),
        sa.Column("recovery_status", sa.String(32), nullable=False),
        sa.Column("recovered_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["commerce_orders.order_id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_commerce_entitlement_grants_user_id", "commerce_entitlement_grants", ["user_id"]
    )
    op.create_table(
        "admin_commerce_audit_records",
        sa.Column("audit_id", sa.String(64), primary_key=True),
        sa.Column("resource_type", sa.String(32), nullable=False),
        sa.Column("resource_id", sa.String(64), nullable=False),
        sa.Column("admin_id", sa.String(64), nullable=False),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("audit_reason", sa.String(500), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_admin_commerce_audit_records_resource_type",
        "admin_commerce_audit_records",
        ["resource_type"],
    )
    op.create_index(
        "ix_admin_commerce_audit_records_resource_id",
        "admin_commerce_audit_records",
        ["resource_id"],
    )
    op.create_index(
        "ix_admin_commerce_audit_records_admin_id",
        "admin_commerce_audit_records",
        ["admin_id"],
    )
    op.create_table(
        "admin_entitlement_adjustments",
        sa.Column("adjustment_id", sa.String(64), primary_key=True),
        sa.Column("idempotency_key", sa.String(128), nullable=False, unique=True),
        sa.Column("request_fingerprint", sa.String(64), nullable=False),
        sa.Column("user_id", sa.String(64), nullable=False),
        sa.Column("unit", sa.String(32), nullable=False),
        sa.Column("delta", sa.BigInteger(), nullable=False),
        sa.Column("reason_code", sa.String(64), nullable=False),
        sa.Column("created_by_admin_id", sa.String(64), nullable=False),
        sa.Column("wallet_ledger_entry_id", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_admin_entitlement_adjustments_user_id",
        "admin_entitlement_adjustments",
        ["user_id"],
    )
    op.create_table(
        "payment_reconciliations",
        sa.Column("reconciliation_id", sa.String(64), primary_key=True),
        sa.Column("stale_before", sa.DateTime(timezone=True), nullable=False),
        sa.Column("max_orders", sa.Integer(), nullable=False),
        sa.Column("scanned_count", sa.Integer(), nullable=False),
        sa.Column("settled_count", sa.Integer(), nullable=False),
        sa.Column("recovered_count", sa.Integer(), nullable=False),
        sa.Column("conflict_count", sa.Integer(), nullable=False),
        sa.Column("created_by_admin_id", sa.String(64), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("payment_reconciliations")
    op.drop_table("admin_entitlement_adjustments")
    op.drop_table("admin_commerce_audit_records")
    op.drop_table("commerce_entitlement_grants")
    op.drop_column("refunds", "executed_by_admin_id")
    op.drop_column("refunds", "reviewed_by_admin_id")
    op.drop_constraint("uq_product_version_number", "product_versions", type_="unique")
    op.drop_column("product_versions", "updated_at")
    op.drop_column("product_versions", "was_published")
    op.drop_column("product_versions", "published_at")
    op.drop_column("product_versions", "published_by_admin_id")
    op.drop_column("product_versions", "created_by_admin_id")
    op.drop_column("product_versions", "resource_version")
