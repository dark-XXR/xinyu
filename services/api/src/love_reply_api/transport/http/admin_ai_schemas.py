"""AI 管理接口的请求校验与响应模型。"""

from datetime import datetime
from string import Formatter
from typing import Any, Literal

from pydantic import ConfigDict, Field, field_validator, model_validator

from love_reply_api.schemas import ApiModel, SuccessEnvelope


class StrictApiModel(ApiModel):
    model_config = ConfigDict(extra="forbid")


class AiModelMappingWriteRequest(StrictApiModel):
    logical_model_id: str = Field(pattern=r"^[a-z][a-z0-9_]{1,63}$")
    provider_id: str = Field(min_length=1, max_length=64)
    provider_model_name: str = Field(min_length=1, max_length=256)
    input_modalities: list[Literal["TEXT", "IMAGE"]] = Field(min_length=1)
    output_modalities: list[Literal["TEXT", "IMAGE"]] = Field(min_length=1)
    context_window_tokens: int = Field(ge=1, le=10_000_000)
    max_output_tokens: int = Field(ge=1, le=1_000_000)
    input_cost_microunits_per_million_tokens: int = Field(ge=0)
    output_cost_microunits_per_million_tokens: int = Field(ge=0)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    quality_tier: str | None = Field(default=None, max_length=64)
    data_region: str | None = Field(default=None, max_length=64)
    retention_policy: str | None = Field(default=None, max_length=500)
    enabled: bool

    @model_validator(mode="after")
    def validate_mapping(self) -> "AiModelMappingWriteRequest":
        if len(set(self.input_modalities)) != len(self.input_modalities):
            raise ValueError("input modalities must be unique")
        if len(set(self.output_modalities)) != len(self.output_modalities):
            raise ValueError("output modalities must be unique")
        if self.max_output_tokens > self.context_window_tokens:
            raise ValueError("max output tokens cannot exceed the context window")
        return self


class AiRouteTargetRequest(StrictApiModel):
    model_mapping_id: str = Field(min_length=1, max_length=64)
    priority: int = Field(ge=0, le=1000)
    timeout_ms: int = Field(ge=1000, le=120_000)
    retry_limit: int = Field(ge=0, le=3)


class AiRouteWriteRequest(StrictApiModel):
    scenario: Literal["REPLY_GENERATION", "REPLY_REFINEMENT", "SCREENSHOT_OCR", "SAFETY_EVALUATION"]
    logical_model_id: str = Field(pattern=r"^[a-z][a-z0-9_]{1,63}$")
    targets: list[AiRouteTargetRequest] = Field(min_length=1, max_length=16)
    max_input_tokens: int = Field(ge=1, le=10_000_000)
    max_output_tokens: int = Field(ge=1, le=1_000_000)
    budget_ceiling_microunits: int = Field(ge=0)
    total_attempt_limit: int = Field(ge=1, le=16)
    safety_policy_id: str = Field(min_length=1, max_length=64)

    @model_validator(mode="after")
    def validate_targets(self) -> "AiRouteWriteRequest":
        ids = [target.model_mapping_id for target in self.targets]
        priorities = [target.priority for target in self.targets]
        if len(ids) != len(set(ids)):
            raise ValueError("route model mappings must be unique")
        if len(priorities) != len(set(priorities)):
            raise ValueError("route target priorities must be unique")
        if self.total_attempt_limit > sum(target.retry_limit + 1 for target in self.targets):
            raise ValueError("total attempt limit exceeds configured target attempts")
        return self


