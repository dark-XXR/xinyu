import os
from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from love_reply_api.application.admin_auth import AdminAuthService
from love_reply_api.application.security import TotpService
from love_reply_api.config import Settings, get_settings
from love_reply_api.infrastructure.admin_records import (
    AdminMfaChallengeRecord,
    AdminSessionRecord,
    AdminUserRecord,
)
from love_reply_api.infrastructure.ai_gateway_records import (
    AiAuditRecord,
    AiEvaluationRunRecord,
    AiGatewayAttemptRecord,
    AiModelMappingRecord,
    AiPromptRecord,
    AiResourceVersionRecord,
    AiRiskPolicyRecord,
    AiRouteRecord,
)
from love_reply_api.infrastructure.database import engine, session_factory
from love_reply_api.infrastructure.identity_records import IdempotencyRecord
from love_reply_api.infrastructure.provider_records import (
    ProviderCredentialVersionRecord,
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

LOGIN = "ai-owner@example.com"
PASSWORD = "AI admin integration password"
TOTP_SECRET = "KRSXG5DSNFXGOIDB"


@pytest.fixture
def ai_settings() -> Settings:
    return Settings(
        _env_file=None,
        admin_jwt_signing_key=SecretStr("ai-admin-jwt-key-at-least-32-random-bytes"),
        data_encryption_key=SecretStr("ai-data-key-at-least-32-random-bytes"),
        admin_bootstrap_login_name=LOGIN,
        admin_bootstrap_password=SecretStr(PASSWORD),
        admin_bootstrap_totp_secret=SecretStr(TOTP_SECRET),
        admin_bootstrap_display_name="AI Test Owner",
    )


@pytest_asyncio.fixture(autouse=True)
async def clean_ai_tables() -> AsyncIterator[None]:
    async with session_factory() as session:
        await _delete_data(session)
    await engine.dispose()
    yield
    app.dependency_overrides.pop(get_settings, None)
    async with session_factory() as session:
        await _delete_data(session)
    await engine.dispose()


async def _delete_data(session: AsyncSession) -> None:
    for record in (
        IdempotencyRecord,
        AiAuditRecord,
        AiGatewayAttemptRecord,
        AiEvaluationRunRecord,
        AiResourceVersionRecord,
        AiRiskPolicyRecord,
        AiPromptRecord,
        AiRouteRecord,
        AiModelMappingRecord,
        ProviderVersionRecord,
        ProviderCredentialVersionRecord,
        ProviderRecord,
        AdminSessionRecord,
        AdminMfaChallengeRecord,
        AdminUserRecord,
    ):
        await session.execute(delete(record))
    await session.commit()


async def _access_token(settings: Settings) -> str:
    async with session_factory() as session:
        service = AdminAuthService(session=session, settings=settings)
        login = await service.login(login_name=LOGIN, password=PASSWORD)
        totp = TotpService()
        now = datetime.now(UTC)
        result = await service.verify_mfa(
            challenge_id=login.mfa_challenge.challenge_id,
            method="TOTP",
            code=totp.code(
                secret=TOTP_SECRET,
                counter=totp.counter(now=now, period_seconds=30),
                digits=6,
            ),
        )
        return result.tokens.access_token


def _headers(
    token: str,
    *,
    key: str | None = None,
    version: int | None = None,
) -> dict[str, str]:
    headers = {
        "X-Request-Id": "req-ai-admin",
        "X-Client-Version": "1.0.0",
        "X-Platform": "ADMIN_WEB",
        "Accept-Language": "zh-CN",
        "Authorization": f"Bearer {token}",
    }
    if key is not None:
        headers["Idempotency-Key"] = key
    if version is not None:
        headers["If-Match"] = str(version)
    return headers


async def _seed_published_ai_provider() -> str:
    now = datetime.now(UTC)
    provider_id = "prv_ai_admin_integration"
    snapshot = {
        "providerName": "AI primary",
        "kind": "AI",
        "status": "READY",
        "configuration": {
            "adapterType": "OPENAI_COMPAT",
            "baseUrl": "https://ai.example.com/v1",
            "timeoutMs": 10000,
        },
        "dataRegion": "US",
        "retentionStatement": "No training.",
        "retryLimit": 1,
        "priority": 100,
        "credentialVersionId": "cred_ai_admin_integration",
        "lastHealthStatus": "HEALTHY",
    }
    async with session_factory() as session:
        session.add(
            ProviderRecord(
                provider_id=provider_id,
                provider_name="AI primary",
                kind="AI",
                status="ACTIVE",
                configuration=snapshot["configuration"],
                data_region="US",
                retention_statement="No training.",
                retry_limit=1,
                priority=100,
                rollout_percentage=100,
                active_credential_version_id="cred_ai_admin_integration",
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
        session.add(
            ProviderVersionRecord(
                provider_version_id="pv_ai_admin_integration",
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
    return provider_id


@pytest.mark.asyncio
async def test_ai_admin_requires_evaluated_versions_and_preserves_published_snapshot(
    ai_settings: Settings,
) -> None:
    app.dependency_overrides[get_settings] = lambda: ai_settings
    token = await _access_token(ai_settings)
    provider_id = await _seed_published_ai_provider()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        mapping = await client.post(
            "/admin/v1/ai/model-mappings",
            headers=_headers(token, key="mapping-1"),
            json={
                "logicalModelId": "reply_primary",
                "providerId": provider_id,
                "providerModelName": "upstream-private-name",
                "inputModalities": ["TEXT"],
                "outputModalities": ["TEXT"],
                "contextWindowTokens": 4000,
                "maxOutputTokens": 1000,
                "inputCostMicrounitsPerMillionTokens": 1000000,
                "outputCostMicrounitsPerMillionTokens": 2000000,
                "currency": "USD",
                "qualityTier": "primary",
                "dataRegion": "US",
                "retentionPolicy": "No training.",
                "enabled": True,
            },
        )
        assert mapping.status_code == 201, mapping.text
        mapping_id = mapping.json()["data"]["modelMappingId"]

        risk = await client.post(
            "/admin/v1/ai/risk-policies",
            headers=_headers(token, key="risk-1"),
            json={
                "policyCode": "REPLY_SAFETY",
                "blockedCategories": ["SELF_HARM"],
                "reviewCategories": ["HARASSMENT"],
                "inputModerationEnabled": True,
                "outputModerationEnabled": True,
                "promptInjectionAction": "BLOCK",
                "minimumSafetyScore": 0.9,
                "allowAppeals": True,
            },
        )
        assert risk.status_code == 201, risk.text
        risk_id = risk.json()["data"]["riskPolicyId"]

        prompt = await client.post(
            "/admin/v1/ai/prompts",
            headers=_headers(token, key="prompt-1"),
            json={
                "promptCode": "REPLY_GENERATION_V1",
                "scenario": "REPLY_GENERATION",
                "systemTemplate": "System {contextJson}",
                "userTemplate": "Input {inputJson}",
                "allowedInputFields": ["message"],
                "outputSchema": {"type": "object"},
                "safetyPolicyId": risk_id,
            },
        )
        assert prompt.status_code == 201, prompt.text
        prompt_id = prompt.json()["data"]["promptId"]

        route = await client.post(
            "/admin/v1/ai/routes",
            headers=_headers(token, key="route-1"),
            json={
                "scenario": "REPLY_GENERATION",
                "logicalModelId": "reply_primary",
                "targets": [
                    {
                        "modelMappingId": mapping_id,
                        "priority": 100,
                        "timeoutMs": 10000,
                        "retryLimit": 1,
                    }
                ],
                "maxInputTokens": 1000,
                "maxOutputTokens": 500,
                "budgetCeilingMicrounits": 4000,
                "totalAttemptLimit": 2,
                "safetyPolicyId": risk_id,
            },
        )
        assert route.status_code == 201, route.text
        route_id = route.json()["data"]["routeId"]

        evaluation = await client.post(
            "/admin/v1/ai/evaluation-runs",
            headers=_headers(token, key="evaluation-1"),
            json={
                "promptId": prompt_id,
                "routeId": route_id,
                "suiteIds": ["reply-regression-v1"],
                "evaluatorLogicalModelId": "reply_primary",
                "maxCostMicrounits": 10000,
            },
        )
        assert evaluation.status_code == 202, evaluation.text
        evaluation_id = evaluation.json()["data"]["evaluationRunId"]
        premature = await client.post(
            f"/admin/v1/ai/routes/{route_id}/publish",
            headers=_headers(token, key="route-publish-premature", version=1),
            json={
                "rolloutPercentage": 100,
                "effectiveAt": datetime.now(UTC).isoformat(),
                "evaluationRunId": evaluation_id,
                "auditReason": "Publish evaluated production route.",
            },
        )
        assert premature.status_code == 409
        assert premature.json()["code"] == "AI_EVALUATION_GATE_FAILED"

        async with session_factory() as session:
            run = await session.get(AiEvaluationRunRecord, evaluation_id)
            assert run is not None
            run.status = "SUCCEEDED"
            run.passed = True
            run.safety_passed = True
            run.total_cases = 10
            run.completed_cases = 10
            run.score = 0.98
            run.cost_microunits = 5000
            run.updated_at = datetime.now(UTC)
            await session.commit()

        risk_published = await client.post(
            f"/admin/v1/ai/risk-policies/{risk_id}/publish",
            headers=_headers(token, key="risk-publish", version=1),
            json={
                "rolloutPercentage": 100,
                "effectiveAt": datetime.now(UTC).isoformat(),
                "evaluationRunId": evaluation_id,
                "auditReason": "Publish evaluated safety policy.",
            },
        )
        assert risk_published.status_code == 200, risk_published.text
        prompt_published = await client.post(
            f"/admin/v1/ai/prompts/{prompt_id}/publish",
            headers=_headers(token, key="prompt-publish", version=1),
            json={
                "rolloutPercentage": 100,
                "effectiveAt": datetime.now(UTC).isoformat(),
                "evaluationRunId": evaluation_id,
                "auditReason": "Publish evaluated generation prompt.",
            },
        )
        assert prompt_published.status_code == 200, prompt_published.text

        published = await client.post(
            f"/admin/v1/ai/routes/{route_id}/publish",
            headers=_headers(token, key="route-publish", version=1),
            json={
                "rolloutPercentage": 100,
                "effectiveAt": datetime.now(UTC).isoformat(),
                "evaluationRunId": evaluation_id,
                "auditReason": "Publish evaluated production route.",
            },
        )
        assert published.status_code == 200, published.text
        assert published.json()["data"]["status"] == "ACTIVE"
        published_resource_version = published.json()["data"]["resourceVersion"]

        updated = await client.patch(
            f"/admin/v1/ai/routes/{route_id}",
            headers=_headers(token, key="route-update", version=published_resource_version),
            json={
                "scenario": "REPLY_GENERATION",
                "logicalModelId": "reply_primary",
                "targets": [
                    {
                        "modelMappingId": mapping_id,
                        "priority": 100,
                        "timeoutMs": 15000,
                        "retryLimit": 0,
                    }
                ],
                "maxInputTokens": 800,
                "maxOutputTokens": 400,
                "budgetCeilingMicrounits": 2000,
                "totalAttemptLimit": 1,
                "safetyPolicyId": risk_id,
            },
        )
        assert updated.status_code == 200, updated.text
        assert updated.json()["data"]["status"] == "DRAFT"
        async with session_factory() as session:
            draft = await session.get(AiRouteRecord, route_id)
            assert draft is not None
            assert draft.max_input_tokens == 800
            assert draft.published_snapshot is not None
            assert draft.published_snapshot["maxInputTokens"] == 1000

        rolled_back = await client.post(
            f"/admin/v1/ai/routes/{route_id}/rollback",
            headers=_headers(
                token,
                key="route-rollback",
                version=updated.json()["data"]["resourceVersion"],
            ),
            json={
                "targetVersion": 1,
                "auditReason": "Restore the evaluated production route.",
            },
        )
        assert rolled_back.status_code == 200, rolled_back.text
        assert rolled_back.json()["data"]["version"] == 1
        assert rolled_back.json()["data"]["maxInputTokens"] == 1000

    async with session_factory() as session:
        saved = await session.get(AiRouteRecord, route_id)
        assert saved is not None
        assert saved.max_input_tokens == 1000
        assert saved.published_snapshot is not None
        assert saved.published_snapshot["maxInputTokens"] == 1000
        version = await session.scalar(
            select(AiResourceVersionRecord).where(
                AiResourceVersionRecord.resource_type == "ROUTE",
                AiResourceVersionRecord.resource_id == route_id,
                AiResourceVersionRecord.version == 1,
            )
        )
        assert version is not None and version.was_published
        assert "upstream-private-name" in str(version.snapshot)


def test_prompt_schema_rejects_executable_and_unknown_placeholders() -> None:
    from love_reply_api.transport.http.admin_ai_schemas import AiPromptWriteRequest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        AiPromptWriteRequest.model_validate(
            {
                "promptCode": "BAD_PROMPT",
                "scenario": "REPLY_GENERATION",
                "systemTemplate": "Run {unknown}",
                "userTemplate": "Input {inputJson}",
                "allowedInputFields": ["message"],
                "outputSchema": {"javascript": "alert(1)"},
            }
        )
