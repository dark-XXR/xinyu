import os
from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from love_reply_api.application.security import TotpService
from love_reply_api.application.tokens import TokenService
from love_reply_api.config import Settings, get_settings
from love_reply_api.infrastructure.admin_records import (
    AdminMfaChallengeRecord,
    AdminSecurityPolicyRecord,
    AdminSessionRecord,
    AdminUserRecord,
)
from love_reply_api.infrastructure.database import engine, session_factory
from love_reply_api.infrastructure.identity_records import IdempotencyRecord
from love_reply_api.main import app
from pydantic import SecretStr
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_INTEGRATION_TESTS") != "1",
    reason="requires the isolated project PostgreSQL container",
)

TEST_LOGIN = "owner@example.com"
TEST_PASSWORD = "correct horse battery staple"
TEST_TOTP_SECRET = "JBSWY3DPEHPK3PXP"


@pytest.fixture
def admin_settings() -> Settings:
    return Settings(
        _env_file=None,
        admin_jwt_signing_key=SecretStr("test-admin-jwt-signing-key-at-least-32-bytes"),
        data_encryption_key=SecretStr("test-data-encryption-key-at-least-32-bytes"),
        admin_bootstrap_login_name=TEST_LOGIN,
        admin_bootstrap_password=SecretStr(TEST_PASSWORD),
        admin_bootstrap_totp_secret=SecretStr(TEST_TOTP_SECRET),
        admin_bootstrap_display_name="Test Platform Owner",
    )


@pytest_asyncio.fixture(autouse=True)
async def clean_admin_tables() -> AsyncIterator[None]:
    async with session_factory() as session:
        await _delete_admin_data(session)
    await engine.dispose()
    yield
    app.dependency_overrides.pop(get_settings, None)
    async with session_factory() as session:
        await _delete_admin_data(session)
    await engine.dispose()


async def _delete_admin_data(session: AsyncSession) -> None:
    for record in (
        IdempotencyRecord,
        AdminSessionRecord,
        AdminMfaChallengeRecord,
        AdminUserRecord,
    ):
        await session.execute(delete(record))
    await session.commit()


def _headers(idempotency_key: str | None = None) -> dict[str, str]:
    headers = {
        "X-Request-Id": "req-admin-auth-integration",
        "X-Client-Version": "1.0.0",
        "X-Platform": "ADMIN_WEB",
        "Accept-Language": "zh-CN",
    }
    if idempotency_key is not None:
        headers["Idempotency-Key"] = idempotency_key
    return headers


def _totp_code(counter_offset: int = 0) -> str:
    service = TotpService()
    counter = service.counter(now=datetime.now(UTC), period_seconds=30)
    return service.code(
        secret=TEST_TOTP_SECRET,
        counter=counter + counter_offset,
        digits=6,
    )


