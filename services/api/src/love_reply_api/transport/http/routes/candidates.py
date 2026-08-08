from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Header, Path, Request

from love_reply_api.application.generation import AiProvider, GenerationService
from love_reply_api.schemas import SuccessEnvelope
from love_reply_api.transport.http.dependencies import (
    AuthContext,
    get_ai_provider,
    get_auth_context,
    get_generation_service,
)
from love_reply_api.transport.http.generation_schemas import (
    AppealData,
    AppealRequest,
    AppealResponse,
    CandidateActionData,
    CandidateActionRequest,
    CandidateActionResponse,
    GenerationResponse,
    RefineCandidateRequest,
)
from love_reply_api.transport.http.routes.generations import _process_generation, _snapshot

router = APIRouter(prefix="/v1")


@router.post(
    "/candidates/{candidateId}/refine",
    operation_id="refineCandidate",
    response_model=GenerationResponse,
    status_code=202,
    tags=["CANDIDATE"],
)
async def refine_candidate(
    body: RefineCandidateRequest,
    candidate_id: Annotated[str, Path(alias="candidateId")],
    request: Request,
    background_tasks: BackgroundTasks,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    service: Annotated[GenerationService, Depends(get_generation_service)],
    provider: Annotated[AiProvider, Depends(get_ai_provider)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
) -> GenerationResponse:
    del idempotency_key
    task = await service.refine_candidate(
        user_id=auth.user_id,
        candidate_id=candidate_id,
        quote_id=body.quote_id,
        client_request_id=body.client_request_id,
        instruction_code=body.instruction_code,
        custom_instruction=body.custom_instruction,
    )
    background_tasks.add_task(
        _process_generation,
        service,
        generation_id=task.generation_id,
        provider=provider,
    )
    return SuccessEnvelope(
        data=await _snapshot(service, user_id=auth.user_id, generation_id=task.generation_id),
        request_id=request.state.request_id,
    )


@router.post(
    "/candidates/{candidateId}/actions",
    operation_id="recordCandidateAction",
    response_model=CandidateActionResponse,
    tags=["CANDIDATE"],
)
async def record_candidate_action(
    body: CandidateActionRequest,
    candidate_id: Annotated[str, Path(alias="candidateId")],
    request: Request,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    service: Annotated[GenerationService, Depends(get_generation_service)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
) -> CandidateActionResponse:
    del idempotency_key
    action = await service.record_candidate_action(
        user_id=auth.user_id,
        candidate_id=candidate_id,
        client_action_id=body.client_action_id,
        action_type=body.action_type,
        outcome_code=body.outcome_code,
        occurred_at=body.occurred_at,
    )
    return SuccessEnvelope(
        data=CandidateActionData.model_validate(action, from_attributes=True),
        request_id=request.state.request_id,
    )


@router.post(
    "/risk-events/{riskEventId}/appeals",
    operation_id="appealRiskEvent",
    response_model=AppealResponse,
    status_code=202,
    tags=["RISK"],
)
async def appeal_risk_event(
    body: AppealRequest,
    risk_event_id: Annotated[str, Path(alias="riskEventId")],
    request: Request,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    service: Annotated[GenerationService, Depends(get_generation_service)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
) -> AppealResponse:
    del idempotency_key
    appeal = await service.appeal_risk_event(
        user_id=auth.user_id,
        risk_event_id=risk_event_id,
        reason_code=body.reason_code,
        comment=body.comment,
    )
    return SuccessEnvelope(
        data=AppealData.model_validate(appeal, from_attributes=True),
        request_id=request.state.request_id,
    )
