from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError

from love_reply_api.application.auth import UnavailableEmailSender, UnavailableSmsSender
from love_reply_api.application.errors import ApiError
from love_reply_api.application.generation import UnavailableAiProvider
from love_reply_api.config import get_settings
from love_reply_api.schemas import HealthData, SuccessEnvelope
from love_reply_api.transport.http.errors import api_error_handler, validation_error_handler
from love_reply_api.transport.http.idempotency import IdempotencyMiddleware
from love_reply_api.transport.http.routes.app import router as app_router
from love_reply_api.transport.http.routes.auth import router as auth_router
from love_reply_api.transport.http.routes.billing import router as billing_router
from love_reply_api.transport.http.routes.candidates import router as candidate_router
from love_reply_api.transport.http.routes.generations import router as generation_router
from love_reply_api.transport.http.routes.me import router as me_router

settings = get_settings()

app = FastAPI(
    title="Love Reply Assistant API",
    version="1.0.0",
    debug=settings.app_debug,
    docs_url="/internal/docs" if settings.app_env != "production" else None,
    openapi_url="/internal/openapi.json" if settings.app_env != "production" else None,
)
app.state.sms_sender = UnavailableSmsSender()
app.state.email_sender = UnavailableEmailSender()
app.state.ai_provider = UnavailableAiProvider()
app.add_exception_handler(ApiError, api_error_handler)  # type: ignore[arg-type]
app.add_exception_handler(RequestValidationError, validation_error_handler)  # type: ignore[arg-type]
app.include_router(app_router)
app.include_router(auth_router)
app.include_router(me_router)
app.include_router(billing_router)
app.include_router(generation_router)
app.include_router(candidate_router)
app.add_middleware(IdempotencyMiddleware)


@app.middleware("http")
async def request_context(request: Request, call_next: object) -> object:
    request_id = request.headers.get("X-Request-Id") or f"req_{uuid4().hex}"
    request.state.request_id = request_id
    response = await call_next(request)  # type: ignore[operator]
    response.headers["X-Request-Id"] = request_id
    return response


@app.get("/health", operation_id="getHealth", response_model=SuccessEnvelope[HealthData])
async def get_health(request: Request) -> SuccessEnvelope[HealthData]:
    request_id = request.headers.get("X-Request-Id") or str(uuid4())
    return SuccessEnvelope(
        data=HealthData(status="ok", version=app.version),
        request_id=request_id,
    )
