"""管理员和普通用户图片上传，以及站内媒体文件读取接口。"""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File, Form, Path, Request, UploadFile
from fastapi.responses import FileResponse

from love_reply_api.application.media import MediaAssetService, media_public_path
from love_reply_api.infrastructure.platform_records import MediaAssetRecord
from love_reply_api.transport.http.dependencies import (
    AdminContext,
    AuthContext,
    get_auth_context,
    get_media_asset_service,
    require_admin_permission,
)
from love_reply_api.transport.http.media_schemas import MediaAssetData, MediaAssetResponse

admin_router = APIRouter(prefix="/admin/v1/media", tags=["ADMIN_PLATFORM"])
user_router = APIRouter(prefix="/v1/media", tags=["USER"])
public_router = APIRouter(prefix="/media", tags=["APP_CONFIG"])
MediaService = Annotated[MediaAssetService, Depends(get_media_asset_service)]
MediaWrite = Annotated[AdminContext, Depends(require_admin_permission("MEDIA_WRITE"))]


def _response(record: MediaAssetRecord, request: Request) -> MediaAssetResponse:
    return MediaAssetResponse(
        data=MediaAssetData(
            asset_id=record.asset_id,
            purpose=record.purpose,
            content_type=record.content_type,
            size_bytes=record.size_bytes,
            width_pixels=record.width_pixels,
            height_pixels=record.height_pixels,
            public_url=media_public_path(record.asset_id),
            created_at=record.created_at,
        ),
        request_id=request.state.request_id,
    )


@admin_router.post(
    "/assets", operation_id="uploadAdminMediaAsset", response_model=MediaAssetResponse
)
async def upload_admin_media_asset(
    request: Request,
    context: MediaWrite,
    service: MediaService,
    file: Annotated[UploadFile, File()],
    purpose: Annotated[
        Literal["USER_AVATAR", "WEBSITE_BRAND", "CONTENT_IMAGE"], Form()
    ],
    audit_reason: Annotated[str, Form(alias="auditReason", min_length=8, max_length=500)],
) -> MediaAssetResponse:
    content = await file.read(service.max_upload_bytes + 1)
    record = await service.create_asset(
        content=content,
        declared_content_type=file.content_type,
        original_file_name=file.filename,
        purpose=purpose,
        owner_user_id=None,
        created_by_admin_id=context.admin.admin_id,
        audit_reason=audit_reason,
    )
    request.state.audit_resource_type = "MEDIA_ASSET"
    request.state.audit_resource_id = record.asset_id
    request.state.audit_metadata = {"purpose": purpose, "sizeBytes": record.size_bytes}
    return _response(record, request)


@user_router.post("/avatar", operation_id="uploadMyAvatar", response_model=MediaAssetResponse)
async def upload_my_avatar(
    request: Request,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    service: MediaService,
    file: Annotated[UploadFile, File()],
) -> MediaAssetResponse:
    content = await file.read(service.max_upload_bytes + 1)
    record = await service.create_asset(
        content=content,
        declared_content_type=file.content_type,
        original_file_name=file.filename,
        purpose="USER_AVATAR",
        owner_user_id=auth.user_id,
        created_by_admin_id=None,
        audit_reason=None,
    )
    request.state.audit_resource_type = "MEDIA_ASSET"
    request.state.audit_resource_id = record.asset_id
    request.state.audit_metadata = {"purpose": "USER_AVATAR", "sizeBytes": record.size_bytes}
    return _response(record, request)


@public_router.get("/{assetId}", operation_id="getMediaAsset", response_class=FileResponse)
async def get_media_asset(
    asset_id: Annotated[str, Path(alias="assetId")], service: MediaService
) -> FileResponse:
    record, path = await service.get_asset(asset_id)
    return FileResponse(
        path,
        media_type=record.content_type,
        headers={
            "Cache-Control": "public, max-age=31536000, immutable",
            "X-Content-Type-Options": "nosniff",
        },
    )
