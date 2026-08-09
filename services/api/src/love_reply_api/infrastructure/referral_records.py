"""邀请推广活动、绑定、风险信号、奖励和审计数据表映射。"""

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from love_reply_api.infrastructure.database import Base


class ReferralCampaignRecord(Base):
    __tablename__ = "referral_campaigns"

    campaign_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    campaign_code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    region: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    sales_channels: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    binding_window_hours: Mapped[int] = mapped_column(Integer, nullable=False)
    max_qualified_invites_per_inviter: Mapped[int] = mapped_column(Integer, nullable=False)
    reward_rules: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    anti_abuse_policy: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    rollout_percentage: Mapped[int] = mapped_column(Integer, nullable=False)
    effective_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_version: Mapped[int | None] = mapped_column(Integer)
    published_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    created_by_admin_id: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_version: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ReferralCampaignVersionRecord(Base):
    __tablename__ = "referral_campaign_versions"
    __table_args__ = (
        UniqueConstraint("campaign_id", "version", name="uq_referral_campaign_version"),
    )

    campaign_version_id: Mapped[str] = mapped_column(String(96), primary_key=True)
    campaign_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("referral_campaigns.campaign_id", ondelete="CASCADE"), index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    was_published: Mapped[bool] = mapped_column(Boolean, nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    created_by_admin_id: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ReferralInviteCodeRecord(Base):
    __tablename__ = "referral_invite_codes"
    __table_args__ = (
        UniqueConstraint("campaign_id", "user_id", name="uq_referral_code_campaign_user"),
    )

    invite_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    campaign_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ReferralBindingRecord(Base):
    __tablename__ = "referral_bindings"

    referral_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    campaign_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    campaign_version: Mapped[int] = mapped_column(Integer, nullable=False)
    campaign_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    inviter_user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    invitee_user_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    invitee_display_hint: Mapped[str] = mapped_column(String(64), nullable=False)
    binding_device_id: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    completed_milestones: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    rejection_reason_code: Mapped[str | None] = mapped_column(String(64))
    risk_score: Mapped[int] = mapped_column(Integer, nullable=False)
    bound_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    qualified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resource_version: Mapped[int] = mapped_column(BigInteger, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ReferralRewardRecord(Base):
    __tablename__ = "referral_rewards"
    __table_args__ = (UniqueConstraint("referral_id", "rule_key", name="uq_referral_reward_rule"),)

    referral_reward_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    referral_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    beneficiary_user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    beneficiary: Mapped[str] = mapped_column(String(16), nullable=False)
    milestone_code: Mapped[str] = mapped_column(String(32), nullable=False)
    reward_unit: Mapped[str] = mapped_column(String(32), nullable=False)
    reward_amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    rule_key: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    wallet_ledger_entry_id: Mapped[str | None] = mapped_column(String(64))
    entitlement_event_id: Mapped[str | None] = mapped_column(String(64))
    available_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    grant_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ReferralPaymentIdentityRecord(Base):
    """只保存支付渠道提供的稳定身份标识哈希，不保存账号、邮箱或姓名。"""

    __tablename__ = "referral_payment_identities"
    __table_args__ = (
        UniqueConstraint("user_id", "identity_hash", name="uq_referral_user_payment_identity"),
    )

    identity_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    identity_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ReferralAuditRecord(Base):
    __tablename__ = "referral_audit_records"

    audit_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    resource_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    resource_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    actor_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
