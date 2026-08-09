"""add published prompt rollout percentage

Revision ID: c1f5a803d2e4
Revises: a4c8e2f17b90
Create Date: 2026-08-09 19:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c1f5a803d2e4"
down_revision: str | None = "a4c8e2f17b90"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "ai_prompts",
        sa.Column(
            "published_rollout_percentage",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    op.drop_column("ai_prompts", "published_rollout_percentage")
