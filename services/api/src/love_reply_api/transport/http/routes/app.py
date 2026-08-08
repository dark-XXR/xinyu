from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from love_reply_api.application.runtime_config import RuntimeConfigService
from love_reply_api.infrastructure.database import get_session
from love_reply_api.schemas import SuccessEnvelope
from love_reply_api.transport.http.dependencies import ClientContext, get_client_context
from love_reply_api.transport.http.operations_schemas import AppBootstrapData, AppBootstrapResponse

router = APIRouter(prefix="/v1/app", tags=["APP_CONFIG"])


@router.get(
    "/bootstrap",
    operation_id="getAppBootstrap",
    response_model=AppBootstrapResponse,
)
async def get_app_bootstrap(
    request: Request,
    client: Annotated[ClientContext, Depends(get_client_context)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AppBootstrapResponse:
    del client
    config = await RuntimeConfigService(session).get_published()
    return SuccessEnvelope(
        data=AppBootstrapData.model_validate(config.model_dump()),
        request_id=request.state.request_id,
    )
