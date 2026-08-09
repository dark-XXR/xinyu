from typing import Annotated, cast

from fastapi import APIRouter, Depends, Header, Path, Query, Request, status

from love_reply_api.application.errors import ApiError
from love_reply_api.application.providers import ProviderService
from love_reply_api.schemas import SuccessEnvelope
from love_reply_api.transport.http.admin_provider_schemas import (
    CredentialRotationData,
    CredentialRotationResponse,
    HealthCheckRequest,
    ProviderData,
    ProviderHealthCheckData,
    ProviderHealthCheckResponse,
    ProviderListData,
    ProviderListResponse,
    ProviderResponse,
    ProviderWriteRequest,
    PublishProviderRequest,
    RollbackProviderRequest,
    RotateCredentialsRequest,
)
from love_reply_api.transport.http.dependencies import (
    AdminContext,
    get_provider_service,
    require_admin_permission,
)

router = APIRouter(prefix="/admin/v1/providers", tags=["ADMIN_PROVIDER"])


def _request_id(request: Request) -> str:
    return cast(str, request.state.request_id)


def _expected_version(if_match: str) -> int:
    try:
        value = int(if_match)
    except ValueError as exc:
        raise ApiError(
            status_code=400,
            code="INVALID_IF_MATCH",
            message="If-Match must contain a resource version.",
        ) from exc
    if value < 1:
        raise ApiError(
            status_code=400,
            code="INVALID_IF_MATCH",
            message="If-Match must contain a positive resource version.",
        )
    return value


