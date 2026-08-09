"""已发布邮件 API 和短信供应商的 PostgreSQL 运行时集成测试。"""

import json
import os
from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from love_reply_api.application.delivery_adapters import DeliveryResult
from love_reply_api.application.provider_runtime import RegistryEmailSender, RegistrySmsSender
from love_reply_api.application.security import SecretCipher
from love_reply_api.config import Settings
from love_reply_api.infrastructure.database import engine, session_factory
from love_reply_api.infrastructure.provider_records import (
    ProviderAuditRecord,
    ProviderCredentialVersionRecord,
    ProviderHealthCheckRecord,
    ProviderRecord,
    ProviderVersionRecord,
)
from pydantic import SecretStr
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_INTEGRATION_TESTS") != "1",
    reason="requires the isolated project PostgreSQL container",
)


class CapturingEmailApiTransport:
    def __init__(self) -> None:
        self.messages: list[dict[str, object]] = []

    async def send(self, **values: object) -> DeliveryResult:
        self.messages.append(values)
        return DeliveryResult(provider_request_id="email-api-request")


class CapturingSmsApiTransport:
    def __init__(self) -> None:
        self.messages: list[dict[str, object]] = []

    async def send_login_code(self, **values: object) -> DeliveryResult:
        self.messages.append(values)
        return DeliveryResult(provider_request_id="sms-api-request")


@pytest.fixture
def delivery_settings() -> Settings:
    return Settings(
        _env_file=None,
        data_encryption_key=SecretStr("delivery-data-key-at-least-32-random-bytes"),
    )


@pytest_asyncio.fixture(autouse=True)
async def clean_provider_tables() -> AsyncIterator[None]:
    async with session_factory() as session:
        await _delete_provider_data(session)
    await engine.dispose()
    yield
    async with session_factory() as session:
        await _delete_provider_data(session)
    await engine.dispose()


async def _delete_provider_data(session: AsyncSession) -> None:
    for record in (
        ProviderAuditRecord,
        ProviderHealthCheckRecord,
        ProviderVersionRecord,
        ProviderCredentialVersionRecord,
        ProviderRecord,
    ):
        await session.execute(delete(record))
    await session.commit()


async def _seed_published_provider(
    *,
    settings: Settings,
    provider_id: str,
    kind: str,
    configuration: dict[str, object],
    credentials: dict[str, str],
) -> None:
    now = datetime.now(UTC)
    credential_id = f"cred_{provider_id}"
    snapshot = {
        "providerName": provider_id,
        "kind": kind,
        "status": "READY",
        "configuration": configuration,
        "dataRegion": configuration.get("region"),
        "retentionStatement": "Test provider.",
        "retryLimit": 1,
        "priority": 100,
        "credentialVersionId": credential_id,
        "lastHealthStatus": "HEALTHY",
    }
    async with session_factory() as session:
        session.add(
            ProviderRecord(
                provider_id=provider_id,
                provider_name=provider_id,
                kind=kind,
                status="ACTIVE",
                configuration=configuration,
                data_region=str(configuration.get("region") or "GLOBAL"),
                retention_statement="Test provider.",
                retry_limit=1,
                priority=100,
                rollout_percentage=100,
                active_credential_version_id=credential_id,
                published_resource_version=1,
                published_rollout_percentage=100,
                published_effective_at=now,
                last_health_status="HEALTHY",
                effective_at=now,
                resource_version=2,
                created_at=now,
                updated_at=now,
            )
        )
        # ORM 模型没有声明 relationship，先刷新父记录以满足数据库外键顺序。
        await session.flush()
        session.add(
            ProviderCredentialVersionRecord(
                credential_version_id=credential_id,
                provider_id=provider_id,
                encrypted_payload=SecretCipher(settings).encrypt(
                    json.dumps(credentials, separators=(",", ":"))
                ),
                fingerprint="hmac-sha256:test",
                rotated_at=now,
                created_by_admin_id="seed",
            )
        )
        session.add(
            ProviderVersionRecord(
                provider_version_id=f"pv_{provider_id}",
                provider_id=provider_id,
                resource_version=1,
                snapshot=snapshot,
                was_published=True,
                action="PUBLISH",
                created_by_admin_id="seed",
                created_at=now,
            )
        )
        await session.commit()


@pytest.mark.asyncio
async def test_registry_uses_published_email_api_and_sms_credentials(
    delivery_settings: Settings,
) -> None:
    await _seed_published_provider(
        settings=delivery_settings,
        provider_id="prv_sendgrid_runtime",
        kind="EMAIL",
        configuration={
            "adapterType": "SENDGRID_API",
            "baseUrl": "https://sendgrid.example.test",
            "region": None,
            "senderAddress": "noreply@example.com",
            "senderName": "Love Reply",
            "timeoutMs": 10000,
        },
        credentials={"apiKey": "sendgrid-secret"},
    )
    await _seed_published_provider(
        settings=delivery_settings,
        provider_id="prv_aliyun_runtime",
        kind="SMS",
        configuration={
            "adapterType": "ALIYUN_SMS",
            "region": "cn-hangzhou",
            "applicationId": None,
            "signatureId": "心语助手",
            "templateId": "SMS_123456",
            "timeoutMs": 10000,
        },
        credentials={
            "accessKeyId": "aliyun-access-id",
            "accessKeySecret": "aliyun-secret",
        },
    )
    email_transport = CapturingEmailApiTransport()
    sms_transport = CapturingSmsApiTransport()
    async with session_factory() as session:
        email_sender = RegistryEmailSender(
            session=session,
            settings=delivery_settings,
            email_api_transport=email_transport,  # type: ignore[arg-type]
        )
        sms_sender = RegistrySmsSender(
            session=session,
            settings=delivery_settings,
            sms_api_transport=sms_transport,  # type: ignore[arg-type]
        )
        assert await email_sender.available() is True
        assert await sms_sender.available() is True
        await email_sender.send_login_code(
            email_normalized="user@example.com",
            code="123456",
            locale="zh-CN",
        )
        await sms_sender.send_login_code(phone_e164="+8613800000000", code="654321")

    assert len(email_transport.messages) == 1
    assert email_transport.messages[0]["credentials"] == {"apiKey": "sendgrid-secret"}
    assert email_transport.messages[0]["destination"] == "user@example.com"
    assert "123456" in str(email_transport.messages[0]["text_body"])
    assert len(sms_transport.messages) == 1
    assert sms_transport.messages[0]["credentials"] == {
        "accessKeyId": "aliyun-access-id",
        "accessKeySecret": "aliyun-secret",
    }
    assert sms_transport.messages[0]["phone_e164"] == "+8613800000000"
    assert sms_transport.messages[0]["code"] == "654321"
