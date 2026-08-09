from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from love_reply_api.infrastructure.database import Base


class AiModelMappingRecord(Base):
    __tablename__ = "ai_model_mappings"

    model_mapping_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    logical_model_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    provider_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("providers.provider_id", ondelete="RESTRICT"), nullable=False
    )
    provider_model_name: Mapped[str] = mapped_column(String(256), nullable=False)
    input_modalities: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    output_modalities: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    context_window_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    max_output_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    input_cost_microunits_per_million_tokens: Mapped[int] = mapped_column(
        BigInteger, nullable=False
    )
    output_cost_microunits_per_million_tokens: Mapped[int] = mapped_column(
        BigInteger, nullable=False
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    quality_tier: Mapped[str | None] = mapped_column(String(64))
    data_region: Mapped[str | None] = mapped_column(String(64))
    retention_policy: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    resource_version: Mapped[int] = mapped_column(BigInteger, nullable=False)
    effective_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AiRouteRecord(Base):
    __tablename__ = "ai_routes"

    route_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    scenario: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    logical_model_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    targets: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    max_input_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    max_output_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    budget_ceiling_microunits: Mapped[int] = mapped_column(BigInteger, nullable=False)
    total_attempt_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    safety_policy_id: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    rollout_percentage: Mapped[int] = mapped_column(Integer, nullable=False)
    effective_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_version: Mapped[int | None] = mapped_column(Integer)
    published_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    published_rollout_percentage: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    published_effective_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resource_version: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AiPromptRecord(Base):
    __tablename__ = "ai_prompts"

    prompt_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    prompt_code: Mapped[str] = mapped_column(String(64), nullable=False)
    scenario: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    system_template: Mapped[str] = mapped_column(Text, nullable=False)
    user_template: Mapped[str] = mapped_column(Text, nullable=False)
    allowed_input_fields: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    output_schema: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    safety_policy_id: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    effective_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_version: Mapped[int | None] = mapped_column(Integer)
    published_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    published_rollout_percentage: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    published_effective_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resource_version: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AiRiskPolicyRecord(Base):
    __tablename__ = "ai_risk_policies"

    risk_policy_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    policy_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    blocked_categories: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    review_categories: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    input_moderation_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    output_moderation_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    prompt_injection_action: Mapped[str] = mapped_column(String(32), nullable=False)
    minimum_safety_score: Mapped[float] = mapped_column(Float, nullable=False)
    allow_appeals: Mapped[bool] = mapped_column(Boolean, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    effective_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_version: Mapped[int | None] = mapped_column(Integer)
    published_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    published_rollout_percentage: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    published_effective_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resource_version: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AiResourceVersionRecord(Base):
    __tablename__ = "ai_resource_versions"
    __table_args__ = (
        UniqueConstraint(
            "resource_type",
            "resource_id",
            "version",
            name="uq_ai_resource_version_number",
        ),
    )

    resource_version_id: Mapped[str] = mapped_column(String(96), primary_key=True)
    resource_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    resource_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    was_published: Mapped[bool] = mapped_column(Boolean, nullable=False)
    rollout_percentage: Mapped[int | None] = mapped_column(Integer)
    effective_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    created_by_admin_id: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AiEvaluationRunRecord(Base):
    __tablename__ = "ai_evaluation_runs"

    evaluation_run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    prompt_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    prompt_version: Mapped[int] = mapped_column(Integer, nullable=False)
    prompt_resource_version: Mapped[int] = mapped_column(BigInteger, nullable=False)
    route_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    route_version: Mapped[int] = mapped_column(Integer, nullable=False)
    route_resource_version: Mapped[int] = mapped_column(BigInteger, nullable=False)
    risk_policy_versions: Mapped[dict[str, int]] = mapped_column(JSON, nullable=False)
    suite_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    evaluator_logical_model_id: Mapped[str] = mapped_column(String(64), nullable=False)
    max_cost_microunits: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    total_cases: Mapped[int] = mapped_column(Integer, nullable=False)
    completed_cases: Mapped[int] = mapped_column(Integer, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    safety_passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    cost_microunits: Mapped[int] = mapped_column(BigInteger, nullable=False)
    failure_code: Mapped[str | None] = mapped_column(String(64))
    created_by_admin_id: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AiAuditRecord(Base):
    __tablename__ = "ai_audit_records"

    audit_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    resource_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    resource_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    admin_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    audit_reason: Mapped[str] = mapped_column(String(500), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AiGatewayAttemptRecord(Base):
    __tablename__ = "ai_gateway_attempts"

    attempt_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    routing_key_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    route_id: Mapped[str] = mapped_column(String(64), nullable=False)
    route_version: Mapped[int] = mapped_column(Integer, nullable=False)
    model_mapping_id: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_id: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_resource_version: Mapped[int] = mapped_column(BigInteger, nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(64))
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    cost_microunits: Mapped[int | None] = mapped_column(BigInteger)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
