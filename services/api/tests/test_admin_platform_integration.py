"""用户运营、公告、网站配置和客服工单 PostgreSQL 集成测试。"""

import os
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
import pytest_asyncio
from love_reply_api.application.admin_platform import AdminPlatformService
from love_reply_api.application.support import SupportService
from love_reply_api.infrastructure.database import engine, session_factory
from love_reply_api.infrastructure.generation_records import (
    EntitlementRecord,
    WalletAccountRecord,
    WalletLedgerRecord,
)
from love_reply_api.infrastructure.identity_records import (
    AuthSessionRecord,
    ConsentRecord,
    UserDeviceRecord,
    UserProfileRecord,
    UserRecord,
)
from love_reply_api.infrastructure.platform_records import (
    AdminPlatformAuditRecord,
    NoticeVersionRecord,
    SupportTicketMessageRecord,
    SupportTicketRecord,
)
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_INTEGRATION_TESTS") != "1", reason="requires PostgreSQL"
)


@pytest_asyncio.fixture(autouse=True)
async def clean_platform_fixtures() -> AsyncIterator[None]:
    async with session_factory() as session:
        await _delete_fixture_rows(session)
    yield
    async with session_factory() as session:
        await _delete_fixture_rows(session)
    await engine.dispose()


async def _delete_fixture_rows(session: AsyncSession) -> None:
    """仅清理本测试创建的运营数据，保留迁移写入的网站配置基线。"""
    await session.execute(delete(SupportTicketMessageRecord))
    await session.execute(delete(SupportTicketRecord))
    await session.execute(delete(NoticeVersionRecord))
    await session.execute(delete(AdminPlatformAuditRecord))
    fixture_users = select(UserRecord.user_id).where(UserRecord.email_normalized.like("platform-%"))
    user_ids = list((await session.scalars(fixture_users)).all())
    if user_ids:
        for model in (
            WalletLedgerRecord,
            WalletAccountRecord,
            EntitlementRecord,
            ConsentRecord,
            AuthSessionRecord,
            UserDeviceRecord,
            UserProfileRecord,
        ):
            await session.execute(delete(model).where(model.user_id.in_(user_ids)))
        await session.execute(delete(UserRecord).where(UserRecord.user_id.in_(user_ids)))
    await session.commit()


async def _create_user(session: AsyncSession) -> UserRecord:
    now = datetime.now(UTC)
    suffix = uuid4().hex[:8]
    user = UserRecord(
        user_id=f"usr_platform_{suffix}",
        phone_e164=f"+1555{suffix[:7]}",
        email_normalized=f"platform-{suffix}@example.com",
        status="ACTIVE",
        locale="zh-CN",
        time_zone="Asia/Shanghai",
        resource_version=1,
        created_at=now,
        updated_at=now,
    )
    session.add(user)
    await session.flush()
    session.add(UserProfileRecord(user_id=user.user_id, nickname="运营测试用户", updated_at=now))
    session.add(
        UserDeviceRecord(
            id=f"dev_{suffix}",
            user_id=user.user_id,
            device_id=f"device_{suffix}",
            platform="ANDROID",
            model="Fixture Phone",
            last_seen_at=now,
            created_at=now,
            revoked_at=None,
        )
    )
    session.add(
        ConsentRecord(
            consent_id=f"consent_{suffix}",
            user_id=user.user_id,
            consent_type="PRIVACY_POLICY",
            document_version="privacy-test-v1",
            granted=True,
            required=True,
            granted_at=now,
            resource_version=1,
            updated_at=now,
        )
    )
    session.add(
        EntitlementRecord(
            user_id=user.user_id,
            plan_code="TEST_PLAN",
            plan_expires_at=now + timedelta(days=30),
            text_remaining=12,
            text_reserved=0,
            vision_remaining=3,
            allowed_model_ids=["model_standard"],
            allowed_style_ids=["warm"],
            resource_version=1,
            updated_at=now,
        )
    )
    session.add(
        WalletAccountRecord(
            user_id=user.user_id,
            energy_balance=88,
            energy_reserved=0,
            resource_version=1,
            updated_at=now,
        )
    )
    session.add(
        WalletLedgerRecord(
            ledger_entry_id=f"ledger_{suffix}",
            user_id=user.user_id,
            generation_id=None,
            entry_type="ADMIN_GRANT",
            energy_delta=88,
            reserved_delta=0,
            balance_after=88,
            reserved_after=0,
            reason_code="TEST_FIXTURE",
            created_at=now,
        )
    )
    session.add(
        AuthSessionRecord(
            session_id=f"ses_{suffix}",
            user_id=user.user_id,
            device_id=f"device_{suffix}",
            refresh_token_hash=f"hash_{suffix}",
            expires_at=now + timedelta(days=7),
            revoked_at=None,
            rotated_to_session_id=None,
            created_at=now,
        )
    )
    await session.commit()
    return user


