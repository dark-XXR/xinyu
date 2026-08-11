"""增加用户资料、会话与套餐管理权限。

Revision ID: a82d91c4e630
Revises: f7c216b8a904
"""

from collections.abc import Sequence

from alembic import op

revision: str = "a82d91c4e630"
down_revision: str | None = "f7c216b8a904"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PERMISSIONS = ("USER_PROFILE_WRITE", "USER_SESSION_REVOKE", "USER_PLAN_ASSIGN")


def upgrade() -> None:
    # 现有平台所有者自动获得新增能力，其他角色仍由权限管理页面显式授权。
    for permission in PERMISSIONS:
        op.execute(
            f"""UPDATE admin_users
            SET permissions = (permissions::jsonb || '["{permission}"]'::jsonb)::json
            WHERE roles::jsonb @> '[{{"role_code":"PLATFORM_OWNER"}}]'::jsonb
              AND NOT permissions::jsonb ? '{permission}'"""
        )


def downgrade() -> None:
    for permission in PERMISSIONS:
        op.execute(
            f"""UPDATE admin_users SET permissions = (
              SELECT COALESCE(json_agg(value), '[]'::json)
              FROM json_array_elements_text(admin_users.permissions) AS value
              WHERE value != '{permission}')"""
        )
