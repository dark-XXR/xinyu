from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from love_reply_api.application.admin_platform import AdminPlatformService
from love_reply_api.application.runtime_config import RuntimeConfigService
from love_reply_api.infrastructure.database import get_session
from love_reply_api.schemas import SuccessEnvelope
from love_reply_api.transport.http.admin_platform_schemas import (
    NoticeListData,
    NoticeListResponse,
    NoticeVersionData,
)
from love_reply_api.transport.http.dependencies import ClientContext, get_client_context
from love_reply_api.transport.http.operations_schemas import AppBootstrapData, AppBootstrapResponse

router = APIRouter(prefix="/v1/app", tags=["APP_CONFIG"])


@router.get(
    "/bootstrap",
    operation_id="getAppBootstrap",
    response_model=AppBootstrapResponse,
)
async def get_app_bootstrap(
    request: Request,
    client: Annotated[ClientContext, Depends(get_client_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AppBootstrapResponse:
    del client
    config = await RuntimeConfigService(session).get_published()
    site_config = await AdminPlatformService(session).get_system_config(published_only=True)
    payload = config.model_dump()
    payload["site_identity"] = site_config.configuration
    return SuccessEnvelope(
        data=AppBootstrapData.model_validate(payload),
        request_id=request.state.request_id,
    )


@router.get("/notices", operation_id="listPublicNotices", response_model=NoticeListResponse)
async def list_public_notices(
    request: Request,
    client: Annotated[ClientContext, Depends(get_client_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> NoticeListResponse:
    """按客户端平台、语言和生效时间返回当前公告。"""
    records = await AdminPlatformService(session).list_public_notices(
        platform=client.platform,
        locale=client.accept_language,
        client_version=client.client_version,
        now=datetime.now(UTC),
    )
    return SuccessEnvelope(
        data=NoticeListData(
            items=[NoticeVersionData.model_validate(item, from_attributes=True) for item in records]
        ),
        request_id=request.state.request_id,
    )
