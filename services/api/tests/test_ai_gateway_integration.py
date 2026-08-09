import json
import os
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
import pytest_asyncio
from love_reply_api.application.ai_gateway import AiTransportResult, RegistryAiProvider
from love_reply_api.application.errors import ApiError
from love_reply_api.application.provider_runtime import ResolvedProvider
from love_reply_api.application.security import SecretCipher
from love_reply_api.config import get_settings
from love_reply_api.infrastructure.ai_gateway_records import (
    AiGatewayAttemptRecord,
    AiModelMappingRecord,
    AiPromptRecord,
    AiRouteRecord,
)
from love_reply_api.infrastructure.database import engine, session_factory
from love_reply_api.infrastructure.provider_records import (
    ProviderCredentialVersionRecord,
    ProviderRecord,
    ProviderVersionRecord,
)
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_INTEGRATION_TESTS") != "1",
    reason="requires the isolated project PostgreSQL container",
)


class FallbackTransport:
    def __init__(self, *, fail_all: bool = False, output_tokens: int = 90) -> None:
        self.fail_all = fail_all
        self.output_tokens = output_tokens
        self.calls: list[str] = []

    async def generate(
        self,
        *,
        provider: ResolvedProvider,
        provider_model_name: str,
        system_prompt: str,
        user_prompt: str,
        max_output_tokens: int,
        timeout_ms: int,
    ) -> AiTransportResult:
        del provider_model_name, system_prompt, user_prompt, max_output_tokens, timeout_ms
        self.calls.append(provider.provider_id)
        if self.fail_all or provider.provider_id == "prv_ai_primary":
            raise ApiError(
                status_code=503,
                code="AI_PROVIDER_UPSTREAM_ERROR",
                message="Synthetic retryable upstream failure.",
                retryable=True,
            )
        return AiTransportResult(
            text=json.dumps(
                {
                    "possibleIntent": "The other person may be checking availability.",
                    "emotion": "Interested but uncertain.",
                    "uncertaintyNote": "This is an inference from limited context.",
                    "riskTips": ["Avoid claiming certainty."],
                    "candidates": [
                        {
                            "strategy": "SAFE",
                            "styleId": "warm",
                            "text": "I am free. What did you have in mind?",
                            "safetyStatus": "PASSED",
                        },
                        {
                            "strategy": "PUSH_PULL",
                            "styleId": "humorous",
                            "text": "Possibly. Is this the start of a good plan?",
                            "safetyStatus": "PASSED",
                        },
                        {
                            "strategy": "DIRECT",
                            "styleId": "direct",
                            "text": "Yes, I am free this weekend. Want to meet?",
                            "safetyStatus": "PASSED",
                        },
                    ],
                }
            ),
            input_tokens=120,
            output_tokens=self.output_tokens,
        )


@pytest_asyncio.fixture(autouse=True)
async def clean_ai_gateway_tables() -> AsyncIterator[None]:
    await _clean()
    yield
    await _clean()
    await engine.dispose()


async def _clean() -> None:
    async with session_factory() as session:
        for record in (
            AiGatewayAttemptRecord,
            AiPromptRecord,
            AiRouteRecord,
            AiModelMappingRecord,
            ProviderVersionRecord,
            ProviderCredentialVersionRecord,
            ProviderRecord,
        ):
            await session.execute(delete(record))
        await session.commit()


