import os
import re
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from love_reply_api.application.admin_auth import AdminAuthService
from love_reply_api.application.provider_runtime import (
    ProviderAdapterHealthChecker,
    PublishedProviderResolver,
    SmtpTransport,
)
from love_reply_api.application.providers import (
    ProviderHealthResult,
    UnavailableProviderHealthChecker,
)
from love_reply_api.application.security import SecretCipher, TotpService
from love_reply_api.config import Settings, get_settings
from love_reply_api.infrastructure.admin_records import (
    AdminMfaChallengeRecord,
    AdminSessionRecord,
    AdminUserRecord,
)
from love_reply_api.infrastructure.database import engine, session_factory
from love_reply_api.infrastructure.identity_records import EmailChallengeRecord, IdempotencyRecord
from love_reply_api.infrastructure.provider_records import (
    ProviderAuditRecord,
    ProviderCredentialVersionRecord,
    ProviderHealthCheckRecord,
    ProviderRecord,
    ProviderVersionRecord,
)
from love_reply_api.main import app
from pydantic import SecretStr
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_INTEGRATION_TESTS") != "1",
    reason="requires the isolated project PostgreSQL container",
)

TEST_LOGIN = "provider-owner@example.com"
TEST_PASSWORD = "provider registry integration password"
TEST_TOTP_SECRET = "KRSXG5DSNFXGOIDB"


class HealthyProviderChecker:
    def __init__(self) -> None:
        self.credentials: dict[str, str] | None = None
        self.destination: str | None = None

    async def check(
        self,
        *,
        kind: str,
        configuration: dict[str, object],
        credentials: dict[str, str],
        administrator_test_destination: str | None,
    ) -> ProviderHealthResult:
        assert kind == "EMAIL"
        assert configuration["adapterType"] == "SMTP"
        self.credentials = credentials
        self.destination = administrator_test_destination
        return ProviderHealthResult(
            status="HEALTHY",
            redacted_summary=(
                f"Connected with {credentials['password']} for "
                f"{administrator_test_destination}."
            ),
            provider_request_id=f"request-{credentials['username']}",
        )


class CapturingSmtpTransport:
    def __init__(self) -> None:
        self.messages: list[dict[str, object]] = []

    async def send(
        self,
        *,
        configuration: dict[str, object],
        credentials: dict[str, str],
        destination: str,
        subject: str,
        text_body: str,
        html_body: str | None,
    ) -> None:
        self.messages.append(
            {
                "configuration": configuration,
                "credentials": credentials,
                "destination": destination,
                "subject": subject,
                "text_body": text_body,
                "html_body": html_body,
            }
        )


@pytest.fixture
def provider_settings() -> Settings:
    return Settings(
        _env_file=None,
        admin_jwt_signing_key=SecretStr("provider-admin-jwt-key-at-least-32-random-bytes"),
        data_encryption_key=SecretStr("provider-data-key-at-least-32-random-bytes"),
        admin_bootstrap_login_name=TEST_LOGIN,
        admin_bootstrap_password=SecretStr(TEST_PASSWORD),
        admin_bootstrap_totp_secret=SecretStr(TEST_TOTP_SECRET),
        admin_bootstrap_display_name="Provider Test Owner",
    )


@pytest_asyncio.fixture(autouse=True)
async def clean_provider_tables() -> AsyncIterator[None]:
    async with session_factory() as session:
        await _delete_provider_data(session)
    await engine.dispose()
    yield
    app.dependency_overrides.pop(get_settings, None)
    app.state.email_sender = None
    app.state.smtp_transport = SmtpTransport()
    app.state.provider_health_checker = ProviderAdapterHealthChecker()
    async with session_factory() as session:
        await _delete_provider_data(session)
    await engine.dispose()


