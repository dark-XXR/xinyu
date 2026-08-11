"""邀请推广版本、并发绑定、风控、奖励和撤销 PostgreSQL 集成测试。"""

import asyncio
import os
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from love_reply_api.application.errors import ApiError
from love_reply_api.application.referrals import ReferralService
from love_reply_api.config import get_settings
from love_reply_api.infrastructure.database import engine, session_factory
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
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_INTEGRATION_TESTS") != "1", reason="requires PostgreSQL"
)


@pytest_asyncio.fixture(autouse=True)
async def clean_database() -> AsyncIterator[None]:
    async with session_factory() as session:
        await _delete(session)
    yield
    async with session_factory() as session:
        await _delete(session)
    await engine.dispose()


async def _delete(session: AsyncSession) -> None:
    for model in (
        ReferralAuditRecord,
        ReferralPaymentIdentityRecord,
        ReferralRewardRecord,
        ReferralBindingRecord,
        ReferralInviteCodeRecord,
        ReferralCampaignVersionRecord,
        ReferralCampaignRecord,
        WalletLedgerRecord,
        UserDeviceRecord,
        WalletAccountRecord,
        EntitlementRecord,
        UserRecord,
    ):
        await session.execute(delete(model))
    await session.commit()


async def _seed_user(session: AsyncSession, user_id: str, device_id: str) -> None:
    now = datetime.now(UTC)
    session.add(
        UserRecord(
            user_id=user_id,
            phone_e164=None,
            email_normalized=f"{user_id}@example.test",
            status="ACTIVE",
            locale="zh-CN",
            time_zone="UTC",
            resource_version=1,
            created_at=now,
            updated_at=now,
        )
    )
    await session.flush()
    session.add(
        UserDeviceRecord(
            id=f"dev_{user_id}",
            user_id=user_id,
            device_id=device_id,
            platform="ANDROID",
            model="fixture",
            last_seen_at=now,
            created_at=now,
            revoked_at=None,
        )
    )
    session.add(
        EntitlementRecord(
            user_id=user_id,
            plan_code="FREE",
            plan_expires_at=None,
            text_remaining=5,
            text_reserved=0,
            vision_remaining=0,
            allowed_model_ids=["basic"],
            allowed_style_ids=["warm"],
            resource_version=1,
            updated_at=now,
        )
    )
    session.add(
        WalletAccountRecord(
            user_id=user_id,
            energy_balance=0,
            energy_reserved=0,
            resource_version=1,
            updated_at=now,
        )
    )


def _campaign_values(inviter_energy: int = 10) -> dict[str, object]:
    return {
        "campaign_code": "INVITE_LAUNCH",
        "display_name": "Invite launch",
        "description": "Synthetic single-level campaign.",
        "region": "CN",
        "sales_channels": ["ANDROID"],
        "binding_window_hours": 168,
        "max_qualified_invites_per_inviter": 100,
        "reward_rules": [
            {
                "milestoneCode": "FIRST_GENERATION",
                "beneficiary": "INVITER",
                "rewardUnit": "ENERGY",
                "rewardAmount": inviter_energy,
                "coolingOffHours": 0,
            },
            {
                "milestoneCode": "FIRST_GENERATION",
                "beneficiary": "INVITEE",
                "rewardUnit": "TEXT_QUOTA",
                "rewardAmount": 2,
                "coolingOffHours": 0,
            },
        ],
        "anti_abuse_policy": {
            "blockSelfReferral": True,
            "blockSameDevice": True,
            "blockSamePaymentIdentity": True,
            "requireVerifiedPrimaryChannel": True,
            "riskReviewScore": 60,
        },
    }


async def _published_campaign(
    session: AsyncSession,
) -> tuple[ReferralService, ReferralCampaignRecord]:
    service = ReferralService(session=session, settings=get_settings())
    draft = await service.create_campaign(admin_id="adm_maker", values=_campaign_values())
    with pytest.raises(ApiError) as captured:
        await service.publish_campaign(
            campaign_id=draft.campaign_id,
            expected_version=1,
            admin_id="adm_maker",
            rollout_percentage=100,
            effective_at=datetime.now(UTC) - timedelta(seconds=1),
            expires_at=None,
            audit_reason="Attempt campaign self approval",
        )
    assert captured.value.code == "REFERRAL_SELF_APPROVAL_FORBIDDEN"
    published = await service.publish_campaign(
        campaign_id=draft.campaign_id,
        expected_version=1,
        admin_id="adm_checker",
        rollout_percentage=100,
        effective_at=datetime.now(UTC) - timedelta(seconds=1),
        expires_at=None,
        audit_reason="Approve reviewed campaign",
    )
    return service, published


