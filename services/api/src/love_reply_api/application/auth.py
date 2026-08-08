from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from hmac import compare_digest
from hmac import new as new_hmac
from random import SystemRandom
from typing import Protocol
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from love_reply_api.application.errors import ApiError
from love_reply_api.application.tokens import IssuedTokens, TokenService
from love_reply_api.config import Settings
from love_reply_api.domain.identity import AccountStatus
from love_reply_api.infrastructure.generation_records import (
    EntitlementRecord,
    WalletAccountRecord,
)
from love_reply_api.infrastructure.identity_records import (
    AuthSessionRecord,
    SmsChallengeRecord,
    UserDeviceRecord,
    UserProfileRecord,
    UserRecord,
)


class SmsSender(Protocol):
    async def send_login_code(self, *, phone_e164: str, code: str) -> None: ...


class UnavailableSmsSender:
    async def send_login_code(self, *, phone_e164: str, code: str) -> None:
        del phone_e164, code
        raise ApiError(
            status_code=503,
            code="SMS_PROVIDER_UNAVAILABLE",
            message="SMS provider is not configured.",
            retryable=True,
        )


@dataclass(frozen=True, slots=True)
class ChallengeResult:
    challenge_id: str
    expires_at: datetime
    resend_after_seconds: int


@dataclass(frozen=True, slots=True)
class LoginResult:
    tokens: IssuedTokens
    user: UserRecord


