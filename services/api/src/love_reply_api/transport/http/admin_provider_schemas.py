from datetime import datetime
from typing import Any, Literal

from pydantic import (
    AnyHttpUrl,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)

from love_reply_api.schemas import ApiModel, SuccessEnvelope


class StrictApiModel(ApiModel):
    model_config = ConfigDict(extra="forbid")


class OpenAiCompatibleConfiguration(StrictApiModel):
    adapter_type: Literal["OPENAI_COMPAT"]
    base_url: AnyHttpUrl
    organization: str | None = Field(default=None, max_length=128)
    project: str | None = Field(default=None, max_length=128)
    timeout_ms: int = Field(ge=1000, le=120_000)

    @field_validator("base_url")
    @classmethod
    def require_https(cls, value: AnyHttpUrl) -> AnyHttpUrl:
        if value.scheme != "https":
            raise ValueError("provider URLs must use HTTPS")
        if value.username is not None or value.password is not None:
            raise ValueError("provider URLs cannot contain credentials")
        return value


class NativeAiConfiguration(StrictApiModel):
    adapter_type: Literal["OPENAI", "ANTHROPIC", "GEMINI"]
    base_url: AnyHttpUrl | None = None
    timeout_ms: int = Field(ge=1000, le=120_000)

    @field_validator("base_url")
    @classmethod
    def require_https(cls, value: AnyHttpUrl | None) -> AnyHttpUrl | None:
        if value is not None and value.scheme != "https":
            raise ValueError("provider URLs must use HTTPS")
        if value is not None and (value.username is not None or value.password is not None):
            raise ValueError("provider URLs cannot contain credentials")
        return value


class SmtpConfiguration(StrictApiModel):
    adapter_type: Literal["SMTP"]
    host: str = Field(pattern=r"^[A-Za-z0-9](?:[A-Za-z0-9.-]{0,251}[A-Za-z0-9])?$")
    port: int = Field(ge=1, le=65_535)
    tls_mode: Literal["REQUIRED", "STARTTLS", "IMPLICIT"]
    sender_address: EmailStr
    sender_name: str = Field(min_length=1, max_length=128)
    reply_to_address: EmailStr | None = None
    timeout_ms: int = Field(ge=1000, le=60_000)


class EmailApiConfiguration(StrictApiModel):
    adapter_type: Literal["SES_API", "SENDGRID_API", "RESEND_API", "MAILGUN_API"]
    region: str | None = Field(default=None, max_length=64)
    base_url: AnyHttpUrl | None = None
    sender_address: EmailStr
    sender_name: str = Field(min_length=1, max_length=128)
    timeout_ms: int = Field(ge=1000, le=60_000)

    @field_validator("base_url")
    @classmethod
    def require_https(cls, value: AnyHttpUrl | None) -> AnyHttpUrl | None:
        if value is not None and value.scheme != "https":
            raise ValueError("provider URLs must use HTTPS")
        if value is not None and (value.username is not None or value.password is not None):
            raise ValueError("provider URLs cannot contain credentials")
        return value


class SmsConfiguration(StrictApiModel):
    adapter_type: Literal["ALIYUN_SMS", "TENCENT_SMS"]
    region: str = Field(min_length=1, max_length=64)
    application_id: str | None = Field(default=None, max_length=128)
    signature_id: str = Field(min_length=1, max_length=128)
    template_id: str = Field(min_length=1, max_length=128)
    timeout_ms: int = Field(ge=1000, le=60_000)


class EpayConfiguration(StrictApiModel):
    adapter_type: Literal["EPAY_COMPAT"]
    gateway_base_url: AnyHttpUrl
    submit_path: str = Field(pattern=r"^/[A-Za-z0-9/_-]+$")
    query_path: str = Field(pattern=r"^/[A-Za-z0-9/_-]+$")
    refund_path: str = Field(pattern=r"^/[A-Za-z0-9/_-]+$")
    merchant_id: str = Field(min_length=1, max_length=128)
    application_id: str | None = Field(default=None, max_length=128)
    payment_types: list[Literal["ALIPAY", "WECHAT_PAY"]] = Field(min_length=1)
    signing_preset: Literal["EPAY_MD5_CANONICAL"]
    callback_ack_text: str = Field(min_length=1, max_length=32)
    timeout_ms: int = Field(ge=1000, le=60_000)

    @field_validator("gateway_base_url")
    @classmethod
    def require_https(cls, value: AnyHttpUrl) -> AnyHttpUrl:
        if value.scheme != "https":
            raise ValueError("provider URLs must use HTTPS")
        if value.username is not None or value.password is not None:
            raise ValueError("provider URLs cannot contain credentials")
        return value

    @model_validator(mode="after")
    def unique_payment_types(self) -> "EpayConfiguration":
        if len(self.payment_types) != len(set(self.payment_types)):
            raise ValueError("payment types must be unique")
        return self


