import os
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from love_reply_api.application.auth import UnavailableEmailSender
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
from love_reply_api.infrastructure.runtime_config_records import RuntimeConfigVersionRecord
from love_reply_api.main import app
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_INTEGRATION_TESTS") != "1",
    reason="requires the isolated project PostgreSQL container",
)


class CapturingSmsSender:
    def __init__(self) -> None:
        self.code: str | None = None

    async def send_login_code(self, *, phone_e164: str, code: str) -> None:
        assert phone_e164 == "+15550000000"
        self.code = code


class CapturingEmailSender:
    def __init__(self) -> None:
        self.code: str | None = None
        self.destination: str | None = None

    async def send_login_code(self, *, email_normalized: str, code: str) -> None:
        self.destination = email_normalized
        self.code = code


@pytest_asyncio.fixture(autouse=True)
async def clean_identity_tables() -> AsyncIterator[None]:
    async with session_factory() as session:
        await _delete_identity_data(session)
    await engine.dispose()
    app.state.email_sender = UnavailableEmailSender()
    yield
    async with session_factory() as session:
        await _delete_identity_data(session)
    await engine.dispose()


async def _delete_identity_data(session: AsyncSession) -> None:
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


@pytest.mark.asyncio
async def test_app_bootstrap_returns_published_runtime_configuration() -> None:
    headers = {
        "X-Request-Id": "req-bootstrap-integration",
        "X-Client-Version": "1.0.0",
        "X-Platform": "ANDROID",
        "X-Device-Id": "device-bootstrap-test",
        "Accept-Language": "zh-CN",
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/v1/app/bootstrap", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["configVersion"] >= 1
    assert data["generationPolicy"]["defaultModelId"] in {
        item["modelId"] for item in data["models"] if item["enabled"]
    }
    assert set(data["freeEntitlement"]["allowedStyleIds"]) <= {
        item["styleId"] for item in data["styles"] if item["enabled"]
    }


@pytest.mark.asyncio
async def test_email_is_primary_and_login_uses_hashed_challenge() -> None:
    email_sender = CapturingEmailSender()
    sms_sender = CapturingSmsSender()
    app.state.email_sender = email_sender
    app.state.sms_sender = sms_sender
    common_headers = {
        "X-Request-Id": "req-email-auth-integration",
        "X-Client-Version": "1.0.0",
        "X-Platform": "ANDROID",
        "X-Device-Id": "device-email-integration-test",
        "Accept-Language": "zh-CN",
    }
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        channels = await client.get("/v1/auth/channels", headers=common_headers)
        assert channels.status_code == 200
        policy = channels.json()["data"]
        assert policy["primaryChannel"] == "EMAIL"
        assert policy["fallbackChannels"] == ["SMS"]
        assert {item["channel"]: item["available"] for item in policy["channels"]} == {
            "EMAIL": True,
            "SMS": True,
        }

        send_response = await client.post(
            "/v1/auth/email/send",
            headers={**common_headers, "Idempotency-Key": "idem-send-email-auth"},
            json={"email": " Fixture.User@Example.com ", "purpose": "LOGIN"},
        )
        assert send_response.status_code == 200
        assert email_sender.destination == "fixture.user@example.com"
        assert email_sender.code is not None
        assert send_response.json()["data"]["maskedDestination"] == "f***@example.com"

        rate_limited = await client.post(
            "/v1/auth/email/send",
            headers={**common_headers, "Idempotency-Key": "idem-resend-email-auth"},
            json={"email": "fixture.user@example.com", "purpose": "LOGIN"},
        )
        assert rate_limited.status_code == 429
        assert rate_limited.json()["code"] == "RATE_LIMITED"
        assert 1 <= rate_limited.json()["error"]["retryAfterSeconds"] <= 60

        challenge_id = send_response.json()["data"]["challengeId"]
        async with session_factory() as session:
            challenge = await session.get(EmailChallengeRecord, challenge_id)
            assert challenge is not None
            assert challenge.code_hash != email_sender.code
            assert email_sender.code not in challenge.code_hash

        login_response = await client.post(
            "/v1/auth/email/login",
            headers={**common_headers, "Idempotency-Key": "idem-login-email-auth"},
            json={"challengeId": challenge_id, "code": email_sender.code},
        )
        assert login_response.status_code == 200
        tokens = login_response.json()["data"]["tokens"]
        user_id = login_response.json()["data"]["user"]["userId"]

        async with session_factory() as session:
            user = await session.get(UserRecord, user_id)
            assert user is not None
            assert user.phone_e164 is None
            assert user.email_normalized == "fixture.user@example.com"
            entitlement = await session.get(EntitlementRecord, user_id)
            assert entitlement is not None
            assert entitlement.plan_code == "FREE"

        refresh = await client.post(
            "/v1/auth/refresh",
            headers={**common_headers, "Idempotency-Key": "idem-refresh-email-auth"},
            json={"refreshToken": tokens["refreshToken"]},
        )
        assert refresh.status_code == 200
        assert refresh.json()["data"]["refreshToken"] != tokens["refreshToken"]

        logout = await client.post(
            "/v1/auth/logout",
            headers={
                **common_headers,
                "Authorization": f"Bearer {refresh.json()['data']['accessToken']}",
                "Idempotency-Key": "idem-logout-email-auth",
            },
        )
        assert logout.status_code == 200

        existing_account_send = await client.post(
            "/v1/auth/email/send",
            headers={**common_headers, "Idempotency-Key": "idem-send-existing-email-auth"},
            json={"email": "fixture.user@example.com", "purpose": "LOGIN"},
        )
        assert existing_account_send.status_code == send_response.status_code
        assert set(existing_account_send.json()["data"]) == set(send_response.json()["data"])
        assert (
            existing_account_send.json()["data"]["maskedDestination"]
            == send_response.json()["data"]["maskedDestination"]
        )


@pytest.mark.asyncio
async def test_email_channel_fails_closed_for_disabled_policy_and_missing_provider() -> None:
    common_headers = {
        "X-Request-Id": "req-email-policy-integration",
        "X-Client-Version": "1.0.0",
        "X-Platform": "ANDROID",
        "X-Device-Id": "device-email-policy-test",
        "Accept-Language": "zh-CN",
        "Idempotency-Key": "idem-email-policy-test",
    }
    app.state.email_sender = UnavailableEmailSender()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        unavailable = await client.post(
            "/v1/auth/email/send",
            headers=common_headers,
            json={"email": "unavailable@example.com", "purpose": "LOGIN"},
        )
        assert unavailable.status_code == 503
        assert unavailable.json()["code"] == "EMAIL_PROVIDER_UNAVAILABLE"

    async with session_factory() as session:
        published = await session.scalar(
            select(RuntimeConfigVersionRecord).where(
                RuntimeConfigVersionRecord.status == "PUBLISHED"
            )
        )
        assert published is not None
        original_policy = published.auth_policy
        disabled_policy = {
            **original_policy,
            "channels": {
                **original_policy["channels"],
                "EMAIL": {**original_policy["channels"]["EMAIL"], "enabled": False},
                "SMS": {**original_policy["channels"]["SMS"], "enabled": False},
            },
        }
        await session.execute(
            update(RuntimeConfigVersionRecord)
            .where(RuntimeConfigVersionRecord.config_id == published.config_id)
            .values(auth_policy=disabled_policy)
        )
        await session.commit()

    try:
        app.state.email_sender = CapturingEmailSender()
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            disabled = await client.post(
                "/v1/auth/email/send",
                headers={**common_headers, "Idempotency-Key": "idem-email-disabled"},
                json={"email": "disabled@example.com", "purpose": "LOGIN"},
            )
            assert disabled.status_code == 503
            assert disabled.json()["code"] == "AUTH_CHANNEL_DISABLED"

            disabled_sms = await client.post(
                "/v1/auth/sms/send",
                headers={**common_headers, "Idempotency-Key": "idem-sms-disabled"},
                json={
                    "phoneNumber": "5550000000",
                    "countryCode": "+1",
                    "purpose": "LOGIN",
                },
            )
            assert disabled_sms.status_code == 503
            assert disabled_sms.json()["code"] == "AUTH_CHANNEL_DISABLED"
    finally:
        async with session_factory() as session:
            await session.execute(
                update(RuntimeConfigVersionRecord)
                .where(RuntimeConfigVersionRecord.config_id == published.config_id)
                .values(auth_policy=original_policy)
            )
            await session.commit()


@pytest.mark.asyncio
async def test_email_attempt_limit_comes_from_published_policy() -> None:
    email_sender = CapturingEmailSender()
    app.state.email_sender = email_sender
    common_headers = {
        "X-Request-Id": "req-email-attempt-policy",
        "X-Client-Version": "1.0.0",
        "X-Platform": "ANDROID",
        "X-Device-Id": "device-email-attempt-test",
        "Accept-Language": "zh-CN",
    }
    async with session_factory() as session:
        published = await session.scalar(
            select(RuntimeConfigVersionRecord).where(
                RuntimeConfigVersionRecord.status == "PUBLISHED"
            )
        )
        assert published is not None
        original_policy = published.auth_policy
        one_attempt_policy = {
            **original_policy,
            "channels": {
                **original_policy["channels"],
                "EMAIL": {
                    **original_policy["channels"]["EMAIL"],
                    "max_attempts": 1,
                },
            },
        }
        await session.execute(
            update(RuntimeConfigVersionRecord)
            .where(RuntimeConfigVersionRecord.config_id == published.config_id)
            .values(auth_policy=one_attempt_policy)
        )
        await session.commit()

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            sent = await client.post(
                "/v1/auth/email/send",
                headers={**common_headers, "Idempotency-Key": "idem-email-attempt-send"},
                json={"email": "attempt-limit@example.com", "purpose": "LOGIN"},
            )
            assert sent.status_code == 200
            challenge_id = sent.json()["data"]["challengeId"]

            invalid = await client.post(
                "/v1/auth/email/login",
                headers={**common_headers, "Idempotency-Key": "idem-email-attempt-one"},
                json={"challengeId": challenge_id, "code": "999999"},
            )
            assert invalid.status_code == 401
            assert invalid.json()["code"] == "INVALID_EMAIL_CODE"

            locked = await client.post(
                "/v1/auth/email/login",
                headers={**common_headers, "Idempotency-Key": "idem-email-attempt-two"},
                json={"challengeId": challenge_id, "code": email_sender.code},
            )
            assert locked.status_code == 429
            assert locked.json()["code"] == "EMAIL_CHALLENGE_LOCKED"
    finally:
        async with session_factory() as session:
            await session.execute(
                update(RuntimeConfigVersionRecord)
                .where(RuntimeConfigVersionRecord.config_id == published.config_id)
                .values(auth_policy=original_policy)
            )
            await session.commit()


@pytest.mark.asyncio
async def test_sms_login_refresh_rotation_and_logout() -> None:
    sms_sender = CapturingSmsSender()
    app.state.sms_sender = sms_sender
    common_headers = {
        "X-Request-Id": "req-auth-integration",
        "X-Client-Version": "1.0.0",
        "X-Platform": "ANDROID",
        "X-Device-Id": "device-integration-test",
        "Accept-Language": "zh-CN",
    }
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        send_response = await client.post(
            "/v1/auth/sms/send",
            headers={**common_headers, "Idempotency-Key": "idem-send-auth-test"},
            json={
                "phoneNumber": "5550000000",
                "countryCode": "+1",
                "purpose": "LOGIN",
                "captchaToken": None,
            },
        )
        assert send_response.status_code == 200
        assert sms_sender.code is not None

        send_replay = await client.post(
            "/v1/auth/sms/send",
            headers={**common_headers, "Idempotency-Key": "idem-send-auth-test"},
            json={
                "phoneNumber": "5550000000",
                "countryCode": "+1",
                "purpose": "LOGIN",
                "captchaToken": None,
            },
        )
        assert send_replay.status_code == 200
        assert send_replay.content == send_response.content
        assert send_replay.headers["Idempotency-Replayed"] == "true"

        reused_key = await client.post(
            "/v1/auth/sms/send",
            headers={**common_headers, "Idempotency-Key": "idem-send-auth-test"},
            json={
                "phoneNumber": "5550000001",
                "countryCode": "+1",
                "purpose": "LOGIN",
                "captchaToken": None,
            },
        )
        assert reused_key.status_code == 409
        assert reused_key.json()["code"] == "IDEMPOTENCY_KEY_REUSED"

        login_response = await client.post(
            "/v1/auth/sms/login",
            headers={**common_headers, "Idempotency-Key": "idem-login-auth-test"},
            json={
                "challengeId": send_response.json()["data"]["challengeId"],
                "code": sms_sender.code,
            },
        )
        assert login_response.status_code == 200
        first_tokens = login_response.json()["data"]["tokens"]

        refresh_response = await client.post(
            "/v1/auth/refresh",
            headers={**common_headers, "Idempotency-Key": "idem-refresh-auth-test"},
            json={"refreshToken": first_tokens["refreshToken"]},
        )
        assert refresh_response.status_code == 200
        rotated_tokens = refresh_response.json()["data"]
        assert rotated_tokens["refreshToken"] != first_tokens["refreshToken"]

        refresh_replay = await client.post(
            "/v1/auth/refresh",
            headers={**common_headers, "Idempotency-Key": "idem-refresh-auth-test"},
            json={"refreshToken": first_tokens["refreshToken"]},
        )
        assert refresh_replay.status_code == 200
        assert refresh_replay.content == refresh_response.content
        assert refresh_replay.headers["Idempotency-Replayed"] == "true"

        replay_response = await client.post(
            "/v1/auth/refresh",
            headers={**common_headers, "Idempotency-Key": "idem-refresh-replay"},
            json={"refreshToken": first_tokens["refreshToken"]},
        )
        assert replay_response.status_code == 401
        assert replay_response.json()["code"] == "AUTH_REFRESH_TOKEN_INVALID"

        authenticated_headers = {
            **common_headers,
            "Authorization": f"Bearer {rotated_tokens['accessToken']}",
        }
        me_response = await client.get("/v1/me", headers=authenticated_headers)
        assert me_response.status_code == 200
        assert me_response.json()["data"]["resourceVersion"] == 1

        update_response = await client.patch(
            "/v1/me",
            headers={
                **authenticated_headers,
                "If-Match": "1",
                "Idempotency-Key": "idem-update-user-test",
            },
            json={"nickname": "Contract Test", "timeZone": "Asia/Shanghai"},
        )
        assert update_response.status_code == 200
        assert update_response.json()["data"]["resourceVersion"] == 2

        consent_response = await client.put(
            "/v1/me/consents/MODEL_TRAINING",
            headers={
                **authenticated_headers,
                "Idempotency-Key": "idem-consent-test",
            },
            json={"documentVersion": "privacy-1", "granted": True},
        )
        assert consent_response.status_code == 200
        assert consent_response.json()["data"]["granted"] is True

        export_response = await client.post(
            "/v1/me/data-export",
            headers={
                **authenticated_headers,
                "Idempotency-Key": "idem-data-export-test",
            },
        )
        assert export_response.status_code == 202
        request_id = export_response.json()["data"]["requestId"]
        export_status = await client.get(
            f"/v1/me/data-requests/{request_id}",
            headers=authenticated_headers,
        )
        assert export_status.status_code == 200
        assert export_status.json()["data"]["status"] == "REQUESTED"

        deletion_response = await client.post(
            "/v1/me/deletion",
            headers={
                **authenticated_headers,
                "Idempotency-Key": "idem-deletion-test",
            },
            json={
                "confirmation": "DELETE_MY_ACCOUNT",
                "reasonCode": "PRIVACY_CONCERN",
            },
        )
        assert deletion_response.status_code == 202
        assert deletion_response.json()["data"]["status"] == "REQUESTED"

        cancel_response = await client.delete(
            "/v1/me/deletion",
            headers={
                **authenticated_headers,
                "Idempotency-Key": "idem-cancel-deletion-test",
            },
        )
        assert cancel_response.status_code == 200

        logout_response = await client.post(
            "/v1/auth/logout",
            headers={
                **authenticated_headers,
                "Idempotency-Key": "idem-logout-auth-test",
            },
        )
        assert logout_response.status_code == 200
        assert logout_response.headers["X-Request-Id"] == "req-auth-integration"

        revoked_response = await client.post(
            "/v1/auth/logout",
            headers={
                **authenticated_headers,
                "Idempotency-Key": "idem-logout-replay",
            },
        )
        assert revoked_response.status_code == 401
        assert revoked_response.json()["code"] == "AUTH_SESSION_REVOKED"

        second_send = await client.post(
            "/v1/auth/sms/send",
            headers={**common_headers, "Idempotency-Key": "idem-send-second-session"},
            json={
                "phoneNumber": "5550000000",
                "countryCode": "+1",
                "purpose": "LOGIN",
            },
        )
        second_login = await client.post(
            "/v1/auth/sms/login",
            headers={**common_headers, "Idempotency-Key": "idem-login-second-session"},
            json={
                "challengeId": second_send.json()["data"]["challengeId"],
                "code": sms_sender.code,
            },
        )
        second_access_token = second_login.json()["data"]["tokens"]["accessToken"]
        second_auth_headers = {
            **common_headers,
            "Authorization": f"Bearer {second_access_token}",
        }
        revoke_response = await client.delete(
            "/v1/me/devices/device-integration-test",
            headers={
                **second_auth_headers,
                "Idempotency-Key": "idem-revoke-device-test",
            },
        )
        assert revoke_response.status_code == 200

        revoked_device_response = await client.get("/v1/me", headers=second_auth_headers)
        assert revoked_device_response.status_code == 401
        assert revoked_device_response.json()["code"] == "AUTH_SESSION_REVOKED"