async def _delete_provider_data(session: AsyncSession) -> None:
    for record in (
        IdempotencyRecord,
        EmailChallengeRecord,
        ProviderAuditRecord,
        ProviderHealthCheckRecord,
        ProviderVersionRecord,
        ProviderCredentialVersionRecord,
        ProviderRecord,
        AdminSessionRecord,
        AdminMfaChallengeRecord,
        AdminUserRecord,
    ):
        await session.execute(delete(record))
    await session.commit()


def _headers(
    *,
    access_token: str,
    idempotency_key: str | None = None,
    resource_version: int | None = None,
) -> dict[str, str]:
    headers = {
        "X-Request-Id": "req-provider-integration",
        "X-Client-Version": "1.0.0",
        "X-Platform": "ADMIN_WEB",
        "Accept-Language": "zh-CN",
        "Authorization": f"Bearer {access_token}",
    }
    if idempotency_key is not None:
        headers["Idempotency-Key"] = idempotency_key
    if resource_version is not None:
        headers["If-Match"] = str(resource_version)
    return headers


async def _admin_access_token(settings: Settings) -> str:
    async with session_factory() as session:
        service = AdminAuthService(session=session, settings=settings)
        login = await service.login(login_name=TEST_LOGIN, password=TEST_PASSWORD)
        totp = TotpService()
        now = datetime.now(UTC)
        code = totp.code(
            secret=TEST_TOTP_SECRET,
            counter=totp.counter(now=now, period_seconds=30),
            digits=6,
        )
        verified = await service.verify_mfa(
            challenge_id=login.mfa_challenge.challenge_id,
            method="TOTP",
            code=code,
        )
        return verified.tokens.access_token


def _smtp_request(port: int = 587, tls_mode: str = "STARTTLS") -> dict[str, object]:
    return {
        "providerName": "Transactional email primary",
        "kind": "EMAIL",
        "configuration": {
            "adapterType": "SMTP",
            "host": "smtp.example.com",
            "port": port,
            "tlsMode": tls_mode,
            "senderAddress": "noreply@example.com",
            "senderName": "Love Reply",
            "replyToAddress": None,
            "timeoutMs": 10000,
        },
        "dataRegion": "CN",
        "retentionStatement": "Delivery metadata retained for 30 days.",
        "retryLimit": 1,
        "priority": 100,
    }