@pytest.mark.asyncio
async def test_user_management_masks_identifiers_and_revokes_sessions() -> None:
    async with session_factory() as session:
        user = await _create_user(session)
        service = AdminPlatformService(session)
        page = await service.list_users(search=user.user_id, status="ACTIVE", cursor=None, limit=20)
        assert len(page.items) == 1
        assert page.items[0]["masked_email"].endswith("@example.com")
        assert page.items[0]["masked_email"] != user.email_normalized
        assert "****" in page.items[0]["masked_phone"]

        detail = await service.get_user_detail(user.user_id)
        assert len(detail["devices"]) == 1
        assert len(detail["consents"]) == 1
        entitlement = await service.get_user_entitlement(user.user_id)
        assert entitlement["wallet"].energy_balance == 88
        ledger = await service.list_user_ledger(user_id=user.user_id, cursor=None, limit=20)
        assert len(ledger.items) == 1

        suspended = await service.change_user_status(
            user_id=user.user_id,
            expected_version=1,
            target_status="SUSPENDED",
            admin_id="adm_platform_test",
            audit_reason="经客服升级核实需要暂时冻结账户",
        )
        assert suspended["status"] == "SUSPENDED"
        auth_session = await session.scalar(
            select(AuthSessionRecord).where(AuthSessionRecord.user_id == user.user_id)
        )
        assert auth_session is not None and auth_session.revoked_at is not None

        restored = await service.change_user_status(
            user_id=user.user_id,
            expected_version=2,
            target_status="ACTIVE",
            admin_id="adm_platform_test",
            audit_reason="复核完成并确认可以恢复账户访问",
        )
        assert restored["status"] == "ACTIVE"
        audits = list(
            (
                await session.scalars(
                    select(AdminPlatformAuditRecord).where(
                        AdminPlatformAuditRecord.resource_id == user.user_id
                    )
                )
            ).all()
        )
        assert [item.action for item in audits] == ["USER_SUSPENDED", "USER_RESTORED"]


@pytest.mark.asyncio
async def test_configuration_draft_notice_targeting_and_support_visibility() -> None:
    async with session_factory() as session:
        user = await _create_user(session)
        platform = AdminPlatformService(session)
        published = await platform.get_system_config(published_only=True)
        configuration = {
            **published.configuration,
            "websiteName": "运营测试站点",
            "appName": "运营测试 App",
        }
        draft = await platform.update_system_config(
            expected_version=(await platform.get_system_config()).resource_version,
            configuration=configuration,
            admin_id="adm_platform_test",
            audit_reason="保存经产品复核的网站基础信息草稿",
        )
        assert draft.status == "DRAFT"
        assert (
            await platform.get_system_config(published_only=True)
        ).config_id == published.config_id
        released = await platform.publish_system_config(
            expected_version=draft.resource_version,
            admin_id="adm_platform_test",
            audit_reason="发布已经复核通过的网站基础信息",
        )
        assert released.status == "PUBLISHED"

        now = datetime.now(UTC)
        notice = await platform.create_notice(
            values={
                "title": "版本定向公告",
                "body": "仅向指定版本和语言展示。",
                "notice_type": "GENERAL",
                "target_platforms": ["ANDROID"],
                "target_locales": ["zh"],
                "min_client_version": "2.0.0",
                "max_client_version": "3.0.0",
                "display_frequency": "ONCE",
                "starts_at": now - timedelta(minutes=1),
                "ends_at": now + timedelta(days=1),
            },
            admin_id="adm_platform_test",
            audit_reason="创建用于验证版本定向能力的公告",
        )
        await platform.publish_notice(
            notice_id=notice.notice_id,
            expected_version=notice.resource_version,
            admin_id="adm_platform_test",
            audit_reason="发布已经复核通过的版本定向公告",
        )
        assert not await platform.list_public_notices(
            platform="ANDROID", locale="zh-CN", client_version="1.9.9", now=now
        )
        visible = await platform.list_public_notices(
            platform="ANDROID", locale="zh-CN", client_version="2.1.0", now=now
        )
        assert [item.notice_id for item in visible] == [notice.notice_id]
        assert not await platform.list_public_notices(
            platform="ADMIN_WEB", locale="zh-CN", client_version="2.1.0", now=now
        )
        await platform.revoke_notice(
            notice_id=notice.notice_id,
            expected_version=visible[0].resource_version,
            admin_id="adm_platform_test",
            audit_reason="验证完成后立即撤回测试公告内容",
        )

        support = SupportService(session)
        ticket = await support.create_ticket(
            user_id=user.user_id,
            category="PAYMENT",
            subject="支付结果咨询",
            body="订单显示支付成功但权益尚未到账。",
        )
        await support.admin_update(
            ticket_id=ticket.ticket_id,
            expected_version=ticket.resource_version,
            admin_id="adm_platform_test",
            body="内部核对支付回调记录。",
            internal=True,
            status="WAITING_SUPPORT",
            priority="HIGH",
            assigned_admin_id="adm_platform_test",
            audit_reason="分派账务客服并记录内部核对事项",
        )
        _, admin_messages = await support.get_ticket(ticket_id=ticket.ticket_id)
        _, user_messages = await support.get_ticket(
            ticket_id=ticket.ticket_id, user_id=user.user_id
        )
        assert len(admin_messages) == 2
        assert len(user_messages) == 1
        assert admin_messages[-1].internal is True
