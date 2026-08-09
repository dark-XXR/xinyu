from typing import Annotated, cast

from fastapi import APIRouter, Depends, Header, Request

from love_reply_api.application.admin_auth import (
    AdminAuthenticationResult,
    AdminAuthService,
    AdminRefreshResult,
)
from love_reply_api.infrastructure.admin_records import AdminSessionRecord, AdminUserRecord
from love_reply_api.schemas import SuccessEnvelope
from love_reply_api.transport.http.admin_schemas import (
    AdminAuthenticationData,
    AdminAuthenticationResponse,
    AdminEmptyData,
    AdminEmptyResponse,
    AdminIdentityData,
    AdminLoginData,
    AdminLoginRequest,
    AdminLoginResponse,
    AdminMeData,
    AdminMeResponse,
    AdminMfaChallengeData,
    AdminMfaVerifyRequest,
    AdminRefreshRequest,
    AdminSessionData,
    AdminTokenData,
    AdminTokenPairData,
    AdminTokenResponse,
)
from love_reply_api.transport.http.dependencies import (
    AdminClientContext,
    AdminContext,
    get_admin_auth_service,
    get_admin_client_context,
    get_admin_context,
)

router = APIRouter(prefix="/admin/v1", tags=["ADMIN_RBAC"])


def _request_id(request: Request) -> str:
    return cast(str, request.state.request_id)


def _admin_data(admin: AdminUserRecord) -> AdminIdentityData:
    return AdminIdentityData(
        admin_id=admin.admin_id,
        login_name=admin.login_name_normalized,
        display_name=admin.display_name,
        account_status=admin.account_status,
        mfa_status=admin.mfa_status,
        mfa_methods=["TOTP"],
        roles=admin.roles,
        permissions=admin.permissions,
        last_login_at=admin.last_login_at,
        resource_version=admin.resource_version,
        created_at=admin.created_at,
        updated_at=admin.updated_at,
    )


def _session_data(session: AdminSessionRecord) -> AdminSessionData:
    return AdminSessionData.model_validate(session, from_attributes=True)


def _auth_data(result: AdminAuthenticationResult) -> AdminAuthenticationData:
    return AdminAuthenticationData(
        tokens=AdminTokenPairData.model_validate(result.tokens, from_attributes=True),
        admin=_admin_data(result.admin),
        session=_session_data(result.session),
    )


def _refresh_data(result: AdminRefreshResult) -> AdminTokenData:
    return AdminTokenData(
        tokens=AdminTokenPairData.model_validate(result.tokens, from_attributes=True),
        session=_session_data(result.session),
    )


@router.post(
    "/auth/login",
    operation_id="loginAdmin",
    response_model=AdminLoginResponse,
)
async def login_admin(
    body: AdminLoginRequest,
    request: Request,
    client: Annotated[AdminClientContext, Depends(get_admin_client_context)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    service: Annotated[AdminAuthService, Depends(get_admin_auth_service)],
) -> AdminLoginResponse:
    del client, idempotency_key
    result = await service.login(login_name=body.login_name, password=body.password)
    return SuccessEnvelope(
        data=AdminLoginData(
            mfa_required=result.mfa_required,
            mfa_challenge=AdminMfaChallengeData.model_validate(
                result.mfa_challenge, from_attributes=True
            ),
        ),
        request_id=_request_id(request),
    )


@router.post(
    "/auth/mfa/verify",
    operation_id="verifyAdminMfa",
    response_model=AdminAuthenticationResponse,
)
async def verify_admin_mfa(
    body: AdminMfaVerifyRequest,
    request: Request,
    client: Annotated[AdminClientContext, Depends(get_admin_client_context)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    service: Annotated[AdminAuthService, Depends(get_admin_auth_service)],
) -> AdminAuthenticationResponse:
    del client, idempotency_key
    result = await service.verify_mfa(
        challenge_id=body.challenge_id,
        method=body.method,
        code=body.code,
    )
    return SuccessEnvelope(data=_auth_data(result), request_id=_request_id(request))


@router.post(
    "/auth/refresh",
    operation_id="refreshAdminAccessToken",
    response_model=AdminTokenResponse,
)
async def refresh_admin_access_token(
    body: AdminRefreshRequest,
    request: Request,
    client: Annotated[AdminClientContext, Depends(get_admin_client_context)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    service: Annotated[AdminAuthService, Depends(get_admin_auth_service)],
) -> AdminTokenResponse:
    del client, idempotency_key
    result = await service.refresh(refresh_token=body.refresh_token)
    return SuccessEnvelope(data=_refresh_data(result), request_id=_request_id(request))


@router.post(
    "/auth/logout",
    operation_id="logoutAdmin",
    response_model=AdminEmptyResponse,
)
async def logout_admin(
    request: Request,
    context: Annotated[AdminContext, Depends(get_admin_context)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    service: Annotated[AdminAuthService, Depends(get_admin_auth_service)],
) -> AdminEmptyResponse:
    del idempotency_key
    await service.logout(session_id=context.session.session_id)
    return SuccessEnvelope(data=AdminEmptyData(), request_id=_request_id(request))


@router.get("/me", operation_id="getCurrentAdmin", response_model=AdminMeResponse)
async def get_current_admin(
    request: Request,
    context: Annotated[AdminContext, Depends(get_admin_context)],
) -> AdminMeResponse:
    return SuccessEnvelope(
        data=AdminMeData(
            admin=_admin_data(context.admin),
            session=_session_data(context.session),
        ),
        request_id=_request_id(request),
    )