@pytest.mark.asyncio
async def test_provider_registry_encrypts_versions_publishes_and_rolls_back(
    provider_settings: Settings,
) -> None:
    checker = HealthyProviderChecker()
    smtp_transport = CapturingSmtpTransport()
    app.state.provider_health_checker = checker
    app.state.email_sender = None
    app.state.smtp_transport = smtp_transport
    app.dependency_overrides[get_settings] = lambda: provider_settings
    access_token = await _admin_access_token(provider_settings)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create = await client.post(
            "/admin/v1/providers",
            headers=_headers(
                access_token=access_token,
                idempotency_key="idem-provider-create",
            ),
            json=_smtp_request(),
        )
        assert create.status_code == 201
        created = create.json()["data"]
        provider_id = created["providerId"]
        assert created["status"] == "DRAFT"
        assert created["resourceVersion"] == 1
        assert created["credentialConfigured"] is False

        premature_publish = await client.post(
            f"/admin/v1/providers/{provider_id}/publish",
            headers=_headers(
                access_token=access_token,
                idempotency_key="idem-provider-premature-publish",
                resource_version=1,
            ),
            json={
                "rolloutPercentage": 10,
                "effectiveAt": datetime.now(UTC).isoformat(),
                "auditReason": "Attempt publication before validation",
            },
        )
        assert premature_publish.status_code == 409
        assert premature_publish.json()["code"] == "PROVIDER_NOT_READY"

        invalid_configuration = _smtp_request()
        invalid_configuration["configuration"] = {
            **invalid_configuration["configuration"],  # type: ignore[dict-item]
            "unexpectedSecret": "must-not-be-accepted",
        }
        invalid = await client.post(
            "/admin/v1/providers",
            headers=_headers(
                access_token=access_token,
                idempotency_key="idem-provider-invalid",
            ),
            json=invalid_configuration,
        )
        assert invalid.status_code == 400

        conflict = await client.post(
            f"/admin/v1/providers/{provider_id}/credentials",
            headers=_headers(
                access_token=access_token,
                idempotency_key="idem-provider-credential-conflict",
                resource_version=99,
            ),
            json={
                "secrets": [
                    {"name": "username", "value": "smtp-user"},
                    {"name": "password", "value": "smtp-password-secret"},
                ],
                "auditReason": "Initial SMTP credential configuration",
            },
        )
        assert conflict.status_code == 409
        assert conflict.json()["code"] == "RESOURCE_VERSION_CONFLICT"

        invalid_credentials = await client.post(
            f"/admin/v1/providers/{provider_id}/credentials",
            headers=_headers(
                access_token=access_token,
                idempotency_key="idem-provider-invalid-credentials",
                resource_version=1,
            ),
            json={
                "secrets": [{"name": "apiKey", "value": "wrong-adapter-secret"}],
                "auditReason": "Reject credentials for the wrong adapter",
            },
        )
        assert invalid_credentials.status_code == 400
        assert invalid_credentials.json()["code"] == "CREDENTIAL_FIELDS_INVALID"

        rotate = await client.post(
            f"/admin/v1/providers/{provider_id}/credentials",
            headers=_headers(
                access_token=access_token,
                idempotency_key="idem-provider-credentials",
                resource_version=1,
            ),
            json={
                "secrets": [
                    {"name": "username", "value": "smtp-user"},
                    {"name": "password", "value": "smtp-password-secret"},
                ],
                "auditReason": "Initial SMTP credential configuration",
            },
        )
        assert rotate.status_code == 201
        assert rotate.json()["data"]["resourceVersion"] == 2
        assert "smtp-password-secret" not in rotate.text

        async with session_factory() as session:
            credential = await session.scalar(select(ProviderCredentialVersionRecord))
            assert credential is not None
            assert "smtp-user" not in credential.encrypted_payload
            assert "smtp-password-secret" not in credential.encrypted_payload
            decrypted = SecretCipher(provider_settings).decrypt(credential.encrypted_payload)
            assert "smtp-password-secret" in decrypted

        health = await client.post(
            f"/admin/v1/providers/{provider_id}/health-checks",
            headers=_headers(
                access_token=access_token,
                idempotency_key="idem-provider-health",
            ),
            json={
                "administratorTestDestination": "admin-test@example.com",
                "auditReason": "Validate provider before publication",
            },
        )
        assert health.status_code == 200
        assert health.json()["data"]["status"] == "HEALTHY"
        assert "smtp-password-secret" not in health.text
        assert "admin-test@example.com" not in health.text
        assert "[REDACTED]" in health.json()["data"]["redactedSummary"]
        assert checker.credentials == {
            "username": "smtp-user",
            "password": "smtp-password-secret",
        }
        assert checker.destination == "admin-test@example.com"

        publish = await client.post(
            f"/admin/v1/providers/{provider_id}/publish",
            headers=_headers(
                access_token=access_token,
                idempotency_key="idem-provider-publish",
                resource_version=3,
            ),
            json={
                "rolloutPercentage": 10,
                "effectiveAt": (datetime.now(UTC) - timedelta(seconds=1)).isoformat(),
                "auditReason": "Begin controlled production rollout",
            },
        )
        assert publish.status_code == 200
        published = publish.json()["data"]
        assert published["status"] == "ACTIVE"
        assert published["resourceVersion"] == 4
        assert published["rolloutPercentage"] == 10
        assert published["publishedResourceVersion"] == 3
        assert published["publishedRolloutPercentage"] == 10

        update_response = await client.patch(
            f"/admin/v1/providers/{provider_id}",
            headers=_headers(
                access_token=access_token,
                idempotency_key="idem-provider-update",
                resource_version=4,
            ),
            json=_smtp_request(port=465, tls_mode="IMPLICIT"),
        )
        assert update_response.status_code == 200
        updated = update_response.json()["data"]
        assert updated["status"] == "DRAFT"
        assert updated["configuration"]["port"] == 465
        assert updated["resourceVersion"] == 5

        async with session_factory() as session:
            resolver = PublishedProviderResolver(
                session=session,
                settings=provider_settings,
            )
            routing_key = next(
                f"rollout-user-{index}@example.com"
                for index in range(1000)
                if resolver.in_rollout(
                    provider_id=provider_id,
                    routing_key=f"rollout-user-{index}@example.com",
                    percentage=10,
                )
            )
            resolved = await resolver.resolve(
                kind="EMAIL",
                routing_key=routing_key,
                adapter_types={"SMTP"},
            )
            assert resolved is not None
            assert resolved.resource_version == 3
            assert resolved.configuration["port"] == 587

        disable = await client.post(
            f"/admin/v1/providers/{provider_id}/disable",
            headers=_headers(
                access_token=access_token,
                idempotency_key="idem-provider-disable",
                resource_version=5,
            ),
            json={"auditReason": "Emergency stop after elevated delivery failures"},
        )
        assert disable.status_code == 200
        disabled = disable.json()["data"]
        assert disabled["status"] == "DISABLED"
        assert disabled["resourceVersion"] == 6
        assert disabled["rolloutPercentage"] == 0
        assert disabled["publishedResourceVersion"] == 3
        assert disabled["publishedRolloutPercentage"] == 0

        async with session_factory() as session:
            resolver = PublishedProviderResolver(
                session=session,
                settings=provider_settings,
            )
            assert (
                await resolver.resolve(
                    kind="EMAIL",
                    routing_key=routing_key,
                    adapter_types={"SMTP"},
                )
                is None
            )

        duplicate_disable = await client.post(
            f"/admin/v1/providers/{provider_id}/disable",
            headers=_headers(
                access_token=access_token,
                idempotency_key="idem-provider-disable-again",
                resource_version=6,
            ),
            json={"auditReason": "Reject duplicate emergency disable request"},
        )
        assert duplicate_disable.status_code == 409
        assert duplicate_disable.json()["code"] == "PROVIDER_ALREADY_DISABLED"

        invalid_rollback = await client.post(
            f"/admin/v1/providers/{provider_id}/rollback",
            headers=_headers(
                access_token=access_token,
                idempotency_key="idem-provider-invalid-rollback",
                resource_version=6,
            ),
            json={
                "targetResourceVersion": 2,
                "auditReason": "Reject a version that was never published",
            },
        )
        assert invalid_rollback.status_code == 409
        assert invalid_rollback.json()["code"] == "ROLLBACK_TARGET_INVALID"

        async with session_factory() as session:
            provider = await session.get(ProviderRecord, provider_id)
            published_version = await session.scalar(
                select(ProviderVersionRecord).where(
                    ProviderVersionRecord.provider_id == provider_id,
                    ProviderVersionRecord.resource_version == 3,
                )
            )
            assert provider is not None
            assert provider.published_resource_version == 3
            assert published_version is not None
            assert published_version.was_published is True
            assert published_version.snapshot["configuration"]["port"] == 587

        rollback = await client.post(
            f"/admin/v1/providers/{provider_id}/rollback",
            headers=_headers(
                access_token=access_token,
                idempotency_key="idem-provider-rollback",
                resource_version=6,
            ),
            json={
                "targetResourceVersion": 3,
                "auditReason": "Rollback after elevated delivery failures",
            },
        )
        assert rollback.status_code == 200
        rolled_back = rollback.json()["data"]
        assert rolled_back["status"] == "ACTIVE"
        assert rolled_back["configuration"]["port"] == 587
        assert rolled_back["rolloutPercentage"] == 100
        assert rolled_back["resourceVersion"] == 7
        assert rolled_back["publishedResourceVersion"] == 3
        assert rolled_back["publishedRolloutPercentage"] == 100

        user_headers = {
            "X-Request-Id": "req-registry-email-auth",
            "X-Client-Version": "1.0.0",
            "X-Platform": "ANDROID",
            "X-Device-Id": "device-registry-email-auth",
            "Accept-Language": "zh-CN",
        }
        channels = await client.get("/v1/auth/channels", headers=user_headers)
        assert channels.status_code == 200
        email_channel = next(
            item
            for item in channels.json()["data"]["channels"]
            if item["channel"] == "EMAIL"
        )
        assert email_channel["available"] is True

        sent_email = await client.post(
            "/v1/auth/email/send",
            headers={
                **user_headers,
                "Idempotency-Key": "idem-registry-email-auth",
            },
            json={"email": "published-user@example.com", "purpose": "LOGIN"},
        )
        assert sent_email.status_code == 200
        assert len(smtp_transport.messages) == 1
        captured_message = smtp_transport.messages[0]
        assert captured_message["destination"] == "published-user@example.com"
        assert captured_message["configuration"]["port"] == 587  # type: ignore[index]
        assert captured_message["credentials"] == {
            "username": "smtp-user",
            "password": "smtp-password-secret",
        }
        challenge_id = sent_email.json()["data"]["challengeId"]
        async with session_factory() as session:
            challenge = await session.get(EmailChallengeRecord, challenge_id)
            assert challenge is not None
            code_match = re.search(r"\b[0-9]{6}\b", str(captured_message["text_body"]))
            assert code_match is not None
            assert challenge.code_hash != code_match.group(0)
            assert code_match.group(0) not in challenge.code_hash

        app.state.provider_health_checker = UnavailableProviderHealthChecker()
        failed_health = await client.post(
            f"/admin/v1/providers/{provider_id}/health-checks",
            headers=_headers(
                access_token=access_token,
                idempotency_key="idem-provider-failed-health",
            ),
            json={
                "administratorTestDestination": "admin-test@example.com",
                "auditReason": "Record unavailable provider health result",
            },
        )
        assert failed_health.status_code == 503
        assert failed_health.json()["code"] == "PROVIDER_UNAVAILABLE"

        listed = await client.get(
            "/admin/v1/providers",
            headers=_headers(access_token=access_token),
        )
        assert listed.status_code == 200
        assert len(listed.json()["data"]["items"]) == 1
        assert "encryptedPayload" not in listed.text

        async with session_factory() as session:
            audits = list((await session.scalars(select(ProviderAuditRecord))).all())
            health_checks = list(
                (await session.scalars(select(ProviderHealthCheckRecord))).all()
            )
            assert len(health_checks) == 2
            assert {item.status for item in health_checks} == {"HEALTHY", "UNHEALTHY"}
            serialized_audits = " ".join(
                f"{item.audit_reason} {item.metadata_json}" for item in audits
            )
            assert "smtp-password-secret" not in serialized_audits
            assert "admin-test@example.com" not in serialized_audits
            assert any(item.action == "PROVIDER_DISABLED" for item in audits)

            admin = await session.scalar(select(AdminUserRecord))
            assert admin is not None
            admin.permissions = [
                permission
                for permission in admin.permissions
                if permission not in {"PROVIDER_WRITE", "PROVIDER_DISABLE"}
            ]
            await session.commit()

        denied = await client.post(
            "/admin/v1/providers",
            headers=_headers(
                access_token=access_token,
                idempotency_key="idem-provider-permission-denied",
            ),
            json=_smtp_request(),
        )
        assert denied.status_code == 403
        assert denied.json()["code"] == "PERMISSION_DENIED"

        disable_denied = await client.post(
            f"/admin/v1/providers/{provider_id}/disable",
            headers=_headers(
                access_token=access_token,
                idempotency_key="idem-provider-disable-permission-denied",
                resource_version=8,
            ),
            json={"auditReason": "Permission denial must happen before state checks"},
        )
        assert disable_denied.status_code == 403
        assert disable_denied.json()["code"] == "PERMISSION_DENIED"