@router.get("", operation_id="listAdminProviders", response_model=ProviderListResponse)
async def list_admin_providers(
    request: Request,
    context: Annotated[
        AdminContext, Depends(require_admin_permission("PROVIDER_READ"))
    ],
    service: Annotated[ProviderService, Depends(get_provider_service)],
    cursor: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ProviderListResponse:
    del context
    result = await service.list_providers(cursor=cursor, limit=limit)
    return SuccessEnvelope(
        data=ProviderListData(
            items=[
                ProviderData.model_validate(item, from_attributes=True)
                for item in result.items
            ],
            next_cursor=result.next_cursor,
            has_more=result.has_more,
        ),
        request_id=_request_id(request),
    )


@router.post(
    "",
    operation_id="createAdminProvider",
    response_model=ProviderResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_admin_provider(
    body: ProviderWriteRequest,
    request: Request,
    context: Annotated[
        AdminContext, Depends(require_admin_permission("PROVIDER_WRITE"))
    ],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    service: Annotated[ProviderService, Depends(get_provider_service)],
) -> ProviderResponse:
    del idempotency_key
    result = await service.create(
        admin_id=context.admin.admin_id,
        **body.model_dump(),
    )
    return SuccessEnvelope(
        data=ProviderData.model_validate(result, from_attributes=True),
        request_id=_request_id(request),
    )


@router.get(
    "/{providerId}",
    operation_id="getAdminProvider",
    response_model=ProviderResponse,
)
async def get_admin_provider(
    provider_id: Annotated[
        str, Path(alias="providerId", min_length=8, max_length=128)
    ],
    request: Request,
    context: Annotated[
        AdminContext, Depends(require_admin_permission("PROVIDER_READ"))
    ],
    service: Annotated[ProviderService, Depends(get_provider_service)],
) -> ProviderResponse:
    del context
    result = await service.get(provider_id=provider_id)
    return SuccessEnvelope(
        data=ProviderData.model_validate(result, from_attributes=True),
        request_id=_request_id(request),
    )


@router.patch(
    "/{providerId}",
    operation_id="updateAdminProvider",
    response_model=ProviderResponse,
)
async def update_admin_provider(
    provider_id: Annotated[
        str, Path(alias="providerId", min_length=8, max_length=128)
    ],
    body: ProviderWriteRequest,
    request: Request,
    context: Annotated[
        AdminContext, Depends(require_admin_permission("PROVIDER_WRITE"))
    ],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    if_match: Annotated[str, Header(alias="If-Match")],
    service: Annotated[ProviderService, Depends(get_provider_service)],
) -> ProviderResponse:
    del idempotency_key
    result = await service.update(
        provider_id=provider_id,
        expected_version=_expected_version(if_match),
        admin_id=context.admin.admin_id,
        **body.model_dump(),
    )
    return SuccessEnvelope(
        data=ProviderData.model_validate(result, from_attributes=True),
        request_id=_request_id(request),
    )


@router.post(
    "/{providerId}/credentials",
    operation_id="rotateAdminProviderCredentials",
    response_model=CredentialRotationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def rotate_admin_provider_credentials(
    provider_id: Annotated[
        str, Path(alias="providerId", min_length=8, max_length=128)
    ],
    body: RotateCredentialsRequest,
    request: Request,
    context: Annotated[
        AdminContext, Depends(require_admin_permission("PROVIDER_SECRET_ROTATE"))
    ],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    if_match: Annotated[str, Header(alias="If-Match")],
    service: Annotated[ProviderService, Depends(get_provider_service)],
) -> CredentialRotationResponse:
    del idempotency_key
    result = await service.rotate_credentials(
        provider_id=provider_id,
        expected_version=_expected_version(if_match),
        admin_id=context.admin.admin_id,
        secrets={item.name: item.value for item in body.secrets},
        audit_reason=body.audit_reason,
    )
    return SuccessEnvelope(
        data=CredentialRotationData.model_validate(result, from_attributes=True),
        request_id=_request_id(request),
    )


@router.post(
    "/{providerId}/health-checks",
    operation_id="checkAdminProviderHealth",
    response_model=ProviderHealthCheckResponse,
)
async def check_admin_provider_health(
    provider_id: Annotated[
        str, Path(alias="providerId", min_length=8, max_length=128)
    ],
    body: HealthCheckRequest,
    request: Request,
    context: Annotated[
        AdminContext, Depends(require_admin_permission("PROVIDER_HEALTH_CHECK"))
    ],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    service: Annotated[ProviderService, Depends(get_provider_service)],
) -> ProviderHealthCheckResponse:
    del idempotency_key
    result = await service.health_check(
        provider_id=provider_id,
        admin_id=context.admin.admin_id,
        administrator_test_destination=body.administrator_test_destination,
        audit_reason=body.audit_reason,
    )
    return SuccessEnvelope(
        data=ProviderHealthCheckData.model_validate(result, from_attributes=True),
        request_id=_request_id(request),
    )


@router.post(
    "/{providerId}/publish",
    operation_id="publishAdminProvider",
    response_model=ProviderResponse,
)
async def publish_admin_provider(
    provider_id: Annotated[
        str, Path(alias="providerId", min_length=8, max_length=128)
    ],
    body: PublishProviderRequest,
    request: Request,
    context: Annotated[
        AdminContext, Depends(require_admin_permission("PROVIDER_PUBLISH"))
    ],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    if_match: Annotated[str, Header(alias="If-Match")],
    service: Annotated[ProviderService, Depends(get_provider_service)],
) -> ProviderResponse:
    del idempotency_key
    result = await service.publish(
        provider_id=provider_id,
        expected_version=_expected_version(if_match),
        admin_id=context.admin.admin_id,
        rollout_percentage=body.rollout_percentage,
        effective_at=body.effective_at,
        audit_reason=body.audit_reason,
    )
    return SuccessEnvelope(
        data=ProviderData.model_validate(result, from_attributes=True),
        request_id=_request_id(request),
    )


@router.post(
    "/{providerId}/rollback",
    operation_id="rollbackAdminProvider",
    response_model=ProviderResponse,
)
async def rollback_admin_provider(
    provider_id: Annotated[
        str, Path(alias="providerId", min_length=8, max_length=128)
    ],
    body: RollbackProviderRequest,
    request: Request,
    context: Annotated[
        AdminContext, Depends(require_admin_permission("PROVIDER_ROLLBACK"))
    ],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    if_match: Annotated[str, Header(alias="If-Match")],
    service: Annotated[ProviderService, Depends(get_provider_service)],
) -> ProviderResponse:
    del idempotency_key
    result = await service.rollback(
        provider_id=provider_id,
        expected_version=_expected_version(if_match),
        admin_id=context.admin.admin_id,
        target_resource_version=body.target_resource_version,
        audit_reason=body.audit_reason,
    )
    return SuccessEnvelope(
        data=ProviderData.model_validate(result, from_attributes=True),
        request_id=_request_id(request),
    )
