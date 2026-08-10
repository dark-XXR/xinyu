from __future__ import annotations

from base64 import urlsafe_b64decode, urlsafe_b64encode
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from hmac import new as new_hmac
from json import dumps, loads
from time import monotonic
from typing import Any, Protocol
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from love_reply_api.application.errors import ApiError
from love_reply_api.application.security import SecretCipher
from love_reply_api.config import Settings
from love_reply_api.infrastructure.provider_records import (
    ProviderAuditRecord,
    ProviderCredentialVersionRecord,
    ProviderHealthCheckRecord,
    ProviderRecord,
    ProviderVersionRecord,
)


@dataclass(frozen=True, slots=True)
class ProviderHealthResult:
    status: str
    redacted_summary: str
    provider_request_id: str | None = None


class ProviderHealthChecker(Protocol):
    async def check(
        self,
        *,
        kind: str,
        configuration: dict[str, Any],
        credentials: dict[str, str],
        administrator_test_destination: str | None,
    ) -> ProviderHealthResult: ...


class UnavailableProviderHealthChecker:
    async def check(
        self,
        *,
        kind: str,
        configuration: dict[str, Any],
        credentials: dict[str, str],
        administrator_test_destination: str | None,
    ) -> ProviderHealthResult:
        del kind, configuration, credentials, administrator_test_destination
        raise ApiError(
            status_code=503,
            code="PROVIDER_UNAVAILABLE",
            message="Provider health checking is not configured.",
            retryable=True,
        )


@dataclass(frozen=True, slots=True)
class ProviderView:
    provider_id: str
    provider_name: str
    kind: str
    status: str
    configuration: dict[str, Any]
    data_region: str | None
    retention_statement: str | None
    retry_limit: int
    priority: int
    rollout_percentage: int
    credential_configured: bool
    credential_fingerprint: str | None
    credential_rotated_at: datetime | None
    last_health_status: str | None
    effective_at: datetime | None
    published_resource_version: int | None
    published_rollout_percentage: int
    published_effective_at: datetime | None
    resource_version: int
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class ProviderListResult:
    items: list[ProviderView]
    next_cursor: str | None
    has_more: bool


@dataclass(frozen=True, slots=True)
class CredentialRotationResult:
    credential_version_id: str
    fingerprint: str
    rotated_at: datetime
    resource_version: int


@dataclass(frozen=True, slots=True)
class ProviderHealthCheckResult:
    health_check_id: str
    status: str
    started_at: datetime
    completed_at: datetime
    latency_ms: int | None
    redacted_summary: str
    provider_request_id: str | None


EXPECTED_CREDENTIAL_NAMES = {
    "OPENAI_COMPAT": {"apiKey"},
    "OPENAI": {"apiKey"},
    "ANTHROPIC": {"apiKey"},
    "GEMINI": {"apiKey"},
    "SMTP": {"username", "password"},
    "SES_API": {"accessKeyId", "accessKeySecret"},
    "SENDGRID_API": {"apiKey"},
    "RESEND_API": {"apiKey"},
    "MAILGUN_API": {"apiKey"},
    "ALIYUN_SMS": {"accessKeyId", "accessKeySecret"},
    "TENCENT_SMS": {"secretId", "secretKey"},
    "EPAY_COMPAT": {"merchantKey"},
}