class AuthService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        settings: Settings,
        sms_sender: SmsSender,
    ) -> None:
        self._session = session
        self._settings = settings
        self._sms_sender = sms_sender
        self._tokens = TokenService(settings)

    def _hash_code(self, *, challenge_id: str, code: str) -> str:
        digest = new_hmac(
            self._settings.jwt_signing_key.get_secret_value().encode("utf-8"),
            f"{challenge_id}:{code}".encode(),
            sha256,
        )
        return digest.hexdigest()

    async def send_challenge(self, *, phone_e164: str, purpose: str) -> ChallengeResult:
        now = datetime.now(UTC)
        challenge_id = f"sms_{uuid4().hex}"
        code = f"{SystemRandom().randrange(0, 1_000_000):06d}"
        expires_at = now + timedelta(seconds=self._settings.sms_challenge_ttl_seconds)
        challenge = SmsChallengeRecord(
            challenge_id=challenge_id,
            phone_e164=phone_e164,
            purpose=purpose,
            code_hash=self._hash_code(challenge_id=challenge_id, code=code),
            attempts=0,
            expires_at=expires_at,
            consumed_at=None,
            created_at=now,
        )
        self._session.add(challenge)
        try:
            await self._sms_sender.send_login_code(phone_e164=phone_e164, code=code)
            await self._session.commit()
        except Exception:
            await self._session.rollback()
            raise
        return ChallengeResult(
            challenge_id=challenge_id,
            expires_at=expires_at,
            resend_after_seconds=60,
        )

    async def login(
        self,
        *,
        challenge_id: str,
        code: str,
        device_id: str,
        locale: str,
    ) -> LoginResult:
        now = datetime.now(UTC)
        challenge = await self._session.scalar(
            select(SmsChallengeRecord)
            .where(SmsChallengeRecord.challenge_id == challenge_id)
            .with_for_update()
        )
        if challenge is None or challenge.consumed_at is not None or challenge.expires_at <= now:
            raise ApiError(
                status_code=401,
                code="SMS_CHALLENGE_INVALID",
                message="SMS challenge is invalid or expired.",
            )
        if challenge.attempts >= 5:
            raise ApiError(
                status_code=429,
                code="SMS_CHALLENGE_LOCKED",
                message="Too many verification attempts.",
            )
        expected = self._hash_code(challenge_id=challenge_id, code=code)
        if not compare_digest(expected, challenge.code_hash):
            challenge.attempts += 1
            await self._session.commit()
            raise ApiError(
                status_code=401,
                code="SMS_CODE_INVALID",
                message="Verification code is invalid.",
            )

        challenge.consumed_at = now
        user = await self._session.scalar(
            select(UserRecord).where(UserRecord.phone_e164 == challenge.phone_e164)
        )
        if user is None:
            user = UserRecord(
                user_id=f"usr_{uuid4().hex}",
                phone_e164=challenge.phone_e164,
                status=AccountStatus.ACTIVE.value,
                locale=locale,
                time_zone="UTC",
                resource_version=1,
                created_at=now,
                updated_at=now,
            )
            self._session.add(user)
            await self._session.flush()
            self._session.add(UserProfileRecord(user_id=user.user_id, updated_at=now))
            self._session.add(
                EntitlementRecord(
                    user_id=user.user_id,
                    plan_code="FREE",
                    plan_expires_at=None,
                    text_remaining=self._settings.free_text_quota,
                    text_reserved=0,
                    vision_remaining=0,
                    allowed_model_ids=[self._settings.default_model_id],
                    allowed_style_ids=self._settings.default_style_ids,
                    resource_version=1,
                    updated_at=now,
                )
            )
            self._session.add(
                WalletAccountRecord(
                    user_id=user.user_id,
                    energy_balance=0,
                    energy_reserved=0,
                    resource_version=1,
                    updated_at=now,
                )
            )

        device = await self._session.scalar(
            select(UserDeviceRecord).where(
                UserDeviceRecord.user_id == user.user_id,
                UserDeviceRecord.device_id == device_id,
            )
        )
        if device is None:
            device = UserDeviceRecord(
                id=f"dev_{uuid4().hex}",
                user_id=user.user_id,
                device_id=device_id,
                platform="ANDROID",
                model=None,
                last_seen_at=now,
                created_at=now,
                revoked_at=None,
            )
            self._session.add(device)
        else:
            device.last_seen_at = now
            device.revoked_at = None

        issued = self._tokens.issue(
            user_id=user.user_id,
            session_id=f"ses_{uuid4().hex}",
            now=now,
        )
        session_id = TokenService(self._settings).decode_access_token(
            issued.access_token
        ).session_id
        self._session.add(
            AuthSessionRecord(
                session_id=session_id,
                user_id=user.user_id,
                device_id=device_id,
                refresh_token_hash=self._tokens.hash_refresh_token(issued.refresh_token),
                expires_at=issued.refresh_token_expires_at,
                revoked_at=None,
                rotated_to_session_id=None,
                created_at=now,
            )
        )
        await self._session.commit()
        return LoginResult(tokens=issued, user=user)

    async def refresh(self, *, refresh_token: str, device_id: str) -> IssuedTokens:
        now = datetime.now(UTC)
        token_hash = self._tokens.hash_refresh_token(refresh_token)
        existing = await self._session.scalar(
            select(AuthSessionRecord)
            .where(AuthSessionRecord.refresh_token_hash == token_hash)
            .with_for_update()
        )
        if (
            existing is None
            or existing.revoked_at is not None
            or existing.expires_at <= now
            or existing.device_id != device_id
        ):
            raise ApiError(
                status_code=401,
                code="AUTH_REFRESH_TOKEN_INVALID",
                message="Refresh token is invalid or expired.",
            )

        new_session_id = f"ses_{uuid4().hex}"
        issued = self._tokens.issue(
            user_id=existing.user_id,
            session_id=new_session_id,
            now=now,
        )
        existing.revoked_at = now
        existing.rotated_to_session_id = new_session_id
        self._session.add(
            AuthSessionRecord(
                session_id=new_session_id,
                user_id=existing.user_id,
                device_id=device_id,
                refresh_token_hash=self._tokens.hash_refresh_token(issued.refresh_token),
                expires_at=issued.refresh_token_expires_at,
                revoked_at=None,
                rotated_to_session_id=None,
                created_at=now,
            )
        )
        await self._session.commit()
        return issued

    async def logout(self, *, session_id: str) -> None:
        await self._session.execute(
            update(AuthSessionRecord)
            .where(
                AuthSessionRecord.session_id == session_id,
                AuthSessionRecord.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(UTC))
        )
        await self._session.commit()

    async def logout_all(self, *, user_id: str) -> None:
        await self._session.execute(
            update(AuthSessionRecord)
            .where(
                AuthSessionRecord.user_id == user_id,
                AuthSessionRecord.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(UTC))
        )
        await self._session.commit()
