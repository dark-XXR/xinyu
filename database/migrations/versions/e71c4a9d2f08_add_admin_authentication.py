"""add administrator authentication

Revision ID: e71c4a9d2f08
Revises: d2b4a61f9c30
Create Date: 2026-08-09 09:00:00
"""

from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

revision: str = "e71c4a9d2f08"
down_revision: str | None = "d2b4a61f9c30"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "admin_users",
        sa.Column("admin_id", sa.String(length=64), nullable=False),
        sa.Column("login_name_normalized", sa.String(length=254), nullable=False),
        sa.Column("display_name", sa.String(length=128), nullable=False),
        sa.Column("password_hash", sa.String(length=512), nullable=False),
        sa.Column("mfa_secret_ciphertext", sa.Text(), nullable=False),
        sa.Column("last_totp_counter", sa.BigInteger(), nullable=True),
        sa.Column("account_status", sa.String(length=32), nullable=False),
        sa.Column("mfa_status", sa.String(length=32), nullable=False),
        sa.Column("roles", sa.JSON(), nullable=False),
        sa.Column("permissions", sa.JSON(), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resource_version", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("admin_id"),
        sa.UniqueConstraint("login_name_normalized"),
    )
    op.create_table(
        "admin_security_policy_versions",
        sa.Column("policy_id", sa.String(length=64), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("configuration", sa.JSON(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("policy_id"),
        sa.UniqueConstraint("version"),
    )
    op.create_index(
        op.f("ix_admin_security_policy_versions_status"),
        "admin_security_policy_versions",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_admin_security_policy_versions_published_at"),
        "admin_security_policy_versions",
        ["published_at"],
        unique=False,
    )
    op.create_table(
        "admin_mfa_challenges",
        sa.Column("challenge_id", sa.String(length=64), nullable=False),
        sa.Column("admin_id", sa.String(length=64), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["admin_id"], ["admin_users.admin_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("challenge_id"),
    )
    op.create_table(
        "admin_sessions",
        sa.Column("session_id", sa.String(length=64), nullable=False),
        sa.Column("admin_id", sa.String(length=64), nullable=False),
        sa.Column("token_family_id", sa.String(length=64), nullable=False),
        sa.Column("refresh_token_hash", sa.String(length=64), nullable=False),
        sa.Column("mfa_verified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rotated_to_session_id", sa.String(length=64), nullable=True),
        sa.Column("reuse_detected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["admin_id"], ["admin_users.admin_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("session_id"),
        sa.UniqueConstraint("refresh_token_hash"),
    )
    op.create_index(
        op.f("ix_admin_sessions_admin_id"), "admin_sessions", ["admin_id"], unique=False
    )
    op.create_index(
        op.f("ix_admin_sessions_token_family_id"),
        "admin_sessions",
        ["token_family_id"],
        unique=False,
    )

    published_at = datetime(2026, 8, 9, 9, 0, tzinfo=UTC)
    policies = sa.table(
        "admin_security_policy_versions",
        sa.column("policy_id", sa.String()),
        sa.column("version", sa.BigInteger()),
        sa.column("status", sa.String()),
        sa.column("configuration", sa.JSON()),
        sa.column("published_at", sa.DateTime(timezone=True)),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )
    op.bulk_insert(
        policies,
        [
            {
                "policy_id": "admin_policy_initial",
                "version": 1,
                "status": "PUBLISHED",
                "configuration": {
                    "mfa_challenge_ttl_seconds": 300,
                    "mfa_max_attempts": 5,
                    "access_token_ttl_seconds": 900,
                    "refresh_token_ttl_seconds": 28800,
                    "totp_period_seconds": 30,
                    "totp_digits": 6,
                    "totp_valid_window": 1,
                },
                "published_at": published_at,
                "created_at": published_at,
            }
        ],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_admin_sessions_token_family_id"), table_name="admin_sessions")
    op.drop_index(op.f("ix_admin_sessions_admin_id"), table_name="admin_sessions")
    op.drop_table("admin_sessions")
    op.drop_table("admin_mfa_challenges")
    op.drop_index(
        op.f("ix_admin_security_policy_versions_published_at"),
        table_name="admin_security_policy_versions",
    )
    op.drop_index(
        op.f("ix_admin_security_policy_versions_status"),
        table_name="admin_security_policy_versions",
    )
    op.drop_table("admin_security_policy_versions")
    op.drop_table("admin_users")
