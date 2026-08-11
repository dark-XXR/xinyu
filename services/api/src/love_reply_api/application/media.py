"""站内图片上传、内容识别、元数据持久化与本地存储编排。"""

from datetime import UTC, datetime
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy.ext.asyncio import AsyncSession

from love_reply_api.application.errors import ApiError
from love_reply_api.config import Settings
from love_reply_api.infrastructure.media_storage import LocalMediaStorage
from love_reply_api.infrastructure.platform_records import (
    AdminPlatformAuditRecord,
    MediaAssetRecord,
)

MEDIA_PUBLIC_PREFIX = "/media"
ADMIN_MEDIA_PURPOSES = {"USER_AVATAR", "WEBSITE_BRAND", "CONTENT_IMAGE"}

_EXTENSIONS = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}


def sniff_image_content_type(content: bytes) -> str | None:
    """按文件签名字节识别图片，不能仅相信浏览器声明或扩展名。"""
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "image/webp"
    return None


def sanitize_image(
    content: bytes, *, content_type: str, max_pixels: int
) -> tuple[bytes, int, int]:
    """解码并重新生成单帧图片，限制像素并移除 EXIF、ICC 和尾部附加内容。"""
    try:
        with Image.open(BytesIO(content)) as source:
            if getattr(source, "n_frames", 1) != 1:
                raise ApiError(
                    status_code=415,
                    code="MEDIA_ANIMATION_UNSUPPORTED",
                    message="Animated or multi-frame images are not supported.",
                )
            width, height = source.size
            if width <= 0 or height <= 0 or width * height > max_pixels:
                raise ApiError(
                    status_code=413,
                    code="MEDIA_DIMENSIONS_TOO_LARGE",
                    message="Image dimensions exceed the configured pixel limit.",
                    details={"maxPixels": max_pixels},
                )
            # EXIF 方向在转码前应用；随后只复制像素，不复制任何原始元数据。
            normalized = ImageOps.exif_transpose(source)
            output = BytesIO()
            if content_type == "image/jpeg":
                normalized.convert("RGB").save(output, format="JPEG", quality=90, optimize=True)
            elif content_type == "image/png":
                mode = "RGBA" if "A" in normalized.getbands() else "RGB"
                normalized.convert(mode).save(output, format="PNG", optimize=True)
            else:
                mode = "RGBA" if "A" in normalized.getbands() else "RGB"
                normalized.convert(mode).save(output, format="WEBP", quality=90, method=4)
            return output.getvalue(), normalized.width, normalized.height
    except ApiError:
        raise
    except (Image.DecompressionBombError, UnidentifiedImageError, OSError, ValueError) as exc:
        raise ApiError(
            status_code=415,
            code="MEDIA_IMAGE_INVALID",
            message="Image content is corrupt or cannot be decoded safely.",
        ) from exc


def media_public_path(asset_id: str) -> str:
    return f"{MEDIA_PUBLIC_PREFIX}/{asset_id}"


def asset_id_from_path(value: str) -> str | None:
    prefix = f"{MEDIA_PUBLIC_PREFIX}/"
    if not value.startswith(prefix):
        return None
    asset_id = value.removeprefix(prefix)
    if not asset_id.startswith("mda_") or len(asset_id) != 36:
        return None
    suffix = asset_id.removeprefix("mda_")
    return asset_id if all(character in "0123456789abcdef" for character in suffix) else None


