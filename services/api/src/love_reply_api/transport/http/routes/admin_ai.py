from typing import Annotated, TypeVar, cast

from fastapi import APIRouter, Depends, Header, Path, Query, Request, status

from love_reply_api.application.ai_admin import AiGatewayAdminService
from love_reply_api.application.errors import ApiError
from love_reply_api.schemas import ApiModel, SuccessEnvelope
from love_reply_api.transport.http.admin_ai_schemas import (
    AiEvaluationRunData,
    AiEvaluationRunRequest,
    AiEvaluationRunResponse,
    AiModelMappingData,
    AiModelMappingListData,
    AiModelMappingListResponse,
    AiModelMappingResponse,
    AiModelMappingWriteRequest,
    AiPromptData,
    AiPromptListData,
    AiPromptListResponse,
    AiPromptResponse,
    AiPromptWriteRequest,
    AiPublishRequest,
    AiRiskPolicyData,
    AiRiskPolicyListData,
    AiRiskPolicyListResponse,
    AiRiskPolicyResponse,
    AiRiskPolicyWriteRequest,
    AiRollbackRequest,
    AiRouteData,
    AiRouteListData,
    AiRouteListResponse,
    AiRouteResponse,
    AiRouteWriteRequest,
)
from love_reply_api.transport.http.dependencies import (
    AdminContext,
    get_ai_admin_service,
    require_admin_permission,
)

router = APIRouter(prefix="/admin/v1/ai", tags=["ADMIN_AI"])
Service = Annotated[AiGatewayAdminService, Depends(get_ai_admin_service)]
AdminRead = Annotated[AdminContext, Depends(require_admin_permission("AI_READ"))]
AdminWrite = Annotated[AdminContext, Depends(require_admin_permission("AI_WRITE"))]
AdminEvaluate = Annotated[AdminContext, Depends(require_admin_permission("AI_EVALUATE"))]
AdminPublish = Annotated[AdminContext, Depends(require_admin_permission("AI_PUBLISH"))]
AdminRollback = Annotated[AdminContext, Depends(require_admin_permission("AI_ROLLBACK"))]
ModelMappingId = Annotated[str, Path(alias="modelMappingId", min_length=8, max_length=128)]
RouteId = Annotated[str, Path(alias="routeId", min_length=8, max_length=128)]
PromptId = Annotated[str, Path(alias="promptId", min_length=8, max_length=128)]
EvaluationRunId = Annotated[str, Path(alias="evaluationRunId", min_length=8, max_length=128)]
RiskPolicyId = Annotated[str, Path(alias="riskPolicyId", min_length=8, max_length=128)]
DataT = TypeVar("DataT", bound=ApiModel)


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


def _data(model: type[DataT], record: object) -> DataT:
    return model.model_validate(record, from_attributes=True)


def _response(request: Request, model: type[DataT], record: object) -> SuccessEnvelope[DataT]:
    return SuccessEnvelope(data=_data(model, record), request_id=_request_id(request))


def _route_values(body: AiRouteWriteRequest) -> dict[str, object]:
    values: dict[str, object] = body.model_dump()
    values["targets"] = [target.model_dump(mode="json", by_alias=True) for target in body.targets]
    return values


