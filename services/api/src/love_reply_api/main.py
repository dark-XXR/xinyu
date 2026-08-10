"""FastAPI 应用入口，负责装配路由、异常处理、请求追踪和合规访问日志。"""

import json
import logging
from datetime import UTC, datetime
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError

from love_reply_api.application.ai_gateway import AiHttpTransport
from love_reply_api.application.audit import ComplianceAuditService
from love_reply_api.application.delivery_adapters import EmailApiTransport, SmsApiTransport
from love_reply_api.application.errors import ApiError
from love_reply_api.application.payment_adapters import EpayTransport
from love_reply_api.application.provider_runtime import (
    ProviderAdapterHealthChecker,
    SmtpTransport,
)
from love_reply_api.config import get_settings
from love_reply_api.infrastructure.database import session_factory
from love_reply_api.schemas import HealthData, SuccessEnvelope
from love_reply_api.transport.http.errors import api_error_handler, validation_error_handler
from love_reply_api.transport.http.idempotency import IdempotencyMiddleware
from love_reply_api.transport.http.routes.admin_ai import router as admin_ai_router
from love_reply_api.transport.http.routes.admin_audit import router as admin_audit_router
from love_reply_api.transport.http.routes.admin_auth import router as admin_auth_router
from love_reply_api.transport.http.routes.admin_commerce import router as admin_commerce_router
from love_reply_api.transport.http.routes.admin_providers import router as admin_provider_router
from love_reply_api.transport.http.routes.app import router as app_router
from love_reply_api.transport.http.routes.auth import router as auth_router
from love_reply_api.transport.http.routes.billing import router as billing_router
from love_reply_api.transport.http.routes.billing import webhook_router as payment_webhook_router
from love_reply_api.transport.http.routes.candidates import router as candidate_router
from love_reply_api.transport.http.routes.generations import router as generation_router
from love_reply_api.transport.http.routes.me import router as me_router
from love_reply_api.transport.http.routes.referrals import router as referral_router

settings = get_settings()
logger = logging.getLogger(__name__)
settings.assert_deployable()

app = FastAPI(
    title="Love Reply Assistant API",
    version="1.0.0",
    debug=settings.app_debug,
    docs_url="/internal/docs" if settings.app_env != "production" else None,
    openapi_url="/internal/openapi.json" if settings.app_env != "production" else None,
)
app.state.sms_sender = None
app.state.email_sender = None
app.state.smtp_transport = SmtpTransport()
app.state.email_api_transport = EmailApiTransport()
app.state.sms_api_transport = SmsApiTransport()
app.state.epay_transport = EpayTransport()
app.state.ai_provider = None
app.state.ai_transport = AiHttpTransport()
app.state.provider_health_checker = ProviderAdapterHealthChecker(
    smtp_transport=app.state.smtp_transport,
    email_api_transport=app.state.email_api_transport,
    sms_api_transport=app.state.sms_api_transport,
    epay_transport=app.state.epay_transport,
)
app.add_exception_handler(ApiError, api_error_handler)  # type: ignore[arg-type]
app.add_exception_handler(RequestValidationError, validation_error_handler)  # type: ignore[arg-type]
app.include_router(app_router)
app.include_router(admin_auth_router)
app.include_router(admin_commerce_router)
app.include_router(admin_ai_router)
app.include_router(admin_audit_router)
app.include_router(admin_provider_router)
app.include_router(auth_router)
app.include_router(me_router)
app.include_router(referral_router)
app.include_router(billing_router)
app.include_router(payment_webhook_router)
app.include_router(generation_router)
app.include_router(candidate_router)
app.add_middleware(IdempotencyMiddleware)


