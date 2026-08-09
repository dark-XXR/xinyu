import os
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from love_reply_api.application.auth import AuthService
from love_reply_api.application.generation import (
    GeneratedCandidate,
    GenerationService,
    ModelGeneration,
)
from love_reply_api.config import get_settings
from love_reply_api.domain.generation import GenerationStatus, ReplyStrategy, SafetyStatus
from love_reply_api.infrastructure.database import engine, session_factory
from love_reply_api.infrastructure.generation_records import (
    CandidateActionRecord,
    EntitlementRecord,
    GenerationEventRecord,
    GenerationQuoteRecord,
    GenerationTaskRecord,
    GenerationUsageRecord,
    ReplyCandidateRecord,
    RiskAppealRecord,
    WalletAccountRecord,
    WalletLedgerRecord,
)
from love_reply_api.infrastructure.identity_records import (
    AuthSessionRecord,
    ConsentRecord,
    DataRequestRecord,
    EmailChallengeRecord,
    IdempotencyRecord,
    SmsChallengeRecord,
    UserDeviceRecord,
    UserProfileRecord,
    UserRecord,
)
from love_reply_api.main import app
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_INTEGRATION_TESTS") != "1",
    reason="requires the isolated project PostgreSQL container",
)


class CapturingSmsSender:
    code: str | None = None

    async def send_login_code(self, *, phone_e164: str, code: str) -> None:
        del phone_e164
        self.code = code


class SuccessfulAiProvider:
    async def generate(
        self,
        *,
        input_data: dict[str, object],
        context_data: dict[str, object],
        model_id: str,
    ) -> ModelGeneration:
        del input_data, context_data, model_id
        return ModelGeneration(
            possible_intent="The other person may be checking availability.",
            emotion="Interested but uncertain.",
            uncertainty_note="This is an inference from limited context.",
            risk_tips=["Avoid claiming certainty about their intent."],
            candidates=[
                GeneratedCandidate(
                    strategy=ReplyStrategy.SAFE,
                    style_id="warm",
                    text="I am free. What did you have in mind?",
                    safety_status=SafetyStatus.PASSED,
                ),
                GeneratedCandidate(
                    strategy=ReplyStrategy.PUSH_PULL,
                    style_id="humorous",
                    text="Possibly. Is this the start of a good plan?",
                    safety_status=SafetyStatus.PASSED,
                ),
                GeneratedCandidate(
                    strategy=ReplyStrategy.DIRECT,
                    style_id="direct",
                    text="Yes, I am free this weekend. Want to meet?",
                    safety_status=SafetyStatus.PASSED,
                ),
            ],
            input_tokens=120,
            output_tokens=90,
        )


class FailingAiProvider:
    async def generate(
        self,
        *,
        input_data: dict[str, object],
        context_data: dict[str, object],
        model_id: str,
    ) -> ModelGeneration:
        del input_data, context_data, model_id
        raise RuntimeError("synthetic provider failure")


@pytest_asyncio.fixture(autouse=True)
async def clean_tables() -> AsyncIterator[None]:
    await _clean()
    yield
    await _clean()
    await engine.dispose()


async def _clean() -> None:
    async with session_factory() as session:
        for record in (
            IdempotencyRecord,
            RiskAppealRecord,
            CandidateActionRecord,
            GenerationEventRecord,
            ReplyCandidateRecord,
            GenerationUsageRecord,
            WalletLedgerRecord,
            GenerationTaskRecord,
            GenerationQuoteRecord,
            EntitlementRecord,
            WalletAccountRecord,
            ConsentRecord,
            DataRequestRecord,
            AuthSessionRecord,
            UserDeviceRecord,
        UserProfileRecord,
        UserRecord,
        EmailChallengeRecord,
        SmsChallengeRecord,
        ):
            await session.execute(delete(record))
        await session.commit()


async def _create_user(session: AsyncSession) -> str:
    sender = CapturingSmsSender()
    auth = AuthService(session=session, settings=get_settings(), sms_sender=sender)
    challenge = await auth.send_challenge(phone_e164="+15550000002", purpose="LOGIN")
    assert sender.code is not None
    login = await auth.login(
        challenge_id=challenge.challenge_id,
        code=sender.code,
        device_id="generation-integration-device",
        locale="zh-CN",
    )
    return login.user.user_id


def _input() -> dict[str, object]:
    return {"text": "Are you free this weekend?", "attachmentIds": []}


