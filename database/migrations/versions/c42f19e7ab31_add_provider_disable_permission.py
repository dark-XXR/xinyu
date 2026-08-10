"""add provider disable permission

Revision ID: c42f19e7ab31
Revises: b91e63a4d2f0
"""

from collections.abc import Sequence

from alembic import op

revision: str = "c42f19e7ab31"
down_revision: str | None = "b91e63a4d2f0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 已存在的平台所有者继承紧急停用能力，其他角色仍需管理员显式授权。
    op.execute(
        """
        UPDATE admin_users
        SET permissions = (permissions::jsonb || '["PROVIDER_DISABLE"]'::jsonb)::json
        WHERE roles::jsonb @> '[{"role_code":"PLATFORM_OWNER"}]'::jsonb
          AND NOT permissions::jsonb ? 'PROVIDER_DISABLE'
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE admin_users
        SET permissions = (
          SELECT COALESCE(json_agg(value), '[]'::json)
          FROM json_array_elements_text(admin_users.permissions) AS value
          WHERE value != 'PROVIDER_DISABLE'
        )
        """
    )