async def _seed_gateway(
    session: AsyncSession,
    *,
    route_budget: int = 100000,
    primary_provider_retry_limit: int = 0,
    primary_target_retry_limit: int = 0,
    total_attempt_limit: int = 3,
    include_fallback: bool = True,
) -> None:
    now = datetime.now(UTC)
    settings = get_settings()
    cipher = SecretCipher(settings)
    providers = [
        ("prv_ai_primary", "OPENAI", primary_provider_retry_limit, 200),
        ("prv_ai_fallback", "ANTHROPIC", 0, 100),
    ]
    targets: list[dict[str, Any]] = []
    for index, (provider_id, adapter, retry_limit, priority) in enumerate(providers):
        credential_id = f"pcred_{provider_id}"
        session.add(
            ProviderRecord(
                provider_id=provider_id,
                provider_name=provider_id,
                kind="AI",
                status="ACTIVE",
                configuration={"adapterType": adapter, "timeoutMs": 10000},
                data_region="US",
                retention_statement="Synthetic integration provider.",
                retry_limit=retry_limit,
                priority=priority,
                rollout_percentage=100,
                active_credential_version_id=credential_id,
                published_resource_version=1,
                published_rollout_percentage=100,
                published_effective_at=now - timedelta(seconds=1),
                last_health_status="HEALTHY",
                effective_at=now - timedelta(seconds=1),
                resource_version=2,
                created_at=now,
                updated_at=now,
            )
        )
        await session.flush()
        session.add(
            ProviderCredentialVersionRecord(
                credential_version_id=credential_id,
                provider_id=provider_id,
                encrypted_payload=cipher.encrypt(json.dumps({"apiKey": f"secret-{index}"})),
                fingerprint=f"fingerprint-{index}",
                rotated_at=now,
                created_by_admin_id="adm_ai_test",
            )
        )
        session.add(
            ProviderVersionRecord(
                provider_version_id=f"pv_{provider_id}_1",
                provider_id=provider_id,
                resource_version=1,
                snapshot={
                    "configuration": {"adapterType": adapter, "timeoutMs": 10000},
                    "credentialVersionId": credential_id,
                    "retryLimit": retry_limit,
                    "priority": priority,
                },
                was_published=True,
                action="PUBLISH",
                created_by_admin_id="adm_ai_test",
                created_at=now,
            )
        )
        await session.flush()
        mapping_id = f"aimap_{index}"
        session.add(
            AiModelMappingRecord(
                model_mapping_id=mapping_id,
                logical_model_id="model_quality",
                provider_id=provider_id,
                provider_model_name=f"provider-model-{index}",
                input_modalities=["TEXT"],
                output_modalities=["TEXT"],
                context_window_tokens=128000,
                max_output_tokens=1600,
                input_cost_microunits_per_million_tokens=2000000,
                output_cost_microunits_per_million_tokens=8000000,
                currency="USD",
                quality_tier="QUALITY",
                data_region="US",
                retention_policy="Synthetic integration mapping.",
                status="ACTIVE",
                enabled=True,
                resource_version=1,
                effective_at=now - timedelta(seconds=1),
                created_at=now,
                updated_at=now,
            )
        )
        if index == 0 or include_fallback:
            targets.append(
                {
                    "modelMappingId": mapping_id,
                    "priority": priority,
                    "timeoutMs": 10000,
                    "retryLimit": primary_target_retry_limit if index == 0 else 0,
                }
            )
    session.add(
        AiRouteRecord(
            route_id="airoute_reply_quality",
            version=1,
            scenario="REPLY_GENERATION",
            logical_model_id="model_quality",
            targets=targets,
            max_input_tokens=12000,
            max_output_tokens=1600,
            budget_ceiling_microunits=route_budget,
            total_attempt_limit=total_attempt_limit,
            safety_policy_id="airisk_reply_default",
            status="ACTIVE",
            rollout_percentage=100,
            effective_at=now - timedelta(seconds=1),
            resource_version=1,
            created_at=now,
            updated_at=now,
        )
    )
    session.add(
        AiPromptRecord(
            prompt_id="aiprompt_reply_default",
            version=1,
            prompt_code="REPLY_DEFAULT",
            scenario="REPLY_GENERATION",
            system_template="Return strict JSON for three reply strategies.",
            user_template="Input: {inputJson}\nContext: {contextJson}",
            allowed_input_fields=["inputJson", "contextJson"],
            output_schema={"type": "object"},
            safety_policy_id="airisk_reply_default",
            status="ACTIVE",
            effective_at=now - timedelta(seconds=1),
            resource_version=1,
            created_at=now,
            updated_at=now,
        )
    )
    await session.commit()


def _input() -> dict[str, Any]:
    return {"text": "Are you free this weekend?", "attachmentIds": []}


