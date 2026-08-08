from base64 import urlsafe_b64encode
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import cast
from uuid import uuid4

from cryptography.fernet import Fernet, InvalidToken
from fastapi import Request
from fastapi.responses import JSONResponse, Response
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import StreamingResponse

from love_reply_api.config import get_settings
from love_reply_api.infrastructure.database import session_factory
from love_reply_api.infrastructure.identity_records import IdempotencyRecord

MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class IdempotencyMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: object) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        settings = get_settings()
        encryption_key = sha256(
            settings.jwt_signing_key.get_secret_value().encode("utf-8")
        ).digest()
        self._cipher = Fernet(urlsafe_b64encode(encryption_key))
        self._ttl_seconds = settings.idempotency_ttl_seconds
        self._max_response_bytes = settings.idempotency_max_response_bytes

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        idempotency_key = request.headers.get("Idempotency-Key")
        if request.method not in MUTATING_METHODS or idempotency_key is None:
            return await call_next(request)

        body = await request.body()
        scope = self._scope(request)
        request_hash = sha256(
            b"\n".join(
                [
                    request.method.encode(),
                    request.url.path.encode(),
                    request.url.query.encode(),
                    body,
                ]
            )
        ).hexdigest()
        existing = await self._claim(scope=scope, key=idempotency_key, request_hash=request_hash)
        if existing is not None:
            return self._replay_or_conflict(
                request=request,
                record=existing,
                request_hash=request_hash,
            )

        try:
            response = cast(StreamingResponse, await call_next(request))
            response_chunks: list[bytes] = []
            async for chunk in response.body_iterator:
                response_chunks.append(chunk.encode() if isinstance(chunk, str) else bytes(chunk))
            response_body = b"".join(response_chunks)
        except Exception:
            await self._release(scope=scope, key=idempotency_key)
            raise

        if response.status_code < 500 and len(response_body) <= self._max_response_bytes:
            await self._complete(
                scope=scope,
                key=idempotency_key,
                status=response.status_code,
                content_type=response.headers.get("content-type", "application/json"),
                body=response_body,
            )
        else:
            await self._release(scope=scope, key=idempotency_key)

        headers = dict(response.headers)
        headers["Idempotency-Replayed"] = "false"
        return Response(
            content=response_body,
            status_code=response.status_code,
            headers=headers,
            media_type=response.media_type,
        )

    @staticmethod
    def _scope(request: Request) -> tuple[str, str, str]:
        authorization = request.headers.get("Authorization")
        actor_source = authorization or request.headers.get("X-Device-Id") or "anonymous"
        actor_key = sha256(actor_source.encode("utf-8")).hexdigest()
        return actor_key, request.method, request.url.path

    async def _claim(
        self,
        *,
        scope: tuple[str, str, str],
        key: str,
        request_hash: str,
    ) -> IdempotencyRecord | None:
        actor_key, method, path = scope
        now = datetime.now(UTC)
        async with session_factory() as session:
            await session.execute(
                delete(IdempotencyRecord).where(IdempotencyRecord.expires_at <= now)
            )
            session.add(
                IdempotencyRecord(
                    id=f"idem_{uuid4().hex}",
                    actor_key=actor_key,
                    http_method=method,
                    normalized_path=path,
                    idempotency_key=key,
                    request_hash=request_hash,
                    state="PROCESSING",
                    response_status=None,
                    response_ciphertext=None,
                    response_content_type=None,
                    expires_at=now + timedelta(seconds=self._ttl_seconds),
                    created_at=now,
                    updated_at=now,
                )
            )
            try:
                await session.commit()
                return None
            except IntegrityError:
                await session.rollback()
                return cast(
                    IdempotencyRecord | None,
                    await session.scalar(
                        select(IdempotencyRecord).where(
                            IdempotencyRecord.actor_key == actor_key,
                            IdempotencyRecord.http_method == method,
                            IdempotencyRecord.normalized_path == path,
                            IdempotencyRecord.idempotency_key == key,
                        )
                    ),
                )

    def _replay_or_conflict(
        self,
        *,
        request: Request,
        record: IdempotencyRecord,
        request_hash: str,
    ) -> Response:
        if record.request_hash != request_hash:
            return self._error(
                request,
                status=409,
                code="IDEMPOTENCY_KEY_REUSED",
                message="Idempotency key was already used with a different request.",
                retryable=False,
            )
        if (
            record.state != "COMPLETED"
            or record.response_status is None
            or record.response_ciphertext is None
        ):
            return self._error(
                request,
                status=409,
                code="IDEMPOTENCY_REQUEST_IN_PROGRESS",
                message="The original request is still being processed.",
                retryable=True,
            )
        try:
            body = self._cipher.decrypt(record.response_ciphertext.encode("ascii"))
        except InvalidToken:
            return self._error(
                request,
                status=500,
                code="IDEMPOTENCY_RESPONSE_UNAVAILABLE",
                message="The stored response cannot be recovered.",
                retryable=False,
            )
        return Response(
            content=body,
            status_code=record.response_status,
            headers={
                "content-type": record.response_content_type or "application/json",
                "Idempotency-Replayed": "true",
            },
        )

    async def _complete(
        self,
        *,
        scope: tuple[str, str, str],
        key: str,
        status: int,
        content_type: str,
        body: bytes,
    ) -> None:
        actor_key, method, path = scope
        async with session_factory() as session:
            record = await session.scalar(
                select(IdempotencyRecord).where(
                    IdempotencyRecord.actor_key == actor_key,
                    IdempotencyRecord.http_method == method,
                    IdempotencyRecord.normalized_path == path,
                    IdempotencyRecord.idempotency_key == key,
                )
            )
            if record is None:
                return
            record.state = "COMPLETED"
            record.response_status = status
            record.response_ciphertext = self._cipher.encrypt(body).decode("ascii")
            record.response_content_type = content_type
            record.updated_at = datetime.now(UTC)
            await session.commit()

    async def _release(self, *, scope: tuple[str, str, str], key: str) -> None:
        actor_key, method, path = scope
        async with session_factory() as session:
            await session.execute(
                delete(IdempotencyRecord).where(
                    IdempotencyRecord.actor_key == actor_key,
                    IdempotencyRecord.http_method == method,
                    IdempotencyRecord.normalized_path == path,
                    IdempotencyRecord.idempotency_key == key,
                )
            )
            await session.commit()

    @staticmethod
    def _error(
        request: Request,
        *,
        status: int,
        code: str,
        message: str,
        retryable: bool,
    ) -> JSONResponse:
        request_id = request.headers.get("X-Request-Id") or f"req_{uuid4().hex}"
        return JSONResponse(
            status_code=status,
            content={
                "code": code,
                "message": message,
                "data": None,
                "error": {
                    "retryable": retryable,
                    "retryAfterSeconds": None,
                    "fieldErrors": [],
                    "details": {},
                },
                "requestId": request_id,
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )
