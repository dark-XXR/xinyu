from datetime import datetime

from pydantic import Field

from love_reply_api.schemas import ApiModel, SuccessEnvelope


class AdminLoginRequest(ApiModel):
    login_name: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=8, max_length=1024)


class AdminMfaChallengeData(ApiModel):
    challenge_id: str
    allowed_methods: list[str]
    expires_at: datetime
    attempts_remaining: int


class AdminLoginData(ApiModel):
    mfa_required: bool
    mfa_challenge: AdminMfaChallengeData


class AdminMfaVerifyRequest(ApiModel):
    challenge_id: str = Field(min_length=8, max_length=128)
    method: str
    code: str = Field(min_length=6, max_length=64)


class AdminRefreshRequest(ApiModel):
    refresh_token: str = Field(min_length=32, max_length=4096)


class AdminRoleData(ApiModel):
    role_id: str
    role_code: str
    display_name: str


class AdminIdentityData(ApiModel):
    admin_id: str
    login_name: str
    display_name: str
    account_status: str
    mfa_status: str
    mfa_methods: list[str]
    roles: list[AdminRoleData]
    permissions: list[str]
    last_login_at: datetime | None
    resource_version: int
    created_at: datetime
    updated_at: datetime


class AdminSessionData(ApiModel):
    session_id: str
    mfa_verified_at: datetime
    created_at: datetime
    last_seen_at: datetime
    expires_at: datetime


class AdminTokenPairData(ApiModel):
    token_type: str
    access_token: str
    access_token_expires_at: datetime
    refresh_token: str
    refresh_token_expires_at: datetime


class AdminAuthenticationData(ApiModel):
    tokens: AdminTokenPairData
    admin: AdminIdentityData
    session: AdminSessionData


class AdminTokenData(ApiModel):
    tokens: AdminTokenPairData
    session: AdminSessionData


class AdminMeData(ApiModel):
    admin: AdminIdentityData
    session: AdminSessionData


class AdminEmptyData(ApiModel):
    pass


AdminLoginResponse = SuccessEnvelope[AdminLoginData]
AdminAuthenticationResponse = SuccessEnvelope[AdminAuthenticationData]
AdminTokenResponse = SuccessEnvelope[AdminTokenData]
AdminMeResponse = SuccessEnvelope[AdminMeData]
AdminEmptyResponse = SuccessEnvelope[AdminEmptyData]
