from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from love_reply_api.application.admin_tokens import AdminTokenService, IssuedAdminTokens
from love_reply_api.application.errors import ApiError
from love_reply_api.application.security import PasswordService, SecretCipher, TotpService
from love_reply_api.config import Settings
from love_reply_api.infrastructure.admin_records import (
    AdminMfaChallengeRecord,
    AdminSecurityPolicyRecord,
    AdminSessionRecord,
    AdminUserRecord,
)

BOOTSTRAP_PERMISSIONS = [
    "DASHBOARD_READ",
    "ROLE_READ",
    "ROLE_WRITE",
    "ADMIN_USER_READ",
    "ADMIN_USER_WRITE",
    "ADMIN_USER_MFA_RESET",
    "AUDIT_LOG_READ",
    "PROVIDER_READ",
    "PROVIDER_WRITE",
    "PROVIDER_SECRET_ROTATE",
    "PROVIDER_HEALTH_CHECK",
    "PROVIDER_PUBLISH",
    "PROVIDER_ROLLBACK",
]


class AdminAuthPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mfa_challenge_ttl_seconds: int = Field(ge=60, le=1800)
    mfa_max_attempts: int = Field(ge=1, le=20)
    access_token_ttl_seconds: int = Field(ge=60, le=3600)
    refresh_token_ttl_seconds: int = Field(ge=300, le=2_592_000)
    totp_period_seconds: int = Field(ge=15, le=120)
    totp_digits: int = Field(ge=6, le=8)
    totp_valid_window: int = Field(ge=0, le=2)


@dataclass(frozen=True, slots=True)
class AdminMfaChallengeResult:
    challenge_id: str
    allowed_methods: list[str]
    expires_at: datetime
    attempts_remaining: int


@dataclass(frozen=True, slots=True)
class AdminLoginResult:
    mfa_required: bool
    mfa_challenge: AdminMfaChallengeResult


@dataclass(frozen=True, slots=True)
class AdminAuthenticationResult:
    tokens: IssuedAdminTokens
    admin: AdminUserRecord
    session: AdminSessionRecord


@dataclass(frozen=True, slots=True)
class AdminRefreshResult:
    tokens: IssuedAdminTokens
    session: AdminSessionRecord


