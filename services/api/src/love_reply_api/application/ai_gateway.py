import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from math import ceil
from time import monotonic
from typing import Any
from uuid import uuid4

from httpx import AsyncClient, HTTPError, Response, TimeoutException
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from love_reply_api.application.errors import ApiError
from love_reply_api.application.generation import GeneratedCandidate, ModelGeneration
from love_reply_api.application.provider_runtime import PublishedProviderResolver, ResolvedProvider
from love_reply_api.config import Settings
from love_reply_api.domain.generation import ReplyStrategy, SafetyStatus
from love_reply_api.infrastructure.ai_gateway_records import (
    AiGatewayAttemptRecord,
    AiModelMappingRecord,
    AiPromptRecord,
    AiRouteRecord,
)

AI_ADAPTER_TYPES = {"OPENAI_COMPAT", "OPENAI", "ANTHROPIC", "GEMINI"}


class CandidatePayload(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    strategy: ReplyStrategy
    style_id: str = Field(alias="styleId", min_length=1, max_length=64)
    text: str = Field(min_length=1, max_length=5000)
    safety_status: SafetyStatus = Field(alias="safetyStatus")


class GenerationPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    possible_intent: str = Field(alias="possibleIntent", min_length=1, max_length=2000)
    emotion: str = Field(min_length=1, max_length=1000)
    uncertainty_note: str = Field(alias="uncertaintyNote", min_length=1, max_length=2000)
    risk_tips: list[str] = Field(alias="riskTips", max_length=20)
    candidates: list[CandidatePayload] = Field(min_length=3, max_length=3)

    @model_validator(mode="after")
    def require_strategies(self) -> "GenerationPayload":
        strategies = {item.strategy for item in self.candidates}
        if strategies != {ReplyStrategy.SAFE, ReplyStrategy.PUSH_PULL, ReplyStrategy.DIRECT}:
            raise ValueError("generation must contain the three required strategies")
        return self


@dataclass(frozen=True, slots=True)
class AiTransportResult:
    text: str
    input_tokens: int
    output_tokens: int
    provider_request_id: str | None = None


class AiHttpTransport:
    def __init__(
        self,
        client_factory: Callable[..., AsyncClient] = AsyncClient,
    ) -> None:
        self._client_factory = client_factory

    async def generate(
        self,
        *,
        provider: ResolvedProvider,
        provider_model_name: str,
        system_prompt: str,
        user_prompt: str,
        max_output_tokens: int,
        timeout_ms: int,
    ) -> AiTransportResult:
        adapter = str(provider.configuration["adapterType"])
        url, headers, payload = self._request(
            adapter=adapter,
            configuration=provider.configuration,
            credentials=provider.credentials,
            provider_model_name=provider_model_name,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_output_tokens=max_output_tokens,
        )
        try:
            async with self._client_factory(timeout=timeout_ms / 1000) as client:
                response = await client.post(url, headers=headers, json=payload)
        except TimeoutException as exc:
            raise self._failure("AI_PROVIDER_TIMEOUT", "AI provider timed out.", True) from exc
        except HTTPError as exc:
            raise self._failure(
                "AI_PROVIDER_NETWORK_ERROR", "AI provider network request failed.", True
            ) from exc
        if response.status_code == 429:
            raise self._failure(
                "AI_PROVIDER_RATE_LIMITED", "AI provider rate limited the request.", True
            )
        if response.status_code >= 500:
            raise self._failure("AI_PROVIDER_UPSTREAM_ERROR", "AI provider is unavailable.", True)
        if not response.is_success:
            raise self._failure(
                "AI_PROVIDER_REQUEST_REJECTED", "AI provider rejected the request.", False
            )
        return self._response(adapter=adapter, response=response)

    @staticmethod
    def _failure(code: str, message: str, retryable: bool) -> ApiError:
        return ApiError(status_code=503, code=code, message=message, retryable=retryable)

    def _request(
        self,
        *,
        adapter: str,
        configuration: dict[str, Any],
        credentials: dict[str, str],
        provider_model_name: str,
        system_prompt: str,
        user_prompt: str,
        max_output_tokens: int,
    ) -> tuple[str, dict[str, str], dict[str, Any]]:
        api_key = credentials.get("apiKey")
        if not api_key:
            raise self._failure(
                "AI_PROVIDER_CREDENTIALS_INVALID", "AI provider credentials are invalid.", False
            )
        if adapter in {"OPENAI", "OPENAI_COMPAT"}:
            default = "https://api.openai.com/v1" if adapter == "OPENAI" else None
            base_url = configuration.get("baseUrl") or default
            if not isinstance(base_url, str):
                raise self._failure(
                    "AI_PROVIDER_CONFIGURATION_INVALID", "AI provider URL is missing.", False
                )
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            organization = configuration.get("organization")
            project = configuration.get("project")
            if organization:
                headers["OpenAI-Organization"] = str(organization)
            if project:
                headers["OpenAI-Project"] = str(project)
            return (
                f"{base_url.rstrip('/')}/chat/completions",
                headers,
                {
                    "model": provider_model_name,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "max_tokens": max_output_tokens,
                    "response_format": {"type": "json_object"},
                },
            )
        if adapter == "ANTHROPIC":
            base_url = str(configuration.get("baseUrl") or "https://api.anthropic.com/v1")
            return (
                f"{base_url.rstrip('/')}/messages",
                {
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                {
                    "model": provider_model_name,
                    "system": system_prompt,
                    "messages": [{"role": "user", "content": user_prompt}],
                    "max_tokens": max_output_tokens,
                },
            )
        if adapter == "GEMINI":
            base_url = str(
                configuration.get("baseUrl") or "https://generativelanguage.googleapis.com/v1beta"
            )
            return (
                f"{base_url.rstrip('/')}/models/{provider_model_name}:generateContent",
                {"x-goog-api-key": api_key, "Content-Type": "application/json"},
                {
                    "systemInstruction": {"parts": [{"text": system_prompt}]},
                    "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
                    "generationConfig": {
                        "maxOutputTokens": max_output_tokens,
                        "responseMimeType": "application/json",
                    },
                },
            )
        raise self._failure(
            "AI_PROVIDER_ADAPTER_UNSUPPORTED", "AI provider adapter is unsupported.", False
        )

    def _response(self, *, adapter: str, response: Response) -> AiTransportResult:
        try:
            body = response.json()
            if adapter in {"OPENAI", "OPENAI_COMPAT"}:
                text = body["choices"][0]["message"]["content"]
                usage = body["usage"]
                input_tokens = usage["prompt_tokens"]
                output_tokens = usage["completion_tokens"]
            elif adapter == "ANTHROPIC":
                text = body["content"][0]["text"]
                usage = body["usage"]
                input_tokens = usage["input_tokens"]
                output_tokens = usage["output_tokens"]
            else:
                text = body["candidates"][0]["content"]["parts"][0]["text"]
                usage = body["usageMetadata"]
                input_tokens = usage["promptTokenCount"]
                output_tokens = usage["candidatesTokenCount"]
            if not isinstance(text, str):
                raise TypeError("response text is not a string")
            return AiTransportResult(
                text=text,
                input_tokens=int(input_tokens),
                output_tokens=int(output_tokens),
                provider_request_id=response.headers.get("x-request-id"),
            )
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise self._failure(
                "AI_PROVIDER_RESPONSE_INVALID", "AI provider returned an invalid response.", False
            ) from exc


class RegistryAiProvider:
    def __init__(
        self,
        *,
        session: AsyncSession,
        settings: Settings,
        transport: AiHttpTransport | None = None,
    ) -> None:
        self._session = session
        self._resolver = PublishedProviderResolver(session=session, settings=settings)
        self._transport = transport or AiHttpTransport()

    async def generate(
        self,
        *,
        input_data: dict[str, Any],
        context_data: dict[str, Any],
        model_id: str,
    ) -> ModelGeneration:
        now = datetime.now(UTC)
        routing_key = self._routing_key(input_data=input_data, context_data=context_data)
        route = await self._active_route(model_id=model_id, routing_key=routing_key, now=now)
        prompt = await self._active_prompt(scenario=route.scenario, now=now)
        input_json = json.dumps(input_data, ensure_ascii=False, separators=(",", ":"))
        context_json = json.dumps(context_data, ensure_ascii=False, separators=(",", ":"))
        estimated_input_tokens = ceil((len(input_json) + len(context_json)) / 4)
        if estimated_input_tokens > route.max_input_tokens:
            raise ApiError(
                status_code=400,
                code="AI_ROUTE_INPUT_LIMIT_EXCEEDED",
                message="Input exceeds the published AI route limit.",
            )
        system_prompt, user_prompt = self._render_prompt(
            prompt=prompt,
            input_json=input_json,
            context_json=context_json,
        )
        mappings = await self._mappings(route=route, now=now)
        attempts = 0
        reserved_cost = 0
        last_error: ApiError | None = None
        targets = sorted(route.targets, key=lambda item: -int(item["priority"]))
        for target in targets:
            mapping = mappings.get(str(target["modelMappingId"]))
            if mapping is None:
                continue
            try:
                provider = await self._resolver.resolve_by_id(
                    provider_id=mapping.provider_id,
                    routing_key=routing_key,
                    adapter_types=AI_ADAPTER_TYPES,
                    now=now,
                )
            except ApiError as error:
                last_error = error
                continue
            if provider is None:
                continue
            retries = min(int(target["retryLimit"]), provider.retry_limit)
            for _ in range(retries + 1):
                if attempts >= route.total_attempt_limit:
                    break
                projected_cost = self._cost(
                    mapping=mapping,
                    input_tokens=estimated_input_tokens,
                    output_tokens=min(route.max_output_tokens, mapping.max_output_tokens),
                )
                if reserved_cost + projected_cost > route.budget_ceiling_microunits:
                    last_error = ApiError(
                        status_code=503,
                        code="AI_ROUTE_BUDGET_EXCEEDED",
                        message="AI route budget ceiling prevents another provider attempt.",
                        retryable=False,
                    )
                    break
                attempts += 1
                reserved_cost += projected_cost
                started = monotonic()
                try:
                    result = await self._transport.generate(
                        provider=provider,
                        provider_model_name=mapping.provider_model_name,
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                        max_output_tokens=min(route.max_output_tokens, mapping.max_output_tokens),
                        timeout_ms=int(target["timeoutMs"]),
                    )
                    output_limit = min(route.max_output_tokens, mapping.max_output_tokens)
                    if (
                        result.input_tokens > route.max_input_tokens
                        or result.output_tokens > output_limit
                    ):
                        raise ApiError(
                            status_code=503,
                            code="AI_PROVIDER_TOKEN_LIMIT_EXCEEDED",
                            message="AI provider usage exceeded the published token limit.",
                            retryable=False,
                        )
                    actual_cost = self._cost(
                        mapping=mapping,
                        input_tokens=result.input_tokens,
                        output_tokens=result.output_tokens,
                    )
                    total_cost = reserved_cost - projected_cost + actual_cost
                    if total_cost > route.budget_ceiling_microunits:
                        raise ApiError(
                            status_code=503,
                            code="AI_PROVIDER_COST_LIMIT_EXCEEDED",
                            message="AI provider usage exceeded the published route budget.",
                            retryable=False,
                        )
                    payload = self._validate_payload(result.text)
                    await self._record_attempt(
                        route=route,
                        mapping=mapping,
                        provider=provider,
                        routing_key=routing_key,
                        attempt_number=attempts,
                        status="SUCCEEDED",
                        error_code=None,
                        input_tokens=result.input_tokens,
                        output_tokens=result.output_tokens,
                        cost_microunits=actual_cost,
                        started=started,
                    )
                    return self._generation(payload, result)
                except ApiError as error:
                    last_error = error
                    await self._record_attempt(
                        route=route,
                        mapping=mapping,
                        provider=provider,
                        routing_key=routing_key,
                        attempt_number=attempts,
                        status="FAILED",
                        error_code=error.code,
                        input_tokens=None,
                        output_tokens=None,
                        cost_microunits=projected_cost,
                        started=started,
                    )
                    if not error.retryable:
                        raise
            if attempts >= route.total_attempt_limit:
                break
        if last_error is not None and last_error.code == "AI_ROUTE_BUDGET_EXCEEDED":
            raise last_error
        raise ApiError(
            status_code=503,
            code="AI_PROVIDER_UNAVAILABLE",
            message="No published AI provider completed the request.",
            retryable=True,
            details={"lastErrorCode": last_error.code if last_error is not None else None},
        )

    async def _active_route(
        self, *, model_id: str, routing_key: str, now: datetime
    ) -> AiRouteRecord:
        routes = list(
            await self._session.scalars(
                select(AiRouteRecord)
                .where(
                    AiRouteRecord.scenario == "REPLY_GENERATION",
                    AiRouteRecord.logical_model_id == model_id,
                    AiRouteRecord.status == "ACTIVE",
                    AiRouteRecord.effective_at.is_not(None),
                    AiRouteRecord.effective_at <= now,
                )
                .order_by(AiRouteRecord.version.desc())
            )
        )
        for route in routes:
            if self._resolver.in_rollout(
                provider_id=route.route_id,
                routing_key=routing_key,
                percentage=route.rollout_percentage,
            ):
                return route
        raise ApiError(
            status_code=503,
            code="AI_ROUTE_UNAVAILABLE",
            message="No published AI route is available.",
            retryable=True,
        )

    async def _active_prompt(self, *, scenario: str, now: datetime) -> AiPromptRecord:
        prompt = await self._session.scalar(
            select(AiPromptRecord)
            .where(
                AiPromptRecord.scenario == scenario,
                AiPromptRecord.status == "ACTIVE",
                AiPromptRecord.effective_at.is_not(None),
                AiPromptRecord.effective_at <= now,
            )
            .order_by(AiPromptRecord.version.desc())
            .limit(1)
        )
        if prompt is None:
            raise ApiError(
                status_code=503,
                code="AI_PROMPT_UNAVAILABLE",
                message="No published AI prompt is available.",
                retryable=True,
            )
        return prompt

    async def _mappings(
        self, *, route: AiRouteRecord, now: datetime
    ) -> dict[str, AiModelMappingRecord]:
        ids = [str(item["modelMappingId"]) for item in route.targets]
        rows = await self._session.scalars(
            select(AiModelMappingRecord).where(
                AiModelMappingRecord.model_mapping_id.in_(ids),
                AiModelMappingRecord.logical_model_id == route.logical_model_id,
                AiModelMappingRecord.status == "ACTIVE",
                AiModelMappingRecord.enabled.is_(True),
                AiModelMappingRecord.effective_at.is_not(None),
                AiModelMappingRecord.effective_at <= now,
            )
        )
        return {row.model_mapping_id: row for row in rows}

    @staticmethod
    def _render_prompt(
        *, prompt: AiPromptRecord, input_json: str, context_json: str
    ) -> tuple[str, str]:
        values = {"inputJson": input_json, "contextJson": context_json}
        try:
            return prompt.system_template.format_map(values), prompt.user_template.format_map(
                values
            )
        except (KeyError, ValueError) as exc:
            raise ApiError(
                status_code=503,
                code="AI_PROMPT_INVALID",
                message="Published AI prompt placeholders are invalid.",
                retryable=False,
            ) from exc

    @staticmethod
    def _validate_payload(text: str) -> GenerationPayload:
        try:
            return GenerationPayload.model_validate(json.loads(text))
        except (json.JSONDecodeError, ValidationError) as exc:
            raise ApiError(
                status_code=503,
                code="AI_PROVIDER_RESPONSE_SCHEMA_INVALID",
                message="AI provider output did not match the published schema.",
                retryable=False,
            ) from exc

    @staticmethod
    def _generation(payload: GenerationPayload, result: AiTransportResult) -> ModelGeneration:
        return ModelGeneration(
            possible_intent=payload.possible_intent,
            emotion=payload.emotion,
            uncertainty_note=payload.uncertainty_note,
            risk_tips=payload.risk_tips,
            candidates=[
                GeneratedCandidate(
                    strategy=item.strategy,
                    style_id=item.style_id,
                    text=item.text,
                    safety_status=item.safety_status,
                )
                for item in payload.candidates
            ],
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
        )

    @staticmethod
    def _routing_key(*, input_data: dict[str, Any], context_data: dict[str, Any]) -> str:
        canonical = json.dumps(
            {"input": input_data, "context": context_data},
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        return sha256(canonical.encode()).hexdigest()

    @staticmethod
    def _cost(*, mapping: AiModelMappingRecord, input_tokens: int, output_tokens: int) -> int:
        weighted = (
            input_tokens * mapping.input_cost_microunits_per_million_tokens
            + output_tokens * mapping.output_cost_microunits_per_million_tokens
        )
        return ceil(weighted / 1_000_000)

    async def _record_attempt(
        self,
        *,
        route: AiRouteRecord,
        mapping: AiModelMappingRecord,
        provider: ResolvedProvider,
        routing_key: str,
        attempt_number: int,
        status: str,
        error_code: str | None,
        input_tokens: int | None,
        output_tokens: int | None,
        cost_microunits: int | None,
        started: float,
    ) -> None:
        self._session.add(
            AiGatewayAttemptRecord(
                attempt_id=f"aiatt_{uuid4().hex}",
                routing_key_hash=routing_key,
                route_id=route.route_id,
                route_version=route.version,
                model_mapping_id=mapping.model_mapping_id,
                provider_id=provider.provider_id,
                provider_resource_version=provider.resource_version,
                attempt_number=attempt_number,
                status=status,
                error_code=error_code,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_microunits=cost_microunits,
                latency_ms=max(0, round((monotonic() - started) * 1000)),
                created_at=datetime.now(UTC),
            )
        )
        await self._session.commit()
