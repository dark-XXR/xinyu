"""统一合规审计账本、加密正文、法务冻结和监管导出 PostgreSQL 集成测试。"""

import os
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from love_reply_api.application.audit import ComplianceAuditService
from love_reply_api.config import get_settings
from love_reply_api.infrastructure.audit_records import (
    ComplianceAuditEventRecord,
    ComplianceAuditExportRecord,
)
from love_reply_api.infrastructure.database import engine, session_factory
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_INTEGRATION_TESTS") != "1", reason="requires PostgreSQL"
)


@pytest_asyncio.fixture(autouse=True)
async def clean_audit_tables() -> AsyncIterator[None]:
    async with session_factory() as session:
        await _delete(session)
    yield
    async with session_factory() as session:
        await _delete(session)
    await engine.dispose()


async def _delete(session: AsyncSession) -> None:
    await session.execute(delete(ComplianceAuditExportRecord))
    await session.execute(delete(ComplianceAuditEventRecord))
    await session.commit()


@pytest.mark.asyncio
async def test_sensitive_content_is_encrypted_redacted_and_read_is_audited() -> None:
    async with session_factory() as session:
        service = ComplianceAuditService(session=session, settings=get_settings())
        source = await service.record_event(
            category="AI",
            event_type="AI_GENERATION_COMPLETED",
            outcome="SUCCEEDED",
            severity="INFO",
            actor_type="USER",
            actor_id="usr_audit",
            user_id="usr_audit",
            resource_type="GENERATION",
            resource_id="gen_audit",
            generation_id="gen_audit",
            summary="AI 回复生成完成",
            metadata={
                "modelId": "gpt-test",
                "apiKey": "must-not-leak",
                "otpCode": "123456",
                "totp_code": "123456",
                "one-time-password": "123456",
                "verification_code": "654321",
                "Authorization": "Bearer must-not-leak",
                "signature": "payment-signature",
                "statusCode": 200,
                "nested": {"client-secret": "nested-secret"},
                "secrets": [
                    {"name": "apiKey", "value": "descriptor-secret"},
                    {"credentialName": "password", "credentialValue": "smtp-secret"},
                ],
            },
            sensitive_payload={
                "input": {"text": "用户原始聊天内容"},
                "output": {"text": "模型回复内容"},
            },
            commit=True,
        )
        assert source.metadata_json["apiKey"] == "[REDACTED]"
        assert source.metadata_json["otpCode"] == "[REDACTED]"
        assert source.metadata_json["totp_code"] == "[REDACTED]"
        assert source.metadata_json["one-time-password"] == "[REDACTED]"
        assert source.metadata_json["verification_code"] == "[REDACTED]"
        assert source.metadata_json["Authorization"] == "[REDACTED]"
        assert source.metadata_json["signature"] == "[REDACTED]"
        assert source.metadata_json["nested"]["client-secret"] == "[REDACTED]"
        assert source.metadata_json["secrets"][0]["value"] == "[REDACTED]"
        assert source.metadata_json["secrets"][1]["credentialValue"] == "[REDACTED]"
        assert source.metadata_json["statusCode"] == 200
        assert source.sensitive_payload_ciphertext is not None
        assert "用户原始聊天内容" not in source.sensitive_payload_ciphertext

        content = await service.reveal_sensitive(
            event_id=source.event_id,
            admin_id="adm_owner",
            session_id="ases_audit",
            audit_reason="依法核查指定用户投诉材料",
            request_id="req_audit_read",
        )
        assert content["input"]["text"] == "用户原始聊天内容"
        read_event = await session.scalar(
            select(ComplianceAuditEventRecord).where(
                ComplianceAuditEventRecord.event_type == "AUDIT_SENSITIVE_CONTENT_READ"
            )
        )
        assert read_event is not None
        assert read_event.admin_id == "adm_owner"


@pytest.mark.asyncio
async def test_hash_chain_detects_tampering_and_legal_hold_is_audited() -> None:
    async with session_factory() as session:
        service = ComplianceAuditService(session=session, settings=get_settings())
        first = await service.record_event(
            category="AUTH",
            event_type="LOGIN_SUCCEEDED",
            outcome="SUCCEEDED",
            severity="INFO",
            actor_type="USER",
            actor_id="usr_chain",
            user_id="usr_chain",
            summary="用户登录成功",
            commit=True,
        )
        second = await service.record_event(
            category="PAYMENT",
            event_type="ORDER_CREATED",
            outcome="SUCCEEDED",
            severity="INFO",
            actor_type="USER",
            actor_id="usr_chain",
            user_id="usr_chain",
            order_id="ord_chain",
            summary="用户创建订单",
            commit=True,
        )
        valid, invalid_id, count = await service.verify_chain()
        assert valid is True and invalid_id is None and count == 2

        held = await service.set_legal_hold(
            event_id=first.event_id,
            enabled=True,
            admin_id="adm_owner",
            session_id="ases_hold",
            audit_reason="监管调查要求冻结记录",
            request_id="req_hold",
        )
        assert held.legal_hold is True
        valid, _, count = await service.verify_chain()
        assert valid is True and count == 3

        second.summary = "数据库被绕过应用直接修改"
        await session.commit()
        valid, invalid_id, _ = await service.verify_chain()
        assert valid is False and invalid_id == second.event_id


@pytest.mark.asyncio
async def test_regulatory_export_is_encrypted_bounded_and_read_is_audited() -> None:
    async with session_factory() as session:
        service = ComplianceAuditService(session=session, settings=get_settings())
        await service.record_event(
            category="PAYMENT",
            event_type="PAYMENT_SETTLED",
            outcome="SUCCEEDED",
            severity="INFO",
            actor_type="SYSTEM",
            user_id="usr_export",
            order_id="ord_export",
            summary="支付到账并完成权益发放",
            sensitive_payload={"providerEvidence": "verified callback"},
            commit=True,
        )
        filters = {
            "category": "PAYMENT",
            "event_type": None,
            "outcome": None,
            "user_id": "usr_export",
            "admin_id": None,
            "request_id": None,
            "resource_type": None,
            "resource_id": None,
            "order_id": None,
            "generation_id": None,
            "from_time": None,
            "to_time": None,
        }
        export = await service.create_export(
            admin_id="adm_owner",
            session_id="ases_export",
            request_id="req_export",
            audit_reason="依法向监管部门提供指定支付记录",
            include_sensitive_content=True,
            filters=filters,
        )
        assert export.event_count == 1
        assert "PAYMENT_SETTLED" not in export.bundle_ciphertext
        bundle = await service.read_export(
            export_id=export.export_id,
            admin_id="adm_owner",
            session_id="ases_export",
            request_id="req_export_read",
            audit_reason="复核监管材料导出内容",
        )
        assert bundle["events"][0]["eventType"] == "PAYMENT_SETTLED"
        assert bundle["events"][0]["sensitiveContent"]["providerEvidence"] == "verified callback"