class AdminAuthService:
    def __init__(self, *, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings
        self._passwords = PasswordService()
        self._cipher = SecretCipher(settings)
        self._totp = TotpService()
        self._tokens = AdminTokenService(settings)

    async def _policy(self) -> AdminAuthPolicy:
        record = await self._session.scalar(
            select(AdminSecurityPolicyRecord)
            .where(
                AdminSecurityPolicyRecord.status == "PUBLISHED",
                AdminSecurityPolicyRecord.published_at.is_not(None),
            )
            .order_by(AdminSecurityPolicyRecord.version.desc())
            .limit(1)
        )
        if record is None:
            raise ApiError(
                status_code=503,
                code="ADMIN_AUTH_POLICY_UNAVAILABLE",
                message="Administrator authentication policy is unavailable.",
                retryable=True,
            )
        try:
            return AdminAuthPolicy.model_validate(record.configuration)
        except ValueError as exc:
            raise ApiError(
                status_code=503,
                code="ADMIN_AUTH_POLICY_INVALID",
                message="Administrator authentication policy is invalid.",
            ) from exc

    async def _ensure_bootstrap_admin(self) -> None:
        count = await self._session.scalar(select(func.count()).select_from(AdminUserRecord))
        if count:
            return
        login_name = self._settings.admin_bootstrap_login_name
        password = self._settings.admin_bootstrap_password
        totp_secret = self._settings.admin_bootstrap_totp_secret
        if login_name is None or password is None or totp_secret is None:
            raise ApiError(
                status_code=503,
                code="ADMIN_BOOTSTRAP_NOT_CONFIGURED",
                message="The initial administrator has not been configured.",
                retryable=False,
            )
        now = datetime.now(UTC)
        try:
            self._totp.code(
                secret=totp_secret.get_secret_value(),
                counter=0,
                digits=6,
            )
        except (ValueError, TypeError) as exc:
            raise ApiError(
                status_code=503,
                code="ADMIN_BOOTSTRAP_INVALID",
                message="The initial administrator MFA secret is invalid.",
            ) from exc
        self._session.add(
            AdminUserRecord(
                admin_id="adm_bootstrap_owner",
                login_name_normalized=login_name.strip().lower(),
                display_name=self._settings.admin_bootstrap_display_name,
                password_hash=self._passwords.hash(password.get_secret_value()),
                mfa_secret_ciphertext=self._cipher.encrypt(totp_secret.get_secret_value()),
                last_totp_counter=None,
                account_status="ACTIVE",
                mfa_status="ENROLLED",
                roles=[
                    {
                        "role_id": "role_platform_owner",
                        "role_code": "PLATFORM_OWNER",
                        "display_name": "Platform Owner",
                    }
                ],
                permissions=BOOTSTRAP_PERMISSIONS,
                last_login_at=None,
                resource_version=1,
                created_at=now,
                updated_at=now,
            )
        )
        try:
            await self._session.commit()
        except IntegrityError:
            await self._session.rollback()

    @staticmethod
    def _assert_active(admin: AdminUserRecord) -> None:
        if admin.account_status == "SUSPENDED":
            raise ApiError(
                status_code=403,
                code="ADMIN_ACCOUNT_SUSPENDED",
                message="The administrator account is suspended.",
            )
        if admin.account_status != "ACTIVE":
            raise ApiError(
                status_code=403,
                code="ADMIN_ACCOUNT_DISABLED",
                message="The administrator account is disabled.",
            )
        if admin.mfa_status != "ENROLLED":
            raise ApiError(
                status_code=403,
                code="MFA_ENROLLMENT_REQUIRED",
                message="Administrator MFA enrollment is required.",
            )

    async def login(self, *, login_name: str, password: str) -> AdminLoginResult:
        await self._ensure_bootstrap_admin()
        policy = await self._policy()
        admin = await self._session.scalar(
            select(AdminUserRecord).where(
                AdminUserRecord.login_name_normalized == login_name.strip().lower()
            )
        )
        password_hash = admin.password_hash if admin is not None else None
        if not self._passwords.verify(password_hash, password):
            raise ApiError(
                status_code=401,
                code="INVALID_CREDENTIALS",
                message="Administrator credentials are invalid.",
            )
        assert admin is not None
        self._assert_active(admin)
        now = datetime.now(UTC)
        challenge = AdminMfaChallengeRecord(
            challenge_id=f"amfa_{uuid4().hex}",
            admin_id=admin.admin_id,
            attempts=0,
            expires_at=now + timedelta(seconds=policy.mfa_challenge_ttl_seconds),
            consumed_at=None,
            created_at=now,
        )
        self._session.add(challenge)
        await self._session.commit()
        return AdminLoginResult(
            mfa_required=True,
            mfa_challenge=AdminMfaChallengeResult(
                challenge_id=challenge.challenge_id,
                allowed_methods=["TOTP"],
                expires_at=challenge.expires_at,
                attempts_remaining=policy.mfa_max_attempts,
            ),
        )

    async def verify_mfa(
        self,
        *,
        challenge_id: str,
        method: str,
        code: str,
    ) -> AdminAuthenticationResult:
        if method != "TOTP":
            raise ApiError(
                status_code=400,
                code="INVALID_ARGUMENT",
                message="The MFA method is not supported for this administrator.",
            )
        policy = await self._policy()
        now = datetime.now(UTC)
        challenge = await self._session.scalar(
            select(AdminMfaChallengeRecord)
            .where(AdminMfaChallengeRecord.challenge_id == challenge_id)
            .with_for_update()
        )
        if challenge is None or challenge.consumed_at is not None or challenge.expires_at <= now:
            raise ApiError(
                status_code=401,
                code="MFA_CHALLENGE_EXPIRED",
                message="The MFA challenge is invalid or expired.",
            )
        if challenge.attempts >= policy.mfa_max_attempts:
            raise ApiError(
                status_code=429,
                code="MFA_ATTEMPTS_EXHAUSTED",
                message="The MFA challenge has no attempts remaining.",
            )
        admin = await self._session.scalar(
            select(AdminUserRecord)
            .where(AdminUserRecord.admin_id == challenge.admin_id)
            .with_for_update()
        )
        if admin is None:
            raise ApiError(
                status_code=401,
                code="MFA_CHALLENGE_EXPIRED",
                message="The MFA challenge is invalid or expired.",
            )
        self._assert_active(admin)
        counter = self._totp.verify(
            secret=self._cipher.decrypt(admin.mfa_secret_ciphertext),
            presented_code=code,
            now=now,
            period_seconds=policy.totp_period_seconds,
            digits=policy.totp_digits,
            valid_window=policy.totp_valid_window,
            minimum_counter=admin.last_totp_counter,
        )
        if counter is None:
            challenge.attempts += 1
            await self._session.commit()
            raise ApiError(
                status_code=401,
                code="MFA_CODE_INVALID",
                message="The MFA verification code is invalid.",
            )

        challenge.consumed_at = now
        admin.last_totp_counter = counter
        admin.last_login_at = now
        admin.updated_at = now
        session_id = f"ases_{uuid4().hex}"
        tokens = self._tokens.issue(
            admin_id=admin.admin_id,
            session_id=session_id,
            now=now,
            access_ttl_seconds=policy.access_token_ttl_seconds,
            refresh_ttl_seconds=policy.refresh_token_ttl_seconds,
        )
        session = AdminSessionRecord(
            session_id=session_id,
            admin_id=admin.admin_id,
            token_family_id=f"afam_{uuid4().hex}",
            refresh_token_hash=self._tokens.hash_refresh_token(tokens.refresh_token),
            mfa_verified_at=now,
            expires_at=tokens.refresh_token_expires_at,
            revoked_at=None,
            rotated_to_session_id=None,
            reuse_detected_at=None,
            created_at=now,
            last_seen_at=now,
        )
        self._session.add(session)
        await self._session.commit()
        return AdminAuthenticationResult(tokens=tokens, admin=admin, session=session)

    async def refresh(self, *, refresh_token: str) -> AdminRefreshResult:
        now = datetime.now(UTC)
        token_hash = self._tokens.hash_refresh_token(refresh_token)
        existing = await self._session.scalar(
            select(AdminSessionRecord)
            .where(AdminSessionRecord.refresh_token_hash == token_hash)
            .with_for_update()
        )
        if existing is None or existing.expires_at <= now:
            raise ApiError(
                status_code=401,
                code="TOKEN_EXPIRED",
                message="Administrator refresh token is invalid or expired.",
            )
        if existing.rotated_to_session_id is not None:
            await self._session.execute(
                update(AdminSessionRecord)
                .where(AdminSessionRecord.token_family_id == existing.token_family_id)
                .values(revoked_at=now, reuse_detected_at=now)
            )
            await self._session.commit()
            raise ApiError(
                status_code=401,
                code="REFRESH_TOKEN_REUSED",
                message="Administrator refresh token reuse was detected.",
            )
        if existing.revoked_at is not None:
            raise ApiError(
                status_code=401,
                code="TOKEN_REVOKED",
                message="Administrator refresh token is revoked.",
            )
        admin = await self._session.get(AdminUserRecord, existing.admin_id)
        if admin is None:
            raise ApiError(
                status_code=401,
                code="SESSION_NOT_FOUND",
                message="Administrator session was not found.",
            )
        self._assert_active(admin)
        policy = await self._policy()
        session_id = f"ases_{uuid4().hex}"
        tokens = self._tokens.issue(
            admin_id=admin.admin_id,
            session_id=session_id,
            now=now,
            access_ttl_seconds=policy.access_token_ttl_seconds,
            refresh_ttl_seconds=policy.refresh_token_ttl_seconds,
        )
        existing.revoked_at = now
        existing.rotated_to_session_id = session_id
        session = AdminSessionRecord(
            session_id=session_id,
            admin_id=admin.admin_id,
            token_family_id=existing.token_family_id,
            refresh_token_hash=self._tokens.hash_refresh_token(tokens.refresh_token),
            mfa_verified_at=existing.mfa_verified_at,
            expires_at=tokens.refresh_token_expires_at,
            revoked_at=None,
            rotated_to_session_id=None,
            reuse_detected_at=None,
            created_at=now,
            last_seen_at=now,
        )
        self._session.add(session)
        await self._session.commit()
        return AdminRefreshResult(tokens=tokens, session=session)

    async def authenticate_access(
        self,
        *,
        access_token: str,
        required_permission: str | None = None,
    ) -> tuple[AdminUserRecord, AdminSessionRecord]:
        claims = self._tokens.decode_access_token(access_token)
        session = await self._session.get(AdminSessionRecord, claims.session_id)
        if (
            session is None
            or session.revoked_at is not None
            or session.admin_id != claims.admin_id
        ):
            raise ApiError(
                status_code=401,
                code="TOKEN_REVOKED",
                message="Administrator session is revoked.",
            )
        admin = await self._session.get(AdminUserRecord, claims.admin_id)
        if admin is None:
            raise ApiError(
                status_code=401,
                code="SESSION_NOT_FOUND",
                message="Administrator session was not found.",
            )
        self._assert_active(admin)
        if required_permission is not None and required_permission not in admin.permissions:
            raise ApiError(
                status_code=403,
                code="PERMISSION_DENIED",
                message="Administrator permission is required.",
            )
        session.last_seen_at = datetime.now(UTC)
        await self._session.commit()
        return admin, session

    async def logout(self, *, session_id: str) -> None:
        session = await self._session.get(AdminSessionRecord, session_id)
        if session is None:
            return
        await self._session.execute(
            update(AdminSessionRecord)
            .where(
                AdminSessionRecord.token_family_id == session.token_family_id,
                AdminSessionRecord.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(UTC))
        )
        await self._session.commit()