class ProviderService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        settings: Settings,
        health_checker: ProviderHealthChecker,
    ) -> None:
        self._session = session
        self._cipher = SecretCipher(settings)
        self._health_checker = health_checker
        master_key = settings.data_encryption_key.get_secret_value().encode("utf-8")
        self._fingerprint_key = sha256(b"provider-fingerprint:" + master_key).digest()

    async def create(
        self,
        *,
        admin_id: str,
        provider_name: str,
        kind: str,
        configuration: dict[str, Any],
        data_region: str | None,
        retention_statement: str | None,
        retry_limit: int,
        priority: int,
    ) -> ProviderView:
        now = datetime.now(UTC)
        provider = ProviderRecord(
            provider_id=f"prv_{uuid4().hex}",
            provider_name=provider_name,
            kind=kind,
            status="DRAFT",
            configuration=configuration,
            data_region=data_region,
            retention_statement=retention_statement,
            retry_limit=retry_limit,
            priority=priority,
            rollout_percentage=0,
            active_credential_version_id=None,
            published_resource_version=None,
            published_rollout_percentage=0,
            published_effective_at=None,
            last_health_status=None,
            effective_at=None,
            resource_version=1,
            created_at=now,
            updated_at=now,
        )
        self._session.add(provider)
        await self._session.flush()
        await self._record_version(provider=provider, admin_id=admin_id, action="CREATE")
        self._audit(
            provider_id=provider.provider_id,
            admin_id=admin_id,
            action="PROVIDER_CREATED",
            reason="Provider draft created.",
            metadata={"resourceVersion": 1, "kind": kind},
            now=now,
        )
        await self._session.commit()
        return await self._view(provider)

    async def get(self, *, provider_id: str) -> ProviderView:
        provider = await self._get(provider_id)
        return await self._view(provider)

    async def list_providers(
        self,
        *,
        cursor: str | None,
        limit: int,
    ) -> ProviderListResult:
        after_id = self._decode_cursor(cursor) if cursor is not None else None
        statement = select(ProviderRecord).order_by(ProviderRecord.provider_id).limit(limit + 1)
        if after_id is not None:
            statement = statement.where(ProviderRecord.provider_id > after_id)
        records = list((await self._session.scalars(statement)).all())
        has_more = len(records) > limit
        selected = records[:limit]
        views = [await self._view(record) for record in selected]
        next_cursor = (
            self._encode_cursor(selected[-1].provider_id) if has_more and selected else None
        )
        return ProviderListResult(items=views, next_cursor=next_cursor, has_more=has_more)

    async def update(
        self,
        *,
        provider_id: str,
        expected_version: int,
        admin_id: str,
        provider_name: str,
        kind: str,
        configuration: dict[str, Any],
        data_region: str | None,
        retention_statement: str | None,
        retry_limit: int,
        priority: int,
    ) -> ProviderView:
        provider = await self._get_locked(provider_id)
        self._assert_version(provider, expected_version)
        if provider.kind != kind:
            raise ApiError(
                status_code=400,
                code="PROVIDER_KIND_IMMUTABLE",
                message="Provider kind cannot be changed after creation.",
            )
        provider.provider_name = provider_name
        provider.configuration = configuration
        provider.data_region = data_region
        provider.retention_statement = retention_statement
        provider.retry_limit = retry_limit
        provider.priority = priority
        provider.status = "DRAFT"
        provider.rollout_percentage = 0
        provider.last_health_status = None
        provider.effective_at = None
        await self._advance(provider=provider, admin_id=admin_id, action="UPDATE")
        self._audit(
            provider_id=provider_id,
            admin_id=admin_id,
            action="PROVIDER_UPDATED",
            reason="Provider draft updated.",
            metadata={"resourceVersion": provider.resource_version},
            now=provider.updated_at,
        )
        await self._session.commit()
        return await self._view(provider)

    async def rotate_credentials(
        self,
        *,
        provider_id: str,
        expected_version: int,
        admin_id: str,
        secrets: dict[str, str],
        audit_reason: str,
    ) -> CredentialRotationResult:
        provider = await self._get_locked(provider_id)
        self._assert_version(provider, expected_version)
        adapter_type = str(provider.configuration["adapterType"])
        if set(secrets) != EXPECTED_CREDENTIAL_NAMES[adapter_type]:
            raise ApiError(
                status_code=400,
                code="CREDENTIAL_FIELDS_INVALID",
                message="Credential fields do not match the provider adapter.",
            )
        canonical = dumps(secrets, sort_keys=True, separators=(",", ":"))
        fingerprint_digest = new_hmac(
            self._fingerprint_key,
            canonical.encode("utf-8"),
            sha256,
        ).hexdigest()
        fingerprint = f"hmac-sha256:{fingerprint_digest}"
        now = datetime.now(UTC)
        credential = ProviderCredentialVersionRecord(
            credential_version_id=f"cred_{uuid4().hex}",
            provider_id=provider_id,
            encrypted_payload=self._cipher.encrypt(canonical),
            fingerprint=fingerprint,
            rotated_at=now,
            created_by_admin_id=admin_id,
        )
        self._session.add(credential)
        provider.active_credential_version_id = credential.credential_version_id
        provider.status = "DRAFT"
        provider.last_health_status = None
        provider.rollout_percentage = 0
        provider.effective_at = None
        await self._advance(provider=provider, admin_id=admin_id, action="ROTATE_CREDENTIALS")
        self._audit(
            provider_id=provider_id,
            admin_id=admin_id,
            action="PROVIDER_CREDENTIALS_ROTATED",
            reason=self._redact_text(audit_reason, list(secrets.values())),
            metadata={
                "credentialVersionId": credential.credential_version_id,
                "fingerprint": fingerprint,
                "resourceVersion": provider.resource_version,
            },
            now=now,
        )
        await self._session.commit()
        return CredentialRotationResult(
            credential_version_id=credential.credential_version_id,
            fingerprint=fingerprint,
            rotated_at=now,
            resource_version=provider.resource_version,
        )

    async def health_check(
        self,
        *,
        provider_id: str,
        admin_id: str,
        administrator_test_destination: str | None,
        audit_reason: str,
    ) -> ProviderHealthCheckResult:
        provider = await self._get_locked(provider_id)
        if provider.active_credential_version_id is None:
            raise ApiError(
                status_code=409,
                code="PROVIDER_CREDENTIALS_REQUIRED",
                message="Provider credentials must be configured before a health check.",
            )
        if provider.kind in {"EMAIL", "SMS"} and not administrator_test_destination:
            raise ApiError(
                status_code=400,
                code="ADMIN_TEST_DESTINATION_REQUIRED",
                message="An administrator test destination is required for this provider.",
            )
        credentials = await self._credentials(provider.active_credential_version_id)
        started_at = datetime.now(UTC)
        started_clock = monotonic()
        sensitive_values = [*credentials.values()]
        if administrator_test_destination is not None:
            sensitive_values.append(administrator_test_destination)
        try:
            result = await self._health_checker.check(
                kind=provider.kind,
                configuration=provider.configuration,
                credentials=credentials,
                administrator_test_destination=administrator_test_destination,
            )
        except ApiError as exc:
            await self._record_failed_health_check(
                provider=provider,
                admin_id=admin_id,
                started_at=started_at,
                started_clock=started_clock,
                audit_reason=self._redact_text(audit_reason, sensitive_values),
                error_code=exc.code,
            )
            raise
        except Exception as exc:
            await self._record_failed_health_check(
                provider=provider,
                admin_id=admin_id,
                started_at=started_at,
                started_clock=started_clock,
                audit_reason=self._redact_text(audit_reason, sensitive_values),
                error_code="PROVIDER_UNAVAILABLE",
            )
            raise ApiError(
                status_code=503,
                code="PROVIDER_UNAVAILABLE",
                message="Provider health check failed.",
                retryable=True,
            ) from exc
        if result.status not in {"HEALTHY", "DEGRADED", "UNHEALTHY"}:
            await self._record_failed_health_check(
                provider=provider,
                admin_id=admin_id,
                started_at=started_at,
                started_clock=started_clock,
                audit_reason=self._redact_text(audit_reason, sensitive_values),
                error_code="PROVIDER_HEALTH_RESPONSE_INVALID",
            )
            raise ApiError(
                status_code=503,
                code="PROVIDER_HEALTH_RESPONSE_INVALID",
                message="Provider health check returned an invalid status.",
            )
        redacted_summary = self._redact_text(
            result.redacted_summary, sensitive_values
        ).strip()
        if not redacted_summary:
            await self._record_failed_health_check(
                provider=provider,
                admin_id=admin_id,
                started_at=started_at,
                started_clock=started_clock,
                audit_reason=self._redact_text(audit_reason, sensitive_values),
                error_code="PROVIDER_HEALTH_RESPONSE_INVALID",
            )
            raise ApiError(
                status_code=503,
                code="PROVIDER_HEALTH_RESPONSE_INVALID",
                message="Provider health check returned an invalid summary.",
            )
        completed_at = datetime.now(UTC)
        latency_ms = max(0, round((monotonic() - started_clock) * 1000))
        health = ProviderHealthCheckRecord(
            health_check_id=f"phc_{uuid4().hex}",
            provider_id=provider_id,
            provider_resource_version=provider.resource_version,
            status=result.status,
            started_at=started_at,
            completed_at=completed_at,
            latency_ms=latency_ms,
            redacted_summary=redacted_summary[:500],
            provider_request_id=self._redacted_request_id(
                result.provider_request_id, sensitive_values
            ),
            created_by_admin_id=admin_id,
        )
        self._session.add(health)
        provider.last_health_status = result.status
        provider.status = "READY" if result.status == "HEALTHY" else "DRAFT"
        await self._advance(provider=provider, admin_id=admin_id, action="HEALTH_CHECK")
        self._audit(
            provider_id=provider_id,
            admin_id=admin_id,
            action="PROVIDER_HEALTH_CHECKED",
            reason=self._redact_text(audit_reason, sensitive_values),
            metadata={
                "healthCheckId": health.health_check_id,
                "status": result.status,
                "resourceVersion": provider.resource_version,
            },
            now=completed_at,
        )
        await self._session.commit()
        return ProviderHealthCheckResult(
            health_check_id=health.health_check_id,
            status=health.status,
            started_at=health.started_at,
            completed_at=health.completed_at,
            latency_ms=health.latency_ms,
            redacted_summary=health.redacted_summary,
            provider_request_id=health.provider_request_id,
        )

    async def publish(
        self,
        *,
        provider_id: str,
        expected_version: int,
        admin_id: str,
        rollout_percentage: int,
        effective_at: datetime,
        audit_reason: str,
    ) -> ProviderView:
        provider = await self._get_locked(provider_id)
        self._assert_version(provider, expected_version)
        if (
            provider.active_credential_version_id is None
            or provider.last_health_status != "HEALTHY"
            or provider.status != "READY"
        ):
            raise ApiError(
                status_code=409,
                code="PROVIDER_NOT_READY",
                message="Provider must pass health checks before publication.",
            )
        source_version = provider.resource_version
        version = await self._version(provider_id=provider_id, resource_version=source_version)
        assert version is not None
        version.was_published = True
        provider.status = "ACTIVE"
        provider.rollout_percentage = rollout_percentage
        provider.effective_at = effective_at
        provider.published_resource_version = source_version
        provider.published_rollout_percentage = rollout_percentage
        provider.published_effective_at = effective_at
        await self._advance(
            provider=provider,
            admin_id=admin_id,
            action="PUBLISH",
            was_published=True,
        )
        credentials = await self._credentials(provider.active_credential_version_id)
        self._audit(
            provider_id=provider_id,
            admin_id=admin_id,
            action="PROVIDER_PUBLISHED",
            reason=self._redact_text(audit_reason, list(credentials.values())),
            metadata={
                "publishedResourceVersion": source_version,
                "resourceVersion": provider.resource_version,
                "rolloutPercentage": rollout_percentage,
                "effectiveAt": effective_at.isoformat(),
            },
            now=provider.updated_at,
        )
        await self._session.commit()
        return await self._view(provider)

    async def rollback(
        self,
        *,
        provider_id: str,
        expected_version: int,
        admin_id: str,
        target_resource_version: int,
        audit_reason: str,
    ) -> ProviderView:
        provider = await self._get_locked(provider_id)
        self._assert_version(provider, expected_version)
        target = await self._version(
            provider_id=provider_id,
            resource_version=target_resource_version,
            required=False,
        )
        if target is None or not target.was_published:
            raise ApiError(
                status_code=409,
                code="ROLLBACK_TARGET_INVALID",
                message="Rollback target is not a published provider version.",
            )
        snapshot = target.snapshot
        target_credential_id = snapshot["credentialVersionId"]
        if not isinstance(target_credential_id, str):
            raise ApiError(
                status_code=409,
                code="ROLLBACK_TARGET_INVALID",
                message="Rollback target has no credential version.",
            )
        provider.provider_name = str(snapshot["providerName"])
        provider.configuration = dict(snapshot["configuration"])
        provider.data_region = snapshot["dataRegion"]
        provider.retention_statement = snapshot["retentionStatement"]
        provider.retry_limit = int(snapshot["retryLimit"])
        provider.priority = int(snapshot["priority"])
        provider.active_credential_version_id = target_credential_id
        provider.last_health_status = "HEALTHY"
        provider.status = "ACTIVE"
        provider.rollout_percentage = 100
        provider.effective_at = datetime.now(UTC)
        provider.published_resource_version = target_resource_version
        provider.published_rollout_percentage = 100
        provider.published_effective_at = provider.effective_at
        await self._advance(
            provider=provider,
            admin_id=admin_id,
            action="ROLLBACK",
            was_published=True,
        )
        credentials = await self._credentials(target_credential_id)
        self._audit(
            provider_id=provider_id,
            admin_id=admin_id,
            action="PROVIDER_ROLLED_BACK",
            reason=self._redact_text(audit_reason, list(credentials.values())),
            metadata={
                "targetResourceVersion": target_resource_version,
                "resourceVersion": provider.resource_version,
            },
            now=provider.updated_at,
        )
        await self._session.commit()
        return await self._view(provider)

    async def disable(
        self,
        *,
        provider_id: str,
        expected_version: int,
        admin_id: str,
        audit_reason: str,
    ) -> ProviderView:
        """立即将供应商移出运行时选择，同时保留发布版本和凭据历史。"""
        provider = await self._get_locked(provider_id)
        self._assert_version(provider, expected_version)
        if provider.status == "DISABLED":
            raise ApiError(
                status_code=409,
                code="PROVIDER_ALREADY_DISABLED",
                message="Provider is already disabled.",
            )
        if (
            provider.published_resource_version is None
            or provider.published_rollout_percentage <= 0
        ):
            raise ApiError(
                status_code=409,
                code="PROVIDER_NOT_ACTIVE",
                message="Provider has no active published traffic to disable.",
            )

        previous_rollout = provider.published_rollout_percentage
        previous_effective_at = provider.published_effective_at
        provider.status = "DISABLED"
        provider.rollout_percentage = 0
        provider.effective_at = None
        # 保留 published_resource_version 作为取证和回滚锚点，但将线上流量立即归零。
        provider.published_rollout_percentage = 0
        await self._advance(provider=provider, admin_id=admin_id, action="DISABLE")
        credentials = (
            await self._credentials(provider.active_credential_version_id)
            if provider.active_credential_version_id is not None
            else {}
        )
        self._audit(
            provider_id=provider_id,
            admin_id=admin_id,
            action="PROVIDER_DISABLED",
            reason=self._redact_text(audit_reason, list(credentials.values())),
            metadata={
                "publishedResourceVersion": provider.published_resource_version,
                "previousRolloutPercentage": previous_rollout,
                "previousEffectiveAt": (
                    previous_effective_at.isoformat()
                    if previous_effective_at is not None
                    else None
                ),
                "resourceVersion": provider.resource_version,
            },
            now=provider.updated_at,
        )
        await self._session.commit()
        return await self._view(provider)

    async def _get(self, provider_id: str) -> ProviderRecord:
        provider = await self._session.get(ProviderRecord, provider_id)
        if provider is None:
            raise ApiError(
                status_code=404,
                code="PROVIDER_NOT_FOUND",
                message="Provider was not found.",
            )
        return provider

    async def _get_locked(self, provider_id: str) -> ProviderRecord:
        provider = await self._session.scalar(
            select(ProviderRecord)
            .where(ProviderRecord.provider_id == provider_id)
            .with_for_update()
        )
        if provider is None:
            raise ApiError(
                status_code=404,
                code="PROVIDER_NOT_FOUND",
                message="Provider was not found.",
            )
        return provider

    @staticmethod
    def _assert_version(provider: ProviderRecord, expected_version: int) -> None:
        if provider.resource_version != expected_version:
            raise ApiError(
                status_code=409,
                code="RESOURCE_VERSION_CONFLICT",
                message="Provider resource version changed.",
                details={"currentResourceVersion": provider.resource_version},
            )

    async def _view(self, provider: ProviderRecord) -> ProviderView:
        credential = None
        if provider.active_credential_version_id is not None:
            credential = await self._session.get(
                ProviderCredentialVersionRecord,
                provider.active_credential_version_id,
            )
        return ProviderView(
            provider_id=provider.provider_id,
            provider_name=provider.provider_name,
            kind=provider.kind,
            status=provider.status,
            configuration=provider.configuration,
            data_region=provider.data_region,
            retention_statement=provider.retention_statement,
            retry_limit=provider.retry_limit,
            priority=provider.priority,
            rollout_percentage=provider.rollout_percentage,
            credential_configured=credential is not None,
            credential_fingerprint=credential.fingerprint if credential is not None else None,
            credential_rotated_at=credential.rotated_at if credential is not None else None,
            last_health_status=provider.last_health_status,
            effective_at=provider.effective_at,
            published_resource_version=provider.published_resource_version,
            published_rollout_percentage=provider.published_rollout_percentage,
            published_effective_at=provider.published_effective_at,
            resource_version=provider.resource_version,
            created_at=provider.created_at,
            updated_at=provider.updated_at,
        )

    async def _credentials(self, credential_version_id: str) -> dict[str, str]:
        record = await self._session.get(
            ProviderCredentialVersionRecord, credential_version_id
        )
        if record is None:
            raise ApiError(
                status_code=503,
                code="PROVIDER_CREDENTIALS_UNAVAILABLE",
                message="Provider credentials are unavailable.",
            )
        value = loads(self._cipher.decrypt(record.encrypted_payload))
        if not isinstance(value, dict) or not all(
            isinstance(key, str) and isinstance(item, str) for key, item in value.items()
        ):
            raise ApiError(
                status_code=503,
                code="PROVIDER_CREDENTIALS_INVALID",
                message="Provider credentials are invalid.",
            )
        return value

    async def _advance(
        self,
        *,
        provider: ProviderRecord,
        admin_id: str,
        action: str,
        was_published: bool = False,
    ) -> None:
        provider.resource_version += 1
        provider.updated_at = datetime.now(UTC)
        await self._record_version(
            provider=provider,
            admin_id=admin_id,
            action=action,
            was_published=was_published,
        )

    async def _record_failed_health_check(
        self,
        *,
        provider: ProviderRecord,
        admin_id: str,
        started_at: datetime,
        started_clock: float,
        audit_reason: str,
        error_code: str,
    ) -> None:
        completed_at = datetime.now(UTC)
        health = ProviderHealthCheckRecord(
            health_check_id=f"phc_{uuid4().hex}",
            provider_id=provider.provider_id,
            provider_resource_version=provider.resource_version,
            status="UNHEALTHY",
            started_at=started_at,
            completed_at=completed_at,
            latency_ms=max(0, round((monotonic() - started_clock) * 1000)),
            redacted_summary=f"Provider health check failed ({error_code})."[:500],
            provider_request_id=None,
            created_by_admin_id=admin_id,
        )
        self._session.add(health)
        provider.last_health_status = "UNHEALTHY"
        provider.status = "DRAFT"
        await self._advance(provider=provider, admin_id=admin_id, action="HEALTH_CHECK")
        self._audit(
            provider_id=provider.provider_id,
            admin_id=admin_id,
            action="PROVIDER_HEALTH_CHECKED",
            reason=audit_reason,
            metadata={
                "healthCheckId": health.health_check_id,
                "status": "UNHEALTHY",
                "errorCode": error_code,
                "resourceVersion": provider.resource_version,
            },
            now=completed_at,
        )
        await self._session.commit()

    async def _record_version(
        self,
        *,
        provider: ProviderRecord,
        admin_id: str,
        action: str,
        was_published: bool = False,
    ) -> None:
        self._session.add(
            ProviderVersionRecord(
                provider_version_id=f"pv_{provider.provider_id}_{provider.resource_version}",
                provider_id=provider.provider_id,
                resource_version=provider.resource_version,
                snapshot=self._snapshot(provider),
                was_published=was_published,
                action=action,
                created_by_admin_id=admin_id,
                created_at=provider.updated_at,
            )
        )

    async def _version(
        self,
        *,
        provider_id: str,
        resource_version: int,
        required: bool = True,
    ) -> ProviderVersionRecord | None:
        record = await self._session.scalar(
            select(ProviderVersionRecord).where(
                ProviderVersionRecord.provider_id == provider_id,
                ProviderVersionRecord.resource_version == resource_version,
            )
        )
        if record is None and required:
            raise ApiError(
                status_code=409,
                code="PROVIDER_VERSION_MISSING",
                message="Provider version history is incomplete.",
            )
        return record

    @staticmethod
    def _snapshot(provider: ProviderRecord) -> dict[str, Any]:
        return {
            "providerName": provider.provider_name,
            "kind": provider.kind,
            "status": provider.status,
            "configuration": provider.configuration,
            "dataRegion": provider.data_region,
            "retentionStatement": provider.retention_statement,
            "retryLimit": provider.retry_limit,
            "priority": provider.priority,
            "credentialVersionId": provider.active_credential_version_id,
            "lastHealthStatus": provider.last_health_status,
        }

    def _audit(
        self,
        *,
        provider_id: str,
        admin_id: str,
        action: str,
        reason: str,
        metadata: dict[str, Any],
        now: datetime,
    ) -> None:
        self._session.add(
            ProviderAuditRecord(
                audit_id=f"paud_{uuid4().hex}",
                provider_id=provider_id,
                admin_id=admin_id,
                action=action,
                audit_reason=reason,
                metadata_json=metadata,
                created_at=now,
            )
        )

    @staticmethod
    def _redact_text(value: str, sensitive_values: list[str]) -> str:
        redacted = value
        for sensitive in sorted(
            {item for item in sensitive_values if item}, key=len, reverse=True
        ):
            redacted = redacted.replace(sensitive, "[REDACTED]")
        return redacted

    def _redacted_request_id(
        self,
        value: str | None,
        sensitive_values: list[str],
    ) -> str | None:
        if value is None:
            return None
        redacted = self._redact_text(value, sensitive_values)[:128]
        return redacted or None

    @staticmethod
    def _encode_cursor(provider_id: str) -> str:
        return urlsafe_b64encode(provider_id.encode("utf-8")).decode("ascii").rstrip("=")

    @staticmethod
    def _decode_cursor(cursor: str) -> str:
        try:
            padded = cursor + "=" * ((4 - len(cursor) % 4) % 4)
            value = urlsafe_b64decode(padded.encode("ascii")).decode("utf-8")
        except (ValueError, UnicodeError) as exc:
            raise ApiError(
                status_code=400,
                code="INVALID_CURSOR",
                message="Provider cursor is invalid.",
            ) from exc
        if not value.startswith("prv_"):
            raise ApiError(
                status_code=400,
                code="INVALID_CURSOR",
                message="Provider cursor is invalid.",
            )
        return value
