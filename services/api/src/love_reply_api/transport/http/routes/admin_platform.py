"""用户、公告和网站基础配置的管理后台 HTTP 接口。"""

from typing import Annotated, Any, cast

from fastapi import APIRouter, Depends, Header, Path, Query, Request, status

from love_reply_api.application.admin_platform import AdminPlatformService
from love_reply_api.application.errors import ApiError
from love_reply_api.schemas import SuccessEnvelope
from love_reply_api.transport.http.admin_platform_schemas import (
    AdminUserDetailData,
    AdminUserDetailResponse,
    AdminUserEntitlementBundleData,
    AdminUserEntitlementResponse,
    AdminUserListData,
    AdminUserListResponse,
    AdminUserResponse,
    AdminUserStatusRequest,
    AdminUserSummaryData,
    AdminWalletLedgerData,
    AdminWalletLedgerListData,
    AdminWalletLedgerListResponse,
    AuditReasonRequest,
    NoticeListData,
    NoticeListResponse,
    NoticeResponse,
    NoticeVersionData,
    NoticeWriteRequest,
    SystemConfigResponse,
    SystemConfigVersionData,
    SystemConfigWriteRequest,
)
from love_reply_api.transport.http.dependencies import (
    AdminContext,
    get_admin_platform_service,
    require_admin_permission,
)

router = APIRouter(prefix="/admin/v1", tags=["ADMIN_PLATFORM"])
Service = Annotated[AdminPlatformService, Depends(get_admin_platform_service)]
UserRead = Annotated[AdminContext, Depends(require_admin_permission("USER_READ"))]
UserWrite = Annotated[AdminContext, Depends(require_admin_permission("USER_STATUS_WRITE"))]
ConfigRead = Annotated[AdminContext, Depends(require_admin_permission("SYSTEM_CONFIG_READ"))]
ConfigWrite = Annotated[AdminContext, Depends(require_admin_permission("SYSTEM_CONFIG_WRITE"))]
ConfigPublish = Annotated[AdminContext, Depends(require_admin_permission("SYSTEM_CONFIG_PUBLISH"))]
NoticeRead = Annotated[AdminContext, Depends(require_admin_permission("NOTICE_READ"))]
NoticeWrite = Annotated[AdminContext, Depends(require_admin_permission("NOTICE_WRITE"))]
NoticePublish = Annotated[AdminContext, Depends(require_admin_permission("NOTICE_PUBLISH"))]
NoticeRevoke = Annotated[AdminContext, Depends(require_admin_permission("NOTICE_REVOKE"))]


def _request_id(request: Request) -> str:
    return cast(str, request.state.request_id)


def _expected_version(value: str) -> int:
    try:
        result = int(value)
    except ValueError as exc:
        raise ApiError(
            status_code=400,
            code="INVALID_IF_MATCH",
            message="If-Match must be a resource version.",
        ) from exc
    if result < 1:
        raise ApiError(
            status_code=400, code="INVALID_IF_MATCH", message="If-Match must be positive."
        )
    return result


def _data(model: type[Any], value: Any) -> Any:
    return model.model_validate(value, from_attributes=True)


