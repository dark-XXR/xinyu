import json
from typing import Any

import httpx
import pytest
from love_reply_api.application.ai_gateway import AiHttpTransport
from love_reply_api.application.errors import ApiError
from love_reply_api.application.provider_runtime import ResolvedProvider


def _provider(adapter: str) -> ResolvedProvider:
    configuration: dict[str, Any] = {"adapterType": adapter, "timeoutMs": 10000}
    if adapter == "OPENAI_COMPAT":
        configuration["baseUrl"] = "https://gateway.example.test/v1"
        configuration["organization"] = "org_test"
        configuration["project"] = "project_test"
    return ResolvedProvider(
        provider_id=f"prv_{adapter.lower()}",
        kind="AI",
        configuration=configuration,
        credentials={"apiKey": "secret-api-key"},
        resource_version=3,
        retry_limit=1,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("adapter", "expected_path", "response_body", "expected_tokens"),
    [
        (
            "OPENAI_COMPAT",
            "/v1/chat/completions",
            {
                "choices": [{"message": {"content": '{"ok":true}'}}],
                "usage": {"prompt_tokens": 11, "completion_tokens": 7},
            },
            (11, 7),
        ),
        (
            "OPENAI",
            "/v1/chat/completions",
            {
                "choices": [{"message": {"content": '{"ok":true}'}}],
                "usage": {"prompt_tokens": 12, "completion_tokens": 8},
            },
            (12, 8),
        ),
        (
            "ANTHROPIC",
            "/v1/messages",
            {
                "content": [{"type": "text", "text": '{"ok":true}'}],
                "usage": {"input_tokens": 13, "output_tokens": 9},
            },
            (13, 9),
        ),
        (
            "GEMINI",
            "/v1beta/models/provider-model:generateContent",
            {
                "candidates": [{"content": {"parts": [{"text": '{"ok":true}'}]}}],
                "usageMetadata": {"promptTokenCount": 14, "candidatesTokenCount": 10},
            },
            (14, 10),
        ),
    ],
)
async def test_ai_transport_maps_adapter_protocols_and_usage(
    adapter: str,
    expected_path: str,
    response_body: dict[str, Any],
    expected_tokens: tuple[int, int],
) -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json=response_body,
            headers={"x-request-id": "upstream-request"},
        )

    def factory(**kwargs: Any) -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=httpx.MockTransport(handler), **kwargs)

    transport = AiHttpTransport(client_factory=factory)
    result = await transport.generate(
        provider=_provider(adapter),
        provider_model_name="provider-model",
        system_prompt="Return structured JSON.",
        user_prompt="Generate three candidates.",
        max_output_tokens=1600,
        timeout_ms=20000,
    )

    assert result.text == '{"ok":true}'
    assert (result.input_tokens, result.output_tokens) == expected_tokens
    assert result.provider_request_id == "upstream-request"
    assert len(requests) == 1
    request = requests[0]
    assert request.url.path == expected_path
    body = json.loads(request.content)
    if adapter in {"OPENAI", "OPENAI_COMPAT"}:
        assert request.headers["authorization"] == "Bearer secret-api-key"
        assert body["model"] == "provider-model"
        assert body["max_tokens"] == 1600
    elif adapter == "ANTHROPIC":
        assert request.headers["x-api-key"] == "secret-api-key"
        assert body["model"] == "provider-model"
        assert body["max_tokens"] == 1600
    else:
        assert request.headers["x-goog-api-key"] == "secret-api-key"
        assert body["generationConfig"]["maxOutputTokens"] == 1600


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "expected_code", "retryable"),
    [
        (400, "AI_PROVIDER_REQUEST_REJECTED", False),
        (429, "AI_PROVIDER_RATE_LIMITED", True),
        (503, "AI_PROVIDER_UPSTREAM_ERROR", True),
    ],
)
async def test_ai_transport_classifies_upstream_failures_without_body_leakage(
    status: int,
    expected_code: str,
    retryable: bool,
) -> None:
    sensitive_body = "upstream-secret-diagnostic"

    def handler(request: httpx.Request) -> httpx.Response:
        del request
        return httpx.Response(status, text=sensitive_body)

    def factory(**kwargs: Any) -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=httpx.MockTransport(handler), **kwargs)

    with pytest.raises(ApiError) as captured:
        await AiHttpTransport(client_factory=factory).generate(
            provider=_provider("OPENAI"),
            provider_model_name="provider-model",
            system_prompt="system",
            user_prompt="user",
            max_output_tokens=100,
            timeout_ms=1000,
        )

    assert captured.value.code == expected_code
    assert captured.value.retryable is retryable
    assert sensitive_body not in captured.value.message


@pytest.mark.asyncio
async def test_ai_transport_marks_timeouts_retryable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("synthetic timeout", request=request)

    def factory(**kwargs: Any) -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=httpx.MockTransport(handler), **kwargs)

    with pytest.raises(ApiError) as captured:
        await AiHttpTransport(client_factory=factory).generate(
            provider=_provider("GEMINI"),
            provider_model_name="provider-model",
            system_prompt="system",
            user_prompt="user",
            max_output_tokens=100,
            timeout_ms=1000,
        )

    assert captured.value.code == "AI_PROVIDER_TIMEOUT"
    assert captured.value.retryable is True
