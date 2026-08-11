"""HTTP 依赖装配。

测试可通过 app.state 注入替身；生产请求默认从数据库解析管理员已经发布的供应商配置。
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated, cast

from fastapi import Depends, Header, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from love_reply_api.application.admin_auth import AdminAuthService
from love_reply_api.application.admin_platform import AdminPlatformService
from love_reply_api.application.ai_admin import AiGatewayAdminService
from love_reply_api.application.ai_gateway import AiHttpTransport, RegistryAiProvider
from love_reply_api.application.audit import ComplianceAuditService
from love_reply_api.application.auth import AuthService, EmailSender, SmsSender
from love_reply_api.application.commerce import CommerceService
from love_reply_api.application.commerce_admin import CommerceAdminService
from love_reply_api.application.delivery_adapters import EmailApiTransport, SmsApiTransport
from love_reply_api.application.errors import ApiError
from love_reply_api.application.generation import AiProvider, GenerationService
from love_reply_api.application.identity import IdentityService
from love_reply_api.application.payment_adapters import EpayTransport
from love_reply_api.application.provider_runtime import (
    RegistryEmailSender,
    RegistryPaymentGateway,
    RegistrySmsSender,
    SmtpTransport,
)
from love_reply_api.application.providers import ProviderHealthChecker, ProviderService
from love_reply_api.application.referrals import ReferralService
from love_reply_api.application.support import SupportService
from love_reply_api.application.tokens import TokenService
from love_reply_api.config import Settings, get_settings
from love_reply_api.infrastructure.admin_records import AdminSessionRecord, AdminUserRecord
from love_reply_api.infrastructure.database import get_session
from love_reply_api.infrastructure.identity_records import AuthSessionRecord, UserRecord

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


def get_sms_sender(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> SmsSender:
    override = request.app.state.sms_sender
    if override is not None:
        return cast(SmsSender, override)
    return RegistrySmsSender(
        session=session,
        settings=settings,
        sms_api_transport=cast(SmsApiTransport, request.app.state.sms_api_transport),
    )


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
        email_api_transport=cast(EmailApiTransport, request.app.state.email_api_transport),
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


def get_admin_platform_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AdminPlatformService:
    """装配用户运营、公告和网站配置服务。"""
    return AdminPlatformService(session)


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


def get_compliance_audit_service(
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ComplianceAuditService:
    return ComplianceAuditService(session=session, settings=settings)


async def get_admin_context(
    request: Request,
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
    admin, session = await service.authenticate_access(access_token=credentials.credentials)
    request.state.audit_actor_type = "ADMIN"
    request.state.audit_actor_id = admin.admin_id
    request.state.audit_admin_id = admin.admin_id
    request.state.audit_session_id = session.session_id
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


def get_commerce_service(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> CommerceService:
    gateway = RegistryPaymentGateway(
        session=session,
        settings=settings,
        epay_transport=cast(EpayTransport, request.app.state.epay_transport),
    )
    return CommerceService(
        session=session,
        gateway=gateway,
        referrals=ReferralService(session=session, settings=settings),
        audit=ComplianceAuditService(session=session, settings=settings),
    )


def get_commerce_admin_service(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> CommerceAdminService:
    gateway = RegistryPaymentGateway(
        session=session,
        settings=settings,
        epay_transport=cast(EpayTransport, request.app.state.epay_transport),
    )
    return CommerceAdminService(
        session=session,
        gateway=gateway,
        referrals=ReferralService(session=session, settings=settings),
    )


def get_referral_service(
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ReferralService:
    return ReferralService(session=session, settings=settings)


def get_support_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SupportService:
    return SupportService(session)


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
    request: Request,
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
    user = await session.get(UserRecord, claims.user_id)
    if user is None:
        raise ApiError(
            status_code=401,
            code="AUTH_USER_NOT_FOUND",
            message="The user account no longer exists.",
        )
    if user.status == "SUSPENDED":
        raise ApiError(
            status_code=403,
            code="USER_ACCOUNT_SUSPENDED",
            message="The user account is suspended.",
        )
    # 删除冷静期仍需允许用户访问账户接口以撤销删除；只有冻结状态立即阻断请求。
    if user.status not in {"ACTIVE", "DELETION_PENDING"}:
        raise ApiError(
            status_code=403,
            code="USER_ACCOUNT_UNAVAILABLE",
            message="The user account is not available.",
        )
    request.state.audit_actor_type = "USER"
    request.state.audit_actor_id = claims.user_id
    request.state.audit_user_id = claims.user_id
    request.state.audit_session_id = claims.session_id
    return AuthContext(
        user_id=claims.user_id,
        session_id=claims.session_id,
        device_id=client.device_id,
    )
