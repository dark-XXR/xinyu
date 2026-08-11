from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from hmac import compare_digest
from hmac import new as new_hmac
from inspect import isawaitable
from math import ceil
from random import SystemRandom
from typing import Protocol
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from love_reply_api.application.errors import ApiError
from love_reply_api.application.runtime_config import (
    AuthChallengePolicyConfig,
    AuthChannel,
    AuthPolicyConfig,
    RuntimeConfigService,
)
from love_reply_api.application.tokens import IssuedTokens, TokenService
from love_reply_api.config import Settings
from love_reply_api.domain.identity import AccountStatus
from love_reply_api.infrastructure.generation_records import (
    EntitlementRecord,
    WalletAccountRecord,
)
from love_reply_api.infrastructure.identity_records import (
    AuthSessionRecord,
    EmailChallengeRecord,
    SmsChallengeRecord,
    UserDeviceRecord,
    UserProfileRecord,
    UserRecord,
)


class EmailSender(Protocol):
    async def send_login_code(
        self,
        *,
        email_normalized: str,
        code: str,
        locale: str,
    ) -> None: ...


class SmsSender(Protocol):
    async def send_login_code(self, *, phone_e164: str, code: str) -> None: ...


class UnavailableEmailSender:
    is_available = False

    async def send_login_code(
        self,
        *,
        email_normalized: str,
        code: str,
        locale: str,
    ) -> None:
        del email_normalized, code, locale
        raise ApiError(
            status_code=503,
            code="EMAIL_PROVIDER_UNAVAILABLE",
            message="Email delivery is temporarily unavailable.",
            retryable=True,
        )


class UnavailableSmsSender:
    is_available = False

    async def send_login_code(self, *, phone_e164: str, code: str) -> None:
        del phone_e164, code
        raise ApiError(
            status_code=503,
            code="SMS_PROVIDER_UNAVAILABLE",
            message="SMS delivery is temporarily unavailable.",
            retryable=True,
        )


@dataclass(frozen=True, slots=True)
class ChallengeResult:
    challenge_id: str
    expires_at: datetime
    resend_after_seconds: int


@dataclass(frozen=True, slots=True)
class EmailChallengeResult(ChallengeResult):
    masked_destination: str


@dataclass(frozen=True, slots=True)
class AuthChannelAvailabilityResult:
    channel: AuthChannel
    available: bool
    challenge_modes: list[str]
    unavailable_reason_code: str | None


