import os
from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from love_reply_api.application.auth import AuthService
from love_reply_api.application.errors import ApiError
from love_reply_api.application.generation import GenerationService
from love_reply_api.application.runtime_config import RuntimeConfigService
from love_reply_api.config import get_settings
from love_reply_api.infrastructure.database import engine, session_factory
from love_reply_api.infrastructure.generation_records import EntitlementRecord
from love_reply_api.infrastructure.identity_records import SmsChallengeRecord, UserRecord
from love_reply_api.infrastructure.runtime_config_records import RuntimeConfigVersionRecord
from sqlalchemy import delete, select, update

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_INTEGRATION_TESTS") != "1",
    reason="requires the isolated project PostgreSQL container",
)


@pytest_asyncio.fixture(autouse=True)
async def dispose_engine_after_test() -> AsyncIterator[None]:
    yield
    await engine.dispose()


class CapturingSmsSender:
    code: str | None = None

    async def send_login_code(self, *, phone_e164: str, code: str) -> None:
        del phone_e164
        self.code = code


@pytest.mark.asyncio
async def test_runtime_config_fails_closed_without_a_published_version() -> None:
    async with session_factory() as session:
        try:
            await session.execute(
                update(RuntimeConfigVersionRecord)
                .where(RuntimeConfigVersionRecord.status == "PUBLISHED")
                .values(status="SUPERSEDED")
            )
            await session.commit()

            with pytest.raises(ApiError) as raised:
                await RuntimeConfigService(session).get_published()
            assert raised.value.status_code == 503
            assert raised.value.code == "APP_CONFIG_UNAVAILABLE"
        finally:
            await session.execute(
                update(RuntimeConfigVersionRecord)
                .where(RuntimeConfigVersionRecord.config_id == "cfg_initial_published")
                .values(status="PUBLISHED")
            )
            await session.commit()


@pytest.mark.asyncio
async def test_published_config_controls_new_entitlement_and_generation_quote() -> None:
    now = datetime.now(UTC)
    override = RuntimeConfigVersionRecord(
        config_id="cfg_runtime_integration",
        version=999,
        status="PUBLISHED",
        models=[
            {
                "model_id": "model_runtime_test",
                "display_name": "Runtime Test",
                "description": None,
                "enabled": True,
            }
        ],
        styles=[
            {"style_id": "runtime_style", "display_name": "Runtime Style", "enabled": True}
        ],
        generation_policy={
            "default_model_id": "model_runtime_test",
            "quote_ttl_seconds": 90,
        },
        free_entitlement={
            "plan_code": "FREE_RUNTIME_TEST",
            "text_quota": 7,
            "vision_quota": 2,
            "allowed_model_ids": ["model_runtime_test"],
            "allowed_style_ids": ["runtime_style"],
        },
        auth_policy={
            "primary_channel": "EMAIL",
            "fallback_channels": ["SMS"],
            "policy_version": 1,
            "channels": {
                "EMAIL": {
                    "enabled": True,
                    "challenge_ttl_seconds": 600,
                    "resend_after_seconds": 60,
                    "max_attempts": 5,
                },
                "SMS": {
                    "enabled": True,
                    "challenge_ttl_seconds": 300,
                    "resend_after_seconds": 60,
                    "max_attempts": 5,
                },
            },
        },
        auth_templates={
            "email_login": {
                "default_locale": "en",
                "locales": {
                    "en": {
                        "subject": "Runtime login code",
                        "text_template": "Your code is {code}.",
                        "html_template": None,
                    }
                },
            }
        },
        feature_flags={"runtimeTest": True},
        published_at=now,
        created_at=now,
    )
    try:
        async with session_factory() as session:
            await session.execute(
                update(RuntimeConfigVersionRecord)
                .where(RuntimeConfigVersionRecord.status == "PUBLISHED")
                .values(status="SUPERSEDED")
            )
            session.add(override)
            await session.commit()

            sender = CapturingSmsSender()
            auth = AuthService(session=session, settings=get_settings(), sms_sender=sender)
            challenge = await auth.send_challenge(
                phone_e164="+15550000999", purpose="LOGIN"
            )
            assert sender.code is not None
            login = await auth.login(
                challenge_id=challenge.challenge_id,
                code=sender.code,
                device_id="runtime-config-test-device",
                locale="zh-CN",
            )
            entitlement = await session.get(EntitlementRecord, login.user.user_id)
            assert entitlement is not None
            assert entitlement.plan_code == "FREE_RUNTIME_TEST"
            assert entitlement.text_remaining == 7
            assert entitlement.vision_remaining == 2
            assert entitlement.allowed_model_ids == ["model_runtime_test"]
            assert entitlement.allowed_style_ids == ["runtime_style"]

            generation = GenerationService(session=session, settings=get_settings())
            quote = await generation.quote(
                user_id=login.user.user_id,
                input_data={"text": "Synthetic runtime configuration test."},
                context_data={"styleIds": ["runtime_style"]},
                requested_model_id=None,
            )
            assert quote.record.model_id == "model_runtime_test"
            ttl_seconds = (quote.record.expires_at - quote.record.created_at).total_seconds()
            assert ttl_seconds == 90
    finally:
        async with session_factory() as session:
            await session.execute(
                delete(RuntimeConfigVersionRecord).where(
                    RuntimeConfigVersionRecord.config_id == "cfg_runtime_integration"
                )
            )
            await session.execute(
                update(RuntimeConfigVersionRecord)
                .where(RuntimeConfigVersionRecord.config_id == "cfg_initial_published")
                .values(status="PUBLISHED")
            )
            user_id = await session.scalar(
                select(UserRecord.user_id).where(UserRecord.phone_e164 == "+15550000999")
            )
            if user_id is not None:
                await session.execute(delete(UserRecord).where(UserRecord.user_id == user_id))
            await session.execute(
                delete(SmsChallengeRecord).where(
                    SmsChallengeRecord.phone_e164 == "+15550000999"
                )
            )
            await session.commit()
        await engine.dispose()
