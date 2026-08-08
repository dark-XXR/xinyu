import os
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
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
    def __init__(self) -> None:
        self.code: str | None = None

    async def send_login_code(self, *, phone_e164: str, code: str) -> None:
        assert phone_e164 == "+15550000000"
        self.code = code


@pytest_asyncio.fixture(autouse=True)
async def clean_identity_tables() -> AsyncIterator[None]:
    async with session_factory() as session:
        await _delete_identity_data(session)
    await engine.dispose()
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