class MediaAssetService:
    """保存媒体内容并生成不可猜测的站内资源地址。"""

    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings
        self._storage = LocalMediaStorage(settings.media_storage_root)

    @property
    def max_upload_bytes(self) -> int:
        return self._settings.media_max_upload_bytes

    async def create_asset(
        self,
        *,
        content: bytes,
        declared_content_type: str | None,
        original_file_name: str | None,
        purpose: str,
        owner_user_id: str | None,
        created_by_admin_id: str | None,
        audit_reason: str | None,
    ) -> MediaAssetRecord:
        if not content:
            raise ApiError(status_code=400, code="MEDIA_FILE_EMPTY", message="Image file is empty.")
        if len(content) > self._settings.media_max_upload_bytes:
            raise ApiError(
                status_code=413,
                code="MEDIA_FILE_TOO_LARGE",
                message="Image file exceeds the configured upload size limit.",
                details={"maxBytes": self._settings.media_max_upload_bytes},
            )
        detected = sniff_image_content_type(content)
        if detected is None:
            raise ApiError(
                status_code=415,
                code="MEDIA_TYPE_UNSUPPORTED",
                message="Only PNG, JPEG, and WebP images are supported.",
            )
        normalized_declared = (declared_content_type or "").split(";", 1)[0].strip().lower()
        if normalized_declared and normalized_declared not in {
            detected,
            "application/octet-stream",
        }:
            raise ApiError(
                status_code=415,
                code="MEDIA_TYPE_MISMATCH",
                message="Declared media type does not match the image content.",
            )
        if created_by_admin_id is None and purpose != "USER_AVATAR":
            raise ApiError(
                status_code=403,
                code="MEDIA_PURPOSE_FORBIDDEN",
                message="Users may only upload their own avatar images.",
            )
        if purpose not in ADMIN_MEDIA_PURPOSES:
            raise ApiError(
                status_code=400,
                code="MEDIA_PURPOSE_INVALID",
                message="Media purpose is not supported.",
            )

        sanitized, width, height = sanitize_image(
            content,
            content_type=detected,
            max_pixels=self._settings.media_max_image_pixels,
        )
        if len(sanitized) > self._settings.media_max_upload_bytes:
            raise ApiError(
                status_code=413,
                code="MEDIA_FILE_TOO_LARGE",
                message="Sanitized image exceeds the configured upload size limit.",
                details={"maxBytes": self._settings.media_max_upload_bytes},
            )

        asset_id = f"mda_{uuid4().hex}"
        now = datetime.now(UTC)
        storage_key = f"{purpose.lower()}/{now:%Y/%m}/{uuid4().hex}.{_EXTENSIONS[detected]}"
        safe_name = Path(original_file_name or "image").name[:255] or "image"
        record = MediaAssetRecord(
            asset_id=asset_id,
            purpose=purpose,
            storage_key=storage_key,
            original_file_name=safe_name,
            content_type=detected,
            size_bytes=len(sanitized),
            width_pixels=width,
            height_pixels=height,
            sha256_digest=sha256(sanitized).hexdigest(),
            owner_user_id=owner_user_id,
            created_by_admin_id=created_by_admin_id,
            created_at=now,
        )
        self._storage.write(storage_key, sanitized)
        try:
            self._session.add(record)
            if created_by_admin_id is not None:
                self._session.add(
                    AdminPlatformAuditRecord(
                        audit_id=f"paud_{uuid4().hex}",
                        resource_type="MEDIA_ASSET",
                        resource_id=asset_id,
                        admin_id=created_by_admin_id,
                        action="MEDIA_ASSET_UPLOADED",
                        audit_reason=audit_reason or "管理员上传站内图片资源",
                        metadata_json={
                            "purpose": purpose,
                            "contentType": detected,
                            "sizeBytes": len(sanitized),
                            "widthPixels": width,
                            "heightPixels": height,
                            "sha256": record.sha256_digest,
                        },
                        created_at=now,
                    )
                )
            await self._session.commit()
        except Exception:
            await self._session.rollback()
            self._storage.delete(storage_key)
            raise
        return record

    async def get_asset(self, asset_id: str) -> tuple[MediaAssetRecord, Path]:
        record = await self._session.get(MediaAssetRecord, asset_id)
        if record is None:
            raise ApiError(status_code=404, code="MEDIA_NOT_FOUND", message="Media was not found.")
        try:
            path = self._storage.resolve(record.storage_key)
        except FileNotFoundError as exc:
            raise ApiError(
                status_code=404,
                code="MEDIA_CONTENT_NOT_FOUND",
                message="Media content was not found.",
            ) from exc
        return record, path
