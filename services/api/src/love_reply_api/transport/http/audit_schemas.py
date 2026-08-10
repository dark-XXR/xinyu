"""合规审计查询、正文披露与法务冻结接口模型。"""

from datetime import datetime
from typing import Any

from pydantic import Field

from love_reply_api.schemas import ApiModel, SuccessEnvelope


class AuditEventData(ApiModel):
    event_id: str
    occurred_at: datetime
    category: str
    event_type: str
    outcome: str
    severity: str
    actor_type: str
    actor_id: str | None
    user_id: str | None
    admin_id: str | None
    session_id: str | None
    request_id: str | None
    client_platform: str | None
    client_version: str | None
    resource_type: str | None
    resource_id: str | None
    order_id: str | None
    generation_id: str | None
    provider_id: str | None
    summary: str
    metadata: dict[str, Any]
    contains_sensitive_content: bool
    sensitive_payload_digest: str | None
    retention_until: datetime
    legal_hold: bool
    previous_event_hash: str
    event_hash: str


class AuditEventListData(ApiModel):
    items: list[AuditEventData]
    next_cursor: str | None
    has_more: bool


class SensitiveContentReadRequest(ApiModel):
    audit_reason: str = Field(min_length=8, max_length=500)


class SensitiveContentData(ApiModel):
    event_id: str
    content: dict[str, Any]


class LegalHoldRequest(ApiModel):
    enabled: bool
    audit_reason: str = Field(min_length=8, max_length=500)


class AuditChainData(ApiModel):
    valid: bool
    checked_count: int
    first_invalid_event_id: str | None


class AuditExportRequest(ApiModel):
    audit_reason: str = Field(min_length=8, max_length=500)
    include_sensitive_content: bool = False
    category: str | None = None
    event_type: str | None = None
    outcome: str | None = None
    user_id: str | None = None
    admin_id: str | None = None
    request_id: str | None = None
    resource_type: str | None = None
    resource_id: str | None = None
    order_id: str | None = None
    generation_id: str | None = None
    from_time: datetime | None = None
    to_time: datetime | None = None


class AuditExportData(ApiModel):
    export_id: str
    include_sensitive_content: bool
    event_count: int
    bundle_digest: str
    created_at: datetime
    expires_at: datetime


class AuditExportReadRequest(ApiModel):
    audit_reason: str = Field(min_length=8, max_length=500)


class AuditExportContentData(ApiModel):
    export_id: str
    bundle: dict[str, Any]


AuditEventListResponse = SuccessEnvelope[AuditEventListData]
SensitiveContentResponse = SuccessEnvelope[SensitiveContentData]
AuditEventResponse = SuccessEnvelope[AuditEventData]
AuditChainResponse = SuccessEnvelope[AuditChainData]
AuditExportResponse = SuccessEnvelope[AuditExportData]
AuditExportContentResponse = SuccessEnvelope[AuditExportContentData]