@app.middleware("http")
async def request_context(request: Request, call_next: object) -> object:
    request_id = request.headers.get("X-Request-Id") or f"req_{uuid4().hex}"
    request.state.request_id = request_id
    request.state.audit_request_body = None
    # 普通用户的 AI 输入、退款说明等正文由对应业务服务加密审计；这里仅采集管理后台
    # 配置写操作的 JSON，用于追踪发布、回滚和配置变更，防止敏感业务正文重复落入普通元数据。
    capture_admin_write_body = (
        request.url.path.startswith("/admin/")
        # 管理员登录名只在路由中保存 SHA-256 摘要；认证请求体不进入普通日志。
        and not request.url.path.startswith("/admin/v1/auth/")
        and request.method in {"POST", "PUT", "PATCH", "DELETE"}
    )
    if capture_admin_write_body and request.headers.get("content-type", "").startswith(
        "application/json"
    ):
        raw_body = await request.body()
        if 0 < len(raw_body) <= 65_536:
            try:
                request.state.audit_request_body = json.loads(raw_body)
            except (UnicodeDecodeError, json.JSONDecodeError):
                request.state.audit_request_body = {"unparseableJson": True}
    started_at = datetime.now(UTC)
    started_counter = perf_counter()
    response = None
    error: Exception | None = None
    try:
        response = await call_next(request)  # type: ignore[operator]
        response.headers["X-Request-Id"] = request_id
        return response
    except Exception as exc:
        error = exc
        raise
    finally:
        status_code = response.status_code if response is not None else 500
        latency_ms = max(0, int((perf_counter() - started_counter) * 1000))
        path = request.url.path
        category = (
            "AUTH"
            if "/auth/" in path
            else "AI"
            if path.startswith("/v1/generations")
            else "PAYMENT"
            if path.startswith(
                (
                    "/v1/orders",
                    "/v1/refunds",
                    "/v1/subscriptions",
                    "/webhooks/v1/payments",
                )
            )
            else "ADMIN"
            if path.startswith("/admin/")
            else "OPERATIONS"
        )
        if path.endswith("/login"):
            event_type = "LOGIN_SUCCEEDED" if status_code < 400 else "LOGIN_FAILED"
        elif path.endswith("/logout") or path.endswith("/logout-all"):
            event_type = "LOGOUT"
        elif path.startswith("/webhooks/v1/payments"):
            event_type = "PAYMENT_CALLBACK_HTTP"
        elif path.startswith("/admin/") and request.method != "GET":
            event_type = (
                "ADMIN_CONFIGURATION_CHANGED"
                if status_code < 400
                else "ADMIN_CONFIGURATION_CHANGE_FAILED"
            )
        else:
            event_type = "HTTP_REQUEST_COMPLETED" if status_code < 500 else "HTTP_REQUEST_FAILED"
        try:
            async with session_factory() as audit_session:
                params = dict(request.path_params)
                route_metadata = getattr(request.state, "audit_metadata", {})
                await ComplianceAuditService(session=audit_session, settings=settings).record_event(
                    category=category,
                    event_type=event_type,
                    outcome="SUCCEEDED" if status_code < 400 else "FAILED",
                    severity=(
                        "ERROR"
                        if status_code >= 500
                        else "WARNING"
                        if status_code >= 400
                        else "INFO"
                    ),
                    actor_type=getattr(request.state, "audit_actor_type", "ANONYMOUS"),
                    actor_id=getattr(request.state, "audit_actor_id", None),
                    user_id=getattr(request.state, "audit_user_id", None),
                    admin_id=getattr(request.state, "audit_admin_id", None),
                    session_id=getattr(request.state, "audit_session_id", None),
                    request_id=request_id,
                    client_platform=request.headers.get("X-Platform"),
                    client_version=request.headers.get("X-Client-Version"),
                    source_ip=request.client.host if request.client is not None else None,
                    resource_type=getattr(request.state, "audit_resource_type", "HTTP_ENDPOINT"),
                    resource_id=getattr(
                        request.state, "audit_resource_id", f"{request.method} {path}"
                    ),
                    order_id=getattr(request.state, "audit_order_id", None)
                    or params.get("orderId"),
                    generation_id=getattr(request.state, "audit_generation_id", None)
                    or params.get("generationId"),
                    provider_id=getattr(request.state, "audit_provider_id", None)
                    or params.get("providerId"),
                    summary=f"{request.method} {path} 返回 {status_code}",
                    occurred_at=started_at,
                    metadata={
                        "method": request.method,
                        "path": path,
                        "statusCode": status_code,
                        "latencyMs": latency_ms,
                        "pathParams": params,
                        "queryKeys": sorted(request.query_params.keys()),
                        "errorType": type(error).__name__ if error is not None else None,
                        "route": route_metadata,
                        "requestBody": getattr(request.state, "audit_request_body", None),
                    },
                    commit=True,
                )
        except Exception:
            # 日志写入故障不能覆盖原业务响应，但基础设施日志必须触发运维告警。
            logger.exception(
                "compliance request audit persistence failed",
                extra={"request_id": request_id},
            )


@app.get("/health", operation_id="getHealth", response_model=SuccessEnvelope[HealthData])
async def get_health(request: Request) -> SuccessEnvelope[HealthData]:
    request_id = request.headers.get("X-Request-Id") or str(uuid4())
    return SuccessEnvelope(
        data=HealthData(status="ok", version=app.version),
        request_id=request_id,
    )
