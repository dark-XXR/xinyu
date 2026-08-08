from typing import Annotated, cast

from fastapi import APIRouter, Depends, Header, Request

from love_reply_api.application.auth import AuthService
from love_reply_api.schemas import SuccessEnvelope
from love_reply_api.transport.http.dependencies import (
    AuthContext,
    ClientContext,
    get_auth_context,
    get_auth_service,
    get_client_context,
)
from love_reply_api.transport.http.identity_schemas import (
    EmptyData,
    EmptyResponse,
    LoginData,
    LoginResponse,
    RefreshRequest,
    SmsChallengeData,
    SmsChallengeResponse,
    SmsLoginRequest,
    SmsSendRequest,
    TokenData,
    TokenResponse,
    UserData,
)

router = APIRouter(prefix="/v1/auth", tags=["AUTH"])


def _request_id(request: Request) -> str:
    return cast(str, request.state.request_id)


def _token_data(tokens: object) -> TokenData:
    return TokenData.model_validate(tokens, from_attributes=True)


@router.post("/sms/send", operation_id="sendSmsChallenge", response_model=SmsChallengeResponse)
async def send_sms_challenge(
    body: SmsSendRequest,
    request: Request,
    client: Annotated[ClientContext, Depends(get_client_context)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> SmsChallengeResponse:
    del client, idempotency_key
    result = await service.send_challenge(
        phone_e164=f"{body.country_code}{body.phone_number}",
        purpose=body.purpose,
    )
    return SuccessEnvelope(
        data=SmsChallengeData.model_validate(result, from_attributes=True),
        request_id=_request_id(request),
    )


@router.post("/sms/login", operation_id="loginWithSms", response_model=LoginResponse)
async def login_with_sms(
    body: SmsLoginRequest,
    request: Request,
    client: Annotated[ClientContext, Depends(get_client_context)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> LoginResponse:
    del idempotency_key
    result = await service.login(
        challenge_id=body.challenge_id,
        code=body.code,
        device_id=client.device_id,
        locale=client.accept_language,
    )
    user = result.user
    return SuccessEnvelope(
        data=LoginData(
            tokens=_token_data(result.tokens),
            user=UserData(
                user_id=user.user_id,
                status=user.status,
                locale=user.locale,
                time_zone=user.time_zone,
                resource_version=user.resource_version,
                created_at=user.created_at,
                updated_at=user.updated_at,
            ),
            pending_consents=[],
        ),
        request_id=_request_id(request),
    )


@router.post("/refresh", operation_id="refreshAccessToken", response_model=TokenResponse)
async def refresh_access_token(
    body: RefreshRequest,
    request: Request,
    client: Annotated[ClientContext, Depends(get_client_context)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenResponse:
    del idempotency_key
    tokens = await service.refresh(
        refresh_token=body.refresh_token,
        device_id=client.device_id,
    )
    return SuccessEnvelope(data=_token_data(tokens), request_id=_request_id(request))


@router.post("/logout", operation_id="logoutCurrentDevice", response_model=EmptyResponse)
async def logout_current_device(
    request: Request,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> EmptyResponse:
    del idempotency_key
    await service.logout(session_id=auth.session_id)
    return SuccessEnvelope(data=EmptyData(), request_id=_request_id(request))


@router.post("/logout-all", operation_id="logoutAllDevices", response_model=EmptyResponse)
async def logout_all_devices(
    request: Request,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> EmptyResponse:
    del idempotency_key
    await service.logout_all(user_id=auth.user_id)
    return SuccessEnvelope(data=EmptyData(), request_id=_request_id(request))