@dataclass(frozen=True, slots=True)
class AuthChannelPolicyResult:
    primary_channel: AuthChannel
    fallback_channels: list[AuthChannel]
    channels: list[AuthChannelAvailabilityResult]
    policy_version: int


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
        email_sender: EmailSender | None = None,
    ) -> None:
        self._session = session
        self._settings = settings
        self._sms_sender = sms_sender
        self._email_sender = email_sender or UnavailableEmailSender()
        self._tokens = TokenService(settings)

    def _hash_code(self, *, challenge_id: str, code: str) -> str:
        digest = new_hmac(
            self._settings.jwt_signing_key.get_secret_value().encode("utf-8"),
            f"{challenge_id}:{code}".encode(),
            sha256,
        )
        return digest.hexdigest()

    @staticmethod
    async def _is_provider_available(sender: object) -> bool:
        available = getattr(sender, "available", None)
        if callable(available):
            result = available()
            if isawaitable(result):
                return bool(await result)
            return bool(result)
        return bool(getattr(sender, "is_available", True))

    async def _auth_policy(self) -> AuthPolicyConfig:
        return (await RuntimeConfigService(self._session).get_published()).auth_policy

    async def _channel_policy(self, channel: AuthChannel) -> AuthChallengePolicyConfig:
        policy = await self._auth_policy()
        channel_policy = policy.channels[channel]
        if not channel_policy.enabled:
            raise ApiError(
                status_code=503,
                code="AUTH_CHANNEL_DISABLED",
                message="The requested authentication channel is disabled.",
                retryable=False,
                details={"channel": channel},
            )
        return channel_policy

    def _channel_availability(
        self,
        *,
        channel: AuthChannel,
        enabled: bool,
        provider_available: bool,
    ) -> AuthChannelAvailabilityResult:
        if not enabled:
            unavailable_reason = "CHANNEL_DISABLED"
        elif not provider_available:
            unavailable_reason = "PROVIDER_NOT_CONFIGURED"
        else:
            unavailable_reason = None
        return AuthChannelAvailabilityResult(
            channel=channel,
            available=enabled and provider_available,
            challenge_modes=["OTP"],
            unavailable_reason_code=unavailable_reason,
        )

    @staticmethod
    def _raise_if_resend_is_early(
        *,
        created_at: datetime,
        consumed_at: datetime | None,
        now: datetime,
        resend_after_seconds: int,
    ) -> None:
        if consumed_at is not None:
            return
        retry_at = created_at + timedelta(seconds=resend_after_seconds)
        if retry_at <= now:
            return
        retry_after = max(1, ceil((retry_at - now).total_seconds()))
        raise ApiError(
            status_code=429,
            code="RATE_LIMITED",
            message="Try again after the retry interval.",
            retryable=True,
            retry_after_seconds=retry_after,
        )

    async def get_auth_channels(self) -> AuthChannelPolicyResult:
        policy = await self._auth_policy()
        email_available = await self._is_provider_available(self._email_sender)
        sms_available = await self._is_provider_available(self._sms_sender)
        return AuthChannelPolicyResult(
            primary_channel=policy.primary_channel,
            fallback_channels=policy.fallback_channels,
            channels=[
                self._channel_availability(
                    channel="EMAIL",
                    enabled=policy.channels["EMAIL"].enabled,
                    provider_available=email_available,
                ),
                self._channel_availability(
                    channel="SMS",
                    enabled=policy.channels["SMS"].enabled,
                    provider_available=sms_available,
                ),
            ],
            policy_version=policy.policy_version,
        )

    async def send_email_challenge(
        self,
        *,
        email_normalized: str,
        purpose: str,
        locale: str,
    ) -> EmailChallengeResult:
        channel_policy = await self._channel_policy("EMAIL")
        if not await self._is_provider_available(self._email_sender):
            raise ApiError(
                status_code=503,
                code="EMAIL_PROVIDER_UNAVAILABLE",
                message="Email delivery is temporarily unavailable.",
                retryable=True,
            )

        normalized = email_normalized.strip().lower()
        now = datetime.now(UTC)
        latest_challenge = await self._session.scalar(
            select(EmailChallengeRecord)
            .where(EmailChallengeRecord.email_normalized == normalized)
            .order_by(EmailChallengeRecord.created_at.desc())
            .limit(1)
        )
        if latest_challenge is not None:
            self._raise_if_resend_is_early(
                created_at=latest_challenge.created_at,
                consumed_at=latest_challenge.consumed_at,
                now=now,
                resend_after_seconds=channel_policy.resend_after_seconds,
            )
        challenge_id = f"email_{uuid4().hex}"
        code = f"{SystemRandom().randrange(0, 1_000_000):06d}"
        expires_at = now + timedelta(seconds=channel_policy.challenge_ttl_seconds)
        challenge = EmailChallengeRecord(
            challenge_id=challenge_id,
            email_normalized=normalized,
            purpose=purpose,
            code_hash=self._hash_code(challenge_id=challenge_id, code=code),
            attempts=0,
            expires_at=expires_at,
            consumed_at=None,
            created_at=now,
        )
        self._session.add(challenge)
        try:
            await self._email_sender.send_login_code(
                email_normalized=normalized,
                code=code,
                locale=locale,
            )
            await self._session.commit()
        except ApiError:
            await self._session.rollback()
            raise
        except Exception as exc:
            await self._session.rollback()
            raise ApiError(
                status_code=503,
                code="EMAIL_PROVIDER_UNAVAILABLE",
                message="Email delivery is temporarily unavailable.",
                retryable=True,
            ) from exc
        return EmailChallengeResult(
            challenge_id=challenge_id,
            expires_at=expires_at,
            resend_after_seconds=channel_policy.resend_after_seconds,
            masked_destination=self._mask_email(normalized),
        )

    async def send_sms_challenge(
        self,
        *,
        phone_e164: str,
        purpose: str,
    ) -> ChallengeResult:
        channel_policy = await self._channel_policy("SMS")
        if not await self._is_provider_available(self._sms_sender):
            raise ApiError(
                status_code=503,
                code="SMS_PROVIDER_UNAVAILABLE",
                message="SMS delivery is temporarily unavailable.",
                retryable=True,
            )

        now = datetime.now(UTC)
        latest_challenge = await self._session.scalar(
            select(SmsChallengeRecord)
            .where(SmsChallengeRecord.phone_e164 == phone_e164)
            .order_by(SmsChallengeRecord.created_at.desc())
            .limit(1)
        )
        if latest_challenge is not None:
            self._raise_if_resend_is_early(
                created_at=latest_challenge.created_at,
                consumed_at=latest_challenge.consumed_at,
                now=now,
                resend_after_seconds=channel_policy.resend_after_seconds,
            )
        challenge_id = f"sms_{uuid4().hex}"
        code = f"{SystemRandom().randrange(0, 1_000_000):06d}"
        expires_at = now + timedelta(seconds=channel_policy.challenge_ttl_seconds)
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
        except ApiError:
            await self._session.rollback()
            raise
        except Exception as exc:
            await self._session.rollback()
            raise ApiError(
                status_code=503,
                code="SMS_PROVIDER_UNAVAILABLE",
                message="SMS delivery is temporarily unavailable.",
                retryable=True,
            ) from exc
        return ChallengeResult(
            challenge_id=challenge_id,
            expires_at=expires_at,
            resend_after_seconds=channel_policy.resend_after_seconds,
        )

    async def send_challenge(self, *, phone_e164: str, purpose: str) -> ChallengeResult:
        return await self.send_sms_challenge(phone_e164=phone_e164, purpose=purpose)

    @staticmethod
    def _mask_email(email_normalized: str) -> str:
        local_part, domain = email_normalized.rsplit("@", 1)
        return f"{local_part[0]}***@{domain}"

    async def login_with_email(
        self,
        *,
        challenge_id: str,
        code: str,
        device_id: str,
        locale: str,
    ) -> LoginResult:
        channel_policy = await self._channel_policy("EMAIL")
        now = datetime.now(UTC)
        challenge = await self._session.scalar(
            select(EmailChallengeRecord)
            .where(EmailChallengeRecord.challenge_id == challenge_id)
            .with_for_update()
        )
        await self._verify_challenge(
            challenge=challenge,
            challenge_id=challenge_id,
            code=code,
            now=now,
            max_attempts=channel_policy.max_attempts,
            channel="EMAIL",
        )
        assert challenge is not None
        challenge.consumed_at = now
        user = await self._session.scalar(
            select(UserRecord).where(UserRecord.email_normalized == challenge.email_normalized)
        )
        if user is None:
            user = await self._create_user(
                phone_e164=None,
                email_normalized=challenge.email_normalized,
                locale=locale,
                now=now,
            )
        return await self._complete_login(user=user, device_id=device_id, now=now)

    async def login_with_sms(
        self,
        *,
        challenge_id: str,
        code: str,
        device_id: str,
        locale: str,
    ) -> LoginResult:
        channel_policy = await self._channel_policy("SMS")
        now = datetime.now(UTC)
        challenge = await self._session.scalar(
            select(SmsChallengeRecord)
            .where(SmsChallengeRecord.challenge_id == challenge_id)
            .with_for_update()
        )
        await self._verify_challenge(
            challenge=challenge,
            challenge_id=challenge_id,
            code=code,
            now=now,
            max_attempts=channel_policy.max_attempts,
            channel="SMS",
        )
        assert challenge is not None
        challenge.consumed_at = now
        user = await self._session.scalar(
            select(UserRecord).where(UserRecord.phone_e164 == challenge.phone_e164)
        )
        if user is None:
            user = await self._create_user(
                phone_e164=challenge.phone_e164,
                email_normalized=None,
                locale=locale,
                now=now,
            )
        return await self._complete_login(user=user, device_id=device_id, now=now)

    async def login(
        self,
        *,
        challenge_id: str,
        code: str,
        device_id: str,
        locale: str,
    ) -> LoginResult:
        return await self.login_with_sms(
            challenge_id=challenge_id,
            code=code,
            device_id=device_id,
            locale=locale,
        )

    async def _verify_challenge(
        self,
        *,
        challenge: EmailChallengeRecord | SmsChallengeRecord | None,
        challenge_id: str,
        code: str,
        now: datetime,
        max_attempts: int,
        channel: AuthChannel,
    ) -> None:
        invalid_code = f"INVALID_{channel}_CODE"
        if challenge is None or challenge.consumed_at is not None or challenge.expires_at <= now:
            raise ApiError(
                status_code=401,
                code=invalid_code,
                message="The verification code is invalid or expired.",
            )
        if challenge.attempts >= max_attempts:
            raise ApiError(
                status_code=429,
                code=f"{channel}_CHALLENGE_LOCKED",
                message="Too many verification attempts.",
            )
        expected = self._hash_code(challenge_id=challenge_id, code=code)
        if not compare_digest(expected, challenge.code_hash):
            challenge.attempts += 1
            await self._session.commit()
            raise ApiError(
                status_code=401,
                code=invalid_code,
                message="The verification code is invalid or expired.",
            )

    async def _create_user(
        self,
        *,
        phone_e164: str | None,
        email_normalized: str | None,
        locale: str,
        now: datetime,
    ) -> UserRecord:
        runtime_config = await RuntimeConfigService(self._session).get_published()
        free_entitlement = runtime_config.free_entitlement
        user = UserRecord(
            user_id=f"usr_{uuid4().hex}",
            phone_e164=phone_e164,
            email_normalized=email_normalized,
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
                plan_code=free_entitlement.plan_code,
                plan_expires_at=None,
                text_remaining=free_entitlement.text_quota,
                text_reserved=0,
                vision_remaining=free_entitlement.vision_quota,
                allowed_model_ids=free_entitlement.allowed_model_ids,
                allowed_style_ids=free_entitlement.allowed_style_ids,
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
        return user

    async def _complete_login(
        self,
        *,
        user: UserRecord,
        device_id: str,
        now: datetime,
    ) -> LoginResult:
        self._assert_user_active(user)
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

        session_id = f"ses_{uuid4().hex}"
        issued = self._tokens.issue(
            user_id=user.user_id,
            session_id=session_id,
            now=now,
        )
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
        user = await self._session.get(UserRecord, existing.user_id)
        if user is None:
            raise ApiError(
                status_code=401,
                code="AUTH_USER_NOT_FOUND",
                message="The user account no longer exists.",
            )
        self._assert_user_active(user)

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

    @staticmethod
    def _assert_user_active(user: UserRecord) -> None:
        """在签发或刷新凭证前再次检查账户状态。"""
        if user.status == AccountStatus.SUSPENDED.value:
            raise ApiError(
                status_code=403,
                code="USER_ACCOUNT_SUSPENDED",
                message="The user account is suspended.",
            )
        if user.status != AccountStatus.ACTIVE.value:
            raise ApiError(
                status_code=403,
                code="USER_ACCOUNT_UNAVAILABLE",
                message="The user account is not available for login.",
            )

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
