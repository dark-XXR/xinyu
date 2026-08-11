"""邀请推广活动管理、单层绑定、风险检查、里程碑奖励和撤销服务。"""

from __future__ import annotations

from base64 import b32encode
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from hmac import new as new_hmac
from json import dumps
from typing import Any, Generic, TypeVar
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from love_reply_api.application.errors import ApiError
from love_reply_api.config import Settings
from love_reply_api.infrastructure.generation_records import (
    EntitlementRecord,
    WalletAccountRecord,
    WalletLedgerRecord,
)
from love_reply_api.infrastructure.identity_records import UserDeviceRecord, UserRecord
from love_reply_api.infrastructure.referral_records import (
    ReferralAuditRecord,
    ReferralBindingRecord,
    ReferralCampaignRecord,
    ReferralCampaignVersionRecord,
    ReferralInviteCodeRecord,
    ReferralPaymentIdentityRecord,
    ReferralRewardRecord,
)

RecordT = TypeVar("RecordT")


@dataclass(frozen=True, slots=True)
class Page(Generic[RecordT]):
    items: list[RecordT]
    next_cursor: str | None
    has_more: bool


@dataclass(frozen=True, slots=True)
class ReferralProgramView:
    campaign_id: str
    campaign_version: int
    display_name: str
    description: str
    invite_code: str
    invite_url: str
    reward_rules: list[dict[str, Any]]
    qualified_invite_count: int
    pending_invite_count: int
    total_rewards: dict[str, int]


