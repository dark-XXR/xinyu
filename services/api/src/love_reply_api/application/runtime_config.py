from datetime import datetime
from string import Formatter
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from love_reply_api.application.errors import ApiError
from love_reply_api.infrastructure.runtime_config_records import RuntimeConfigVersionRecord


class LogicalModelConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_id: str
    display_name: str
    description: str | None = None
    enabled: bool


class ReplyStyleConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    style_id: str
    display_name: str
    enabled: bool


class GenerationPolicyConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    default_model_id: str
    quote_ttl_seconds: int = Field(ge=30, le=1800)


class FreeEntitlementConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plan_code: str
    text_quota: int = Field(ge=0)
    vision_quota: int = Field(ge=0)
    allowed_model_ids: list[str] = Field(min_length=1)
    allowed_style_ids: list[str] = Field(min_length=1)


AuthChannel = Literal["EMAIL", "SMS"]


class AuthChallengePolicyConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool
    challenge_ttl_seconds: int = Field(ge=60, le=3600)
    resend_after_seconds: int = Field(ge=1, le=3600)
    max_attempts: int = Field(ge=1, le=20)


class AuthPolicyConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    primary_channel: AuthChannel
    fallback_channels: list[AuthChannel]
    channels: dict[AuthChannel, AuthChallengePolicyConfig]
    policy_version: int = Field(ge=1)

    @model_validator(mode="after")
    def validate_channels(self) -> "AuthPolicyConfig":
        if set(self.channels) != {"EMAIL", "SMS"}:
            raise ValueError("auth policy must configure EMAIL and SMS")
        if self.primary_channel in self.fallback_channels:
            raise ValueError("primary auth channel cannot also be a fallback")
        if len(self.fallback_channels) != len(set(self.fallback_channels)):
            raise ValueError("fallback auth channels must be unique")
        return self


class EmailTemplateVariantConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject: str = Field(min_length=1, max_length=200)
    text_template: str = Field(min_length=1, max_length=10_000)
    html_template: str | None = Field(default=None, max_length=50_000)

    @field_validator("subject")
    @classmethod
    def reject_header_injection(cls, value: str) -> str:
        if "\r" in value or "\n" in value:
            raise ValueError("email subject cannot contain line breaks")
        return value

    @model_validator(mode="after")
    def validate_placeholders(self) -> "EmailTemplateVariantConfig":
        formatter = Formatter()
        values = [self.subject, self.text_template]
        if self.html_template is not None:
            values.append(self.html_template)
        fields: list[str] = []
        try:
            for value in values:
                fields.extend(
                    field_name
                    for _, field_name, _, _ in formatter.parse(value)
                    if field_name is not None
                )
        except ValueError as exc:
            raise ValueError("email template contains invalid formatting") from exc
        if not fields or "code" not in fields or set(fields) != {"code"}:
            raise ValueError("email template may contain only the required {code} placeholder")
        return self


class LocalizedEmailTemplateConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    default_locale: str = Field(min_length=2, max_length=35)
    locales: dict[str, EmailTemplateVariantConfig] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_default_locale(self) -> "LocalizedEmailTemplateConfig":
        if self.default_locale not in self.locales:
            raise ValueError("default email template locale is missing")
        return self

    def for_locale(self, locale: str) -> EmailTemplateVariantConfig:
        exact = self.locales.get(locale)
        if exact is not None:
            return exact
        language = locale.split("-", 1)[0]
        return self.locales.get(language, self.locales[self.default_locale])


class AuthTemplatesConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email_login: LocalizedEmailTemplateConfig


class PublishedRuntimeConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    config_version: int = Field(ge=1)
    published_at: datetime
    models: list[LogicalModelConfig] = Field(min_length=1)
    styles: list[ReplyStyleConfig] = Field(min_length=1)
    generation_policy: GenerationPolicyConfig
    free_entitlement: FreeEntitlementConfig
    auth_policy: AuthPolicyConfig
    auth_templates: AuthTemplatesConfig
    feature_flags: dict[str, bool]

    @model_validator(mode="after")
    def validate_references(self) -> "PublishedRuntimeConfig":
        enabled_models = {item.model_id for item in self.models if item.enabled}
        enabled_styles = {item.style_id for item in self.styles if item.enabled}
        if self.generation_policy.default_model_id not in enabled_models:
            raise ValueError("default model must reference an enabled logical model")
        if not set(self.free_entitlement.allowed_model_ids) <= enabled_models:
            raise ValueError("free entitlement contains an unavailable logical model")
        if not set(self.free_entitlement.allowed_style_ids) <= enabled_styles:
            raise ValueError("free entitlement contains an unavailable reply style")
        if len(self.free_entitlement.allowed_model_ids) != len(
            set(self.free_entitlement.allowed_model_ids)
        ):
            raise ValueError("free entitlement model identifiers must be unique")
        if len(self.free_entitlement.allowed_style_ids) != len(
            set(self.free_entitlement.allowed_style_ids)
        ):
            raise ValueError("free entitlement style identifiers must be unique")
        return self


class RuntimeConfigService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_published(self) -> PublishedRuntimeConfig:
        record = await self._session.scalar(
            select(RuntimeConfigVersionRecord)
            .where(
                RuntimeConfigVersionRecord.status == "PUBLISHED",
                RuntimeConfigVersionRecord.published_at.is_not(None),
            )
            .order_by(RuntimeConfigVersionRecord.version.desc())
            .limit(1)
        )
        if record is None or record.published_at is None:
            raise ApiError(
                status_code=503,
                code="APP_CONFIG_UNAVAILABLE",
                message="No published application configuration is available.",
                retryable=True,
            )
        try:
            return PublishedRuntimeConfig(
                config_version=record.version,
                published_at=record.published_at,
                models=record.models,
                styles=record.styles,
                generation_policy=record.generation_policy,
                free_entitlement=record.free_entitlement,
                auth_policy=record.auth_policy,
                auth_templates=record.auth_templates,
                feature_flags=record.feature_flags,
            )
        except ValueError as exc:
            raise ApiError(
                status_code=503,
                code="APP_CONFIG_INVALID",
                message="The published application configuration is invalid.",
                retryable=False,
            ) from exc
