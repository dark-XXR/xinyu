"""用户客服工单接口，正文通过业务表和合规访问日志留痕。"""

from typing import Annotated, cast

from fastapi import APIRouter, Depends, Path, Request, status

from love_reply_api.application.support import SupportService
from love_reply_api.schemas import SuccessEnvelope
from love_reply_api.transport.http.dependencies import (
    AuthContext,
    get_auth_context,
    get_support_service,
)
from love_reply_api.transport.http.support_schemas import (
    AddSupportMessageRequest,
    CreateSupportTicketRequest,
    SupportMessageData,
    SupportTicketData,
    SupportTicketDetailData,
    SupportTicketDetailResponse,
    SupportTicketListData,
    SupportTicketListResponse,
    SupportTicketResponse,
)

router = APIRouter(prefix="/v1/support/tickets", tags=["SUPPORT"])
Service = Annotated[SupportService, Depends(get_support_service)]
User = Annotated[AuthContext, Depends(get_auth_context)]


def _request_id(request: Request) -> str:
    return cast(str, request.state.request_id)


def _ticket(record: object) -> SupportTicketData:
    return SupportTicketData.model_validate(record, from_attributes=True)


@router.get("", operation_id="listMySupportTickets", response_model=SupportTicketListResponse)
async def list_tickets(request: Request, user: User, service: Service) -> SupportTicketListResponse:
    records = await service.list_tickets(user_id=user.user_id)
    return SuccessEnvelope(
        data=SupportTicketListData(items=[_ticket(item) for item in records]),
        request_id=_request_id(request),
    )


@router.post(
    "",
    operation_id="createSupportTicket",
    response_model=SupportTicketResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_ticket(
    body: CreateSupportTicketRequest, request: Request, user: User, service: Service
) -> SupportTicketResponse:
    request.state.audit_sensitive_payload = {"requestBody": body.model_dump(mode="json")}
    record = await service.create_ticket(user_id=user.user_id, **body.model_dump())
    return SuccessEnvelope(data=_ticket(record), request_id=_request_id(request))


@router.get(
    "/{ticketId}", operation_id="getMySupportTicket", response_model=SupportTicketDetailResponse
)
async def get_ticket(
    ticket_id: Annotated[str, Path(alias="ticketId")],
    request: Request,
    user: User,
    service: Service,
) -> SupportTicketDetailResponse:
    ticket, messages = await service.get_ticket(ticket_id=ticket_id, user_id=user.user_id)
    return SuccessEnvelope(
        data=SupportTicketDetailData(
            ticket=_ticket(ticket),
            messages=[
                SupportMessageData.model_validate(item, from_attributes=True) for item in messages
            ],
        ),
        request_id=_request_id(request),
    )


@router.post(
    "/{ticketId}/messages", operation_id="addMySupportMessage", response_model=SupportTicketResponse
)
async def add_message(
    ticket_id: Annotated[str, Path(alias="ticketId")],
    body: AddSupportMessageRequest,
    request: Request,
    user: User,
    service: Service,
) -> SupportTicketResponse:
    request.state.audit_sensitive_payload = {"requestBody": body.model_dump(mode="json")}
    record = await service.add_user_message(
        ticket_id=ticket_id, user_id=user.user_id, body=body.body
    )
    return SuccessEnvelope(data=_ticket(record), request_id=_request_id(request))
