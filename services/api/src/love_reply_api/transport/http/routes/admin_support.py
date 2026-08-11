"""管理员客服队列、会话与处理接口。"""

from typing import Annotated, cast

from fastapi import APIRouter, Depends, Header, Path, Query, Request

from love_reply_api.application.errors import ApiError
from love_reply_api.application.support import SupportService
from love_reply_api.schemas import SuccessEnvelope
from love_reply_api.transport.http.dependencies import (
    AdminContext,
    get_support_service,
    require_admin_permission,
)
from love_reply_api.transport.http.support_schemas import (
    AdminUpdateSupportTicketRequest,
    SupportMessageData,
    SupportTicketData,
    SupportTicketDetailData,
    SupportTicketDetailResponse,
    SupportTicketListData,
    SupportTicketListResponse,
    SupportTicketResponse,
)

router = APIRouter(prefix="/admin/v1/support/tickets", tags=["ADMIN_SUPPORT"])
Service = Annotated[SupportService, Depends(get_support_service)]
Read = Annotated[AdminContext, Depends(require_admin_permission("SUPPORT_READ"))]
Write = Annotated[AdminContext, Depends(require_admin_permission("SUPPORT_WRITE"))]


def _request_id(request: Request) -> str:
    return cast(str, request.state.request_id)


def _version(value: str) -> int:
    try:
        result = int(value)
    except ValueError as exc:
        raise ApiError(
            status_code=400, code="INVALID_IF_MATCH", message="Invalid If-Match."
        ) from exc
    if result < 1:
        raise ApiError(status_code=400, code="INVALID_IF_MATCH", message="Invalid If-Match.")
    return result


def _ticket(record: object) -> SupportTicketData:
    return SupportTicketData.model_validate(record, from_attributes=True)


@router.get("", operation_id="listAdminSupportTickets", response_model=SupportTicketListResponse)
async def list_tickets(
    request: Request,
    context: Read,
    service: Service,
    ticket_status: Annotated[str | None, Query(alias="status")] = None,
) -> SupportTicketListResponse:
    del context
    records = await service.list_tickets(status=ticket_status)
    return SuccessEnvelope(
        data=SupportTicketListData(items=[_ticket(item) for item in records]),
        request_id=_request_id(request),
    )


@router.get(
    "/{ticketId}", operation_id="getAdminSupportTicket", response_model=SupportTicketDetailResponse
)
async def get_ticket(
    ticket_id: Annotated[str, Path(alias="ticketId")],
    request: Request,
    context: Read,
    service: Service,
) -> SupportTicketDetailResponse:
    del context
    ticket, messages = await service.get_ticket(ticket_id=ticket_id)
    return SuccessEnvelope(
        data=SupportTicketDetailData(
            ticket=_ticket(ticket),
            messages=[
                SupportMessageData.model_validate(item, from_attributes=True) for item in messages
            ],
        ),
        request_id=_request_id(request),
    )


@router.patch(
    "/{ticketId}", operation_id="updateAdminSupportTicket", response_model=SupportTicketResponse
)
async def update_ticket(
    ticket_id: Annotated[str, Path(alias="ticketId")],
    body: AdminUpdateSupportTicketRequest,
    request: Request,
    context: Write,
    service: Service,
    if_match: Annotated[str, Header(alias="If-Match")],
) -> SupportTicketResponse:
    request.state.audit_sensitive_payload = {"requestBody": body.model_dump(mode="json")}
    record = await service.admin_update(
        ticket_id=ticket_id,
        expected_version=_version(if_match),
        admin_id=context.admin.admin_id,
        **body.model_dump(),
    )
    return SuccessEnvelope(data=_ticket(record), request_id=_request_id(request))
