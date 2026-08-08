from datetime import datetime

from pydantic import Field

from love_reply_api.schemas import ApiModel, SuccessEnvelope


class SmsSendRequest(ApiModel):
    phone_number: str = Field(pattern=r"^[0-9]{6,15}$")
    country_code: str = Field(pattern=r"^\+[1-9][0-9]{0,3}$")
    purpose: str = Field(pattern=r"^LOGIN$")
    captcha_token: str | None = Field(default=None, max_length=2048)


class SmsChallengeData(ApiModel):
    challenge_id: str
    expires_at: datetime
    resend_after_seconds: int


class SmsLoginRequest(ApiModel):
    challenge_id: str
    code: str = Field(pattern=r"^[0-9]{4,8}$")


class RefreshRequest(ApiModel):
    refresh_token: str


class TokenData(ApiModel):
    access_token: str
    access_token_expires_at: datetime
    refresh_token: str
    refresh_token_expires_at: datetime


class UserData(ApiModel):
    user_id: str
    status: str
    nickname: str | None = None
    avatar_url: str | None = None
    locale: str
    time_zone: str
    resource_version: int
    created_at: datetime
    updated_at: datetime


class UpdateUserRequest(ApiModel):
    nickname: str | None = Field(default=None, max_length=64)
    avatar_url: str | None = None
    locale: str | None = Field(default=None, max_length=35)
    time_zone: str | None = Field(default=None, max_length=64)


class DeviceData(ApiModel):
    device_id: str
    platform: str
    model: str | None
    current: bool
    last_seen_at: datetime
    created_at: datetime


class DeviceListData(ApiModel):
    items: list[DeviceData]


class ConsentData(ApiModel):
    consent_type: str
    document_version: str
    granted: bool
    required: bool
    granted_at: datetime | None
    resource_version: int
    updated_at: datetime


class ConsentListData(ApiModel):
    items: list[ConsentData]


class UpdateConsentRequest(ApiModel):
    document_version: str
    granted: bool


class DataRequestData(ApiModel):
    request_id: str
    job_id: str | None
    request_type: str
    status: str
    download_url: str | None
    expires_at: datetime | None
    rejection_reason_code: str | None
    created_at: datetime
    updated_at: datetime


class DeletionRequest(ApiModel):
    confirmation: str = Field(pattern=r"^DELETE_MY_ACCOUNT$")
    reason_code: str


class DeletionStatusData(DataRequestData):
    cooling_off_ends_at: datetime
    estimated_completion_at: datetime | None
    blockers: list[str]


class PendingConsentData(ApiModel):
    consent_type: str
    document_version: str
    required: bool


class LoginData(ApiModel):
    tokens: TokenData
    user: UserData
    pending_consents: list[PendingConsentData]


class EmptyData(ApiModel):
    pass


SmsChallengeResponse = SuccessEnvelope[SmsChallengeData]
LoginResponse = SuccessEnvelope[LoginData]
TokenResponse = SuccessEnvelope[TokenData]
EmptyResponse = SuccessEnvelope[EmptyData]
UserResponse = SuccessEnvelope[UserData]
DeviceListResponse = SuccessEnvelope[DeviceListData]
ConsentListResponse = SuccessEnvelope[ConsentListData]
ConsentResponse = SuccessEnvelope[ConsentData]
DataRequestResponse = SuccessEnvelope[DataRequestData]
DeletionStatusResponse = SuccessEnvelope[DeletionStatusData]