def _validate_declarative_schema(value: dict[str, Any]) -> dict[str, Any]:
    forbidden_keys = {"eval", "script", "javascript", "function", "x-expression"}
    nodes = 0

    def visit(item: object, depth: int) -> None:
        nonlocal nodes
        nodes += 1
        if depth > 32 or nodes > 10_000:
            raise ValueError("output schema is too complex")
        if isinstance(item, dict):
            for key, child in item.items():
                if not isinstance(key, str):
                    raise ValueError("output schema keys must be strings")
                if key.lower() in forbidden_keys:
                    raise ValueError("output schema must be declarative")
                visit(child, depth + 1)
        elif isinstance(item, list):
            for child in item:
                visit(child, depth + 1)
        elif item is not None and not isinstance(item, (str, int, float, bool)):
            raise ValueError("output schema contains a non-JSON value")

    visit(value, 0)
    return value


class AiPromptWriteRequest(StrictApiModel):
    prompt_code: str = Field(pattern=r"^[A-Z][A-Z0-9_]{1,63}$")
    scenario: Literal["REPLY_GENERATION", "REPLY_REFINEMENT", "SCREENSHOT_OCR", "SAFETY_EVALUATION"]
    system_template: str = Field(min_length=1, max_length=50_000)
    user_template: str = Field(min_length=1, max_length=50_000)
    allowed_input_fields: list[str] = Field(min_length=1)
    output_schema: dict[str, Any]
    safety_policy_id: str | None = Field(default=None, max_length=64)

    @field_validator("allowed_input_fields")
    @classmethod
    def validate_fields(cls, value: list[str]) -> list[str]:
        import re

        if len(value) != len(set(value)):
            raise ValueError("allowed input fields must be unique")
        if not all(re.fullmatch(r"[a-z][A-Za-z0-9]{0,63}", item) for item in value):
            raise ValueError("allowed input field is invalid")
        return value

    @field_validator("output_schema")
    @classmethod
    def validate_output_schema(cls, value: dict[str, Any]) -> dict[str, Any]:
        return _validate_declarative_schema(value)

    @model_validator(mode="after")
    def validate_placeholders(self) -> "AiPromptWriteRequest":
        supported = {"inputJson", "contextJson"}
        formatter = Formatter()
        for template in (self.system_template, self.user_template):
            try:
                fields = {name for _, name, _, _ in formatter.parse(template) if name}
            except ValueError as exc:
                raise ValueError("prompt template braces are invalid") from exc
            if fields - supported:
                raise ValueError("prompt template contains unsupported placeholders")
        return self


class AiRiskPolicyWriteRequest(StrictApiModel):
    policy_code: str = Field(pattern=r"^[A-Z][A-Z0-9_]{1,63}$")
    blocked_categories: list[str]
    review_categories: list[str]
    input_moderation_enabled: bool
    output_moderation_enabled: bool
    prompt_injection_action: Literal["BLOCK", "REVIEW", "ALLOW_WITH_WARNING"]
    minimum_safety_score: float = Field(ge=0, le=1)
    allow_appeals: bool

    @model_validator(mode="after")
    def validate_categories(self) -> "AiRiskPolicyWriteRequest":
        import re

        all_items = self.blocked_categories + self.review_categories
        if not all(re.fullmatch(r"[A-Z][A-Z0-9_]*", item) for item in all_items):
            raise ValueError("risk category is invalid")
        if len(self.blocked_categories) != len(set(self.blocked_categories)):
            raise ValueError("blocked categories must be unique")
        if len(self.review_categories) != len(set(self.review_categories)):
            raise ValueError("review categories must be unique")
        if set(self.blocked_categories) & set(self.review_categories):
            raise ValueError("blocked and review categories cannot overlap")
        return self


