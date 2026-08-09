"""add referral runtime

Revision ID: a6ce441f72d8
Revises: f5b1c27a9e10
Create Date: 2026-08-10 00:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a6ce441f72d8"
down_revision: str | None = "f5b1c27a9e10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "referral_campaigns",
        sa.Column("campaign_id", sa.String(64), primary_key=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("campaign_code", sa.String(64), nullable=False, unique=True),
        sa.Column("display_name", sa.String(128), nullable=False),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("region", sa.String(16), nullable=False),
        sa.Column("sales_channels", sa.JSON(), nullable=False),
        sa.Column("binding_window_hours", sa.Integer(), nullable=False),
        sa.Column("max_qualified_invites_per_inviter", sa.Integer(), nullable=False),
        sa.Column("reward_rules", sa.JSON(), nullable=False),
        sa.Column("anti_abuse_policy", sa.JSON(), nullable=False),
        sa.Column("rollout_percentage", sa.Integer(), nullable=False),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("published_version", sa.Integer()),
        sa.Column("published_snapshot", sa.JSON()),
        sa.Column("created_by_admin_id", sa.String(64), nullable=False),
        sa.Column("resource_version", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_referral_campaigns_status", "referral_campaigns", ["status"])
    op.create_index("ix_referral_campaigns_region", "referral_campaigns", ["region"])
    op.create_table(
        "referral_campaign_versions",
        sa.Column("campaign_version_id", sa.String(96), primary_key=True),
        sa.Column("campaign_id", sa.String(64), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("was_published", sa.Boolean(), nullable=False),
        sa.Column("action", sa.String(32), nullable=False),
        sa.Column("created_by_admin_id", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["campaign_id"], ["referral_campaigns.campaign_id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint("campaign_id", "version", name="uq_referral_campaign_version"),
    )
    op.create_index(
        "ix_referral_campaign_versions_campaign_id", "referral_campaign_versions", ["campaign_id"]
    )
    op.create_table(
        "referral_invite_codes",
        sa.Column("invite_code", sa.String(16), primary_key=True),
        sa.Column("campaign_id", sa.String(64), nullable=False),
        sa.Column("user_id", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("campaign_id", "user_id", name="uq_referral_code_campaign_user"),
    )
    op.create_index(
        "ix_referral_invite_codes_campaign_id", "referral_invite_codes", ["campaign_id"]
    )
    op.create_index("ix_referral_invite_codes_user_id", "referral_invite_codes", ["user_id"])
    op.create_table(
        "referral_bindings",
        sa.Column("referral_id", sa.String(64), primary_key=True),
        sa.Column("campaign_id", sa.String(64), nullable=False),
        sa.Column("campaign_version", sa.Integer(), nullable=False),
        sa.Column("campaign_snapshot", sa.JSON(), nullable=False),
        sa.Column("inviter_user_id", sa.String(64), nullable=False),
        sa.Column("invitee_user_id", sa.String(64), nullable=False, unique=True),
        sa.Column("invitee_display_hint", sa.String(64), nullable=False),
        sa.Column("binding_device_id", sa.String(128), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("completed_milestones", sa.JSON(), nullable=False),
        sa.Column("rejection_reason_code", sa.String(64)),
        sa.Column("risk_score", sa.Integer(), nullable=False),
        sa.Column("bound_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("qualified_at", sa.DateTime(timezone=True)),
        sa.Column("resource_version", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_referral_bindings_campaign_id", "referral_bindings", ["campaign_id"])
    op.create_index(
        "ix_referral_bindings_inviter_user_id", "referral_bindings", ["inviter_user_id"]
    )
    op.create_index("ix_referral_bindings_status", "referral_bindings", ["status"])
    op.create_table(
        "referral_rewards",
        sa.Column("referral_reward_id", sa.String(64), primary_key=True),
        sa.Column("referral_id", sa.String(64), nullable=False),
        sa.Column("beneficiary_user_id", sa.String(64), nullable=False),
        sa.Column("beneficiary", sa.String(16), nullable=False),
        sa.Column("milestone_code", sa.String(32), nullable=False),
        sa.Column("reward_unit", sa.String(32), nullable=False),
        sa.Column("reward_amount", sa.BigInteger(), nullable=False),
        sa.Column("rule_key", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("wallet_ledger_entry_id", sa.String(64)),
        sa.Column("entitlement_event_id", sa.String(64)),
        sa.Column("available_at", sa.DateTime(timezone=True)),
        sa.Column("grant_snapshot", sa.JSON()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("referral_id", "rule_key", name="uq_referral_reward_rule"),
    )
    op.create_index("ix_referral_rewards_referral_id", "referral_rewards", ["referral_id"])
    op.create_index(
        "ix_referral_rewards_beneficiary_user_id", "referral_rewards", ["beneficiary_user_id"]
    )
    op.create_index("ix_referral_rewards_status", "referral_rewards", ["status"])
    op.create_table(
        "referral_payment_identities",
        sa.Column("identity_id", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.String(64), nullable=False),
        sa.Column("identity_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "identity_hash", name="uq_referral_user_payment_identity"),
    )
    op.create_index(
        "ix_referral_payment_identities_user_id", "referral_payment_identities", ["user_id"]
    )
    op.create_index(
        "ix_referral_payment_identities_identity_hash",
        "referral_payment_identities",
        ["identity_hash"],
    )
    op.create_table(
        "referral_audit_records",
        sa.Column("audit_id", sa.String(64), primary_key=True),
        sa.Column("resource_type", sa.String(32), nullable=False),
        sa.Column("resource_id", sa.String(64), nullable=False),
        sa.Column("actor_id", sa.String(64), nullable=False),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    for column in ("resource_type", "resource_id", "actor_id"):
        op.create_index(f"ix_referral_audit_records_{column}", "referral_audit_records", [column])


def downgrade() -> None:
    op.drop_table("referral_audit_records")
    op.drop_table("referral_payment_identities")
    op.drop_table("referral_rewards")
    op.drop_table("referral_bindings")
    op.drop_table("referral_invite_codes")
    op.drop_table("referral_campaign_versions")
    op.drop_table("referral_campaigns")
