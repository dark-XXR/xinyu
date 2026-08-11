"""新增核心平台运营后台数据结构。

Revision ID: e31a6d8c4f20
Revises: c42f19e7ab31
"""

from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

revision: str = "e31a6d8c4f20"
down_revision: str | None = "c42f19e7ab31"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PERMISSIONS = (
    "USER_READ",
    "USER_STATUS_WRITE",
    "SYSTEM_CONFIG_READ",
    "SYSTEM_CONFIG_WRITE",
    "SYSTEM_CONFIG_PUBLISH",
    "NOTICE_READ",
    "NOTICE_WRITE",
    "NOTICE_PUBLISH",
    "NOTICE_REVOKE",
)


def upgrade() -> None:
    op.create_table(
        "system_config_versions",
        sa.Column("config_id", sa.String(64), primary_key=True),
        sa.Column("version", sa.BigInteger(), nullable=False, unique=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("configuration", sa.JSON(), nullable=False),
        sa.Column("resource_version", sa.BigInteger(), nullable=False),
        sa.Column("created_by_admin_id", sa.String(64), nullable=False),
        sa.Column("published_by_admin_id", sa.String(64)),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_system_config_versions_status", "system_config_versions", ["status"])
    op.create_index(
        "ix_system_config_versions_published_at", "system_config_versions", ["published_at"]
    )
    op.create_table(
        "notice_versions",
        sa.Column("notice_version_id", sa.String(64), primary_key=True),
        sa.Column("notice_id", sa.String(64), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("notice_type", sa.String(32), nullable=False),
        sa.Column("target_platforms", sa.JSON(), nullable=False),
        sa.Column("target_locales", sa.JSON(), nullable=False),
        sa.Column("min_client_version", sa.String(64)),
        sa.Column("max_client_version", sa.String(64)),
        sa.Column("display_frequency", sa.String(32), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True)),
        sa.Column("resource_version", sa.BigInteger(), nullable=False),
        sa.Column("created_by_admin_id", sa.String(64), nullable=False),
        sa.Column("published_by_admin_id", sa.String(64)),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("notice_id", "version", name="uq_notice_versions_notice_version"),
    )
    for column in ("notice_id", "status", "starts_at", "ends_at", "published_at"):
        op.create_index(f"ix_notice_versions_{column}", "notice_versions", [column])
    op.create_table(
        "admin_platform_audits",
        sa.Column("audit_id", sa.String(64), primary_key=True),
        sa.Column("resource_type", sa.String(48), nullable=False),
        sa.Column("resource_id", sa.String(128), nullable=False),
        sa.Column("admin_id", sa.String(64), nullable=False),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("audit_reason", sa.String(500), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    for column in ("resource_type", "resource_id", "admin_id", "action", "created_at"):
        op.create_index(f"ix_admin_platform_audits_{column}", "admin_platform_audits", [column])

    now = datetime.now(UTC)
    table = sa.table(
        "system_config_versions",
        sa.column("config_id", sa.String),
        sa.column("version", sa.BigInteger),
        sa.column("status", sa.String),
        sa.column("configuration", sa.JSON),
        sa.column("resource_version", sa.BigInteger),
        sa.column("created_by_admin_id", sa.String),
        sa.column("published_by_admin_id", sa.String),
        sa.column("published_at", sa.DateTime(timezone=True)),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    # 初始名称只承担迁移后的安全默认值，管理员可以在设置页创建草稿并发布覆盖。
    op.bulk_insert(
        table,
        [
            {
                "config_id": "scfg_initial",
                "version": 1,
                "status": "PUBLISHED",
                "configuration": {
                    "websiteName": "心语",
                    "appName": "心语",
                    "companyName": "待配置运营主体",
                    "logoUrl": None,
                    "customerServiceEmail": "support@example.com",
                    "privacyEmail": "privacy@example.com",
                    "defaultLocale": "zh-CN",
                    "officialWebsiteUrl": None,
                    "filingInformation": None,
                    "maintenanceMode": False,
                    "maintenanceMessage": None,
                },
                "resource_version": 1,
                "created_by_admin_id": "SYSTEM_MIGRATION",
                "published_by_admin_id": None,
                "published_at": now,
                "created_at": now,
                "updated_at": now,
            }
        ],
    )
    for permission in PERMISSIONS:
        op.execute(
            f"""
            UPDATE admin_users
            SET permissions = (permissions::jsonb || '["{permission}"]'::jsonb)::json
            WHERE roles::jsonb @> '[{{"role_code":"PLATFORM_OWNER"}}]'::jsonb
              AND NOT permissions::jsonb ? '{permission}'
            """
        )


def downgrade() -> None:
    for permission in PERMISSIONS:
        op.execute(
            f"""
            UPDATE admin_users
            SET permissions = (
              SELECT COALESCE(json_agg(value), '[]'::json)
              FROM json_array_elements_text(admin_users.permissions) AS value
              WHERE value != '{permission}'
            )
            """
        )
    op.drop_table("admin_platform_audits")
    op.drop_table("notice_versions")
    op.drop_table("system_config_versions")
