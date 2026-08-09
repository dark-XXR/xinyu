"""邀请推广用户端和管理员端 HTTP 请求及响应模型。"""

from datetime import datetime
from typing import Literal

from pydantic import ConfigDict, Field, model_validator

from love_reply_api.schemas import ApiModel, SuccessEnvelope


class StrictApiModel(ApiModel):
    model_config = ConfigDict(extra="forbid")


class ReferralRewardRuleData(StrictApiModel):
    milestone_code: Literal["ACCOUNT_VERIFIED", "FIRST_GENERATION", "FIRST_PURCHASE"]
    beneficiary: Literal["INVITER", "INVITEE"]
    reward_unit: Literal["ENERGY", "TEXT_QUOTA", "VISION_QUOTA", "PLAN_DAYS"]
    reward_amount: int = Field(ge=1)
    cooling_off_hours: int = Field(ge=0, le=720)


class ReferralAntiAbusePolicyData(StrictApiModel):
    block_self_referral: Literal[True]
    block_same_device: bool
    block_same_payment_identity: bool
    require_verified_primary_channel: bool
    risk_review_score: int = Field(ge=0, le=100)


class ReferralCampaignWriteRequest(StrictApiModel):
    campaign_code: str = Field(pattern=r"^[A-Z][A-Z0-9_]{1,63}$")
    display_name: str = Field(min_length=1, max_length=128)
    description: str = Field(min_length=1, max_length=500)
    region: str = Field(min_length=2, max_length=16)
    sales_channels: list[Literal["ANDROID", "ADMIN_ASSISTED"]] = Field(min_length=1)
    binding_window_hours: int = Field(ge=1, le=720)
    max_qualified_invites_per_inviter: int = Field(ge=1, le=100000)
    reward_rules: list[ReferralRewardRuleData] = Field(min_length=1, max_length=20)
    anti_abuse_policy: ReferralAntiAbusePolicyData

    @model_validator(mode="after")
    def unique_rules(self) -> "ReferralCampaignWriteRequest":
        keys = [
            (item.milestone_code, item.beneficiary, item.reward_unit) for item in self.reward_rules
        ]
        if len(keys) != len(set(keys)):
            raise ValueError("referral reward rules must be unique")
        return self


class PublishReferralCampaignRequest(StrictApiModel):
    rollout_percentage: int = Field(ge=1, le=100)
    effective_at: datetime
    expires_at: datetime | None = None
    audit_reason: str = Field(min_length=8, max_length=500)


class RollbackReferralCampaignRequest(StrictApiModel):
    target_version: int = Field(ge=1)
    audit_reason: str = Field(min_length=8, max_length=500)


class BindReferralRequest(StrictApiModel):
    invite_code: str = Field(pattern=r"^[A-Z0-9]{6,16}$")


class ReferralCampaignData(ApiModel):
    campaign_id: str
    version: int
    campaign_code: str
    display_name: str
    description: str
    status: str
    region: str
    sales_channels: list[str]
    binding_window_hours: int
    max_qualified_invites_per_inviter: int
    reward_rules: list[ReferralRewardRuleData]
    anti_abuse_policy: ReferralAntiAbusePolicyData
    rollout_percentage: int
    effective_at: datetime
    expires_at: datetime | None
    resource_version: int
    created_at: datetime
    updated_at: datetime


class ReferralCampaignListData(ApiModel):
    items: list[ReferralCampaignData]
    next_cursor: str | None
    has_more: bool


class ReferralProgramData(ApiModel):
    campaign_id: str
    campaign_version: int
    display_name: str
    description: str
    invite_code: str
    invite_url: str
    reward_rules: list[ReferralRewardRuleData]
    qualified_invite_count: int
    pending_invite_count: int
    total_rewards: dict[str, int]


class ReferralInviteData(ApiModel):
    referral_id: str
    campaign_id: str
    campaign_version: int
    invitee_display_hint: str
    status: str
    completed_milestones: list[str]
    rejection_reason_code: str | None
    bound_at: datetime
    qualified_at: datetime | None
    resource_version: int
    updated_at: datetime


class ReferralInviteListData(ApiModel):
    items: list[ReferralInviteData]
    next_cursor: str | None
    has_more: bool


class ReferralRewardData(ApiModel):
    referral_reward_id: str
    referral_id: str
    beneficiary: str
    milestone_code: str
    reward_unit: str
    reward_amount: int
    status: str
    wallet_ledger_entry_id: str | None
    entitlement_event_id: str | None
    available_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ReferralRewardListData(ApiModel):
    items: list[ReferralRewardData]
    next_cursor: str | None
    has_more: bool


ReferralCampaignResponse = SuccessEnvelope[ReferralCampaignData]
ReferralCampaignListResponse = SuccessEnvelope[ReferralCampaignListData]
ReferralProgramResponse = SuccessEnvelope[ReferralProgramData]
ReferralInviteResponse = SuccessEnvelope[ReferralInviteData]
ReferralInviteListResponse = SuccessEnvelope[ReferralInviteListData]
ReferralRewardListResponse = SuccessEnvelope[ReferralRewardListData]
