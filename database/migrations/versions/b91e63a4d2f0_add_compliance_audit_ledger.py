"""add compliance audit ledger

Revision ID: b91e63a4d2f0
Revises: a6ce441f72d8
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b91e63a4d2f0"
down_revision: str | None = "a6ce441f72d8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "compliance_audit_events",
        sa.Column("event_id", sa.String(64), primary_key=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("category", sa.String(32), nullable=False),
        sa.Column("event_type", sa.String(96), nullable=False),
        sa.Column("outcome", sa.String(24), nullable=False),
        sa.Column("severity", sa.String(24), nullable=False),
        sa.Column("actor_type", sa.String(24), nullable=False),
        sa.Column("actor_id", sa.String(128)),
        sa.Column("user_id", sa.String(64)),
        sa.Column("admin_id", sa.String(64)),
        sa.Column("session_id", sa.String(64)),
        sa.Column("request_id", sa.String(128)),
        sa.Column("client_platform", sa.String(32)),
        sa.Column("client_version", sa.String(64)),
        sa.Column("source_ip_hash", sa.String(64)),
        sa.Column("resource_type", sa.String(48)),
        sa.Column("resource_id", sa.String(128)),
        sa.Column("order_id", sa.String(64)),
        sa.Column("generation_id", sa.String(64)),
        sa.Column("provider_id", sa.String(64)),
        sa.Column("summary", sa.String(500), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("contains_sensitive_content", sa.Boolean(), nullable=False),
        sa.Column("sensitive_payload_ciphertext", sa.Text()),
        sa.Column("sensitive_payload_digest", sa.String(64)),
        sa.Column("retention_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("legal_hold", sa.Boolean(), nullable=False),
        sa.Column("previous_event_hash", sa.String(64), nullable=False),
        sa.Column("event_hash", sa.String(64), nullable=False, unique=True),
    )
    for column in (
        "occurred_at",
        "category",
        "event_type",
        "outcome",
        "severity",
        "actor_type",
        "actor_id",
        "user_id",
        "admin_id",
        "session_id",
        "request_id",
        "source_ip_hash",
        "resource_type",
        "resource_id",
        "order_id",
        "generation_id",
        "provider_id",
        "retention_until",
        "legal_hold",
    ):
        op.create_index(f"ix_compliance_audit_events_{column}", "compliance_audit_events", [column])

    op.create_table(
        "compliance_audit_exports",
        sa.Column("export_id", sa.String(64), primary_key=True),
        sa.Column("created_by_admin_id", sa.String(64), nullable=False),
        sa.Column("audit_reason", sa.String(500), nullable=False),
        sa.Column("filters_json", sa.JSON(), nullable=False),
        sa.Column("include_sensitive_content", sa.Boolean(), nullable=False),
        sa.Column("event_count", sa.BigInteger(), nullable=False),
        sa.Column("bundle_ciphertext", sa.Text(), nullable=False),
        sa.Column("bundle_digest", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_compliance_audit_exports_created_by_admin_id",
        "compliance_audit_exports",
        ["created_by_admin_id"],
    )
    op.create_index(
        "ix_compliance_audit_exports_expires_at", "compliance_audit_exports", ["expires_at"]
    )
    # 仅平台所有者继承高敏正文、导出和法务冻结能力，普通审计员仍只有摘要读取权限。
    op.execute(
        """
        UPDATE admin_users
        SET permissions = (permissions::jsonb ||
          '["AUDIT_SENSITIVE_CONTENT_READ","AUDIT_EXPORT","AUDIT_LEGAL_HOLD"]'::jsonb)::json
        WHERE roles::jsonb @> '[{"role_code":"PLATFORM_OWNER"}]'::jsonb
          AND permissions::jsonb ? 'AUDIT_LOG_READ'
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE admin_users
        SET permissions = (
          SELECT COALESCE(json_agg(value), '[]'::json)
          FROM json_array_elements_text(admin_users.permissions) AS value
          WHERE value NOT IN (
            'AUDIT_SENSITIVE_CONTENT_READ', 'AUDIT_EXPORT', 'AUDIT_LEGAL_HOLD'
          )
        )
        """
    )
    op.drop_table("compliance_audit_exports")
    op.drop_table("compliance_audit_events")
