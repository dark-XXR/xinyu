"""用户和管理员客服工单接口模型。"""

from datetime import datetime
from typing import Literal

from pydantic import Field

from love_reply_api.schemas import ApiModel, SuccessEnvelope


class SupportTicketData(ApiModel):
    ticket_id: str
    user_id: str
    category: str
    subject: str
    status: str
    priority: str
    assigned_admin_id: str | None
    last_message_at: datetime
    resource_version: int
    created_at: datetime
    updated_at: datetime


class SupportMessageData(ApiModel):
    message_id: str
    ticket_id: str
    sender_type: str
    sender_id: str
    body: str
    internal: bool
    created_at: datetime


class SupportTicketDetailData(ApiModel):
    ticket: SupportTicketData
    messages: list[SupportMessageData]


class SupportTicketListData(ApiModel):
    items: list[SupportTicketData]


class CreateSupportTicketRequest(ApiModel):
    category: Literal["GENERAL", "ACCOUNT", "PAYMENT", "PRIVACY", "COMPLAINT"]
    subject: str = Field(min_length=2, max_length=160)
    body: str = Field(min_length=2, max_length=20_000)


class AddSupportMessageRequest(ApiModel):
    body: str = Field(min_length=2, max_length=20_000)


class AdminUpdateSupportTicketRequest(ApiModel):
    body: str | None = Field(default=None, min_length=2, max_length=20_000)
    internal: bool = False
    status: Literal["OPEN", "WAITING_SUPPORT", "WAITING_USER", "RESOLVED", "CLOSED"]
    priority: Literal["LOW", "NORMAL", "HIGH", "URGENT"]
    assigned_admin_id: str | None = None
    audit_reason: str = Field(min_length=8, max_length=500)


SupportTicketResponse = SuccessEnvelope[SupportTicketData]
SupportTicketDetailResponse = SuccessEnvelope[SupportTicketDetailData]
SupportTicketListResponse = SuccessEnvelope[SupportTicketListData]
