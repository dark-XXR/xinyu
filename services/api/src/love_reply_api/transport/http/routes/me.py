from typing import Annotated

from fastapi import APIRouter, Depends, Header, Path, Request

from love_reply_api.application.errors import ApiError
from love_reply_api.application.identity import IdentityService
from love_reply_api.domain.identity import ConsentType
from love_reply_api.infrastructure.identity_records import (
    ConsentRecord,
    DataRequestRecord,
    UserProfileRecord,
    UserRecord,
)
from love_reply_api.schemas import SuccessEnvelope
from love_reply_api.transport.http.dependencies import (
    AuthContext,
    get_auth_context,
    get_identity_service,
)
from love_reply_api.transport.http.identity_schemas import (
    ConsentData,
    ConsentListData,
    ConsentListResponse,
    ConsentResponse,
    DataRequestData,
    DataRequestResponse,
    DeletionRequest,
    DeletionStatusData,
    DeletionStatusResponse,
    DeviceData,
    DeviceListData,
    DeviceListResponse,
    EmptyData,
    EmptyResponse,
    UpdateConsentRequest,
    UpdateUserRequest,
    UserData,
    UserResponse,
)

router = APIRouter(prefix="/v1/me")


def _user_data(user: UserRecord, profile: UserProfileRecord) -> UserData:
    return UserData(
        user_id=user.user_id,
        status=user.status,
        nickname=profile.nickname,
        avatar_url=profile.avatar_url,
        locale=user.locale,
        time_zone=user.time_zone,
        resource_version=user.resource_version,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


def _consent_data(record: ConsentRecord) -> ConsentData:
    return ConsentData.model_validate(record, from_attributes=True)


def _data_request_data(record: DataRequestRecord) -> DataRequestData:
    return DataRequestData.model_validate(record, from_attributes=True)


def _deletion_data(record: DataRequestRecord) -> DeletionStatusData:
    if record.cooling_off_ends_at is None:
        raise ApiError(
            status_code=500,
            code="DELETION_STATE_INVALID",
            message="Deletion request is missing its cooling-off deadline.",
        )
    return DeletionStatusData(
        **_data_request_data(record).model_dump(),
        cooling_off_ends_at=record.cooling_off_ends_at,
        estimated_completion_at=None,
        blockers=[],
    )


@router.get("", operation_id="getCurrentUser", response_model=UserResponse, tags=["USER"])
async def get_current_user(
    request: Request,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    service: Annotated[IdentityService, Depends(get_identity_service)],
) -> UserResponse:
    user, profile = await service.get_user(auth.user_id)
    return SuccessEnvelope(data=_user_data(user, profile), request_id=request.state.request_id)


@router.patch("", operation_id="updateCurrentUser", response_model=UserResponse, tags=["USER"])
async def update_current_user(
    body: UpdateUserRequest,
    request: Request,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    if_match: Annotated[str, Header(alias="If-Match")],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    service: Annotated[IdentityService, Depends(get_identity_service)],
) -> UserResponse:
    del idempotency_key
    try:
        expected_version = int(if_match)
    except ValueError as exc:
        raise ApiError(
            status_code=400,
            code="INVALID_RESOURCE_VERSION",
            message="If-Match must contain a decimal resource version.",
        ) from exc
    changes = body.model_dump(exclude_unset=True)
    if not changes:
        raise ApiError(
            status_code=400,
            code="EMPTY_UPDATE",
            message="At least one account field must be provided.",
        )
    user, profile = await service.update_user(
        user_id=auth.user_id,
        expected_version=expected_version,
        changes=changes,
    )
    return SuccessEnvelope(data=_user_data(user, profile), request_id=request.state.request_id)


@router.get(
    "/devices",
    operation_id="listDevices",
    response_model=DeviceListResponse,
    tags=["USER"],
)
async def list_devices(
    request: Request,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    service: Annotated[IdentityService, Depends(get_identity_service)],
) -> DeviceListResponse:
    records = await service.list_devices(auth.user_id)
    items = [
        DeviceData(
            device_id=record.device_id,
            platform=record.platform,
            model=record.model,
            current=record.device_id == auth.device_id,
            last_seen_at=record.last_seen_at,
            created_at=record.created_at,
        )
        for record in records
    ]
    return SuccessEnvelope(data=DeviceListData(items=items), request_id=request.state.request_id)


@router.delete(
    "/devices/{deviceId}",
    operation_id="revokeDevice",
    response_model=EmptyResponse,
    tags=["USER"],
)
async def revoke_device(
    device_id: Annotated[str, Path(alias="deviceId")],
    request: Request,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    service: Annotated[IdentityService, Depends(get_identity_service)],
) -> EmptyResponse:
    del idempotency_key
    await service.revoke_device(user_id=auth.user_id, device_id=device_id)
    return SuccessEnvelope(data=EmptyData(), request_id=request.state.request_id)


@router.get(
    "/consents",
    operation_id="listMyConsents",
    response_model=ConsentListResponse,
    tags=["CONSENT"],
)
async def list_my_consents(
    request: Request,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    service: Annotated[IdentityService, Depends(get_identity_service)],
) -> ConsentListResponse:
    records = await service.list_consents(auth.user_id)
    return SuccessEnvelope(
        data=ConsentListData(items=[_consent_data(record) for record in records]),
        request_id=request.state.request_id,
    )


@router.put(
    "/consents/{consentType}",
    operation_id="updateConsent",
    response_model=ConsentResponse,
    tags=["CONSENT"],
)
async def update_consent(
    consent_type: Annotated[ConsentType, Path(alias="consentType")],
    body: UpdateConsentRequest,
    request: Request,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    service: Annotated[IdentityService, Depends(get_identity_service)],
) -> ConsentResponse:
    del idempotency_key
    record = await service.update_consent(
        user_id=auth.user_id,
        consent_type=consent_type,
        document_version=body.document_version,
        granted=body.granted,
    )
    return SuccessEnvelope(data=_consent_data(record), request_id=request.state.request_id)


@router.post(
    "/data-export",
    operation_id="requestDataExport",
    response_model=DataRequestResponse,
    status_code=202,
    tags=["DATA_GOVERNANCE"],
)
async def request_data_export(
    request: Request,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    service: Annotated[IdentityService, Depends(get_identity_service)],
) -> DataRequestResponse:
    del idempotency_key
    record = await service.request_export(auth.user_id)
    return SuccessEnvelope(data=_data_request_data(record), request_id=request.state.request_id)


@router.get(
    "/data-requests/{requestId}",
    operation_id="getDataRequest",
    response_model=DataRequestResponse,
    tags=["DATA_GOVERNANCE"],
)
async def get_data_request(
    request_id: Annotated[str, Path(alias="requestId")],
    request: Request,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    service: Annotated[IdentityService, Depends(get_identity_service)],
) -> DataRequestResponse:
    record = await service.get_data_request(user_id=auth.user_id, request_id=request_id)
    return SuccessEnvelope(data=_data_request_data(record), request_id=request.state.request_id)


@router.get(
    "/deletion",
    operation_id="getDeletionStatus",
    response_model=DeletionStatusResponse,
    tags=["DATA_GOVERNANCE"],
)
async def get_deletion_status(
    request: Request,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    service: Annotated[IdentityService, Depends(get_identity_service)],
) -> DeletionStatusResponse:
    record = await service.get_deletion(auth.user_id)
    return SuccessEnvelope(data=_deletion_data(record), request_id=request.state.request_id)


@router.post(
    "/deletion",
    operation_id="requestAccountDeletion",
    response_model=DeletionStatusResponse,
    status_code=202,
    tags=["DATA_GOVERNANCE"],
)
async def request_account_deletion(
    body: DeletionRequest,
    request: Request,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    service: Annotated[IdentityService, Depends(get_identity_service)],
) -> DeletionStatusResponse:
    del idempotency_key
    record = await service.request_deletion(user_id=auth.user_id, reason_code=body.reason_code)
    return SuccessEnvelope(data=_deletion_data(record), request_id=request.state.request_id)


@router.delete(
    "/deletion",
    operation_id="cancelAccountDeletion",
    response_model=EmptyResponse,
    tags=["DATA_GOVERNANCE"],
)
async def cancel_account_deletion(
    request: Request,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    service: Annotated[IdentityService, Depends(get_identity_service)],
) -> EmptyResponse:
    del idempotency_key
    await service.cancel_deletion(auth.user_id)
    return SuccessEnvelope(data=EmptyData(), request_id=request.state.request_id)
