import json
import logging
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Header, Path, Request
from fastapi.responses import StreamingResponse

from love_reply_api.application.errors import ApiError
from love_reply_api.application.generation import AiProvider, GenerationService
from love_reply_api.schemas import SuccessEnvelope
from love_reply_api.transport.http.dependencies import (
    AuthContext,
    get_ai_provider,
    get_auth_context,
    get_generation_service,
)
from love_reply_api.transport.http.generation_schemas import (
    CandidateData,
    CreateGenerationRequest,
    GenerationAnalysisData,
    GenerationContextData,
    GenerationInputData,
    GenerationQuoteData,
    GenerationQuoteRequest,
    GenerationQuoteResponse,
    GenerationResponse,
    GenerationSnapshotData,
    GenerationUsageData,
    ModelQuoteOptionData,
    RegenerateRequest,
)

router = APIRouter(prefix="/v1/generations")
logger = logging.getLogger(__name__)


def _input_data(body: GenerationInputData) -> dict[str, object]:
    return body.model_dump(by_alias=True)


def _context_data(body: GenerationContextData) -> dict[str, object]:
    return body.model_dump(by_alias=True)


async def _snapshot(
    service: GenerationService,
    *,
    user_id: str,
    generation_id: str,
) -> GenerationSnapshotData:
    task = await service.get_task(user_id=user_id, generation_id=generation_id)
    candidates = await service.get_candidates(generation_id)
    usage = await service.get_usage(generation_id)
    return GenerationSnapshotData(
        generation_id=task.generation_id,
        parent_generation_id=task.parent_generation_id,
        status=task.status,
        analysis=GenerationAnalysisData.model_validate(task.analysis_data)
        if task.analysis_data is not None
        else None,
        candidates=[
            CandidateData.model_validate(item, from_attributes=True) for item in candidates
        ],
        usage=GenerationUsageData.model_validate(usage, from_attributes=True)
        if usage is not None
        else None,
        failure_code=task.failure_code,
        risk_event_id=task.risk_event_id,
        resource_version=task.resource_version,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


async def _process_generation(
    service: GenerationService,
    *,
    generation_id: str,
    provider: AiProvider,
) -> None:
    try:
        await service.process(generation_id=generation_id, provider=provider)
    except Exception:
        # GenerationService persists the failure and releases the reservation before re-raising.
        logger.exception(
            "generation background processing failed",
            extra={"generation_id": generation_id},
        )
        return


@router.post(
    "/quote",
    operation_id="quoteGeneration",
    response_model=GenerationQuoteResponse,
    tags=["GENERATION"],
)
async def quote_generation(
    body: GenerationQuoteRequest,
    request: Request,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    service: Annotated[GenerationService, Depends(get_generation_service)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
) -> GenerationQuoteResponse:
    del idempotency_key
    result = await service.quote(
        user_id=auth.user_id,
        input_data=_input_data(body.input),
        context_data=_context_data(body.context),
        requested_model_id=body.requested_model_id,
    )
    record = result.record
    options = [
        ModelQuoteOptionData(
            model_id=model_id,
            energy_amount=record.estimated_energy,
            available=model_id in result.available_model_ids,
            recommended=model_id == record.model_id,
            unavailable_reason_code=(
                None if model_id in result.available_model_ids else "MODEL_NOT_ENTITLED"
            ),
        )
        for model_id in result.available_model_ids
    ]
    data = GenerationQuoteData(
        quote_id=record.quote_id,
        model_options=options,
        selected_model_id=record.model_id,
        estimated_energy_amount=record.estimated_energy,
        charged_from=record.charged_from,
        entitlement_version=record.entitlement_version,
        expires_at=record.expires_at,
    )
    return SuccessEnvelope(data=data, request_id=request.state.request_id)


@router.post(
    "",
    operation_id="createGeneration",
    response_model=GenerationResponse,
    status_code=202,
    tags=["GENERATION"],
)
async def create_generation(
    body: CreateGenerationRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    service: Annotated[GenerationService, Depends(get_generation_service)],
    provider: Annotated[AiProvider, Depends(get_ai_provider)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
) -> GenerationResponse:
    del idempotency_key
    task = await service.create(
        user_id=auth.user_id,
        quote_id=body.quote_id,
        client_request_id=body.client_request_id,
        input_data=_input_data(body.input),
        context_data=_context_data(body.context),
        model_id=body.model_id,
        save_to_history=body.save_to_history,
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


@router.get(
    "/{generationId}",
    operation_id="getGeneration",
    response_model=GenerationResponse,
    tags=["GENERATION"],
)
async def get_generation(
    generation_id: Annotated[str, Path(alias="generationId")],
    request: Request,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    service: Annotated[GenerationService, Depends(get_generation_service)],
) -> GenerationResponse:
    return SuccessEnvelope(
        data=await _snapshot(service, user_id=auth.user_id, generation_id=generation_id),
        request_id=request.state.request_id,
    )


@router.post(
    "/{generationId}/cancel",
    operation_id="cancelGeneration",
    response_model=GenerationResponse,
    tags=["GENERATION"],
)
async def cancel_generation(
    generation_id: Annotated[str, Path(alias="generationId")],
    request: Request,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    service: Annotated[GenerationService, Depends(get_generation_service)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
) -> GenerationResponse:
    del idempotency_key
    task = await service.cancel(user_id=auth.user_id, generation_id=generation_id)
    return SuccessEnvelope(
        data=await _snapshot(service, user_id=auth.user_id, generation_id=task.generation_id),
        request_id=request.state.request_id,
    )


@router.post(
    "/{generationId}/regenerate",
    operation_id="regenerateGeneration",
    response_model=GenerationResponse,
    status_code=202,
    tags=["GENERATION"],
)
async def regenerate_generation(
    body: RegenerateRequest,
    generation_id: Annotated[str, Path(alias="generationId")],
    request: Request,
    background_tasks: BackgroundTasks,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    service: Annotated[GenerationService, Depends(get_generation_service)],
    provider: Annotated[AiProvider, Depends(get_ai_provider)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
) -> GenerationResponse:
    del idempotency_key
    task = await service.regenerate(
        user_id=auth.user_id,
        parent_generation_id=generation_id,
        quote_id=body.quote_id,
        client_request_id=body.client_request_id,
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


@router.get("/{generationId}/events", operation_id="streamGenerationEvents", tags=["GENERATION"])
async def stream_generation_events(
    generation_id: Annotated[str, Path(alias="generationId")],
    request: Request,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    service: Annotated[GenerationService, Depends(get_generation_service)],
    last_event_id: Annotated[str | None, Header(alias="Last-Event-ID")] = None,
) -> StreamingResponse:
    retained_events = await service.get_events(
        user_id=auth.user_id,
        generation_id=generation_id,
        after_sequence=0,
    )
    after_sequence = 0
    if last_event_id is not None:
        resumed_event = next(
            (event for event in retained_events if event.event_id == last_event_id),
            None,
        )
        if resumed_event is None:
            raise ApiError(
                status_code=410,
                code="GENERATION_EVENT_CURSOR_EXPIRED",
                message="The requested generation event is no longer retained.",
            )
        after_sequence = resumed_event.sequence
    events = [event for event in retained_events if event.sequence > after_sequence]

    async def event_stream() -> AsyncIterator[str]:
        for event in events:
            payload = {
                "schemaVersion": "1.0",
                "eventId": event.event_id,
                "eventType": event.event_type,
                "occurredAt": event.occurred_at.isoformat(),
                "generationId": event.generation_id,
                "sequence": event.sequence,
                "payload": event.payload,
            }
            serialized = json.dumps(payload, separators=(",", ":"))
            yield (
                f"id: {event.event_id}\n"
                f"event: {event.event_type}\n"
                f"data: {serialized}\n\n"
            )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )
