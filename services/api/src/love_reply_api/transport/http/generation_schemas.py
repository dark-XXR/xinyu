from datetime import datetime
from typing import Literal

from pydantic import Field, field_validator

from love_reply_api.schemas import ApiModel, SuccessEnvelope


class GenerationInputData(ApiModel):
    text: str = Field(min_length=1, max_length=12000)
    attachment_ids: list[str] = Field(max_length=10)
    confirmed_ocr_version: int | None = Field(default=None, ge=1)


class GenerationContextData(ApiModel):
    target_profile_id: str | None = None
    relationship_stage: Literal[
        "MATCHING",
        "DATING",
        "AMBIGUOUS",
        "IN_RELATIONSHIP",
        "CONFLICT",
        "NO_CONTACT",
        "OTHER",
    ]
    communication_goal: Literal[
        "START_CONVERSATION",
        "KEEP_CONVERSATION",
        "ACCEPT_INVITATION",
        "DECLINE_POLITELY",
        "INVITE_DATE",
        "APOLOGIZE",
        "SET_BOUNDARY",
        "RESOLVE_CONFLICT",
        "OTHER",
    ]
    style_ids: list[str] = Field(min_length=1, max_length=5)
    additional_context: str | None = Field(default=None, max_length=2000)

    @field_validator("style_ids")
    @classmethod
    def validate_unique_styles(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("styleIds must contain unique values")
        return value


class GenerationQuoteRequest(ApiModel):
    input: GenerationInputData
    context: GenerationContextData
    requested_model_id: str | None = None
    save_to_history: bool


class ModelQuoteOptionData(ApiModel):
    model_id: str
    energy_amount: int = Field(ge=1)
    available: bool
    recommended: bool
    unavailable_reason_code: str | None = None


class GenerationQuoteData(ApiModel):
    quote_id: str
    model_options: list[ModelQuoteOptionData] = Field(min_length=1)
    selected_model_id: str
    estimated_energy_amount: int = Field(ge=1)
    charged_from: Literal["SUBSCRIPTION", "WALLET", "SUBSCRIPTION_THEN_WALLET"]
    entitlement_version: int = Field(ge=1)
    expires_at: datetime


class CreateGenerationRequest(ApiModel):
    client_request_id: str = Field(min_length=8, max_length=128)
    input: GenerationInputData
    context: GenerationContextData
    model_id: str
    save_to_history: bool
    quote_id: str


class RegenerateRequest(ApiModel):
    quote_id: str
    client_request_id: str


class CandidateData(ApiModel):
    candidate_id: str
    strategy: Literal["SAFE", "PUSH_PULL", "DIRECT"]
    style_id: str
    text: str = Field(max_length=4000)
    safety_status: Literal["PENDING", "PASSED", "BLOCKED", "REVIEW_REQUIRED"]


class GenerationAnalysisData(ApiModel):
    possible_intent: str = Field(max_length=1000)
    emotion: str = Field(max_length=500)
    uncertainty_note: str = Field(max_length=500)
    risk_tips: list[str] = Field(max_length=10)


class GenerationUsageData(ApiModel):
    model_id: str
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    reserved_energy: int = Field(ge=0)
    charged_energy: int = Field(ge=0)
    charged_from: Literal["SUBSCRIPTION", "WALLET", "SUBSCRIPTION_THEN_WALLET"]


class GenerationSnapshotData(ApiModel):
    generation_id: str
    parent_generation_id: str | None
    status: Literal[
        "CREATED",
        "QUOTA_RESERVED",
        "PARSING",
        "ANALYZING",
        "GENERATING",
        "FILTERING",
        "SUCCEEDED",
        "FAILED",
        "CANCELLED",
    ]
    analysis: GenerationAnalysisData | None
    candidates: list[CandidateData] = Field(max_length=3)
    usage: GenerationUsageData | None
    failure_code: str | None
    risk_event_id: str | None
    resource_version: int = Field(ge=1)
    created_at: datetime
    updated_at: datetime


GenerationQuoteResponse = SuccessEnvelope[GenerationQuoteData]
GenerationResponse = SuccessEnvelope[GenerationSnapshotData]
