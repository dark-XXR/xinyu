"""add provider runtime publication and auth templates

Revision ID: b7e3c19a5d40
Revises: f4b98d7c1a62
Create Date: 2026-08-09 13:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b7e3c19a5d40"
down_revision: str | None = "f4b98d7c1a62"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


INITIAL_AUTH_TEMPLATES = {
    "email_login": {
        "default_locale": "en",
        "locales": {
            "en": {
                "subject": "Your Love Reply login code",
                "text_template": (
                    "Your verification code is {code}. "
                    "If you did not request it, ignore this message."
                ),
                "html_template": None,
            }
        },
    }
}


def upgrade() -> None:
    op.add_column(
        "providers",
        sa.Column(
            "published_rollout_percentage",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.alter_column("providers", "published_rollout_percentage", server_default=None)
    op.add_column(
        "providers",
        sa.Column("published_effective_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "runtime_config_versions",
        sa.Column("auth_templates", sa.JSON(), nullable=True),
    )
    runtime_configs = sa.table(
        "runtime_config_versions",
        sa.column("auth_templates", sa.JSON()),
    )
    op.execute(sa.update(runtime_configs).values(auth_templates=INITIAL_AUTH_TEMPLATES))
    op.alter_column("runtime_config_versions", "auth_templates", nullable=False)


def downgrade() -> None:
    op.drop_column("runtime_config_versions", "auth_templates")
    op.drop_column("providers", "published_effective_at")
    op.drop_column("providers", "published_rollout_percentage")
