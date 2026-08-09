from asyncio import to_thread
from dataclasses import dataclass
from datetime import UTC, datetime
from email.message import EmailMessage
from email.utils import formataddr
from hashlib import sha256
from hmac import new as new_hmac
from json import loads
from smtplib import SMTP, SMTP_SSL
from ssl import create_default_context
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from love_reply_api.application.errors import ApiError
from love_reply_api.application.providers import ProviderHealthResult
from love_reply_api.application.runtime_config import RuntimeConfigService
from love_reply_api.application.security import SecretCipher
from love_reply_api.config import Settings
from love_reply_api.infrastructure.provider_records import (
    ProviderCredentialVersionRecord,
    ProviderRecord,
    ProviderVersionRecord,
)


@dataclass(frozen=True, slots=True)
class ResolvedProvider:
    provider_id: str
    kind: str
    configuration: dict[str, Any]
    credentials: dict[str, str]
    resource_version: int
    retry_limit: int


class PublishedProviderResolver:
    def __init__(self, *, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._cipher = SecretCipher(settings)
        master_key = settings.data_encryption_key.get_secret_value().encode("utf-8")
        self._rollout_key = sha256(b"provider-rollout:" + master_key).digest()

    async def has_effective(
        self,
        *,
        kind: str,
        adapter_types: set[str],
        now: datetime | None = None,
    ) -> bool:
        candidates = await self._candidates(kind=kind, now=now or datetime.now(UTC))
        return any(
            str(version.snapshot["configuration"]["adapterType"]) in adapter_types
            for _, version in candidates
        )

    async def resolve(
        self,
        *,
        kind: str,
        routing_key: str,
        adapter_types: set[str],
        now: datetime | None = None,
    ) -> ResolvedProvider | None:
        candidates = await self._candidates(kind=kind, now=now or datetime.now(UTC))
        candidates.sort(
            key=lambda item: (
                -int(item[1].snapshot["priority"]),
                item[0].provider_id,
            )
        )
        for provider, version in candidates:
            configuration = dict(version.snapshot["configuration"])
            if str(configuration["adapterType"]) not in adapter_types:
                continue
            if not self.in_rollout(
                provider_id=provider.provider_id,
                routing_key=routing_key,
                percentage=provider.published_rollout_percentage,
            ):
                continue
            credential_id = version.snapshot["credentialVersionId"]
            if not isinstance(credential_id, str):
                continue
            credentials = await self._credentials(credential_id)
            return ResolvedProvider(
                provider_id=provider.provider_id,
                kind=provider.kind,
                configuration=configuration,
                credentials=credentials,
                resource_version=version.resource_version,
                retry_limit=int(version.snapshot["retryLimit"]),
            )
        return None

    async def resolve_by_id(
        self,
        *,
        provider_id: str,
        routing_key: str,
        adapter_types: set[str],
        now: datetime | None = None,
    ) -> ResolvedProvider | None:
        candidates = await self._candidates(kind="AI", now=now or datetime.now(UTC))
        for provider, version in candidates:
            if provider.provider_id != provider_id:
                continue
            configuration = dict(version.snapshot["configuration"])
            if str(configuration["adapterType"]) not in adapter_types:
                return None
            if not self.in_rollout(
                provider_id=provider.provider_id,
                routing_key=routing_key,
                percentage=provider.published_rollout_percentage,
            ):
                return None
            credential_id = version.snapshot["credentialVersionId"]
            if not isinstance(credential_id, str):
                return None
            return ResolvedProvider(
                provider_id=provider.provider_id,
                kind=provider.kind,
                configuration=configuration,
                credentials=await self._credentials(credential_id),
                resource_version=version.resource_version,
                retry_limit=int(version.snapshot["retryLimit"]),
            )
        return None

    def in_rollout(self, *, provider_id: str, routing_key: str, percentage: int) -> bool:
        digest = new_hmac(
            self._rollout_key,
            f"{provider_id}:{routing_key}".encode(),
            sha256,
        ).digest()
        return int.from_bytes(digest[:8], "big") % 100 < percentage

    async def _candidates(
        self,
        *,
        kind: str,
        now: datetime,
    ) -> list[tuple[ProviderRecord, ProviderVersionRecord]]:
        providers = list(
            (
                await self._session.scalars(
                    select(ProviderRecord).where(
                        ProviderRecord.kind == kind,
                        ProviderRecord.published_resource_version.is_not(None),
                        ProviderRecord.published_rollout_percentage > 0,
                        ProviderRecord.published_effective_at.is_not(None),
                        ProviderRecord.published_effective_at <= now,
                    )
                )
            ).all()
        )
        candidates: list[tuple[ProviderRecord, ProviderVersionRecord]] = []
        for provider in providers:
            version = await self._session.scalar(
                select(ProviderVersionRecord).where(
                    ProviderVersionRecord.provider_id == provider.provider_id,
                    ProviderVersionRecord.resource_version == provider.published_resource_version,
                    ProviderVersionRecord.was_published.is_(True),
                )
            )
            if version is not None:
                candidates.append((provider, version))
        return candidates

    async def _credentials(self, credential_id: str) -> dict[str, str]:
        credential = await self._session.get(ProviderCredentialVersionRecord, credential_id)
        if credential is None:
            raise ApiError(
                status_code=503,
                code="PROVIDER_CREDENTIALS_UNAVAILABLE",
                message="Published provider credentials are unavailable.",
            )
        value = loads(self._cipher.decrypt(credential.encrypted_payload))
        if not isinstance(value, dict) or not all(
            isinstance(key, str) and isinstance(item, str) for key, item in value.items()
        ):
            raise ApiError(
                status_code=503,
                code="PROVIDER_CREDENTIALS_INVALID",
                message="Published provider credentials are invalid.",
            )
        return value


class SmtpTransport:
    async def send(
        self,
        *,
        configuration: dict[str, Any],
        credentials: dict[str, str],
        destination: str,
        subject: str,
        text_body: str,
        html_body: str | None,
    ) -> None:
        await to_thread(
            self._send_sync,
            configuration,
            credentials,
            destination,
            subject,
            text_body,
            html_body,
        )

    @staticmethod
    def _send_sync(
        configuration: dict[str, Any],
        credentials: dict[str, str],
        destination: str,
        subject: str,
        text_body: str,
        html_body: str | None,
    ) -> None:
        message = EmailMessage()
        message["From"] = formataddr(
            (str(configuration["senderName"]), str(configuration["senderAddress"]))
        )
        message["To"] = destination
        message["Subject"] = subject
        reply_to = configuration.get("replyToAddress")
        if reply_to:
            message["Reply-To"] = str(reply_to)
        message.set_content(text_body)
        if html_body is not None:
            message.add_alternative(html_body, subtype="html")

        host = str(configuration["host"])
        port = int(configuration["port"])
        timeout = int(configuration["timeoutMs"]) / 1000
        tls_mode = str(configuration["tlsMode"])
        context = create_default_context()
        client: SMTP
        if tls_mode == "IMPLICIT":
            client = SMTP_SSL(host=host, port=port, timeout=timeout, context=context)
        else:
            client = SMTP(host=host, port=port, timeout=timeout)
        with client:
            if tls_mode in {"REQUIRED", "STARTTLS"}:
                client.ehlo()
                client.starttls(context=context)
                client.ehlo()
            client.login(credentials["username"], credentials["password"])
            client.send_message(message)


class RegistryEmailSender:
    def __init__(
        self,
        *,
        session: AsyncSession,
        settings: Settings,
        smtp_transport: SmtpTransport | None = None,
    ) -> None:
        self._session = session
        self._resolver = PublishedProviderResolver(session=session, settings=settings)
        self._smtp = smtp_transport or SmtpTransport()

    async def available(self) -> bool:
        return await self._resolver.has_effective(kind="EMAIL", adapter_types={"SMTP"})

    async def send_login_code(
        self,
        *,
        email_normalized: str,
        code: str,
        locale: str,
    ) -> None:
        provider = await self._resolver.resolve(
            kind="EMAIL",
            routing_key=email_normalized,
            adapter_types={"SMTP"},
        )
        if provider is None:
            raise ApiError(
                status_code=503,
                code="EMAIL_PROVIDER_UNAVAILABLE",
                message="Email delivery is temporarily unavailable.",
                retryable=True,
            )
        runtime_config = await RuntimeConfigService(self._session).get_published()
        template = runtime_config.auth_templates.email_login.for_locale(locale)
        await self._smtp.send(
            configuration=provider.configuration,
            credentials=provider.credentials,
            destination=email_normalized,
            subject=template.subject.format(code=code),
            text_body=template.text_template.format(code=code),
            html_body=(
                template.html_template.format(code=code)
                if template.html_template is not None
                else None
            ),
        )


class ProviderAdapterHealthChecker:
    def __init__(self, smtp_transport: SmtpTransport | None = None) -> None:
        self._smtp = smtp_transport or SmtpTransport()

    async def check(
        self,
        *,
        kind: str,
        configuration: dict[str, Any],
        credentials: dict[str, str],
        administrator_test_destination: str | None,
    ) -> ProviderHealthResult:
        adapter_type = configuration.get("adapterType")
        if kind != "EMAIL" or adapter_type != "SMTP":
            raise ApiError(
                status_code=503,
                code="PROVIDER_ADAPTER_UNAVAILABLE",
                message="Provider health adapter is not implemented.",
                retryable=False,
            )
        if administrator_test_destination is None:
            raise ApiError(
                status_code=400,
                code="ADMIN_TEST_DESTINATION_REQUIRED",
                message="An administrator test destination is required.",
            )
        await self._smtp.send(
            configuration=configuration,
            credentials=credentials,
            destination=administrator_test_destination,
            subject="Love Reply provider health check",
            text_body="The configured SMTP provider accepted this health-check message.",
            html_body=None,
        )
        return ProviderHealthResult(
            status="HEALTHY",
            redacted_summary="TLS authentication and synthetic delivery succeeded.",
        )
