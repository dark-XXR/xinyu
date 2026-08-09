"""add email authentication and published auth policy

Revision ID: d2b4a61f9c30
Revises: c9861b148a01
Create Date: 2026-08-08 18:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d2b4a61f9c30"
down_revision: str | None = "c9861b148a01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


INITIAL_AUTH_POLICY = {
    "primary_channel": "EMAIL",
    "fallback_channels": ["SMS"],
    "policy_version": 1,
    "channels": {
        "EMAIL": {
            "enabled": True,
            "challenge_ttl_seconds": 600,
            "resend_after_seconds": 60,
            "max_attempts": 5,
        },
        "SMS": {
            "enabled": True,
            "challenge_ttl_seconds": 300,
            "resend_after_seconds": 60,
            "max_attempts": 5,
        },
    },
}


def upgrade() -> None:
    op.alter_column(
        "users",
        "phone_e164",
        existing_type=sa.String(length=20),
        nullable=True,
    )
    op.add_column(
        "users",
        sa.Column("email_normalized", sa.String(length=254), nullable=True),
    )
    op.create_unique_constraint(
        "uq_users_email_normalized",
        "users",
        ["email_normalized"],
    )
    op.create_table(
        "email_challenges",
        sa.Column("challenge_id", sa.String(length=64), nullable=False),
        sa.Column("email_normalized", sa.String(length=254), nullable=False),
        sa.Column("purpose", sa.String(length=32), nullable=False),
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("challenge_id"),
    )
    op.create_index(
        op.f("ix_email_challenges_email_normalized"),
        "email_challenges",
        ["email_normalized"],
        unique=False,
    )
    op.add_column(
        "runtime_config_versions",
        sa.Column("auth_policy", sa.JSON(), nullable=True),
    )
    runtime_configs = sa.table(
        "runtime_config_versions",
        sa.column("auth_policy", sa.JSON()),
    )
    op.execute(sa.update(runtime_configs).values(auth_policy=INITIAL_AUTH_POLICY))
    op.alter_column("runtime_config_versions", "auth_policy", nullable=False)


def downgrade() -> None:
    op.drop_column("runtime_config_versions", "auth_policy")
    op.drop_index(
        op.f("ix_email_challenges_email_normalized"),
        table_name="email_challenges",
    )
    op.drop_table("email_challenges")
    op.drop_constraint("uq_users_email_normalized", "users", type_="unique")
    op.drop_column("users", "email_normalized")
    op.alter_column(
        "users",
        "phone_e164",
        existing_type=sa.String(length=20),
        nullable=False,
    )
