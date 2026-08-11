"""新增站内图片资源与上传权限。

Revision ID: d19f4a72c6b1
Revises: a82d91c4e630
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d19f4a72c6b1"
down_revision: str | None = "a82d91c4e630"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PERMISSION = "MEDIA_WRITE"


def upgrade() -> None:
    op.create_table(
        "media_assets",
        sa.Column("asset_id", sa.String(64), primary_key=True),
        sa.Column("purpose", sa.String(32), nullable=False),
        sa.Column("storage_key", sa.String(255), nullable=False, unique=True),
        sa.Column("original_file_name", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(64), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("width_pixels", sa.Integer(), nullable=False),
        sa.Column("height_pixels", sa.Integer(), nullable=False),
        sa.Column("sha256_digest", sa.String(64), nullable=False),
        sa.Column("owner_user_id", sa.String(64)),
        sa.Column("created_by_admin_id", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("size_bytes > 0", name="ck_media_assets_size_positive"),
        sa.CheckConstraint("width_pixels > 0", name="ck_media_assets_width_positive"),
        sa.CheckConstraint("height_pixels > 0", name="ck_media_assets_height_positive"),
    )
    for column in (
        "purpose",
        "sha256_digest",
        "owner_user_id",
        "created_by_admin_id",
        "created_at",
    ):
        op.create_index(f"ix_media_assets_{column}", "media_assets", [column])
    op.execute(
        f"""UPDATE admin_users
        SET permissions = (permissions::jsonb || '["{PERMISSION}"]'::jsonb)::json
        WHERE roles::jsonb @> '[{{"role_code":"PLATFORM_OWNER"}}]'::jsonb
          AND NOT permissions::jsonb ? '{PERMISSION}'"""
    )


def downgrade() -> None:
    op.execute(
        f"""UPDATE admin_users SET permissions = (
          SELECT COALESCE(json_agg(value), '[]'::json)
          FROM json_array_elements_text(admin_users.permissions) AS value
          WHERE value != '{PERMISSION}')"""
    )
    op.drop_table("media_assets")
