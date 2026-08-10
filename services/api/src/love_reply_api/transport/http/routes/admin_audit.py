"""管理员合规审计日志检索、敏感正文披露、法务冻结和完整性校验接口。"""

from datetime import datetime
from typing import Annotated, Any, cast

from fastapi import APIRouter, Depends, Path, Query, Request

from love_reply_api.application.audit import ComplianceAuditService
from love_reply_api.schemas import SuccessEnvelope
from love_reply_api.transport.http.audit_schemas import (
    AuditChainData,
    AuditChainResponse,
    AuditEventData,
    AuditEventListData,
    AuditEventListResponse,
    AuditEventResponse,
    AuditExportContentData,
    AuditExportContentResponse,
    AuditExportData,
    AuditExportReadRequest,
    AuditExportRequest,
    AuditExportResponse,
    LegalHoldRequest,
    SensitiveContentData,
    SensitiveContentReadRequest,
    SensitiveContentResponse,
)
from love_reply_api.transport.http.dependencies import (
    AdminContext,
    get_compliance_audit_service,
    require_admin_permission,
)

router = APIRouter(prefix="/admin/v1/audit-events", tags=["ADMIN_RBAC"])
AuditRead = Annotated[AdminContext, Depends(require_admin_permission("AUDIT_LOG_READ"))]
ContentRead = Annotated[
    AdminContext, Depends(require_admin_permission("AUDIT_SENSITIVE_CONTENT_READ"))
]
LegalHold = Annotated[AdminContext, Depends(require_admin_permission("AUDIT_LEGAL_HOLD"))]
AuditExport = Annotated[AdminContext, Depends(require_admin_permission("AUDIT_EXPORT"))]
Service = Annotated[ComplianceAuditService, Depends(get_compliance_audit_service)]


def _request_id(request: Request) -> str:
    return cast(str, request.state.request_id)


def _data(record: Any) -> AuditEventData:
    return AuditEventData.model_validate(
        {**record.__dict__, "metadata": record.metadata_json}, from_attributes=True
    )


@router.get("", operation_id="listAdminAuditEvents", response_model=AuditEventListResponse)
async def list_audit_events(
    request: Request,
    context: AuditRead,
    service: Service,
    cursor: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    category: Annotated[str | None, Query()] = None,
    event_type: Annotated[str | None, Query(alias="eventType")] = None,
    outcome: Annotated[str | None, Query()] = None,
    user_id: Annotated[str | None, Query(alias="userId")] = None,
    admin_id: Annotated[str | None, Query(alias="adminId")] = None,
    request_id: Annotated[str | None, Query(alias="requestId")] = None,
    resource_type: Annotated[str | None, Query(alias="resourceType")] = None,
    resource_id: Annotated[str | None, Query(alias="resourceId")] = None,
    order_id: Annotated[str | None, Query(alias="orderId")] = None,
    generation_id: Annotated[str | None, Query(alias="generationId")] = None,
    from_time: Annotated[datetime | None, Query(alias="from")] = None,
    to_time: Annotated[datetime | None, Query(alias="to")] = None,
) -> AuditEventListResponse:
    del context
    page = await service.list_events(
        limit=limit,
        cursor=cursor,
        category=category,
        event_type=event_type,
        outcome=outcome,
        user_id=user_id,
        admin_id=admin_id,
        request_id=request_id,
        resource_type=resource_type,
        resource_id=resource_id,
        order_id=order_id,
        generation_id=generation_id,
        from_time=from_time,
        to_time=to_time,
    )
    return SuccessEnvelope(
        data=AuditEventListData(
            items=[_data(item) for item in page.items],
            next_cursor=page.next_cursor,
            has_more=page.has_more,
        ),
        request_id=_request_id(request),
    )


@router.post(
    "/{eventId}/sensitive-content",
    operation_id="readAdminAuditSensitiveContent",
    response_model=SensitiveContentResponse,
)
async def read_sensitive_content(
    event_id: Annotated[str, Path(alias="eventId")],
    body: SensitiveContentReadRequest,
    request: Request,
    context: ContentRead,
    service: Service,
) -> SensitiveContentResponse:
    content = await service.reveal_sensitive(
        event_id=event_id,
        admin_id=context.admin.admin_id,
        session_id=context.session.session_id,
        audit_reason=body.audit_reason,
        request_id=_request_id(request),
    )
    return SuccessEnvelope(
        data=SensitiveContentData(event_id=event_id, content=content),
        request_id=_request_id(request),
    )


@router.post(
    "/{eventId}/legal-hold",
    operation_id="changeAdminAuditLegalHold",
    response_model=AuditEventResponse,
)
async def change_legal_hold(
    event_id: Annotated[str, Path(alias="eventId")],
    body: LegalHoldRequest,
    request: Request,
    context: LegalHold,
    service: Service,
) -> AuditEventResponse:
    record = await service.set_legal_hold(
        event_id=event_id,
        enabled=body.enabled,
        admin_id=context.admin.admin_id,
        session_id=context.session.session_id,
        audit_reason=body.audit_reason,
        request_id=_request_id(request),
    )
    return SuccessEnvelope(data=_data(record), request_id=_request_id(request))


@router.get(
    "/integrity", operation_id="verifyAdminAuditIntegrity", response_model=AuditChainResponse
)
async def verify_integrity(
    request: Request, context: AuditRead, service: Service
) -> AuditChainResponse:
    del context
    valid, first_invalid, count = await service.verify_chain()
    return SuccessEnvelope(
        data=AuditChainData(valid=valid, checked_count=count, first_invalid_event_id=first_invalid),
        request_id=_request_id(request),
    )


@router.post("/exports", operation_id="createAdminAuditExport", response_model=AuditExportResponse)
async def create_audit_export(
    body: AuditExportRequest, request: Request, context: AuditExport, service: Service
) -> AuditExportResponse:
    if (
        body.include_sensitive_content
        and "AUDIT_SENSITIVE_CONTENT_READ" not in context.admin.permissions
    ):
        from love_reply_api.application.errors import ApiError

        raise ApiError(
            status_code=403,
            code="PERMISSION_DENIED",
            message="Sensitive audit content permission is required.",
        )
    filters = body.model_dump(exclude={"audit_reason", "include_sensitive_content"})
    record = await service.create_export(
        admin_id=context.admin.admin_id,
        session_id=context.session.session_id,
        request_id=_request_id(request),
        audit_reason=body.audit_reason,
        include_sensitive_content=body.include_sensitive_content,
        filters=filters,
    )
    return SuccessEnvelope(
        data=AuditExportData.model_validate(record, from_attributes=True),
        request_id=_request_id(request),
    )


@router.post(
    "/exports/{exportId}/content",
    operation_id="readAdminAuditExport",
    response_model=AuditExportContentResponse,
)
async def read_audit_export(
    export_id: Annotated[str, Path(alias="exportId")],
    body: AuditExportReadRequest,
    request: Request,
    context: AuditExport,
    service: Service,
) -> AuditExportContentResponse:
    bundle = await service.read_export(
        export_id=export_id,
        admin_id=context.admin.admin_id,
        session_id=context.session.session_id,
        request_id=_request_id(request),
        audit_reason=body.audit_reason,
    )
    return SuccessEnvelope(
        data=AuditExportContentData(export_id=export_id, bundle=bundle),
        request_id=_request_id(request),
    )