class ReferralService:
    def __init__(self, *, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._invite_base_url = settings.referral_invite_base_url.rstrip("/")
        secret = settings.data_encryption_key.get_secret_value().encode()
        self._opaque_key = sha256(b"referral-opaque:" + secret).digest()

    def hash_payment_identity(self, *, provider_id: str, payer_reference: str) -> str:
        """把已验签付款方标识转换为不可逆、按部署隔离的风控哈希。"""

        return new_hmac(
            self._opaque_key,
            f"{provider_id}:{payer_reference}".encode(),
            sha256,
        ).hexdigest()

    async def list_campaigns(
        self, *, cursor: str | None, limit: int
    ) -> Page[ReferralCampaignRecord]:
        query = select(ReferralCampaignRecord).order_by(ReferralCampaignRecord.campaign_id)
        if cursor is not None:
            query = query.where(ReferralCampaignRecord.campaign_id > cursor)
        rows = list((await self._session.scalars(query.limit(limit + 1))).all())
        return self._page(rows, limit, lambda item: item.campaign_id)

    async def get_campaign(self, *, campaign_id: str) -> ReferralCampaignRecord:
        record = await self._session.get(ReferralCampaignRecord, campaign_id)
        if record is None:
            raise self._not_found("REFERRAL_CAMPAIGN_NOT_FOUND", "Campaign")
        return record

    async def list_campaign_versions(
        self, *, campaign_id: str
    ) -> list[ReferralCampaignVersionRecord]:
        """按版本倒序返回活动不可变历史，供管理员选择合法回滚目标。"""

        await self.get_campaign(campaign_id=campaign_id)
        return list(
            (
                await self._session.scalars(
                    select(ReferralCampaignVersionRecord)
                    .where(ReferralCampaignVersionRecord.campaign_id == campaign_id)
                    .order_by(ReferralCampaignVersionRecord.version.desc())
                )
            ).all()
        )

    async def create_campaign(
        self, *, admin_id: str, values: dict[str, Any]
    ) -> ReferralCampaignRecord:
        self._validate_rules(values)
        now = datetime.now(UTC)
        record = ReferralCampaignRecord(
            campaign_id=f"rcp_{uuid4().hex}",
            version=1,
            status="DRAFT",
            rollout_percentage=0,
            effective_at=now,
            expires_at=None,
            published_version=None,
            published_snapshot=None,
            created_by_admin_id=admin_id,
            resource_version=1,
            created_at=now,
            updated_at=now,
            **values,
        )
        self._session.add(record)
        await self._session.flush()
        self._version(record, admin_id=admin_id, action="CREATE", was_published=False, now=now)
        self._audit(record.campaign_id, admin_id, "CAMPAIGN_CREATED", "Draft created.", {}, now)
        await self._session.commit()
        return record

    async def update_campaign(
        self, *, campaign_id: str, expected_version: int, admin_id: str, values: dict[str, Any]
    ) -> ReferralCampaignRecord:
        self._validate_rules(values)
        record = await self._locked_campaign(campaign_id)
        self._assert_version(record, expected_version)
        if record.campaign_code != values["campaign_code"]:
            raise ApiError(
                status_code=409,
                code="REFERRAL_CAMPAIGN_CODE_IMMUTABLE",
                message="Campaign code cannot be changed.",
            )
        latest = await self._session.scalar(
            select(func.max(ReferralCampaignVersionRecord.version)).where(
                ReferralCampaignVersionRecord.campaign_id == campaign_id
            )
        )
        now = datetime.now(UTC)
        for name, value in values.items():
            setattr(record, name, value)
        record.created_by_admin_id = admin_id
        record.version = int(latest or record.version) + 1
        record.status = "DRAFT"
        record.rollout_percentage = 0
        record.resource_version += 1
        record.updated_at = now
        self._version(record, admin_id=admin_id, action="UPDATE", was_published=False, now=now)
        self._audit(campaign_id, admin_id, "CAMPAIGN_UPDATED", "Draft updated.", {}, now)
        await self._session.commit()
        return record

    async def publish_campaign(
        self,
        *,
        campaign_id: str,
        expected_version: int,
        admin_id: str,
        rollout_percentage: int,
        effective_at: datetime,
        expires_at: datetime | None,
        audit_reason: str,
    ) -> ReferralCampaignRecord:
        record = await self._locked_campaign(campaign_id)
        self._assert_version(record, expected_version)
        if record.status not in {"DRAFT", "READY"}:
            raise ApiError(
                status_code=409,
                code="REFERRAL_CAMPAIGN_NOT_READY",
                message="Campaign is not ready to publish.",
            )
        if record.created_by_admin_id == admin_id:
            raise ApiError(
                status_code=409,
                code="REFERRAL_SELF_APPROVAL_FORBIDDEN",
                message="Campaign creator cannot approve the same campaign.",
            )
        if expires_at is not None and expires_at <= effective_at:
            raise ApiError(
                status_code=400,
                code="REFERRAL_WINDOW_INVALID",
                message="Campaign expiry must follow activation.",
            )
        now = datetime.now(UTC)
        record.status = "ACTIVE"
        record.rollout_percentage = rollout_percentage
        record.effective_at = effective_at
        record.expires_at = expires_at
        record.published_version = record.version
        published_snapshot = self._snapshot(record)
        published_snapshot.update(
            {
                "_rolloutPercentage": rollout_percentage,
                "_effectiveAt": effective_at.isoformat(),
                "_expiresAt": expires_at.isoformat() if expires_at else None,
            }
        )
        record.published_snapshot = published_snapshot
        record.resource_version += 1
        record.updated_at = now
        version = await self._campaign_version(campaign_id, record.version)
        assert version is not None
        version.was_published = True
        version.snapshot = dict(record.published_snapshot)
        self._audit(
            campaign_id,
            admin_id,
            "CAMPAIGN_PUBLISHED",
            audit_reason,
            {"version": record.version, "rolloutPercentage": rollout_percentage},
            now,
        )
        await self._session.commit()
        return record

    async def rollback_campaign(
        self,
        *,
        campaign_id: str,
        expected_version: int,
        admin_id: str,
        target_version: int,
        audit_reason: str,
    ) -> ReferralCampaignRecord:
        record = await self._locked_campaign(campaign_id)
        self._assert_version(record, expected_version)
        target = await self._campaign_version(campaign_id, target_version, required=False)
        if target is None or not target.was_published:
            raise ApiError(
                status_code=409,
                code="ROLLBACK_TARGET_INVALID",
                message="Target campaign version was not published.",
            )
        now = datetime.now(UTC)
        self._apply_snapshot(record, target.snapshot)
        record.version = target_version
        record.status = "ACTIVE"
        record.rollout_percentage = 100
        record.effective_at = now
        record.expires_at = None
        record.published_version = target_version
        published_snapshot = dict(target.snapshot)
        published_snapshot.update(
            {
                "_rolloutPercentage": 100,
                "_effectiveAt": now.isoformat(),
                "_expiresAt": None,
            }
        )
        record.published_snapshot = published_snapshot
        record.resource_version += 1
        record.updated_at = now
        self._audit(
            campaign_id,
            admin_id,
            "CAMPAIGN_ROLLED_BACK",
            audit_reason,
            {"targetVersion": target_version},
            now,
        )
        await self._session.commit()
        return record

    async def get_program(self, *, user_id: str, channel: str) -> ReferralProgramView:
        user = await self._user(user_id)
        campaign = await self._active_campaign(user=user, channel=channel)
        code = await self._invite_code(campaign=campaign, user_id=user_id)
        qualified = int(
            await self._session.scalar(
                select(func.count())
                .select_from(ReferralBindingRecord)
                .where(
                    ReferralBindingRecord.campaign_id == campaign.campaign_id,
                    ReferralBindingRecord.inviter_user_id == user_id,
                    ReferralBindingRecord.status.in_(["QUALIFIED", "REWARDED"]),
                )
            )
            or 0
        )
        pending = int(
            await self._session.scalar(
                select(func.count())
                .select_from(ReferralBindingRecord)
                .where(
                    ReferralBindingRecord.campaign_id == campaign.campaign_id,
                    ReferralBindingRecord.inviter_user_id == user_id,
                    ReferralBindingRecord.status.in_(
                        ["BOUND", "PENDING_QUALIFICATION", "RISK_REVIEW"]
                    ),
                )
            )
            or 0
        )
        rewards = list(
            (
                await self._session.scalars(
                    select(ReferralRewardRecord).where(
                        ReferralRewardRecord.beneficiary_user_id == user_id,
                        ReferralRewardRecord.status == "GRANTED",
                    )
                )
            ).all()
        )
        totals: dict[str, int] = {}
        for reward in rewards:
            totals[reward.reward_unit] = totals.get(reward.reward_unit, 0) + reward.reward_amount
        snapshot = dict(campaign.published_snapshot or {})
        await self._session.commit()
        return ReferralProgramView(
            campaign_id=campaign.campaign_id,
            campaign_version=int(campaign.published_version or campaign.version),
            display_name=str(snapshot["displayName"]),
            description=str(snapshot["description"]),
            invite_code=code.invite_code,
            invite_url=f"{self._invite_base_url}/{code.invite_code}",
            reward_rules=list(snapshot["rewardRules"]),
            qualified_invite_count=qualified,
            pending_invite_count=pending,
            total_rewards=totals,
        )

    async def bind(
        self, *, invitee_user_id: str, invite_code: str, device_id: str
    ) -> ReferralBindingRecord:
        # 同一受邀用户的并发请求先获取事务级锁，再检查唯一绑定，避免竞争落到数据库异常。
        await self._session.execute(
            select(func.pg_advisory_xact_lock(self._lock_key(invitee_user_id)))
        )
        existing = await self._session.scalar(
            select(ReferralBindingRecord).where(
                ReferralBindingRecord.invitee_user_id == invitee_user_id
            )
        )
        if existing is not None:
            code = await self._session.get(ReferralInviteCodeRecord, invite_code)
            if code is not None and code.user_id == existing.inviter_user_id:
                return existing
            raise ApiError(
                status_code=409,
                code="REFERRAL_ALREADY_BOUND",
                message="Account is already bound to an inviter.",
            )
        code = await self._session.get(ReferralInviteCodeRecord, invite_code)
        if code is None:
            raise self._not_found("REFERRAL_CODE_NOT_FOUND", "Invite code")
        if code.user_id == invitee_user_id:
            raise ApiError(
                status_code=400,
                code="REFERRAL_SELF_BIND_FORBIDDEN",
                message="Self-referral is not allowed.",
            )
        invitee = await self._user(invitee_user_id)
        campaign = await self._active_campaign(
            user=invitee, channel="ANDROID", campaign_id=code.campaign_id
        )
        snapshot = dict(campaign.published_snapshot or {})
        now = datetime.now(UTC)
        if invitee.created_at + timedelta(hours=int(snapshot["bindingWindowHours"])) < now:
            raise ApiError(
                status_code=409,
                code="REFERRAL_BINDING_WINDOW_EXPIRED",
                message="Referral binding window has expired.",
            )
        verified = invitee.email_normalized is not None or invitee.phone_e164 is not None
        same_device = await self._same_device(code.user_id, device_id)
        shared_payment = await self._shared_payment_identity(code.user_id, invitee_user_id)
        policy = dict(snapshot["antiAbusePolicy"])
        rejection = None
        if policy["blockSameDevice"] and same_device:
            rejection = "SAME_DEVICE"
        elif policy["blockSamePaymentIdentity"] and shared_payment:
            rejection = "SHARED_PAYMENT_IDENTITY"
        elif policy["requireVerifiedPrimaryChannel"] and not verified:
            rejection = "PRIMARY_CHANNEL_UNVERIFIED"
        milestones = ["ACCOUNT_VERIFIED"] if verified else []
        record = ReferralBindingRecord(
            referral_id=f"ref_{uuid4().hex}",
            campaign_id=campaign.campaign_id,
            campaign_version=int(campaign.published_version or campaign.version),
            campaign_snapshot=snapshot,
            inviter_user_id=code.user_id,
            invitee_user_id=invitee_user_id,
            invitee_display_hint=self._display_hint(invitee_user_id),
            binding_device_id=device_id,
            status="REJECTED" if rejection else "PENDING_QUALIFICATION",
            completed_milestones=milestones,
            rejection_reason_code=rejection,
            risk_score=100 if rejection else 0,
            bound_at=now,
            qualified_at=None,
            resource_version=1,
            updated_at=now,
        )
        self._session.add(record)
        await self._session.flush()
        if not rejection and verified:
            await self._apply_milestone(record, "ACCOUNT_VERIFIED", now)
        self._audit(
            record.referral_id,
            invitee_user_id,
            "REFERRAL_BOUND",
            "Authenticated invite binding.",
            {"status": record.status},
            now,
        )
        await self._session.commit()
        return record

    async def list_invites(
        self, *, inviter_user_id: str, cursor: str | None, limit: int
    ) -> Page[ReferralBindingRecord]:
        query = (
            select(ReferralBindingRecord)
            .where(ReferralBindingRecord.inviter_user_id == inviter_user_id)
            .order_by(ReferralBindingRecord.referral_id)
        )
        if cursor is not None:
            query = query.where(ReferralBindingRecord.referral_id > cursor)
        rows = list((await self._session.scalars(query.limit(limit + 1))).all())
        return self._page(rows, limit, lambda item: item.referral_id)

    async def list_rewards(
        self, *, user_id: str, cursor: str | None, limit: int
    ) -> Page[ReferralRewardRecord]:
        await self.release_due_rewards(user_id=user_id)
        query = (
            select(ReferralRewardRecord)
            .where(ReferralRewardRecord.beneficiary_user_id == user_id)
            .order_by(ReferralRewardRecord.referral_reward_id)
        )
        if cursor is not None:
            query = query.where(ReferralRewardRecord.referral_reward_id > cursor)
        rows = list((await self._session.scalars(query.limit(limit + 1))).all())
        return self._page(rows, limit, lambda item: item.referral_reward_id)

    async def record_milestone(
        self, *, invitee_user_id: str, milestone_code: str, payment_identity_hash: str | None = None
    ) -> None:
        record = await self._session.scalar(
            select(ReferralBindingRecord)
            .where(ReferralBindingRecord.invitee_user_id == invitee_user_id)
            .with_for_update()
        )
        if record is None or record.status in {"REJECTED", "REVOKED"}:
            return
        now = datetime.now(UTC)
        if payment_identity_hash is not None:
            await self._register_payment_identity(invitee_user_id, payment_identity_hash, now)
            policy = dict(record.campaign_snapshot["antiAbusePolicy"])
            if policy["blockSamePaymentIdentity"] and await self._shared_payment_identity(
                record.inviter_user_id, invitee_user_id
            ):
                record.status = "REJECTED"
                record.rejection_reason_code = "SHARED_PAYMENT_IDENTITY"
                record.risk_score = 100
                record.resource_version += 1
                record.updated_at = now
                await self._reject_rewards(record=record, now=now)
                self._audit(
                    record.referral_id,
                    invitee_user_id,
                    "REFERRAL_REJECTED",
                    "Shared payment identity detected.",
                    {},
                    now,
                )
                return
        await self._apply_milestone(record, milestone_code, now)

    async def _reject_rewards(self, *, record: ReferralBindingRecord, now: datetime) -> None:
        rewards = list(
            (
                await self._session.scalars(
                    select(ReferralRewardRecord)
                    .where(ReferralRewardRecord.referral_id == record.referral_id)
                    .with_for_update()
                )
            ).all()
        )
        for reward in rewards:
            if reward.status == "PENDING":
                reward.status = "REJECTED"
                reward.updated_at = now
            elif reward.status == "GRANTED":
                try:
                    await self._reverse_grant(reward, now)
                except ApiError:
                    self._audit(
                        record.referral_id,
                        record.invitee_user_id,
                        "REWARD_REVERSAL_REVIEW_REQUIRED",
                        "Risk rejection found a consumed reward.",
                        {"referralRewardId": reward.referral_reward_id},
                        now,
                    )
                else:
                    reward.status = "REVERSED"
                    reward.updated_at = now

    async def release_due_rewards(self, *, user_id: str | None = None) -> int:
        now = datetime.now(UTC)
        query = (
            select(ReferralRewardRecord)
            .where(
                ReferralRewardRecord.status == "PENDING",
                ReferralRewardRecord.available_at <= now,
            )
            .with_for_update(skip_locked=True)
        )
        if user_id is not None:
            query = query.where(ReferralRewardRecord.beneficiary_user_id == user_id)
        rewards = list((await self._session.scalars(query)).all())
        for reward in rewards:
            await self._grant_reward(reward, now)
            binding = await self._session.get(ReferralBindingRecord, reward.referral_id)
            if binding is not None:
                await self._refresh_binding_status(binding)
        if rewards:
            await self._session.commit()
        return len(rewards)

    async def reverse_reward(
        self, *, referral_reward_id: str, actor_id: str, reason: str
    ) -> ReferralRewardRecord:
        reward = await self._session.scalar(
            select(ReferralRewardRecord)
            .where(ReferralRewardRecord.referral_reward_id == referral_reward_id)
            .with_for_update()
        )
        if reward is None:
            raise self._not_found("REFERRAL_REWARD_NOT_FOUND", "Referral reward")
        if reward.status == "REVERSED":
            return reward
        if reward.status != "GRANTED" or reward.grant_snapshot is None:
            raise ApiError(
                status_code=409,
                code="REFERRAL_REWARD_NOT_REVERSIBLE",
                message="Reward has not been granted.",
            )
        now = datetime.now(UTC)
        await self._reverse_grant(reward, now)
        reward.status = "REVERSED"
        reward.updated_at = now
        self._audit(
            reward.referral_id,
            actor_id,
            "REWARD_REVERSED",
            reason,
            {"referralRewardId": referral_reward_id},
            now,
        )
        await self._session.commit()
        return reward

    async def _apply_milestone(
        self, record: ReferralBindingRecord, code: str, now: datetime
    ) -> None:
        if code not in record.completed_milestones:
            record.completed_milestones = sorted([*record.completed_milestones, code])
            record.resource_version += 1
            record.updated_at = now
        rules = [
            dict(item)
            for item in record.campaign_snapshot["rewardRules"]
            if item["milestoneCode"] == code
        ]
        if not rules:
            return
        qualified_count = int(
            await self._session.scalar(
                select(func.count())
                .select_from(ReferralBindingRecord)
                .where(
                    ReferralBindingRecord.campaign_id == record.campaign_id,
                    ReferralBindingRecord.inviter_user_id == record.inviter_user_id,
                    ReferralBindingRecord.status.in_(["QUALIFIED", "REWARDED"]),
                )
            )
            or 0
        )
        if qualified_count >= int(record.campaign_snapshot["maxQualifiedInvitesPerInviter"]):
            record.status = "REJECTED"
            record.rejection_reason_code = "INVITER_LIMIT_REACHED"
            return
        record.status = "QUALIFIED"
        record.qualified_at = record.qualified_at or now
        for index, rule in enumerate(rules):
            rule_key = sha256(dumps({"index": index, **rule}, sort_keys=True).encode()).hexdigest()
            exists = await self._session.scalar(
                select(ReferralRewardRecord).where(
                    ReferralRewardRecord.referral_id == record.referral_id,
                    ReferralRewardRecord.rule_key == rule_key,
                )
            )
            if exists is not None:
                continue
            beneficiary = (
                record.inviter_user_id
                if rule["beneficiary"] == "INVITER"
                else record.invitee_user_id
            )
            reward = ReferralRewardRecord(
                referral_reward_id=f"rrw_{uuid4().hex}",
                referral_id=record.referral_id,
                beneficiary_user_id=beneficiary,
                beneficiary=str(rule["beneficiary"]),
                milestone_code=code,
                reward_unit=str(rule["rewardUnit"]),
                reward_amount=int(rule["rewardAmount"]),
                rule_key=rule_key,
                status="PENDING",
                wallet_ledger_entry_id=None,
                entitlement_event_id=None,
                available_at=now + timedelta(hours=int(rule["coolingOffHours"])),
                grant_snapshot=None,
                created_at=now,
                updated_at=now,
            )
            self._session.add(reward)
            if int(rule["coolingOffHours"]) == 0:
                await self._session.flush()
                await self._grant_reward(reward, now)
        await self._refresh_binding_status(record)

    async def _grant_reward(self, reward: ReferralRewardRecord, now: datetime) -> None:
        entitlement = await self._session.scalar(
            select(EntitlementRecord)
            .where(EntitlementRecord.user_id == reward.beneficiary_user_id)
            .with_for_update()
        )
        wallet = await self._session.scalar(
            select(WalletAccountRecord)
            .where(WalletAccountRecord.user_id == reward.beneficiary_user_id)
            .with_for_update()
        )
        if entitlement is None or wallet is None:
            reward.status = "REJECTED"
            reward.updated_at = now
            return
        if reward.reward_unit == "ENERGY":
            balance_before = wallet.energy_balance
            wallet.energy_balance += reward.reward_amount
            wallet.resource_version += 1
            wallet.updated_at = now
            ledger_id = f"wle_{uuid4().hex}"
            reward.wallet_ledger_entry_id = ledger_id
            reward.grant_snapshot = {
                "before": balance_before,
                "after": wallet.energy_balance,
            }
            self._session.add(
                WalletLedgerRecord(
                    ledger_entry_id=ledger_id,
                    user_id=reward.beneficiary_user_id,
                    generation_id=None,
                    entry_type="CREDIT",
                    energy_delta=reward.reward_amount,
                    reserved_delta=0,
                    balance_after=wallet.energy_balance,
                    reserved_after=wallet.energy_reserved,
                    reason_code=f"REFERRAL_{reward.referral_reward_id}",
                    created_at=now,
                )
            )
        else:
            entitlement_before = self._entitlement_snapshot(entitlement)
            if reward.reward_unit == "TEXT_QUOTA":
                entitlement.text_remaining += reward.reward_amount
            elif reward.reward_unit == "VISION_QUOTA":
                entitlement.vision_remaining += reward.reward_amount
            elif reward.reward_unit == "PLAN_DAYS":
                entitlement.plan_expires_at = max(
                    now, entitlement.plan_expires_at or now
                ) + timedelta(days=reward.reward_amount)
            entitlement.resource_version += 1
            entitlement.updated_at = now
            reward.entitlement_event_id = f"rent_{uuid4().hex}"
            reward.grant_snapshot = {
                "before": entitlement_before,
                "after": self._entitlement_snapshot(entitlement),
            }
        reward.status = "GRANTED"
        reward.updated_at = now
        self._audit(
            reward.referral_id,
            reward.beneficiary_user_id,
            "REWARD_GRANTED",
            "Configured referral reward granted.",
            {"rewardId": reward.referral_reward_id},
            now,
        )

    async def _reverse_grant(self, reward: ReferralRewardRecord, now: datetime) -> None:
        snapshot = dict(reward.grant_snapshot or {})
        if reward.reward_unit == "ENERGY":
            wallet = await self._session.scalar(
                select(WalletAccountRecord)
                .where(WalletAccountRecord.user_id == reward.beneficiary_user_id)
                .with_for_update()
            )
            assert wallet is not None
            if wallet.energy_balance - reward.reward_amount < wallet.energy_reserved:
                raise ApiError(
                    status_code=409,
                    code="REFERRAL_REWARD_ALREADY_CONSUMED",
                    message="Reward cannot be reversed after consumption.",
                )
            wallet.energy_balance -= reward.reward_amount
            wallet.resource_version += 1
            wallet.updated_at = now
            self._session.add(
                WalletLedgerRecord(
                    ledger_entry_id=f"wle_{uuid4().hex}",
                    user_id=reward.beneficiary_user_id,
                    generation_id=None,
                    entry_type="ADJUSTMENT",
                    energy_delta=-reward.reward_amount,
                    reserved_delta=0,
                    balance_after=wallet.energy_balance,
                    reserved_after=wallet.energy_reserved,
                    reason_code=f"REFERRAL_REVERSAL_{reward.referral_reward_id}",
                    created_at=now,
                )
            )
            return
        entitlement = await self._session.scalar(
            select(EntitlementRecord)
            .where(EntitlementRecord.user_id == reward.beneficiary_user_id)
            .with_for_update()
        )
        assert entitlement is not None
        if self._entitlement_snapshot(entitlement) != snapshot["after"]:
            raise ApiError(
                status_code=409,
                code="REFERRAL_REWARD_ALREADY_CONSUMED",
                message="Reward cannot be reversed after entitlement changes.",
            )
        before = dict(snapshot["before"])
        entitlement.text_remaining = int(before["textRemaining"])
        entitlement.vision_remaining = int(before["visionRemaining"])
        expiry = before["planExpiresAt"]
        entitlement.plan_expires_at = datetime.fromisoformat(expiry) if expiry else None
        entitlement.resource_version += 1
        entitlement.updated_at = now

    async def _refresh_binding_status(self, record: ReferralBindingRecord) -> None:
        rewards = list(
            (
                await self._session.scalars(
                    select(ReferralRewardRecord).where(
                        ReferralRewardRecord.referral_id == record.referral_id
                    )
                )
            ).all()
        )
        if rewards and all(item.status == "GRANTED" for item in rewards):
            record.status = "REWARDED"

    async def _active_campaign(
        self, *, user: UserRecord, channel: str, campaign_id: str | None = None
    ) -> ReferralCampaignRecord:
        now = datetime.now(UTC)
        region = user.locale.rsplit("-", 1)[-1].upper()
        query = select(ReferralCampaignRecord).where(
            ReferralCampaignRecord.region == region,
            ReferralCampaignRecord.published_snapshot.is_not(None),
        )
        if campaign_id is not None:
            query = query.where(ReferralCampaignRecord.campaign_id == campaign_id)
        campaigns = list(
            (
                await self._session.scalars(
                    query.order_by(ReferralCampaignRecord.updated_at.desc())
                )
            ).all()
        )
        for campaign in campaigns:
            snapshot = dict(campaign.published_snapshot or {})
            effective_at = datetime.fromisoformat(str(snapshot["_effectiveAt"]))
            expires_value = snapshot.get("_expiresAt")
            expires_at = datetime.fromisoformat(str(expires_value)) if expires_value else None
            rollout = int(snapshot["_rolloutPercentage"])
            if (
                channel in snapshot["salesChannels"]
                and effective_at <= now
                and (expires_at is None or expires_at > now)
                and self._bucket(user.user_id, campaign.campaign_id) < rollout
            ):
                return campaign
        raise self._not_found("REFERRAL_CAMPAIGN_UNAVAILABLE", "Referral campaign")

    async def _invite_code(
        self, *, campaign: ReferralCampaignRecord, user_id: str
    ) -> ReferralInviteCodeRecord:
        existing = await self._session.scalar(
            select(ReferralInviteCodeRecord).where(
                ReferralInviteCodeRecord.campaign_id == campaign.campaign_id,
                ReferralInviteCodeRecord.user_id == user_id,
            )
        )
        if existing is not None:
            return existing
        digest = new_hmac(
            self._opaque_key, f"{campaign.campaign_id}:{user_id}".encode(), sha256
        ).digest()
        code = b32encode(digest).decode().rstrip("=")[:10]
        record = ReferralInviteCodeRecord(
            invite_code=code,
            campaign_id=campaign.campaign_id,
            user_id=user_id,
            created_at=datetime.now(UTC),
        )
        self._session.add(record)
        await self._session.flush()
        return record

    async def _same_device(self, inviter_user_id: str, device_id: str) -> bool:
        return (
            await self._session.scalar(
                select(UserDeviceRecord.id).where(
                    UserDeviceRecord.user_id == inviter_user_id,
                    UserDeviceRecord.device_id == device_id,
                    UserDeviceRecord.revoked_at.is_(None),
                )
            )
            is not None
        )

    async def _shared_payment_identity(self, inviter: str, invitee: str) -> bool:
        inviter_hashes = select(ReferralPaymentIdentityRecord.identity_hash).where(
            ReferralPaymentIdentityRecord.user_id == inviter
        )
        return (
            await self._session.scalar(
                select(ReferralPaymentIdentityRecord.identity_id).where(
                    ReferralPaymentIdentityRecord.user_id == invitee,
                    ReferralPaymentIdentityRecord.identity_hash.in_(inviter_hashes),
                )
            )
            is not None
        )

    async def _register_payment_identity(
        self, user_id: str, identity_hash: str, now: datetime
    ) -> None:
        existing = await self._session.scalar(
            select(ReferralPaymentIdentityRecord).where(
                ReferralPaymentIdentityRecord.user_id == user_id,
                ReferralPaymentIdentityRecord.identity_hash == identity_hash,
            )
        )
        if existing is None:
            self._session.add(
                ReferralPaymentIdentityRecord(
                    identity_id=f"rpi_{uuid4().hex}",
                    user_id=user_id,
                    identity_hash=identity_hash,
                    created_at=now,
                )
            )
            await self._session.flush()

    async def _user(self, user_id: str) -> UserRecord:
        user = await self._session.get(UserRecord, user_id)
        if user is None:
            raise self._not_found("USER_NOT_FOUND", "User")
        return user

    async def _locked_campaign(self, campaign_id: str) -> ReferralCampaignRecord:
        record = await self._session.scalar(
            select(ReferralCampaignRecord)
            .where(ReferralCampaignRecord.campaign_id == campaign_id)
            .with_for_update()
        )
        if record is None:
            raise self._not_found("REFERRAL_CAMPAIGN_NOT_FOUND", "Campaign")
        return record

    async def _campaign_version(
        self, campaign_id: str, version: int, required: bool = True
    ) -> ReferralCampaignVersionRecord | None:
        record = await self._session.scalar(
            select(ReferralCampaignVersionRecord).where(
                ReferralCampaignVersionRecord.campaign_id == campaign_id,
                ReferralCampaignVersionRecord.version == version,
            )
        )
        if record is None and required:
            raise self._not_found("REFERRAL_CAMPAIGN_VERSION_NOT_FOUND", "Campaign version")
        return record

    def _version(
        self,
        record: ReferralCampaignRecord,
        *,
        admin_id: str,
        action: str,
        was_published: bool,
        now: datetime,
    ) -> None:
        self._session.add(
            ReferralCampaignVersionRecord(
                campaign_version_id=f"rcpv_{uuid4().hex}",
                campaign_id=record.campaign_id,
                version=record.version,
                snapshot=self._snapshot(record),
                was_published=was_published,
                action=action,
                created_by_admin_id=admin_id,
                created_at=now,
            )
        )

    @staticmethod
    def _snapshot(record: ReferralCampaignRecord) -> dict[str, Any]:
        return {
            "campaignCode": record.campaign_code,
            "displayName": record.display_name,
            "description": record.description,
            "region": record.region,
            "salesChannels": list(record.sales_channels),
            "bindingWindowHours": record.binding_window_hours,
            "maxQualifiedInvitesPerInviter": record.max_qualified_invites_per_inviter,
            "rewardRules": list(record.reward_rules),
            "antiAbusePolicy": dict(record.anti_abuse_policy),
        }

    @staticmethod
    def _apply_snapshot(record: ReferralCampaignRecord, snapshot: dict[str, Any]) -> None:
        record.campaign_code = str(snapshot["campaignCode"])
        record.display_name = str(snapshot["displayName"])
        record.description = str(snapshot["description"])
        record.region = str(snapshot["region"])
        record.sales_channels = list(snapshot["salesChannels"])
        record.binding_window_hours = int(snapshot["bindingWindowHours"])
        record.max_qualified_invites_per_inviter = int(snapshot["maxQualifiedInvitesPerInviter"])
        record.reward_rules = list(snapshot["rewardRules"])
        record.anti_abuse_policy = dict(snapshot["antiAbusePolicy"])

    @staticmethod
    def _validate_rules(values: dict[str, Any]) -> None:
        rules = list(values["reward_rules"])
        keys = [(item["milestoneCode"], item["beneficiary"], item["rewardUnit"]) for item in rules]
        if len(keys) != len(set(keys)):
            raise ApiError(
                status_code=400,
                code="REFERRAL_RULE_INVALID",
                message="Referral reward rules must be unique.",
            )
        if not values["anti_abuse_policy"]["blockSelfReferral"]:
            raise ApiError(
                status_code=400,
                code="REFERRAL_RULE_INVALID",
                message="Self-referral protection cannot be disabled.",
            )

    def _display_hint(self, user_id: str) -> str:
        digest = new_hmac(self._opaque_key, user_id.encode(), sha256).hexdigest().upper()
        return f"new user {digest[:4]}"

    @staticmethod
    def _entitlement_snapshot(record: EntitlementRecord) -> dict[str, Any]:
        return {
            "textRemaining": record.text_remaining,
            "visionRemaining": record.vision_remaining,
            "planExpiresAt": record.plan_expires_at.isoformat() if record.plan_expires_at else None,
        }

    @staticmethod
    def _bucket(user_id: str, campaign_id: str) -> int:
        return int.from_bytes(sha256(f"{campaign_id}:{user_id}".encode()).digest()[:8], "big") % 100

    @staticmethod
    def _lock_key(value: str) -> int:
        return int.from_bytes(sha256(value.encode()).digest()[:8], "big") % (2**63 - 1)

    @staticmethod
    def _assert_version(record: ReferralCampaignRecord, expected: int) -> None:
        if record.resource_version != expected:
            raise ApiError(
                status_code=409,
                code="RESOURCE_VERSION_CONFLICT",
                message="Campaign resource version changed.",
                details={"currentVersion": record.resource_version},
            )

    def _audit(
        self,
        resource_id: str,
        actor_id: str,
        action: str,
        reason: str,
        metadata: dict[str, Any],
        now: datetime,
    ) -> None:
        self._session.add(
            ReferralAuditRecord(
                audit_id=f"raud_{uuid4().hex}",
                resource_type="REFERRAL",
                resource_id=resource_id,
                actor_id=actor_id,
                action=action,
                reason=reason,
                metadata_json=metadata,
                created_at=now,
            )
        )

    @staticmethod
    def _page(rows: list[RecordT], limit: int, key: Any) -> Page[RecordT]:
        visible = rows[:limit]
        return Page(
            items=visible,
            next_cursor=key(visible[-1]) if len(rows) > limit and visible else None,
            has_more=len(rows) > limit,
        )

    @staticmethod
    def _not_found(code: str, label: str) -> ApiError:
        return ApiError(status_code=404, code=code, message=f"{label} was not found.")