def _context() -> dict[str, Any]:
    return {
        "relationshipStage": "DATING",
        "communicationGoal": "ACCEPT_INVITATION",
        "styleIds": ["warm", "humorous", "direct"],
    }


@pytest.mark.asyncio
async def test_registry_ai_provider_fails_over_and_records_redacted_attempts() -> None:
    async with session_factory() as session:
        await _seed_gateway(session)
        transport = FallbackTransport()
        provider = RegistryAiProvider(
            session=session,
            settings=get_settings(),
            transport=transport,  # type: ignore[arg-type]
        )

        generated = await provider.generate(
            input_data=_input(),
            context_data=_context(),
            model_id="model_quality",
        )

        assert transport.calls == ["prv_ai_primary", "prv_ai_fallback"]
        assert generated.input_tokens == 120
        assert {item.strategy.value for item in generated.candidates} == {
            "SAFE",
            "PUSH_PULL",
            "DIRECT",
        }
        attempts = list(
            await session.scalars(
                select(AiGatewayAttemptRecord).order_by(AiGatewayAttemptRecord.attempt_number)
            )
        )
        assert [item.status for item in attempts] == ["FAILED", "SUCCEEDED"]
        assert [item.provider_id for item in attempts] == transport.calls


@pytest.mark.asyncio
async def test_registry_ai_provider_enforces_route_budget_before_call() -> None:
    async with session_factory() as session:
        await _seed_gateway(session, route_budget=1)
        transport = FallbackTransport()
        provider = RegistryAiProvider(
            session=session,
            settings=get_settings(),
            transport=transport,  # type: ignore[arg-type]
        )

        with pytest.raises(ApiError) as captured:
            await provider.generate(
                input_data=_input(),
                context_data=_context(),
                model_id="model_quality",
            )

        assert captured.value.code == "AI_ROUTE_BUDGET_EXCEEDED"
        assert captured.value.retryable is False
        assert transport.calls == []


@pytest.mark.asyncio
async def test_registry_ai_provider_bounds_retries_by_provider_and_route() -> None:
    async with session_factory() as session:
        await _seed_gateway(
            session,
            primary_provider_retry_limit=1,
            primary_target_retry_limit=3,
            total_attempt_limit=5,
            include_fallback=False,
        )
        transport = FallbackTransport(fail_all=True)
        provider = RegistryAiProvider(
            session=session,
            settings=get_settings(),
            transport=transport,  # type: ignore[arg-type]
        )

        with pytest.raises(ApiError) as captured:
            await provider.generate(
                input_data=_input(),
                context_data=_context(),
                model_id="model_quality",
            )

        assert captured.value.code == "AI_PROVIDER_UNAVAILABLE"
        assert transport.calls == ["prv_ai_primary", "prv_ai_primary"]


@pytest.mark.asyncio
async def test_registry_ai_provider_rejects_usage_above_published_token_limit() -> None:
    async with session_factory() as session:
        await _seed_gateway(session)
        transport = FallbackTransport(output_tokens=1601)
        provider = RegistryAiProvider(
            session=session,
            settings=get_settings(),
            transport=transport,  # type: ignore[arg-type]
        )

        with pytest.raises(ApiError) as captured:
            await provider.generate(
                input_data=_input(),
                context_data=_context(),
                model_id="model_quality",
            )

        assert captured.value.code == "AI_PROVIDER_TOKEN_LIMIT_EXCEEDED"
        assert captured.value.retryable is False


@pytest.mark.asyncio
async def test_registry_ai_provider_skips_target_with_missing_published_credentials() -> None:
    async with session_factory() as session:
        await _seed_gateway(session)
        primary_credential = await session.get(
            ProviderCredentialVersionRecord, "pcred_prv_ai_primary"
        )
        assert primary_credential is not None
        await session.delete(primary_credential)
        await session.commit()
        transport = FallbackTransport()
        provider = RegistryAiProvider(
            session=session,
            settings=get_settings(),
            transport=transport,  # type: ignore[arg-type]
        )

        generated = await provider.generate(
            input_data=_input(),
            context_data=_context(),
            model_id="model_quality",
        )

        assert generated.output_tokens == 90
        assert transport.calls == ["prv_ai_fallback"]
