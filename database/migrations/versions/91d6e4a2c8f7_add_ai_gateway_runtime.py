"""add configurable AI gateway runtime

Revision ID: 91d6e4a2c8f7
Revises: b7e3c19a5d40
Create Date: 2026-08-09 16:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "91d6e4a2c8f7"
down_revision: str | None = "b7e3c19a5d40"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ai_model_mappings",
        sa.Column("model_mapping_id", sa.String(length=64), nullable=False),
        sa.Column("logical_model_id", sa.String(length=64), nullable=False),
        sa.Column("provider_id", sa.String(length=64), nullable=False),
        sa.Column("provider_model_name", sa.String(length=256), nullable=False),
        sa.Column("input_modalities", sa.JSON(), nullable=False),
        sa.Column("output_modalities", sa.JSON(), nullable=False),
        sa.Column("context_window_tokens", sa.Integer(), nullable=False),
        sa.Column("max_output_tokens", sa.Integer(), nullable=False),
        sa.Column("input_cost_microunits_per_million_tokens", sa.BigInteger(), nullable=False),
        sa.Column("output_cost_microunits_per_million_tokens", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("quality_tier", sa.String(length=64), nullable=True),
        sa.Column("data_region", sa.String(length=64), nullable=True),
        sa.Column("retention_policy", sa.String(length=500), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("resource_version", sa.BigInteger(), nullable=False),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["provider_id"], ["providers.provider_id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("model_mapping_id"),
    )
    op.create_index(
        op.f("ix_ai_model_mappings_logical_model_id"),
        "ai_model_mappings",
        ["logical_model_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ai_model_mappings_status"), "ai_model_mappings", ["status"], unique=False
    )
    op.create_table(
        "ai_routes",
        sa.Column("route_id", sa.String(length=64), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("scenario", sa.String(length=64), nullable=False),
        sa.Column("logical_model_id", sa.String(length=64), nullable=False),
        sa.Column("targets", sa.JSON(), nullable=False),
        sa.Column("max_input_tokens", sa.Integer(), nullable=False),
        sa.Column("max_output_tokens", sa.Integer(), nullable=False),
        sa.Column("budget_ceiling_microunits", sa.BigInteger(), nullable=False),
        sa.Column("total_attempt_limit", sa.Integer(), nullable=False),
        sa.Column("safety_policy_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("rollout_percentage", sa.Integer(), nullable=False),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resource_version", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("route_id"),
    )
    op.create_index(op.f("ix_ai_routes_scenario"), "ai_routes", ["scenario"], unique=False)
    op.create_index(
        op.f("ix_ai_routes_logical_model_id"), "ai_routes", ["logical_model_id"], unique=False
    )
    op.create_index(op.f("ix_ai_routes_status"), "ai_routes", ["status"], unique=False)
    op.create_table(
        "ai_prompts",
        sa.Column("prompt_id", sa.String(length=64), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("prompt_code", sa.String(length=64), nullable=False),
        sa.Column("scenario", sa.String(length=64), nullable=False),
        sa.Column("system_template", sa.Text(), nullable=False),
        sa.Column("user_template", sa.Text(), nullable=False),
        sa.Column("allowed_input_fields", sa.JSON(), nullable=False),
        sa.Column("output_schema", sa.JSON(), nullable=False),
        sa.Column("safety_policy_id", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resource_version", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("prompt_id"),
    )
    op.create_index(op.f("ix_ai_prompts_scenario"), "ai_prompts", ["scenario"], unique=False)
    op.create_index(op.f("ix_ai_prompts_status"), "ai_prompts", ["status"], unique=False)
    op.create_table(
        "ai_gateway_attempts",
        sa.Column("attempt_id", sa.String(length=64), nullable=False),
        sa.Column("routing_key_hash", sa.String(length=64), nullable=False),
        sa.Column("route_id", sa.String(length=64), nullable=False),
        sa.Column("route_version", sa.Integer(), nullable=False),
        sa.Column("model_mapping_id", sa.String(length=64), nullable=False),
        sa.Column("provider_id", sa.String(length=64), nullable=False),
        sa.Column("provider_resource_version", sa.BigInteger(), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("cost_microunits", sa.BigInteger(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("attempt_id"),
    )
    op.create_index(
        op.f("ix_ai_gateway_attempts_routing_key_hash"),
        "ai_gateway_attempts",
        ["routing_key_hash"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_ai_gateway_attempts_routing_key_hash"), table_name="ai_gateway_attempts")
    op.drop_table("ai_gateway_attempts")
    op.drop_index(op.f("ix_ai_prompts_status"), table_name="ai_prompts")
    op.drop_index(op.f("ix_ai_prompts_scenario"), table_name="ai_prompts")
    op.drop_table("ai_prompts")
    op.drop_index(op.f("ix_ai_routes_status"), table_name="ai_routes")
    op.drop_index(op.f("ix_ai_routes_logical_model_id"), table_name="ai_routes")
    op.drop_index(op.f("ix_ai_routes_scenario"), table_name="ai_routes")
    op.drop_table("ai_routes")
    op.drop_index(op.f("ix_ai_model_mappings_status"), table_name="ai_model_mappings")
    op.drop_index(op.f("ix_ai_model_mappings_logical_model_id"), table_name="ai_model_mappings")
    op.drop_table("ai_model_mappings")
