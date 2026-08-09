from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from secrets import token_urlsafe

import jwt

from love_reply_api.application.errors import ApiError
from love_reply_api.config import Settings


@dataclass(frozen=True, slots=True)
class AdminAccessClaims:
    admin_id: str
    session_id: str
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class IssuedAdminTokens:
    token_type: str
    access_token: str
    access_token_expires_at: datetime
    refresh_token: str
    refresh_token_expires_at: datetime


class AdminTokenService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._issuer = f"{settings.jwt_issuer}-admin"

    @staticmethod
    def hash_refresh_token(token: str) -> str:
        return sha256(token.encode("utf-8")).hexdigest()

    def issue(
        self,
        *,
        admin_id: str,
        session_id: str,
        now: datetime,
        access_ttl_seconds: int,
        refresh_ttl_seconds: int,
    ) -> IssuedAdminTokens:
        access_expires_at = now + timedelta(seconds=access_ttl_seconds)
        refresh_expires_at = now + timedelta(seconds=refresh_ttl_seconds)
        payload = {
            "sub": admin_id,
            "sid": session_id,
            "iss": self._issuer,
            "typ": "admin_access",
            "iat": int(now.timestamp()),
            "exp": int(access_expires_at.timestamp()),
        }
        access_token = jwt.encode(
            payload,
            self._settings.admin_jwt_signing_key.get_secret_value(),
            algorithm="HS256",
        )
        return IssuedAdminTokens(
            token_type="Bearer",
            access_token=access_token,
            access_token_expires_at=access_expires_at,
            refresh_token=token_urlsafe(48),
            refresh_token_expires_at=refresh_expires_at,
        )

    def decode_access_token(self, token: str) -> AdminAccessClaims:
        try:
            payload = jwt.decode(
                token,
                self._settings.admin_jwt_signing_key.get_secret_value(),
                algorithms=["HS256"],
                issuer=self._issuer,
                options={"require": ["sub", "sid", "iss", "typ", "iat", "exp"]},
            )
            if payload["typ"] != "admin_access":
                raise jwt.InvalidTokenError("wrong token type")
            return AdminAccessClaims(
                admin_id=str(payload["sub"]),
                session_id=str(payload["sid"]),
                expires_at=datetime.fromtimestamp(int(payload["exp"]), UTC),
            )
        except jwt.PyJWTError as exc:
            raise ApiError(
                status_code=401,
                code="TOKEN_EXPIRED",
                message="Administrator access token is invalid or expired.",
            ) from exc