CONFIGURATION_MODELS: dict[str, type[StrictApiModel]] = {
    "OPENAI_COMPAT": OpenAiCompatibleConfiguration,
    "OPENAI": NativeAiConfiguration,
    "ANTHROPIC": NativeAiConfiguration,
    "GEMINI": NativeAiConfiguration,
    "SMTP": SmtpConfiguration,
    "SES_API": EmailApiConfiguration,
    "SENDGRID_API": EmailApiConfiguration,
    "RESEND_API": EmailApiConfiguration,
    "MAILGUN_API": EmailApiConfiguration,
    "ALIYUN_SMS": SmsConfiguration,
    "TENCENT_SMS": SmsConfiguration,
    "EPAY_COMPAT": EpayConfiguration,
}

ADAPTER_KINDS = {
    "OPENAI_COMPAT": "AI",
    "OPENAI": "AI",
    "ANTHROPIC": "AI",
    "GEMINI": "AI",
    "SMTP": "EMAIL",
    "SES_API": "EMAIL",
    "SENDGRID_API": "EMAIL",
    "RESEND_API": "EMAIL",
    "MAILGUN_API": "EMAIL",
    "ALIYUN_SMS": "SMS",
    "TENCENT_SMS": "SMS",
    "EPAY_COMPAT": "PAYMENT",
}


def validate_configuration(*, kind: str, configuration: dict[str, Any]) -> dict[str, Any]:
    adapter_value = configuration.get("adapterType")
    if not isinstance(adapter_value, str):
        raise ValueError("adapter type is required")
    adapter_type = adapter_value
    model_type = CONFIGURATION_MODELS.get(adapter_type)
    if model_type is None or ADAPTER_KINDS[adapter_type] != kind:
        raise ValueError("adapter type does not match provider kind")
    model = model_type.model_validate(configuration)
    return dict(model.model_dump(mode="json", by_alias=True))


class ProviderWriteRequest(StrictApiModel):
    provider_name: str = Field(min_length=1, max_length=128)
    kind: Literal["AI", "EMAIL", "SMS", "PAYMENT"]
    configuration: dict[str, Any]
    data_region: str | None = Field(default=None, max_length=64)
    retention_statement: str | None = Field(default=None, max_length=500)
    retry_limit: int = Field(ge=0, le=3)
    priority: int = Field(ge=0, le=1000)

    @model_validator(mode="after")
    def validate_adapter(self) -> "ProviderWriteRequest":
        self.configuration = validate_configuration(
            kind=self.kind,
            configuration=self.configuration,
        )
        return self


class CredentialSecretInput(StrictApiModel):
    name: Literal[
        "apiKey",
        "username",
        "password",
        "accessKeyId",
        "accessKeySecret",
        "secretId",
        "secretKey",
        "merchantKey",
    ]
    value: str = Field(min_length=1, max_length=8192)


class RotateCredentialsRequest(StrictApiModel):
    secrets: list[CredentialSecretInput] = Field(min_length=1, max_length=8)
    audit_reason: str = Field(min_length=8, max_length=500)

    @model_validator(mode="after")
    def unique_names(self) -> "RotateCredentialsRequest":
        names = [item.name for item in self.secrets]
        if len(names) != len(set(names)):
            raise ValueError("credential names must be unique")
        return self


class HealthCheckRequest(StrictApiModel):
    administrator_test_destination: str | None = Field(default=None, max_length=254)
    audit_reason: str = Field(min_length=8, max_length=500)


class PublishProviderRequest(StrictApiModel):
    rollout_percentage: int = Field(ge=1, le=100)
    effective_at: datetime
    audit_reason: str = Field(min_length=8, max_length=500)

    @field_validator("effective_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("effectiveAt must include a time-zone offset")
        return value


class RollbackProviderRequest(StrictApiModel):
    target_resource_version: int = Field(ge=1)
    audit_reason: str = Field(min_length=8, max_length=500)


class ProviderData(ApiModel):
    provider_id: str
    provider_name: str
    kind: str
    status: str
    configuration: dict[str, Any]
    data_region: str | None
    retention_statement: str | None
    retry_limit: int
    priority: int
    rollout_percentage: int
    credential_configured: bool
    credential_fingerprint: str | None
    credential_rotated_at: datetime | None
    last_health_status: str | None
    effective_at: datetime | None
    resource_version: int
    created_at: datetime
    updated_at: datetime


class ProviderListData(ApiModel):
    items: list[ProviderData]
    next_cursor: str | None
    has_more: bool


class CredentialRotationData(ApiModel):
    credential_version_id: str
    fingerprint: str
    rotated_at: datetime
    resource_version: int


class ProviderHealthCheckData(ApiModel):
    health_check_id: str
    status: str
    started_at: datetime
    completed_at: datetime
    latency_ms: int | None
    redacted_summary: str
    provider_request_id: str | None


ProviderResponse = SuccessEnvelope[ProviderData]
ProviderListResponse = SuccessEnvelope[ProviderListData]
CredentialRotationResponse = SuccessEnvelope[CredentialRotationData]
ProviderHealthCheckResponse = SuccessEnvelope[ProviderHealthCheckData]
