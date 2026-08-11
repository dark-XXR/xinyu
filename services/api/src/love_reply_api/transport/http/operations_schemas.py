from datetime import datetime

from pydantic import Field

from love_reply_api.schemas import ApiModel, SuccessEnvelope


class LogicalModelData(ApiModel):
    model_id: str
    display_name: str
    description: str | None
    enabled: bool


class ReplyStyleData(ApiModel):
    style_id: str
    display_name: str
    enabled: bool


class GenerationPolicyData(ApiModel):
    default_model_id: str
    quote_ttl_seconds: int = Field(ge=30, le=1800)


class FreeEntitlementTemplateData(ApiModel):
    plan_code: str
    text_quota: int = Field(ge=0)
    vision_quota: int = Field(ge=0)
    allowed_model_ids: list[str]
    allowed_style_ids: list[str]


class AppBootstrapData(ApiModel):
    config_version: int = Field(ge=1)
    published_at: datetime
    models: list[LogicalModelData]
    styles: list[ReplyStyleData]
    generation_policy: GenerationPolicyData
    free_entitlement: FreeEntitlementTemplateData
    feature_flags: dict[str, bool]
    site_identity: dict[str, object]


AppBootstrapResponse = SuccessEnvelope[AppBootstrapData]
