from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from secrets import token_urlsafe

import jwt

from love_reply_api.application.errors import ApiError
from love_reply_api.config import Settings


@dataclass(frozen=True, slots=True)
class AccessClaims:
    user_id: str
    session_id: str
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class IssuedTokens:
    access_token: str
    access_token_expires_at: datetime
    refresh_token: str
    refresh_token_expires_at: datetime


class TokenService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    @staticmethod
    def hash_refresh_token(token: str) -> str:
        return sha256(token.encode("utf-8")).hexdigest()

    def issue(self, *, user_id: str, session_id: str, now: datetime) -> IssuedTokens:
        access_expires_at = now + timedelta(seconds=self._settings.access_token_ttl_seconds)
        refresh_expires_at = now + timedelta(seconds=self._settings.refresh_token_ttl_seconds)
        payload = {
            "sub": user_id,
            "sid": session_id,
            "iss": self._settings.jwt_issuer,
            "iat": int(now.timestamp()),
            "exp": int(access_expires_at.timestamp()),
        }
        access_token = jwt.encode(
            payload,
            self._settings.jwt_signing_key.get_secret_value(),
            algorithm="HS256",
        )
        return IssuedTokens(
            access_token=access_token,
            access_token_expires_at=access_expires_at,
            refresh_token=token_urlsafe(48),
            refresh_token_expires_at=refresh_expires_at,
        )

    def decode_access_token(self, token: str) -> AccessClaims:
        try:
            payload = jwt.decode(
                token,
                self._settings.jwt_signing_key.get_secret_value(),
                algorithms=["HS256"],
                issuer=self._settings.jwt_issuer,
                options={"require": ["sub", "sid", "iss", "iat", "exp"]},
            )
            return AccessClaims(
                user_id=str(payload["sub"]),
                session_id=str(payload["sid"]),
                expires_at=datetime.fromtimestamp(int(payload["exp"]), UTC),
            )
        except jwt.PyJWTError as exc:
            raise ApiError(
                status_code=401,
                code="AUTH_TOKEN_INVALID",
                message="Access token is invalid or expired.",
            ) from exc

