"""用户运营、网站配置和公告发布接口的数据模型。"""

from datetime import datetime
from typing import Literal

from pydantic import Field, HttpUrl, model_validator

from love_reply_api.schemas import ApiModel, SuccessEnvelope


class AdminUserSummaryData(ApiModel):
    user_id: str
    status: Literal["ACTIVE", "SUSPENDED", "DELETION_PENDING"]
    masked_email: str | None
    masked_phone: str | None
    nickname: str | None
    locale: str
    time_zone: str
    plan_code: str | None
    plan_expires_at: datetime | None
    text_remaining: int
    vision_remaining: int
    energy_balance: int
    device_count: int = Field(ge=0)
    resource_version: int = Field(ge=1)
    created_at: datetime
    updated_at: datetime


class AdminUserDeviceData(ApiModel):
    id: str
    device_id: str
    platform: str
    model: str | None
    last_seen_at: datetime
    created_at: datetime
    revoked_at: datetime | None


class AdminUserConsentData(ApiModel):
    consent_id: str
    consent_type: str
    document_version: str
    granted: bool
    required: bool
    granted_at: datetime | None
    resource_version: int
    updated_at: datetime


class AdminUserDetailData(AdminUserSummaryData):
    devices: list[AdminUserDeviceData]
    consents: list[AdminUserConsentData]


class AdminUserEntitlementData(ApiModel):
    user_id: str
    plan_code: str
    plan_expires_at: datetime | None
    text_remaining: int
    text_reserved: int
    vision_remaining: int
    allowed_model_ids: list[str]
    allowed_style_ids: list[str]
    resource_version: int
    updated_at: datetime


class AdminUserWalletData(ApiModel):
    user_id: str
    energy_balance: int
    energy_reserved: int
    resource_version: int
    updated_at: datetime


class AdminUserEntitlementBundleData(ApiModel):
    entitlement: AdminUserEntitlementData
    wallet: AdminUserWalletData


class AdminWalletLedgerData(ApiModel):
    ledger_entry_id: str
    user_id: str
    generation_id: str | None
    entry_type: str
    energy_delta: int
    reserved_delta: int
    balance_after: int
    reserved_after: int
    reason_code: str | None
    created_at: datetime


class AdminUserListData(ApiModel):
    items: list[AdminUserSummaryData]
    next_cursor: str | None
    has_more: bool


class AdminWalletLedgerListData(ApiModel):
    items: list[AdminWalletLedgerData]
    next_cursor: str | None
    has_more: bool


class AdminUserStatusRequest(ApiModel):
    status: Literal["ACTIVE", "SUSPENDED"]
    audit_reason: str = Field(min_length=8, max_length=500)
    confirmation_user_id: str


class SystemIdentityConfig(ApiModel):
    website_name: str = Field(min_length=1, max_length=80)
    app_name: str = Field(min_length=1, max_length=80)
    company_name: str = Field(min_length=1, max_length=160)
    logo_url: HttpUrl | None = None
    customer_service_email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    privacy_email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    default_locale: str = Field(min_length=2, max_length=35)
    official_website_url: HttpUrl | None = None
    filing_information: str | None = Field(default=None, max_length=200)
    maintenance_mode: bool
    maintenance_message: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def validate_maintenance_message(self) -> "SystemIdentityConfig":
        if self.maintenance_mode and not self.maintenance_message:
            raise ValueError("maintenance message is required when maintenance mode is enabled")
        return self


class SystemConfigVersionData(ApiModel):
    config_id: str
    version: int = Field(ge=1)
    status: Literal["DRAFT", "PUBLISHED", "SUPERSEDED"]
    configuration: SystemIdentityConfig
    resource_version: int = Field(ge=1)
    created_by_admin_id: str
    published_by_admin_id: str | None
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime


class SystemConfigWriteRequest(ApiModel):
    configuration: SystemIdentityConfig
    audit_reason: str = Field(min_length=8, max_length=500)


class AuditReasonRequest(ApiModel):
    audit_reason: str = Field(min_length=8, max_length=500)


class NoticeWriteRequest(ApiModel):
    title: str = Field(min_length=1, max_length=160)
    body: str = Field(min_length=1, max_length=20_000)
    notice_type: Literal["GENERAL", "MAINTENANCE", "PROMOTION", "SECURITY"]
    target_platforms: list[Literal["ANDROID", "ADMIN_WEB"]] = Field(min_length=1)
    target_locales: list[str]
    min_client_version: str | None = Field(default=None, max_length=64)
    max_client_version: str | None = Field(default=None, max_length=64)
    display_frequency: Literal["ONCE", "ONCE_PER_VERSION", "EVERY_LAUNCH"]
    starts_at: datetime
    ends_at: datetime | None = None
    audit_reason: str = Field(min_length=8, max_length=500)

    @model_validator(mode="after")
    def validate_window(self) -> "NoticeWriteRequest":
        if self.ends_at is not None and self.ends_at <= self.starts_at:
            raise ValueError("endsAt must be later than startsAt")
        if len(self.target_platforms) != len(set(self.target_platforms)):
            raise ValueError("targetPlatforms must be unique")
        if len(self.target_locales) != len(set(self.target_locales)):
            raise ValueError("targetLocales must be unique")
        return self


class NoticeVersionData(ApiModel):
    notice_version_id: str
    notice_id: str
    version: int
    status: Literal["DRAFT", "PUBLISHED", "SUPERSEDED", "REVOKED"]
    title: str
    body: str
    notice_type: str
    target_platforms: list[str]
    target_locales: list[str]
    min_client_version: str | None
    max_client_version: str | None
    display_frequency: str
    starts_at: datetime
    ends_at: datetime | None
    resource_version: int
    created_by_admin_id: str
    published_by_admin_id: str | None
    published_at: datetime | None
    revoked_at: datetime | None
    created_at: datetime
    updated_at: datetime


class NoticeListData(ApiModel):
    items: list[NoticeVersionData]


AdminUserListResponse = SuccessEnvelope[AdminUserListData]
AdminUserResponse = SuccessEnvelope[AdminUserSummaryData]
AdminUserDetailResponse = SuccessEnvelope[AdminUserDetailData]
AdminUserEntitlementResponse = SuccessEnvelope[AdminUserEntitlementBundleData]
AdminWalletLedgerListResponse = SuccessEnvelope[AdminWalletLedgerListData]
SystemConfigResponse = SuccessEnvelope[SystemConfigVersionData]
NoticeResponse = SuccessEnvelope[NoticeVersionData]
NoticeListResponse = SuccessEnvelope[NoticeListData]