def _context() -> dict[str, object]:
    return {
        "relationshipStage": "DATING",
        "communicationGoal": "ACCEPT_INVITATION",
        "styleIds": ["warm", "humorous", "direct"],
    }


@pytest.mark.asyncio
async def test_generation_settles_success_and_releases_failure_and_cancel() -> None:
    async with session_factory() as session:
        user_id = await _create_user(session)
        service = GenerationService(session=session, settings=get_settings())

        quote = await service.quote(
            user_id=user_id,
            input_data=_input(),
            context_data=_context(),
            requested_model_id=None,
        )
        assert quote.record.charged_from == "SUBSCRIPTION"
        task = await service.create(
            user_id=user_id,
            quote_id=quote.record.quote_id,
            client_request_id="client-generation-success",
            input_data=_input(),
            context_data=_context(),
            model_id=quote.record.model_id,
            save_to_history=True,
        )
        entitlement, _ = await service.get_entitlement(user_id)
        assert entitlement.text_reserved == 1

        await service.process(generation_id=task.generation_id, provider=SuccessfulAiProvider())
        succeeded = await service.get_task(user_id=user_id, generation_id=task.generation_id)
        candidates = await service.get_candidates(task.generation_id)
        usage = await service.get_usage(task.generation_id)
        entitlement, _ = await service.get_entitlement(user_id)
        assert succeeded.status == GenerationStatus.SUCCEEDED.value
        assert {candidate.strategy for candidate in candidates} == {"SAFE", "PUSH_PULL", "DIRECT"}
        assert usage is not None
        assert entitlement.text_remaining == 2
        assert entitlement.text_reserved == 0

        action = await service.record_candidate_action(
            user_id=user_id,
            candidate_id=candidates[0].candidate_id,
            client_action_id="client-candidate-action",
            action_type="COPY",
            outcome_code=None,
            occurred_at=succeeded.updated_at,
        )
        replayed_action = await service.record_candidate_action(
            user_id=user_id,
            candidate_id=candidates[0].candidate_id,
            client_action_id="client-candidate-action",
            action_type="COPY",
            outcome_code=None,
            occurred_at=succeeded.updated_at,
        )
        assert replayed_action.action_id == action.action_id

        succeeded.risk_event_id = "risk_generation_integration"
        await session.commit()
        appeal = await service.appeal_risk_event(
            user_id=user_id,
            risk_event_id="risk_generation_integration",
            reason_code="CONTEXT_MISUNDERSTOOD",
            comment="Synthetic integration appeal.",
        )
        assert appeal.status == "SUBMITTED"

        failed_quote = await service.quote(
            user_id=user_id,
            input_data=_input(),
            context_data=_context(),
            requested_model_id=None,
        )
        failed_task = await service.create(
            user_id=user_id,
            quote_id=failed_quote.record.quote_id,
            client_request_id="client-generation-failure",
            input_data=_input(),
            context_data=_context(),
            model_id=failed_quote.record.model_id,
            save_to_history=True,
        )
        with pytest.raises(RuntimeError, match="synthetic provider failure"):
            await service.process(
                generation_id=failed_task.generation_id,
                provider=FailingAiProvider(),
            )
        failed = await service.get_task(user_id=user_id, generation_id=failed_task.generation_id)
        entitlement, _ = await service.get_entitlement(user_id)
        assert failed.status == GenerationStatus.FAILED.value
        assert entitlement.text_remaining == 2
        assert entitlement.text_reserved == 0

        cancel_quote = await service.quote(
            user_id=user_id,
            input_data=_input(),
            context_data=_context(),
            requested_model_id=None,
        )
        cancel_task = await service.create(
            user_id=user_id,
            quote_id=cancel_quote.record.quote_id,
            client_request_id="client-generation-cancel",
            input_data=_input(),
            context_data=_context(),
            model_id=cancel_quote.record.model_id,
            save_to_history=True,
        )
        cancelled = await service.cancel(user_id=user_id, generation_id=cancel_task.generation_id)
        entitlement, _ = await service.get_entitlement(user_id)
        assert cancelled.status == GenerationStatus.CANCELLED.value
        assert entitlement.text_remaining == 2
        assert entitlement.text_reserved == 0


