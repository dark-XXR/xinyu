from datetime import UTC, datetime
from uuid import uuid4

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from love_reply_api.application.errors import ApiError


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", f"req_{uuid4().hex}")


async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.code,
            "message": exc.message,
            "data": None,
            "error": {
                "retryable": exc.retryable,
                "retryAfterSeconds": exc.retry_after_seconds,
                "fieldErrors": [],
                "details": exc.details,
            },
            "requestId": _request_id(request),
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )


async def validation_error_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    field_errors = [
        {
            "field": ".".join(str(part) for part in error["loc"] if part != "body"),
            "reason": error["type"],
        }
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=400,
        content={
            "code": "VALIDATION_ERROR",
            "message": "One or more fields are invalid.",
            "data": None,
            "error": {
                "retryable": False,
                "retryAfterSeconds": None,
                "fieldErrors": field_errors,
                "details": {},
            },
            "requestId": _request_id(request),
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )
