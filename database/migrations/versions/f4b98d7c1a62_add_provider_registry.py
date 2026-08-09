"""add encrypted provider registry

Revision ID: f4b98d7c1a62
Revises: e71c4a9d2f08
Create Date: 2026-08-09 11:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f4b98d7c1a62"
down_revision: str | None = "e71c4a9d2f08"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "providers",
        sa.Column("provider_id", sa.String(length=64), nullable=False),
        sa.Column("provider_name", sa.String(length=128), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("configuration", sa.JSON(), nullable=False),
        sa.Column("data_region", sa.String(length=64), nullable=True),
        sa.Column("retention_statement", sa.String(length=500), nullable=True),
        sa.Column("retry_limit", sa.Integer(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("rollout_percentage", sa.Integer(), nullable=False),
        sa.Column("active_credential_version_id", sa.String(length=64), nullable=True),
        sa.Column("published_resource_version", sa.BigInteger(), nullable=True),
        sa.Column("last_health_status", sa.String(length=32), nullable=True),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resource_version", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("provider_id"),
    )
    op.create_index(op.f("ix_providers_kind"), "providers", ["kind"], unique=False)
    op.create_index(op.f("ix_providers_status"), "providers", ["status"], unique=False)
    op.create_table(
        "provider_credential_versions",
        sa.Column("credential_version_id", sa.String(length=64), nullable=False),
        sa.Column("provider_id", sa.String(length=64), nullable=False),
        sa.Column("encrypted_payload", sa.Text(), nullable=False),
        sa.Column("fingerprint", sa.String(length=128), nullable=False),
        sa.Column("rotated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by_admin_id", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["provider_id"], ["providers.provider_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("credential_version_id"),
    )
    op.create_index(
        op.f("ix_provider_credential_versions_provider_id"),
        "provider_credential_versions",
        ["provider_id"],
        unique=False,
    )
    op.create_table(
        "provider_versions",
        sa.Column("provider_version_id", sa.String(length=96), nullable=False),
        sa.Column("provider_id", sa.String(length=64), nullable=False),
        sa.Column("resource_version", sa.BigInteger(), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("was_published", sa.Boolean(), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("created_by_admin_id", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["provider_id"], ["providers.provider_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("provider_version_id"),
        sa.UniqueConstraint("provider_id", "resource_version", name="uq_provider_version_number"),
    )
    op.create_index(
        op.f("ix_provider_versions_provider_id"),
        "provider_versions",
        ["provider_id"],
        unique=False,
    )
    op.create_table(
        "provider_health_checks",
        sa.Column("health_check_id", sa.String(length=64), nullable=False),
        sa.Column("provider_id", sa.String(length=64), nullable=False),
        sa.Column("provider_resource_version", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("redacted_summary", sa.String(length=500), nullable=False),
        sa.Column("provider_request_id", sa.String(length=128), nullable=True),
        sa.Column("created_by_admin_id", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["provider_id"], ["providers.provider_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("health_check_id"),
    )
    op.create_index(
        op.f("ix_provider_health_checks_provider_id"),
        "provider_health_checks",
        ["provider_id"],
        unique=False,
    )
    op.create_table(
        "provider_audit_records",
        sa.Column("audit_id", sa.String(length=64), nullable=False),
        sa.Column("provider_id", sa.String(length=64), nullable=False),
        sa.Column("admin_id", sa.String(length=64), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("audit_reason", sa.String(length=500), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["provider_id"], ["providers.provider_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("audit_id"),
    )
    op.create_index(
        op.f("ix_provider_audit_records_provider_id"),
        "provider_audit_records",
        ["provider_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_provider_audit_records_admin_id"),
        "provider_audit_records",
        ["admin_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_provider_audit_records_admin_id"), table_name="provider_audit_records"
    )
    op.drop_index(
        op.f("ix_provider_audit_records_provider_id"), table_name="provider_audit_records"
    )
    op.drop_table("provider_audit_records")
    op.drop_index(
        op.f("ix_provider_health_checks_provider_id"), table_name="provider_health_checks"
    )
    op.drop_table("provider_health_checks")
    op.drop_index(op.f("ix_provider_versions_provider_id"), table_name="provider_versions")
    op.drop_table("provider_versions")
    op.drop_index(
        op.f("ix_provider_credential_versions_provider_id"),
        table_name="provider_credential_versions",
    )
    op.drop_table("provider_credential_versions")
    op.drop_index(op.f("ix_providers_status"), table_name="providers")
    op.drop_index(op.f("ix_providers_kind"), table_name="providers")
    op.drop_table("providers")
