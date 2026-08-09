from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated, cast

from fastapi import Depends, Header, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from love_reply_api.application.admin_auth import AdminAuthService
from love_reply_api.application.ai_admin import AiGatewayAdminService
from love_reply_api.application.ai_gateway import AiHttpTransport, RegistryAiProvider
from love_reply_api.application.auth import AuthService, EmailSender, SmsSender
from love_reply_api.application.errors import ApiError
from love_reply_api.application.generation import AiProvider, GenerationService
from love_reply_api.application.identity import IdentityService
from love_reply_api.application.provider_runtime import RegistryEmailSender, SmtpTransport
from love_reply_api.application.providers import ProviderHealthChecker, ProviderService
from love_reply_api.application.tokens import TokenService
from love_reply_api.config import Settings, get_settings
from love_reply_api.infrastructure.admin_records import AdminSessionRecord, AdminUserRecord
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


@dataclass(frozen=True, slots=True)
class AdminClientContext:
    client_version: str
    platform: str
    accept_language: str


@dataclass(frozen=True, slots=True)
class AdminContext:
    admin: AdminUserRecord
    session: AdminSessionRecord


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


def get_admin_client_context(
    x_client_version: Annotated[str, Header(alias="X-Client-Version")],
    x_platform: Annotated[str, Header(alias="X-Platform")],
    accept_language: Annotated[str, Header(alias="Accept-Language")],
) -> AdminClientContext:
    if x_platform != "ADMIN_WEB":
        raise ApiError(
            status_code=400,
            code="INVALID_PLATFORM",
            message="Administrator endpoints require X-Platform ADMIN_WEB.",
        )
    return AdminClientContext(
        client_version=x_client_version,
        platform=x_platform,
        accept_language=accept_language,
    )


def get_sms_sender(request: Request) -> SmsSender:
    return cast(SmsSender, request.app.state.sms_sender)


def get_email_sender(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> EmailSender:
    override = request.app.state.email_sender
    if override is not None:
        return cast(EmailSender, override)
    smtp_transport = cast(SmtpTransport, request.app.state.smtp_transport)
    return RegistryEmailSender(
        session=session,
        settings=settings,
        smtp_transport=smtp_transport,
    )


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


def get_admin_auth_service(
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AdminAuthService:
    return AdminAuthService(session=session, settings=settings)


def get_provider_health_checker(request: Request) -> ProviderHealthChecker:
    return cast(ProviderHealthChecker, request.app.state.provider_health_checker)


def get_provider_service(
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    health_checker: Annotated[ProviderHealthChecker, Depends(get_provider_health_checker)],
) -> ProviderService:
    return ProviderService(
        session=session,
        settings=settings,
        health_checker=health_checker,
    )


def get_ai_admin_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AiGatewayAdminService:
    return AiGatewayAdminService(session=session)


async def get_admin_context(
    client: Annotated[AdminClientContext, Depends(get_admin_client_context)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    service: Annotated[AdminAuthService, Depends(get_admin_auth_service)],
) -> AdminContext:
    del client
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise ApiError(
            status_code=401,
            code="TOKEN_EXPIRED",
            message="Administrator bearer token is required.",
        )
    admin, session = await service.authenticate_access(
        access_token=credentials.credentials
    )
    return AdminContext(admin=admin, session=session)


def require_admin_permission(
    permission: str,
) -> Callable[[AdminContext], AdminContext]:
    def dependency(
        context: Annotated[AdminContext, Depends(get_admin_context)],
    ) -> AdminContext:
        if permission not in context.admin.permissions:
            raise ApiError(
                status_code=403,
                code="PERMISSION_DENIED",
                message="Administrator permission is required.",
            )
        return context

    return dependency


def get_identity_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> IdentityService:
    return IdentityService(session)


def get_generation_service(
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> GenerationService:
    return GenerationService(session=session, settings=settings)


def get_ai_provider(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AiProvider:
    override = request.app.state.ai_provider
    if override is not None:
        return cast(AiProvider, override)
    return RegistryAiProvider(
        session=session,
        settings=settings,
        transport=cast(AiHttpTransport, request.app.state.ai_transport),
    )


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