@pytest.mark.asyncio
async def test_admin_mfa_refresh_reuse_and_logout(admin_settings: Settings) -> None:
    app.dependency_overrides[get_settings] = lambda: admin_settings
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        unknown_login = await client.post(
            "/admin/v1/auth/login",
            headers=_headers("idem-admin-unknown"),
            json={"loginName": "unknown@example.com", "password": "incorrect password"},
        )
        wrong_password = await client.post(
            "/admin/v1/auth/login",
            headers=_headers("idem-admin-wrong-password"),
            json={"loginName": TEST_LOGIN, "password": "incorrect password"},
        )
        assert unknown_login.status_code == wrong_password.status_code == 401
        assert unknown_login.json()["code"] == wrong_password.json()["code"]
        assert unknown_login.json()["message"] == wrong_password.json()["message"]

        login = await client.post(
            "/admin/v1/auth/login",
            headers=_headers("idem-admin-login"),
            json={"loginName": TEST_LOGIN.upper(), "password": TEST_PASSWORD},
        )
        assert login.status_code == 200
        challenge = login.json()["data"]["mfaChallenge"]
        assert login.json()["data"]["mfaRequired"] is True
        assert challenge["allowedMethods"] == ["TOTP"]

        async with session_factory() as session:
            admin = await session.scalar(select(AdminUserRecord))
            assert admin is not None
            assert TEST_PASSWORD not in admin.password_hash
            assert admin.mfa_secret_ciphertext != TEST_TOTP_SECRET
            assert "PROVIDER_SECRET_ROTATE" in admin.permissions

        correct_code = _totp_code()
        wrong_code = "000000" if correct_code != "000000" else "000001"
        invalid_mfa = await client.post(
            "/admin/v1/auth/mfa/verify",
            headers=_headers("idem-admin-invalid-mfa"),
            json={
                "challengeId": challenge["challengeId"],
                "method": "TOTP",
                "code": wrong_code,
            },
        )
        assert invalid_mfa.status_code == 401
        assert invalid_mfa.json()["code"] == "MFA_CODE_INVALID"

        verified = await client.post(
            "/admin/v1/auth/mfa/verify",
            headers=_headers("idem-admin-verify"),
            json={
                "challengeId": challenge["challengeId"],
                "method": "TOTP",
                "code": correct_code,
            },
        )
        assert verified.status_code == 200
        auth_data = verified.json()["data"]
        assert auth_data["admin"]["loginName"] == TEST_LOGIN
        assert TEST_PASSWORD not in verified.text
        assert TEST_TOTP_SECRET not in verified.text

        admin_access = auth_data["tokens"]["accessToken"]
        admin_refresh = auth_data["tokens"]["refreshToken"]
        admin_headers = {**_headers(), "Authorization": f"Bearer {admin_access}"}
        me = await client.get("/admin/v1/me", headers=admin_headers)
        assert me.status_code == 200
        assert "PROVIDER_PUBLISH" in me.json()["data"]["admin"]["permissions"]

        ordinary_user_tokens = TokenService(admin_settings).issue(
            user_id="usr_cross_boundary_test",
            session_id="ses_cross_boundary_test",
            now=datetime.now(UTC),
        )
        user_token_on_admin = await client.get(
            "/admin/v1/me",
            headers={
                **_headers(),
                "Authorization": f"Bearer {ordinary_user_tokens.access_token}",
            },
        )
        assert user_token_on_admin.status_code == 401

        refreshed = await client.post(
            "/admin/v1/auth/refresh",
            headers=_headers("idem-admin-refresh"),
            json={"refreshToken": admin_refresh},
        )
        assert refreshed.status_code == 200
        rotated_access = refreshed.json()["data"]["tokens"]["accessToken"]
        assert refreshed.json()["data"]["tokens"]["refreshToken"] != admin_refresh

        reused = await client.post(
            "/admin/v1/auth/refresh",
            headers=_headers("idem-admin-refresh-reuse"),
            json={"refreshToken": admin_refresh},
        )
        assert reused.status_code == 401
        assert reused.json()["code"] == "REFRESH_TOKEN_REUSED"

        revoked_family = await client.get(
            "/admin/v1/me",
            headers={**_headers(), "Authorization": f"Bearer {rotated_access}"},
        )
        assert revoked_family.status_code == 401
        assert revoked_family.json()["code"] == "TOKEN_REVOKED"

        second_login = await client.post(
            "/admin/v1/auth/login",
            headers=_headers("idem-admin-second-login"),
            json={"loginName": TEST_LOGIN, "password": TEST_PASSWORD},
        )
        second_challenge = second_login.json()["data"]["mfaChallenge"]["challengeId"]
        second_verified = await client.post(
            "/admin/v1/auth/mfa/verify",
            headers=_headers("idem-admin-second-verify"),
            json={
                "challengeId": second_challenge,
                "method": "TOTP",
                "code": _totp_code(counter_offset=1),
            },
        )
        assert second_verified.status_code == 200
        second_access = second_verified.json()["data"]["tokens"]["accessToken"]
        second_headers = {**_headers(), "Authorization": f"Bearer {second_access}"}

        logout = await client.post(
            "/admin/v1/auth/logout",
            headers={**second_headers, "Idempotency-Key": "idem-admin-logout"},
        )
        assert logout.status_code == 200
        logged_out = await client.get("/admin/v1/me", headers=second_headers)
        assert logged_out.status_code == 401
        assert logged_out.json()["code"] == "TOKEN_REVOKED"


@pytest.mark.asyncio
async def test_admin_mfa_attempt_limit_comes_from_published_policy(
    admin_settings: Settings,
) -> None:
    app.dependency_overrides[get_settings] = lambda: admin_settings
    async with session_factory() as session:
        policy = await session.scalar(
            select(AdminSecurityPolicyRecord).where(
                AdminSecurityPolicyRecord.status == "PUBLISHED"
            )
        )
        assert policy is not None
        original = policy.configuration
        await session.execute(
            update(AdminSecurityPolicyRecord)
            .where(AdminSecurityPolicyRecord.policy_id == policy.policy_id)
            .values(configuration={**original, "mfa_max_attempts": 1})
        )
        await session.commit()

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            login = await client.post(
                "/admin/v1/auth/login",
                headers=_headers("idem-admin-limit-login"),
                json={"loginName": TEST_LOGIN, "password": TEST_PASSWORD},
            )
            challenge_id = login.json()["data"]["mfaChallenge"]["challengeId"]
            correct_code = _totp_code()
            wrong_code = "000000" if correct_code != "000000" else "000001"

            invalid = await client.post(
                "/admin/v1/auth/mfa/verify",
                headers=_headers("idem-admin-limit-invalid"),
                json={"challengeId": challenge_id, "method": "TOTP", "code": wrong_code},
            )
            assert invalid.status_code == 401

            exhausted = await client.post(
                "/admin/v1/auth/mfa/verify",
                headers=_headers("idem-admin-limit-exhausted"),
                json={
                    "challengeId": challenge_id,
                    "method": "TOTP",
                    "code": correct_code,
                },
            )
            assert exhausted.status_code == 429
            assert exhausted.json()["code"] == "MFA_ATTEMPTS_EXHAUSTED"
    finally:
        async with session_factory() as session:
            await session.execute(
                update(AdminSecurityPolicyRecord)
                .where(AdminSecurityPolicyRecord.policy_id == policy.policy_id)
                .values(configuration=original)
            )
            await session.commit()


@pytest.mark.asyncio
async def test_admin_bootstrap_fails_closed_when_deployment_values_are_missing() -> None:
    missing_bootstrap = Settings(
        _env_file=None,
        admin_bootstrap_login_name=None,
        admin_bootstrap_password=None,
        admin_bootstrap_totp_secret=None,
    )
    app.dependency_overrides[get_settings] = lambda: missing_bootstrap
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/admin/v1/auth/login",
            headers=_headers("idem-admin-missing-bootstrap"),
            json={"loginName": TEST_LOGIN, "password": TEST_PASSWORD},
        )
    assert response.status_code == 503
    assert response.json()["code"] == "ADMIN_BOOTSTRAP_NOT_CONFIGURED"
