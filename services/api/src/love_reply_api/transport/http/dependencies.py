from dataclasses import dataclass
from typing import Annotated, cast

from fastapi import Depends, Header, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from love_reply_api.application.auth import AuthService, EmailSender, SmsSender
from love_reply_api.application.errors import ApiError
from love_reply_api.application.generation import AiProvider, GenerationService
from love_reply_api.application.identity import IdentityService
from love_reply_api.application.tokens import TokenService
from love_reply_api.config import Settings, get_settings
from love_reply_api.infrastructure.database import get_session
from love_reply_api.infrastructure.identity_records import AuthSessionRecord

bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True, slots=True)
class AuthContext:
    user_id: str
    session_id: str
    device_id: str


@dataclass(frozen=True, slots=True)
class ClientContext:
    client_version: str
    platform: str
    device_id: str
    accept_language: str


def get_client_context(
    x_client_version: Annotated[str, Header(alias="X-Client-Version")],
    x_platform: Annotated[str, Header(alias="X-Platform")],
    x_device_id: Annotated[str, Header(alias="X-Device-Id")],
    accept_language: Annotated[str, Header(alias="Accept-Language")],
) -> ClientContext:
    if x_platform not in {"ANDROID", "ADMIN_WEB"}:
        raise ApiError(
            status_code=400,
            code="INVALID_PLATFORM",
            message="X-Platform is not supported.",
        )
    return ClientContext(
        client_version=x_client_version,
        platform=x_platform,
        device_id=x_device_id,
        accept_language=accept_language,
    )


def get_sms_sender(request: Request) -> SmsSender:
    return cast(SmsSender, request.app.state.sms_sender)


def get_email_sender(request: Request) -> EmailSender:
    return cast(EmailSender, request.app.state.email_sender)


def get_auth_service(
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    sms_sender: Annotated[SmsSender, Depends(get_sms_sender)],
    email_sender: Annotated[EmailSender, Depends(get_email_sender)],
) -> AuthService:
    return AuthService(
        session=session,
        settings=settings,
        sms_sender=sms_sender,
        email_sender=email_sender,
    )


def get_identity_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> IdentityService:
    return IdentityService(session)


def get_generation_service(
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> GenerationService:
    return GenerationService(session=session, settings=settings)


def get_ai_provider(request: Request) -> AiProvider:
    return cast(AiProvider, request.app.state.ai_provider)


async def get_auth_context(
    client: Annotated[ClientContext, Depends(get_client_context)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthContext:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise ApiError(
            status_code=401,
            code="AUTH_TOKEN_MISSING",
            message="Bearer access token is required.",
        )
    claims = TokenService(settings).decode_access_token(credentials.credentials)
    auth_session = await session.scalar(
        select(AuthSessionRecord).where(AuthSessionRecord.session_id == claims.session_id)
    )
    if auth_session is None or auth_session.revoked_at is not None:
        raise ApiError(
            status_code=401,
            code="AUTH_SESSION_REVOKED",
            message="Authentication session is no longer active.",
        )
    if client.device_id != auth_session.device_id:
        raise ApiError(
            status_code=401,
            code="AUTH_DEVICE_MISMATCH",
            message="Access token does not belong to this device.",
        )
    return AuthContext(
        user_id=claims.user_id,
        session_id=claims.session_id,
        device_id=client.device_id,
    )
