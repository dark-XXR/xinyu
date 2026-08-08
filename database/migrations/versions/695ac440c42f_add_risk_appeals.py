"""add risk appeals

Revision ID: 695ac440c42f
Revises: f00bd6b3f309
Create Date: 2026-08-08 03:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "695ac440c42f"
down_revision: str | None = "f00bd6b3f309"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "risk_appeals",
        sa.Column("appeal_id", sa.String(length=64), nullable=False),
        sa.Column("risk_event_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("reason_code", sa.String(length=64), nullable=False),
        sa.Column("comment", sa.String(length=500), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("appeal_id"),
        sa.UniqueConstraint("user_id", "risk_event_id", name="uq_risk_appeal_user_event"),
    )
    op.create_index(
        op.f("ix_risk_appeals_risk_event_id"),
        "risk_appeals",
        ["risk_event_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_risk_appeals_user_id"), "risk_appeals", ["user_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_risk_appeals_user_id"), table_name="risk_appeals")
    op.drop_index(op.f("ix_risk_appeals_risk_event_id"), table_name="risk_appeals")
    op.drop_table("risk_appeals")