@pytest.mark.asyncio
async def test_concurrent_binding_and_milestone_replay_grant_each_reward_once() -> None:
    async with session_factory() as session:
        await _seed_user(session, "usr_inviter", "inviter-device")
        await _seed_user(session, "usr_invitee", "invitee-device")
        await session.commit()
        service, campaign = await _published_campaign(session)
        program = await service.get_program(user_id="usr_inviter", channel="ANDROID")

    async def bind_once() -> str:
        async with session_factory() as concurrent_session:
            concurrent = ReferralService(session=concurrent_session, settings=get_settings())
            record = await concurrent.bind(
                invitee_user_id="usr_invitee",
                invite_code=program.invite_code,
                device_id="invitee-device",
            )
            return record.referral_id

    first, second = await asyncio.gather(bind_once(), bind_once())
    assert first == second
    async with session_factory() as session:
        service = ReferralService(session=session, settings=get_settings())
        await service.record_milestone(
            invitee_user_id="usr_invitee", milestone_code="FIRST_GENERATION"
        )
        await session.commit()
        await service.record_milestone(
            invitee_user_id="usr_invitee", milestone_code="FIRST_GENERATION"
        )
        await session.commit()
        rewards = list((await session.scalars(select(ReferralRewardRecord))).all())
        binding = await session.get(ReferralBindingRecord, first)
        inviter_wallet = await session.get(WalletAccountRecord, "usr_inviter")
        invitee_entitlement = await session.get(EntitlementRecord, "usr_invitee")
        assert campaign.version == 1
        assert len(rewards) == 2 and all(item.status == "GRANTED" for item in rewards)
        assert binding is not None and binding.status == "REWARDED"
        assert inviter_wallet is not None and inviter_wallet.energy_balance == 10
        assert invitee_entitlement is not None and invitee_entitlement.text_remaining == 7


@pytest.mark.asyncio
async def test_campaign_update_and_rollback_do_not_reprice_existing_binding() -> None:
    async with session_factory() as session:
        for user_id, device in (
            ("usr_inviter", "device-a"),
            ("usr_old", "device-b"),
            ("usr_new", "device-c"),
        ):
            await _seed_user(session, user_id, device)
        await session.commit()
        service, campaign = await _published_campaign(session)
        program = await service.get_program(user_id="usr_inviter", channel="ANDROID")
        old_binding = await service.bind(
            invitee_user_id="usr_old", invite_code=program.invite_code, device_id="device-b"
        )
        updated = await service.update_campaign(
            campaign_id=campaign.campaign_id,
            expected_version=campaign.resource_version,
            admin_id="adm_editor",
            values=_campaign_values(inviter_energy=99),
        )
        published_v2 = await service.publish_campaign(
            campaign_id=campaign.campaign_id,
            expected_version=updated.resource_version,
            admin_id="adm_checker_2",
            rollout_percentage=100,
            effective_at=datetime.now(UTC) - timedelta(seconds=1),
            expires_at=None,
            audit_reason="Publish second reward version",
        )
        new_binding = await service.bind(
            invitee_user_id="usr_new", invite_code=program.invite_code, device_id="device-c"
        )
        assert old_binding.campaign_version == 1
        assert old_binding.campaign_snapshot["rewardRules"][0]["rewardAmount"] == 10
        assert new_binding.campaign_version == 2
        assert new_binding.campaign_snapshot["rewardRules"][0]["rewardAmount"] == 99
        rolled_back = await service.rollback_campaign(
            campaign_id=campaign.campaign_id,
            expected_version=published_v2.resource_version,
            admin_id="adm_rollback",
            target_version=1,
            audit_reason="Restore first campaign version",
        )
        assert rolled_back.version == 1
        await session.refresh(old_binding)
        assert old_binding.campaign_snapshot["rewardRules"][0]["rewardAmount"] == 10