@pytest.mark.asyncio
async def test_generation_http_flow_returns_quote_snapshot_and_sse() -> None:
    original_sms_sender = app.state.sms_sender
    original_ai_provider = app.state.ai_provider
    sender = CapturingSmsSender()
    app.state.sms_sender = sender
    app.state.ai_provider = SuccessfulAiProvider()
    headers = {
        "X-Client-Version": "0.1.0",
        "X-Platform": "ANDROID",
        "X-Device-Id": "http-generation-device",
        "Accept-Language": "zh-CN",
        "Idempotency-Key": "http-generation-1",
    }
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            send = await client.post(
                "/v1/auth/sms/send",
                headers=headers,
                json={
                    "countryCode": "+1",
                    "phoneNumber": "5550000003",
                    "purpose": "LOGIN",
                },
            )
            assert send.status_code == 200
            assert sender.code is not None
            login = await client.post(
                "/v1/auth/sms/login",
                headers={**headers, "Idempotency-Key": "http-generation-2"},
                json={
                    "challengeId": send.json()["data"]["challengeId"],
                    "code": sender.code,
                },
            )
            assert login.status_code == 200
            access_token = login.json()["data"]["tokens"]["accessToken"]
            auth_headers = {**headers, "Authorization": f"Bearer {access_token}"}
            quote = await client.post(
                "/v1/generations/quote",
                headers={**auth_headers, "Idempotency-Key": "http-generation-3"},
                json={
                    "input": _input(),
                    "context": _context(),
                    "saveToHistory": True,
                },
            )
            assert quote.status_code == 200
            quote_data = quote.json()["data"]
            create = await client.post(
                "/v1/generations",
                headers={**auth_headers, "Idempotency-Key": "http-generation-4"},
                json={
                    "clientRequestId": "http-generation-request",
                    "input": _input(),
                    "context": _context(),
                    "modelId": quote_data["selectedModelId"],
                    "saveToHistory": True,
                    "quoteId": quote_data["quoteId"],
                },
            )
            assert create.status_code == 202
            generation_id = create.json()["data"]["generationId"]
            snapshot = await client.get(
                f"/v1/generations/{generation_id}",
                headers=auth_headers,
            )
            assert snapshot.status_code == 200
            assert snapshot.json()["data"]["status"] == "SUCCEEDED"
            candidate_id = snapshot.json()["data"]["candidates"][0]["candidateId"]
            action = await client.post(
                f"/v1/candidates/{candidate_id}/actions",
                headers={**auth_headers, "Idempotency-Key": "http-generation-5"},
                json={
                    "clientActionId": "http-candidate-action",
                    "actionType": "COPY",
                    "occurredAt": snapshot.json()["data"]["updatedAt"],
                },
            )
            assert action.status_code == 200

            refine_quote = await client.post(
                "/v1/generations/quote",
                headers={**auth_headers, "Idempotency-Key": "http-generation-6"},
                json={
                    "input": _input(),
                    "context": _context(),
                    "saveToHistory": True,
                },
            )
            assert refine_quote.status_code == 200
            refine = await client.post(
                f"/v1/candidates/{candidate_id}/refine",
                headers={**auth_headers, "Idempotency-Key": "http-generation-7"},
                json={
                    "quoteId": refine_quote.json()["data"]["quoteId"],
                    "clientRequestId": "http-refine-request",
                    "instructionCode": "WARMER",
                },
            )
            assert refine.status_code == 202
            refined_id = refine.json()["data"]["generationId"]
            refined_snapshot = await client.get(
                f"/v1/generations/{refined_id}",
                headers=auth_headers,
            )
            assert refined_snapshot.json()["data"]["status"] == "SUCCEEDED"

            regenerate_quote = await client.post(
                "/v1/generations/quote",
                headers={**auth_headers, "Idempotency-Key": "http-generation-8"},
                json={
                    "input": _input(),
                    "context": _context(),
                    "saveToHistory": True,
                },
            )
            assert regenerate_quote.status_code == 200
            regenerate = await client.post(
                f"/v1/generations/{generation_id}/regenerate",
                headers={**auth_headers, "Idempotency-Key": "http-generation-9"},
                json={
                    "quoteId": regenerate_quote.json()["data"]["quoteId"],
                    "clientRequestId": "http-regenerate-request",
                },
            )
            assert regenerate.status_code == 202
            regenerated_id = regenerate.json()["data"]["generationId"]
            regenerated_snapshot = await client.get(
                f"/v1/generations/{regenerated_id}",
                headers=auth_headers,
            )
            assert regenerated_snapshot.json()["data"]["status"] == "SUCCEEDED"
            events = await client.get(
                f"/v1/generations/{generation_id}/events",
                headers=auth_headers,
            )
            assert events.status_code == 200
            assert "task.completed" in events.text
    finally:
        app.state.sms_sender = original_sms_sender
        app.state.ai_provider = original_ai_provider