@router.get(
    "/model-mappings",
    operation_id="listAdminAiModelMappings",
    response_model=AiModelMappingListResponse,
)
async def list_model_mappings(
    request: Request,
    context: AdminRead,
    service: Service,
    cursor: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> AiModelMappingListResponse:
    del context
    page = await service.list_model_mappings(cursor=cursor, limit=limit)
    return SuccessEnvelope(
        data=AiModelMappingListData(
            items=[_data(AiModelMappingData, item) for item in page.items],
            next_cursor=page.next_cursor,
            has_more=page.has_more,
        ),
        request_id=_request_id(request),
    )


@router.post(
    "/model-mappings",
    operation_id="createAdminAiModelMapping",
    response_model=AiModelMappingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_model_mapping(
    body: AiModelMappingWriteRequest,
    request: Request,
    context: AdminWrite,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    service: Service,
) -> AiModelMappingResponse:
    del idempotency_key
    return _response(
        request,
        AiModelMappingData,
        await service.create_model_mapping(admin_id=context.admin.admin_id, **body.model_dump()),
    )


@router.get(
    "/model-mappings/{modelMappingId}",
    operation_id="getAdminAiModelMapping",
    response_model=AiModelMappingResponse,
)
async def get_model_mapping(
    model_mapping_id: ModelMappingId, request: Request, context: AdminRead, service: Service
) -> AiModelMappingResponse:
    del context
    return _response(
        request,
        AiModelMappingData,
        await service.get_model_mapping(model_mapping_id=model_mapping_id),
    )


@router.patch(
    "/model-mappings/{modelMappingId}",
    operation_id="updateAdminAiModelMapping",
    response_model=AiModelMappingResponse,
)
async def update_model_mapping(
    model_mapping_id: ModelMappingId,
    body: AiModelMappingWriteRequest,
    request: Request,
    context: AdminWrite,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    if_match: Annotated[str, Header(alias="If-Match")],
    service: Service,
) -> AiModelMappingResponse:
    del idempotency_key
    return _response(
        request,
        AiModelMappingData,
        await service.update_model_mapping(
            model_mapping_id=model_mapping_id,
            expected_version=_expected_version(if_match),
            admin_id=context.admin.admin_id,
            **body.model_dump(),
        ),
    )


@router.get("/routes", operation_id="listAdminAiRoutes", response_model=AiRouteListResponse)
async def list_routes(
    request: Request,
    context: AdminRead,
    service: Service,
    cursor: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> AiRouteListResponse:
    del context
    page = await service.list_routes(cursor=cursor, limit=limit)
    return SuccessEnvelope(
        data=AiRouteListData(
            items=[_data(AiRouteData, item) for item in page.items],
            next_cursor=page.next_cursor,
            has_more=page.has_more,
        ),
        request_id=_request_id(request),
    )


@router.post(
    "/routes",
    operation_id="createAdminAiRoute",
    response_model=AiRouteResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_route(
    body: AiRouteWriteRequest,
    request: Request,
    context: AdminWrite,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    service: Service,
) -> AiRouteResponse:
    del idempotency_key
    return _response(
        request,
        AiRouteData,
        await service.create_route(admin_id=context.admin.admin_id, **_route_values(body)),
    )


@router.get("/routes/{routeId}", operation_id="getAdminAiRoute", response_model=AiRouteResponse)
async def get_route(
    route_id: RouteId, request: Request, context: AdminRead, service: Service
) -> AiRouteResponse:
    del context
    return _response(request, AiRouteData, await service.get_route(route_id=route_id))


@router.patch(
    "/routes/{routeId}", operation_id="updateAdminAiRoute", response_model=AiRouteResponse
)
async def update_route(
    route_id: RouteId,
    body: AiRouteWriteRequest,
    request: Request,
    context: AdminWrite,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    if_match: Annotated[str, Header(alias="If-Match")],
    service: Service,
) -> AiRouteResponse:
    del idempotency_key
    return _response(
        request,
        AiRouteData,
        await service.update_route(
            route_id=route_id,
            expected_version=_expected_version(if_match),
            admin_id=context.admin.admin_id,
            **_route_values(body),
        ),
    )


@router.post(
    "/routes/{routeId}/publish", operation_id="publishAdminAiRoute", response_model=AiRouteResponse
)
async def publish_route(
    route_id: RouteId,
    body: AiPublishRequest,
    request: Request,
    context: AdminPublish,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    if_match: Annotated[str, Header(alias="If-Match")],
    service: Service,
) -> AiRouteResponse:
    del idempotency_key
    return _response(
        request,
        AiRouteData,
        await service.publish_route(
            route_id=route_id,
            expected_version=_expected_version(if_match),
            admin_id=context.admin.admin_id,
            **body.model_dump(),
        ),
    )


@router.post(
    "/routes/{routeId}/rollback",
    operation_id="rollbackAdminAiRoute",
    response_model=AiRouteResponse,
)
async def rollback_route(
    route_id: RouteId,
    body: AiRollbackRequest,
    request: Request,
    context: AdminRollback,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    if_match: Annotated[str, Header(alias="If-Match")],
    service: Service,
) -> AiRouteResponse:
    del idempotency_key
    return _response(
        request,
        AiRouteData,
        await service.rollback_route(
            route_id=route_id,
            expected_version=_expected_version(if_match),
            admin_id=context.admin.admin_id,
            **body.model_dump(),
        ),
    )


@router.get("/prompts", operation_id="listAdminAiPrompts", response_model=AiPromptListResponse)
async def list_prompts(
    request: Request,
    context: AdminRead,
    service: Service,
    cursor: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> AiPromptListResponse:
    del context
    page = await service.list_prompts(cursor=cursor, limit=limit)
    return SuccessEnvelope(
        data=AiPromptListData(
            items=[_data(AiPromptData, item) for item in page.items],
            next_cursor=page.next_cursor,
            has_more=page.has_more,
        ),
        request_id=_request_id(request),
    )


@router.post(
    "/prompts",
    operation_id="createAdminAiPrompt",
    response_model=AiPromptResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_prompt(
    body: AiPromptWriteRequest,
    request: Request,
    context: AdminWrite,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    service: Service,
) -> AiPromptResponse:
    del idempotency_key
    return _response(
        request,
        AiPromptData,
        await service.create_prompt(admin_id=context.admin.admin_id, **body.model_dump()),
    )


@router.get("/prompts/{promptId}", operation_id="getAdminAiPrompt", response_model=AiPromptResponse)
async def get_prompt(
    prompt_id: PromptId, request: Request, context: AdminRead, service: Service
) -> AiPromptResponse:
    del context
    return _response(request, AiPromptData, await service.get_prompt(prompt_id=prompt_id))


@router.patch(
    "/prompts/{promptId}", operation_id="updateAdminAiPrompt", response_model=AiPromptResponse
)
async def update_prompt(
    prompt_id: PromptId,
    body: AiPromptWriteRequest,
    request: Request,
    context: AdminWrite,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    if_match: Annotated[str, Header(alias="If-Match")],
    service: Service,
) -> AiPromptResponse:
    del idempotency_key
    return _response(
        request,
        AiPromptData,
        await service.update_prompt(
            prompt_id=prompt_id,
            expected_version=_expected_version(if_match),
            admin_id=context.admin.admin_id,
            **body.model_dump(),
        ),
    )


@router.post(
    "/prompts/{promptId}/publish",
    operation_id="publishAdminAiPrompt",
    response_model=AiPromptResponse,
)
async def publish_prompt(
    prompt_id: PromptId,
    body: AiPublishRequest,
    request: Request,
    context: AdminPublish,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    if_match: Annotated[str, Header(alias="If-Match")],
    service: Service,
) -> AiPromptResponse:
    del idempotency_key
    return _response(
        request,
        AiPromptData,
        await service.publish_prompt(
            prompt_id=prompt_id,
            expected_version=_expected_version(if_match),
            admin_id=context.admin.admin_id,
            **body.model_dump(),
        ),
    )


@router.post(
    "/prompts/{promptId}/rollback",
    operation_id="rollbackAdminAiPrompt",
    response_model=AiPromptResponse,
)
async def rollback_prompt(
    prompt_id: PromptId,
    body: AiRollbackRequest,
    request: Request,
    context: AdminRollback,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    if_match: Annotated[str, Header(alias="If-Match")],
    service: Service,
) -> AiPromptResponse:
    del idempotency_key
    return _response(
        request,
        AiPromptData,
        await service.rollback_prompt(
            prompt_id=prompt_id,
            expected_version=_expected_version(if_match),
            admin_id=context.admin.admin_id,
            **body.model_dump(),
        ),
    )


@router.post(
    "/evaluation-runs",
    operation_id="createAdminAiEvaluationRun",
    response_model=AiEvaluationRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_evaluation_run(
    body: AiEvaluationRunRequest,
    request: Request,
    context: AdminEvaluate,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    service: Service,
) -> AiEvaluationRunResponse:
    del idempotency_key
    return _response(
        request,
        AiEvaluationRunData,
        await service.create_evaluation_run(admin_id=context.admin.admin_id, **body.model_dump()),
    )


@router.get(
    "/evaluation-runs/{evaluationRunId}",
    operation_id="getAdminAiEvaluationRun",
    response_model=AiEvaluationRunResponse,
)
async def get_evaluation_run(
    evaluation_run_id: EvaluationRunId,
    request: Request,
    context: AdminRead,
    service: Service,
) -> AiEvaluationRunResponse:
    del context
    return _response(
        request,
        AiEvaluationRunData,
        await service.get_evaluation_run(evaluation_run_id=evaluation_run_id),
    )


@router.get(
    "/risk-policies",
    operation_id="listAdminAiRiskPolicies",
    response_model=AiRiskPolicyListResponse,
)
async def list_risk_policies(
    request: Request,
    context: AdminRead,
    service: Service,
    cursor: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> AiRiskPolicyListResponse:
    del context
    page = await service.list_risk_policies(cursor=cursor, limit=limit)
    return SuccessEnvelope(
        data=AiRiskPolicyListData(
            items=[_data(AiRiskPolicyData, item) for item in page.items],
            next_cursor=page.next_cursor,
            has_more=page.has_more,
        ),
        request_id=_request_id(request),
    )


@router.post(
    "/risk-policies",
    operation_id="createAdminAiRiskPolicy",
    response_model=AiRiskPolicyResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_risk_policy(
    body: AiRiskPolicyWriteRequest,
    request: Request,
    context: AdminWrite,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    service: Service,
) -> AiRiskPolicyResponse:
    del idempotency_key
    return _response(
        request,
        AiRiskPolicyData,
        await service.create_risk_policy(admin_id=context.admin.admin_id, **body.model_dump()),
    )


@router.get(
    "/risk-policies/{riskPolicyId}",
    operation_id="getAdminAiRiskPolicy",
    response_model=AiRiskPolicyResponse,
)
async def get_risk_policy(
    risk_policy_id: RiskPolicyId, request: Request, context: AdminRead, service: Service
) -> AiRiskPolicyResponse:
    del context
    return _response(
        request, AiRiskPolicyData, await service.get_risk_policy(risk_policy_id=risk_policy_id)
    )


@router.patch(
    "/risk-policies/{riskPolicyId}",
    operation_id="updateAdminAiRiskPolicy",
    response_model=AiRiskPolicyResponse,
)
async def update_risk_policy(
    risk_policy_id: RiskPolicyId,
    body: AiRiskPolicyWriteRequest,
    request: Request,
    context: AdminWrite,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    if_match: Annotated[str, Header(alias="If-Match")],
    service: Service,
) -> AiRiskPolicyResponse:
    del idempotency_key
    return _response(
        request,
        AiRiskPolicyData,
        await service.update_risk_policy(
            risk_policy_id=risk_policy_id,
            expected_version=_expected_version(if_match),
            admin_id=context.admin.admin_id,
            **body.model_dump(),
        ),
    )


@router.post(
    "/risk-policies/{riskPolicyId}/publish",
    operation_id="publishAdminAiRiskPolicy",
    response_model=AiRiskPolicyResponse,
)
async def publish_risk_policy(
    risk_policy_id: RiskPolicyId,
    body: AiPublishRequest,
    request: Request,
    context: AdminPublish,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    if_match: Annotated[str, Header(alias="If-Match")],
    service: Service,
) -> AiRiskPolicyResponse:
    del idempotency_key
    return _response(
        request,
        AiRiskPolicyData,
        await service.publish_risk_policy(
            risk_policy_id=risk_policy_id,
            expected_version=_expected_version(if_match),
            admin_id=context.admin.admin_id,
            **body.model_dump(),
        ),
    )


@router.post(
    "/risk-policies/{riskPolicyId}/rollback",
    operation_id="rollbackAdminAiRiskPolicy",
    response_model=AiRiskPolicyResponse,
)
async def rollback_risk_policy(
    risk_policy_id: RiskPolicyId,
    body: AiRollbackRequest,
    request: Request,
    context: AdminRollback,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    if_match: Annotated[str, Header(alias="If-Match")],
    service: Service,
) -> AiRiskPolicyResponse:
    del idempotency_key
    return _response(
        request,
        AiRiskPolicyData,
        await service.rollback_risk_policy(
            risk_policy_id=risk_policy_id,
            expected_version=_expected_version(if_match),
            admin_id=context.admin.admin_id,
            **body.model_dump(),
        ),
    )
