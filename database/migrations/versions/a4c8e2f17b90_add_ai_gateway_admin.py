"""add AI gateway administration and immutable publication records

Revision ID: a4c8e2f17b90
Revises: 91d6e4a2c8f7
Create Date: 2026-08-09 18:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a4c8e2f17b90"
down_revision: str | None = "91d6e4a2c8f7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("ai_routes", sa.Column("published_version", sa.Integer(), nullable=True))
    op.add_column("ai_routes", sa.Column("published_snapshot", sa.JSON(), nullable=True))
    op.add_column(
        "ai_routes",
        sa.Column("published_rollout_percentage", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "ai_routes", sa.Column("published_effective_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column("ai_prompts", sa.Column("published_version", sa.Integer(), nullable=True))
    op.add_column("ai_prompts", sa.Column("published_snapshot", sa.JSON(), nullable=True))
    op.add_column(
        "ai_prompts", sa.Column("published_effective_at", sa.DateTime(timezone=True), nullable=True)
    )

    op.create_table(
        "ai_risk_policies",
        sa.Column("risk_policy_id", sa.String(length=64), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("policy_code", sa.String(length=64), nullable=False),
        sa.Column("blocked_categories", sa.JSON(), nullable=False),
        sa.Column("review_categories", sa.JSON(), nullable=False),
        sa.Column("input_moderation_enabled", sa.Boolean(), nullable=False),
        sa.Column("output_moderation_enabled", sa.Boolean(), nullable=False),
        sa.Column("prompt_injection_action", sa.String(length=32), nullable=False),
        sa.Column("minimum_safety_score", sa.Float(), nullable=False),
        sa.Column("allow_appeals", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_version", sa.Integer(), nullable=True),
        sa.Column("published_snapshot", sa.JSON(), nullable=True),
        sa.Column("published_rollout_percentage", sa.Integer(), nullable=False),
        sa.Column("published_effective_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resource_version", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("risk_policy_id"),
    )
    op.create_index(op.f("ix_ai_risk_policies_policy_code"), "ai_risk_policies", ["policy_code"])
    op.create_index(op.f("ix_ai_risk_policies_status"), "ai_risk_policies", ["status"])

    op.create_table(
        "ai_resource_versions",
        sa.Column("resource_version_id", sa.String(length=96), nullable=False),
        sa.Column("resource_type", sa.String(length=32), nullable=False),
        sa.Column("resource_id", sa.String(length=64), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("was_published", sa.Boolean(), nullable=False),
        sa.Column("rollout_percentage", sa.Integer(), nullable=True),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("created_by_admin_id", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("resource_version_id"),
        sa.UniqueConstraint(
            "resource_type", "resource_id", "version", name="uq_ai_resource_version_number"
        ),
    )
    op.create_index(
        op.f("ix_ai_resource_versions_resource_type"), "ai_resource_versions", ["resource_type"]
    )
    op.create_index(
        op.f("ix_ai_resource_versions_resource_id"), "ai_resource_versions", ["resource_id"]
    )

    op.create_table(
        "ai_evaluation_runs",
        sa.Column("evaluation_run_id", sa.String(length=64), nullable=False),
        sa.Column("prompt_id", sa.String(length=64), nullable=False),
        sa.Column("prompt_version", sa.Integer(), nullable=False),
        sa.Column("prompt_resource_version", sa.BigInteger(), nullable=False),
        sa.Column("route_id", sa.String(length=64), nullable=False),
        sa.Column("route_version", sa.Integer(), nullable=False),
        sa.Column("route_resource_version", sa.BigInteger(), nullable=False),
        sa.Column("risk_policy_versions", sa.JSON(), nullable=False),
        sa.Column("suite_ids", sa.JSON(), nullable=False),
        sa.Column("evaluator_logical_model_id", sa.String(length=64), nullable=False),
        sa.Column("max_cost_microunits", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("total_cases", sa.Integer(), nullable=False),
        sa.Column("completed_cases", sa.Integer(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("safety_passed", sa.Boolean(), nullable=False),
        sa.Column("cost_microunits", sa.BigInteger(), nullable=False),
        sa.Column("failure_code", sa.String(length=64), nullable=True),
        sa.Column("created_by_admin_id", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("evaluation_run_id"),
    )
    op.create_index(op.f("ix_ai_evaluation_runs_prompt_id"), "ai_evaluation_runs", ["prompt_id"])
    op.create_index(op.f("ix_ai_evaluation_runs_route_id"), "ai_evaluation_runs", ["route_id"])
    op.create_index(op.f("ix_ai_evaluation_runs_status"), "ai_evaluation_runs", ["status"])

    op.create_table(
        "ai_audit_records",
        sa.Column("audit_id", sa.String(length=64), nullable=False),
        sa.Column("resource_type", sa.String(length=32), nullable=False),
        sa.Column("resource_id", sa.String(length=64), nullable=False),
        sa.Column("admin_id", sa.String(length=64), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("audit_reason", sa.String(length=500), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("audit_id"),
    )
    op.create_index(
        op.f("ix_ai_audit_records_resource_type"), "ai_audit_records", ["resource_type"]
    )
    op.create_index(op.f("ix_ai_audit_records_resource_id"), "ai_audit_records", ["resource_id"])
    op.create_index(op.f("ix_ai_audit_records_admin_id"), "ai_audit_records", ["admin_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_ai_audit_records_admin_id"), table_name="ai_audit_records")
    op.drop_index(op.f("ix_ai_audit_records_resource_id"), table_name="ai_audit_records")
    op.drop_index(op.f("ix_ai_audit_records_resource_type"), table_name="ai_audit_records")
    op.drop_table("ai_audit_records")
    op.drop_index(op.f("ix_ai_evaluation_runs_status"), table_name="ai_evaluation_runs")
    op.drop_index(op.f("ix_ai_evaluation_runs_route_id"), table_name="ai_evaluation_runs")
    op.drop_index(op.f("ix_ai_evaluation_runs_prompt_id"), table_name="ai_evaluation_runs")
    op.drop_table("ai_evaluation_runs")
    op.drop_index(op.f("ix_ai_resource_versions_resource_id"), table_name="ai_resource_versions")
    op.drop_index(op.f("ix_ai_resource_versions_resource_type"), table_name="ai_resource_versions")
    op.drop_table("ai_resource_versions")
    op.drop_index(op.f("ix_ai_risk_policies_status"), table_name="ai_risk_policies")
    op.drop_index(op.f("ix_ai_risk_policies_policy_code"), table_name="ai_risk_policies")
    op.drop_table("ai_risk_policies")
    op.drop_column("ai_prompts", "published_effective_at")
    op.drop_column("ai_prompts", "published_snapshot")
    op.drop_column("ai_prompts", "published_version")
    op.drop_column("ai_routes", "published_effective_at")
    op.drop_column("ai_routes", "published_rollout_percentage")
    op.drop_column("ai_routes", "published_snapshot")
    op.drop_column("ai_routes", "published_version")