class AiEvaluationRunRequest(StrictApiModel):
    prompt_id: str = Field(min_length=1, max_length=64)
    route_id: str = Field(min_length=1, max_length=64)
    suite_ids: list[str] = Field(min_length=1, max_length=50)
    evaluator_logical_model_id: str = Field(pattern=r"^[a-z][a-z0-9_]{1,63}$")
    max_cost_microunits: int = Field(ge=0)

    @field_validator("suite_ids")
    @classmethod
    def unique_suite_ids(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("evaluation suite ids must be unique")
        if any(not item or len(item) > 128 for item in value):
            raise ValueError("evaluation suite id is invalid")
        return value


class AiPublishRequest(StrictApiModel):
    rollout_percentage: int = Field(ge=1, le=100)
    effective_at: datetime
    evaluation_run_id: str = Field(min_length=1, max_length=64)
    audit_reason: str = Field(min_length=8, max_length=500)

    @field_validator("effective_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("effectiveAt must include a time-zone offset")
        return value


class AiRollbackRequest(StrictApiModel):
    target_version: int = Field(ge=1)
    audit_reason: str = Field(min_length=8, max_length=500)


class AiModelMappingData(ApiModel):
    model_mapping_id: str
    logical_model_id: str
    provider_id: str
    provider_model_name: str
    input_modalities: list[str]
    output_modalities: list[str]
    context_window_tokens: int
    max_output_tokens: int
    input_cost_microunits_per_million_tokens: int
    output_cost_microunits_per_million_tokens: int
    currency: str
    quality_tier: str | None
    data_region: str | None
    retention_policy: str | None
    status: str
    enabled: bool
    resource_version: int
    created_at: datetime
    updated_at: datetime


class AiRouteData(ApiModel):
    route_id: str
    version: int
    scenario: str
    logical_model_id: str
    targets: list[dict[str, Any]]
    max_input_tokens: int
    max_output_tokens: int
    budget_ceiling_microunits: int
    total_attempt_limit: int
    safety_policy_id: str
    status: str
    rollout_percentage: int
    effective_at: datetime | None
    resource_version: int
    created_at: datetime
    updated_at: datetime


class AiPromptData(ApiModel):
    prompt_id: str
    version: int
    prompt_code: str
    scenario: str
    system_template: str
    user_template: str
    allowed_input_fields: list[str]
    output_schema: dict[str, Any]
    safety_policy_id: str | None
    status: str
    effective_at: datetime | None
    resource_version: int
    created_at: datetime
    updated_at: datetime


class AiRiskPolicyData(ApiModel):
    risk_policy_id: str
    version: int
    policy_code: str
    blocked_categories: list[str]
    review_categories: list[str]
    input_moderation_enabled: bool
    output_moderation_enabled: bool
    prompt_injection_action: str
    minimum_safety_score: float
    allow_appeals: bool
    status: str
    effective_at: datetime | None
    resource_version: int
    created_at: datetime
    updated_at: datetime


class AiEvaluationRunData(ApiModel):
    evaluation_run_id: str
    prompt_id: str
    route_id: str
    suite_ids: list[str]
    status: str
    passed: bool
    total_cases: int
    completed_cases: int
    score: float
    safety_passed: bool
    cost_microunits: int
    failure_code: str | None
    created_at: datetime
    updated_at: datetime


class AiModelMappingListData(ApiModel):
    items: list[AiModelMappingData]
    next_cursor: str | None
    has_more: bool


class AiRouteListData(ApiModel):
    items: list[AiRouteData]
    next_cursor: str | None
    has_more: bool


class AiPromptListData(ApiModel):
    items: list[AiPromptData]
    next_cursor: str | None
    has_more: bool


class AiRiskPolicyListData(ApiModel):
    items: list[AiRiskPolicyData]
    next_cursor: str | None
    has_more: bool


AiModelMappingResponse = SuccessEnvelope[AiModelMappingData]
AiModelMappingListResponse = SuccessEnvelope[AiModelMappingListData]
AiRouteResponse = SuccessEnvelope[AiRouteData]
AiRouteListResponse = SuccessEnvelope[AiRouteListData]
AiPromptResponse = SuccessEnvelope[AiPromptData]
AiPromptListResponse = SuccessEnvelope[AiPromptListData]
AiRiskPolicyResponse = SuccessEnvelope[AiRiskPolicyData]
AiRiskPolicyListResponse = SuccessEnvelope[AiRiskPolicyListData]
AiEvaluationRunResponse = SuccessEnvelope[AiEvaluationRunData]
