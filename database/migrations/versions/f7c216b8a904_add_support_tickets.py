"""新增客服工单数据结构。

Revision ID: f7c216b8a904
Revises: e31a6d8c4f20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f7c216b8a904"
down_revision: str | None = "e31a6d8c4f20"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "support_tickets",
        sa.Column("ticket_id", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.String(64), nullable=False),
        sa.Column("category", sa.String(32), nullable=False),
        sa.Column("subject", sa.String(160), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("priority", sa.String(16), nullable=False),
        sa.Column("assigned_admin_id", sa.String(64)),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resource_version", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], ondelete="CASCADE"),
    )
    for column in ("user_id", "category", "status", "priority", "assigned_admin_id"):
        op.create_index(f"ix_support_tickets_{column}", "support_tickets", [column])
    op.create_table(
        "support_ticket_messages",
        sa.Column("message_id", sa.String(64), primary_key=True),
        sa.Column("ticket_id", sa.String(64), nullable=False),
        sa.Column("sender_type", sa.String(16), nullable=False),
        sa.Column("sender_id", sa.String(64), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("internal", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["ticket_id"], ["support_tickets.ticket_id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_support_ticket_messages_ticket_id", "support_ticket_messages", ["ticket_id"]
    )
    for permission in ("SUPPORT_READ", "SUPPORT_WRITE"):
        op.execute(
            f"""UPDATE admin_users
            SET permissions = (permissions::jsonb || '["{permission}"]'::jsonb)::json
            WHERE roles::jsonb @> '[{{"role_code":"PLATFORM_OWNER"}}]'::jsonb
              AND NOT permissions::jsonb ? '{permission}'"""
        )


def downgrade() -> None:
    for permission in ("SUPPORT_READ", "SUPPORT_WRITE"):
        op.execute(
            f"""UPDATE admin_users SET permissions = (
              SELECT COALESCE(json_agg(value), '[]'::json)
              FROM json_array_elements_text(admin_users.permissions) AS value
              WHERE value != '{permission}')"""
        )
    op.drop_table("support_ticket_messages")
    op.drop_table("support_tickets")
