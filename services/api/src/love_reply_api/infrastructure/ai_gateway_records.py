from datetime import datetime
from typing import Any

from sqlalchemy import JSON, BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text
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
    resource_version: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


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
