"""add published runtime configuration versions

Revision ID: c9861b148a01
Revises: 695ac440c42f
Create Date: 2026-08-08 16:00:00
"""

from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

revision: str = "c9861b148a01"
down_revision: str | None = "695ac440c42f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "runtime_config_versions",
        sa.Column("config_id", sa.String(length=64), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("models", sa.JSON(), nullable=False),
        sa.Column("styles", sa.JSON(), nullable=False),
        sa.Column("generation_policy", sa.JSON(), nullable=False),
        sa.Column("free_entitlement", sa.JSON(), nullable=False),
        sa.Column("feature_flags", sa.JSON(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("config_id"),
        sa.UniqueConstraint("version"),
    )
    op.create_index(
        op.f("ix_runtime_config_versions_published_at"),
        "runtime_config_versions",
        ["published_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_runtime_config_versions_status"),
        "runtime_config_versions",
        ["status"],
        unique=False,
    )

    published_at = datetime(2026, 8, 8, 16, 0, tzinfo=UTC)
    runtime_config = sa.table(
        "runtime_config_versions",
        sa.column("config_id", sa.String),
        sa.column("version", sa.BigInteger),
        sa.column("status", sa.String),
        sa.column("models", sa.JSON),
        sa.column("styles", sa.JSON),
        sa.column("generation_policy", sa.JSON),
        sa.column("free_entitlement", sa.JSON),
        sa.column("feature_flags", sa.JSON),
        sa.column("published_at", sa.DateTime(timezone=True)),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )
    op.bulk_insert(
        runtime_config,
        [
            {
                "config_id": "cfg_initial_published",
                "version": 1,
                "status": "PUBLISHED",
                "models": [
                    {
                        "model_id": "model_standard",
                        "display_name": "Standard",
                        "description": "Balanced response generation.",
                        "enabled": True,
                    }
                ],
                "styles": [
                    {"style_id": "warm", "display_name": "Warm", "enabled": True},
                    {
                        "style_id": "humorous",
                        "display_name": "Humorous",
                        "enabled": True,
                    },
                    {"style_id": "direct", "display_name": "Direct", "enabled": True},
                ],
                "generation_policy": {
                    "default_model_id": "model_standard",
                    "quote_ttl_seconds": 300,
                },
                "free_entitlement": {
                    "plan_code": "FREE",
                    "text_quota": 3,
                    "vision_quota": 0,
                    "allowed_model_ids": ["model_standard"],
                    "allowed_style_ids": ["warm", "humorous", "direct"],
                },
                "feature_flags": {"screenshotInput": False, "subscriptions": False},
                "published_at": published_at,
                "created_at": published_at,
            }
        ],
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_runtime_config_versions_status"), table_name="runtime_config_versions"
    )
    op.drop_index(
        op.f("ix_runtime_config_versions_published_at"),
        table_name="runtime_config_versions",
    )
    op.drop_table("runtime_config_versions")