@router.get("/users", operation_id="listAdminUsers", response_model=AdminUserListResponse)
async def list_users(
    request: Request,
    context: UserRead,
    service: Service,
    search: Annotated[str | None, Query(max_length=254)] = None,
    account_status: Annotated[str | None, Query(alias="status")] = None,
    cursor: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> AdminUserListResponse:
    del context
    page = await service.list_users(
        search=search, status=account_status, cursor=cursor, limit=limit
    )
    return SuccessEnvelope(
        data=AdminUserListData(
            items=[AdminUserSummaryData.model_validate(item) for item in page.items],
            next_cursor=page.next_cursor,
            has_more=page.has_more,
        ),
        request_id=_request_id(request),
    )


@router.get("/users/{userId}", operation_id="getAdminUser", response_model=AdminUserDetailResponse)
async def get_user(
    user_id: Annotated[str, Path(alias="userId")],
    request: Request,
    context: UserRead,
    service: Service,
) -> AdminUserDetailResponse:
    del context
    return SuccessEnvelope(
        data=AdminUserDetailData.model_validate(await service.get_user_detail(user_id)),
        request_id=_request_id(request),
    )


@router.patch(
    "/users/{userId}/status", operation_id="changeAdminUserStatus", response_model=AdminUserResponse
)
async def change_user_status(
    user_id: Annotated[str, Path(alias="userId")],
    body: AdminUserStatusRequest,
    request: Request,
    context: UserWrite,
    service: Service,
    if_match: Annotated[str, Header(alias="If-Match")],
) -> AdminUserResponse:
    if body.confirmation_user_id != user_id:
        raise ApiError(
            status_code=400,
            code="CONFIRMATION_MISMATCH",
            message="The confirmation user ID does not match.",
        )
    record = await service.change_user_status(
        user_id=user_id,
        expected_version=_expected_version(if_match),
        target_status=body.status,
        admin_id=context.admin.admin_id,
        audit_reason=body.audit_reason,
    )
    return SuccessEnvelope(
        data=AdminUserSummaryData.model_validate(record), request_id=_request_id(request)
    )


@router.get(
    "/users/{userId}/entitlements",
    operation_id="getAdminUserEntitlements",
    response_model=AdminUserEntitlementResponse,
)
async def get_user_entitlements(
    user_id: Annotated[str, Path(alias="userId")],
    request: Request,
    context: UserRead,
    service: Service,
) -> AdminUserEntitlementResponse:
    del context
    bundle = await service.get_user_entitlement(user_id)
    return SuccessEnvelope(
        data=AdminUserEntitlementBundleData.model_validate(bundle, from_attributes=True),
        request_id=_request_id(request),
    )


@router.get(
    "/users/{userId}/ledger",
    operation_id="listAdminUserLedger",
    response_model=AdminWalletLedgerListResponse,
)
async def list_user_ledger(
    user_id: Annotated[str, Path(alias="userId")],
    request: Request,
    context: UserRead,
    service: Service,
    cursor: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> AdminWalletLedgerListResponse:
    del context
    page = await service.list_user_ledger(user_id=user_id, cursor=cursor, limit=limit)
    return SuccessEnvelope(
        data=AdminWalletLedgerListData(
            items=[_data(AdminWalletLedgerData, item) for item in page.items],
            next_cursor=page.next_cursor,
            has_more=page.has_more,
        ),
        request_id=_request_id(request),
    )


@router.get(
    "/system-config", operation_id="getAdminSystemConfig", response_model=SystemConfigResponse
)
async def get_system_config(
    request: Request,
    context: ConfigRead,
    service: Service,
    published_only: Annotated[bool, Query(alias="publishedOnly")] = False,
) -> SystemConfigResponse:
    del context
    return SuccessEnvelope(
        data=_data(
            SystemConfigVersionData,
            await service.get_system_config(published_only=published_only),
        ),
        request_id=_request_id(request),
    )


@router.patch(
    "/system-config", operation_id="updateAdminSystemConfig", response_model=SystemConfigResponse
)
async def update_system_config(
    body: SystemConfigWriteRequest,
    request: Request,
    context: ConfigWrite,
    service: Service,
    if_match: Annotated[str, Header(alias="If-Match")],
) -> SystemConfigResponse:
    record = await service.update_system_config(
        expected_version=_expected_version(if_match),
        configuration=body.configuration.model_dump(mode="json", by_alias=True),
        admin_id=context.admin.admin_id,
        audit_reason=body.audit_reason,
    )
    return SuccessEnvelope(
        data=_data(SystemConfigVersionData, record), request_id=_request_id(request)
    )


@router.post(
    "/system-config/publish",
    operation_id="publishAdminSystemConfig",
    response_model=SystemConfigResponse,
)
async def publish_system_config(
    body: AuditReasonRequest,
    request: Request,
    context: ConfigPublish,
    service: Service,
    if_match: Annotated[str, Header(alias="If-Match")],
) -> SystemConfigResponse:
    record = await service.publish_system_config(
        expected_version=_expected_version(if_match),
        admin_id=context.admin.admin_id,
        audit_reason=body.audit_reason,
    )
    return SuccessEnvelope(
        data=_data(SystemConfigVersionData, record), request_id=_request_id(request)
    )


@router.get("/notices", operation_id="listAdminNotices", response_model=NoticeListResponse)
async def list_notices(
    request: Request, context: NoticeRead, service: Service
) -> NoticeListResponse:
    del context
    return SuccessEnvelope(
        data=NoticeListData(
            items=[_data(NoticeVersionData, item) for item in await service.list_notices()]
        ),
        request_id=_request_id(request),
    )


def _notice_values(body: NoticeWriteRequest) -> dict[str, Any]:
    return body.model_dump(exclude={"audit_reason"})


@router.post(
    "/notices",
    operation_id="createAdminNotice",
    response_model=NoticeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_notice(
    body: NoticeWriteRequest, request: Request, context: NoticeWrite, service: Service
) -> NoticeResponse:
    record = await service.create_notice(
        values=_notice_values(body), admin_id=context.admin.admin_id, audit_reason=body.audit_reason
    )
    return SuccessEnvelope(data=_data(NoticeVersionData, record), request_id=_request_id(request))


@router.patch(
    "/notices/{noticeId}", operation_id="updateAdminNotice", response_model=NoticeResponse
)
async def update_notice(
    notice_id: Annotated[str, Path(alias="noticeId")],
    body: NoticeWriteRequest,
    request: Request,
    context: NoticeWrite,
    service: Service,
    if_match: Annotated[str, Header(alias="If-Match")],
) -> NoticeResponse:
    record = await service.update_notice(
        notice_id=notice_id,
        expected_version=_expected_version(if_match),
        values=_notice_values(body),
        admin_id=context.admin.admin_id,
        audit_reason=body.audit_reason,
    )
    return SuccessEnvelope(data=_data(NoticeVersionData, record), request_id=_request_id(request))


@router.post(
    "/notices/{noticeId}/publish", operation_id="publishAdminNotice", response_model=NoticeResponse
)
async def publish_notice(
    notice_id: Annotated[str, Path(alias="noticeId")],
    body: AuditReasonRequest,
    request: Request,
    context: NoticePublish,
    service: Service,
    if_match: Annotated[str, Header(alias="If-Match")],
) -> NoticeResponse:
    record = await service.publish_notice(
        notice_id=notice_id,
        expected_version=_expected_version(if_match),
        admin_id=context.admin.admin_id,
        audit_reason=body.audit_reason,
    )
    return SuccessEnvelope(data=_data(NoticeVersionData, record), request_id=_request_id(request))


@router.post(
    "/notices/{noticeId}/revoke", operation_id="revokeAdminNotice", response_model=NoticeResponse
)
async def revoke_notice(
    notice_id: Annotated[str, Path(alias="noticeId")],
    body: AuditReasonRequest,
    request: Request,
    context: NoticeRevoke,
    service: Service,
    if_match: Annotated[str, Header(alias="If-Match")],
) -> NoticeResponse:
    record = await service.revoke_notice(
        notice_id=notice_id,
        expected_version=_expected_version(if_match),
        admin_id=context.admin.admin_id,
        audit_reason=body.audit_reason,
    )
    return SuccessEnvelope(data=_data(NoticeVersionData, record), request_id=_request_id(request))
