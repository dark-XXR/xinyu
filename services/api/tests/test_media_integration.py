"""站内图片上传元数据、管理员审计与文件读取 PostgreSQL 集成测试。"""

import os
from collections.abc import AsyncIterator
from io import BytesIO
from pathlib import Path

import pytest
import pytest_asyncio
from love_reply_api.application.errors import ApiError
from love_reply_api.application.media import MediaAssetService, media_public_path
from love_reply_api.config import Settings
from love_reply_api.infrastructure.database import engine, session_factory
from love_reply_api.infrastructure.platform_records import (
    AdminPlatformAuditRecord,
    MediaAssetRecord,
)
from PIL import Image
from sqlalchemy import delete, select

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_INTEGRATION_TESTS") != "1", reason="requires PostgreSQL"
)


@pytest_asyncio.fixture(autouse=True)
async def clean_media_fixtures() -> AsyncIterator[None]:
    async with session_factory() as session:
        await session.execute(
            delete(AdminPlatformAuditRecord).where(
                AdminPlatformAuditRecord.resource_type == "MEDIA_ASSET"
            )
        )
        await session.execute(delete(MediaAssetRecord))
        await session.commit()
    yield
    async with session_factory() as session:
        await session.execute(
            delete(AdminPlatformAuditRecord).where(
                AdminPlatformAuditRecord.resource_type == "MEDIA_ASSET"
            )
        )
        await session.execute(delete(MediaAssetRecord))
        await session.commit()
    await engine.dispose()


@pytest.mark.asyncio
async def test_admin_upload_persists_first_party_asset_and_audit(tmp_path: Path) -> None:
    settings = Settings(media_storage_root=tmp_path, media_max_upload_bytes=4096)
    source = BytesIO()
    Image.new("RGBA", (12, 8), (220, 50, 47, 255)).save(
        source, format="PNG", pnginfo=None
    )
    # 追加内容模拟隐藏尾部数据；服务端重新编码后不得原样保留。
    content = source.getvalue() + b"hidden-tail"
    async with session_factory() as session:
        service = MediaAssetService(session=session, settings=settings)
        asset = await service.create_asset(
            content=content,
            declared_content_type="image/png",
            original_file_name="../../brand.png",
            purpose="WEBSITE_BRAND",
            owner_user_id=None,
            created_by_admin_id="adm_media_test",
            audit_reason="上传经过运营复核的网站品牌图片",
        )

        assert media_public_path(asset.asset_id) == f"/media/{asset.asset_id}"
        assert asset.original_file_name == "brand.png"
        assert asset.storage_key.endswith(".png")
        assert (asset.width_pixels, asset.height_pixels) == (12, 8)
        record, stored_path = await service.get_asset(asset.asset_id)
        assert record.sha256_digest == asset.sha256_digest
        stored_content = stored_path.read_bytes()
        assert stored_content != content
        assert b"hidden-tail" not in stored_content
        audit = await session.scalar(
            select(AdminPlatformAuditRecord).where(
                AdminPlatformAuditRecord.resource_id == asset.asset_id
            )
        )
        assert audit is not None
        assert audit.action == "MEDIA_ASSET_UPLOADED"
        assert audit.metadata_json["sizeBytes"] == len(stored_content)


@pytest.mark.asyncio
async def test_upload_rejects_declared_type_mismatch_without_writing(tmp_path: Path) -> None:
    settings = Settings(media_storage_root=tmp_path, media_max_upload_bytes=4096)
    async with session_factory() as session:
        service = MediaAssetService(session=session, settings=settings)
        with pytest.raises(ApiError, match="does not match") as captured:
            await service.create_asset(
                content=b"\x89PNG\r\n\x1a\ncontent",
                declared_content_type="image/jpeg",
                original_file_name="avatar.jpg",
                purpose="USER_AVATAR",
                owner_user_id="usr_media_test",
                created_by_admin_id=None,
                audit_reason=None,
            )
        assert captured.value.code == "MEDIA_TYPE_MISMATCH"
        # 此处在异步测试中只检查明确目标目录，避免测试代码执行递归磁盘扫描。
        assert not (tmp_path / "user_avatar").exists()