@pytest.mark.asyncio
async def test_same_device_shared_payment_and_self_referral_are_blocked() -> None:
    async with session_factory() as session:
        for user_id, device in (
            ("usr_inviter", "shared-device"),
            ("usr_same_device", "shared-device"),
            ("usr_payment", "payment-device"),
        ):
            await _seed_user(session, user_id, device)
        await session.commit()
        service, _ = await _published_campaign(session)
        program = await service.get_program(user_id="usr_inviter", channel="ANDROID")
        with pytest.raises(ApiError) as captured:
            await service.bind(
                invitee_user_id="usr_inviter",
                invite_code=program.invite_code,
                device_id="shared-device",
            )
        assert captured.value.code == "REFERRAL_SELF_BIND_FORBIDDEN"
        same_device = await service.bind(
            invitee_user_id="usr_same_device",
            invite_code=program.invite_code,
            device_id="shared-device",
        )
        assert same_device.status == "REJECTED"
        session.add(
            ReferralPaymentIdentityRecord(
                identity_id="rpi_inviter",
                user_id="usr_inviter",
                identity_hash="hash-shared-payment",
                created_at=datetime.now(UTC),
            )
        )
        await session.commit()
        payment_binding = await service.bind(
            invitee_user_id="usr_payment",
            invite_code=program.invite_code,
            device_id="payment-device",
        )
        await service.record_milestone(
            invitee_user_id="usr_payment",
            milestone_code="FIRST_PURCHASE",
            payment_identity_hash="hash-shared-payment",
        )
        await session.commit()
        await session.refresh(payment_binding)
        assert payment_binding.status == "REJECTED"
        assert payment_binding.rejection_reason_code == "SHARED_PAYMENT_IDENTITY"


@pytest.mark.asyncio
async def test_granted_reward_reversal_is_audited_and_cannot_repeat() -> None:
    async with session_factory() as session:
        await _seed_user(session, "usr_inviter", "device-a")
        await _seed_user(session, "usr_invitee", "device-b")
        await session.commit()
        service, _ = await _published_campaign(session)
        program = await service.get_program(user_id="usr_inviter", channel="ANDROID")
        await service.bind(
            invitee_user_id="usr_invitee", invite_code=program.invite_code, device_id="device-b"
        )
        await service.record_milestone(
            invitee_user_id="usr_invitee", milestone_code="FIRST_GENERATION"
        )
        await session.commit()
        reward = await session.scalar(
            select(ReferralRewardRecord).where(
                ReferralRewardRecord.beneficiary_user_id == "usr_inviter"
            )
        )
        assert reward is not None
        reversed_reward = await service.reverse_reward(
            referral_reward_id=reward.referral_reward_id,
            actor_id="adm_risk",
            reason="Reverse confirmed abusive referral",
        )
        replay = await service.reverse_reward(
            referral_reward_id=reward.referral_reward_id,
            actor_id="adm_risk",
            reason="Idempotent reversal replay",
        )
        wallet = await session.get(WalletAccountRecord, "usr_inviter")
        audit_count = await session.scalar(
            select(func.count())
            .select_from(ReferralAuditRecord)
            .where(ReferralAuditRecord.action == "REWARD_REVERSED")
        )
        assert reversed_reward.status == "REVERSED" and replay.status == "REVERSED"
        assert wallet is not None and wallet.energy_balance == 0
        assert audit_count == 1


@pytest.mark.asyncio
async def test_campaign_version_history_marks_only_published_targets() -> None:
    """后台版本历史只把真正发布过的快照标记为可回滚目标。"""

    async with session_factory() as session:
        service, campaign = await _published_campaign(session)
        updated_values = _campaign_values()
        updated_values["display_name"] = "邀请活动第二版草稿"
        await service.update_campaign(
            campaign_id=campaign.campaign_id,
            expected_version=campaign.resource_version,
            admin_id="adm_editor",
            values=updated_values,
        )

        versions = await service.list_campaign_versions(campaign_id=campaign.campaign_id)

        assert [item.version for item in versions] == [2, 1]
        assert versions[0].was_published is False
        assert versions[1].was_published is True
