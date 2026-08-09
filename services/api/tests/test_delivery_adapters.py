"""邮件 API 与短信签名适配器的无网络单元测试。"""

import json
from datetime import UTC, datetime
from typing import Any
from urllib.parse import parse_qs

import httpx
import pytest
from love_reply_api.application.delivery_adapters import EmailApiTransport, SmsApiTransport
from love_reply_api.application.errors import ApiError


def _factory(
    handler: Any,
) -> Any:
    def factory(**kwargs: Any) -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=httpx.MockTransport(handler), **kwargs)

    return factory


@pytest.mark.asyncio
async def test_sendgrid_transport_maps_authenticated_message() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(202, headers={"x-request-id": "sendgrid-request"})

    transport = EmailApiTransport(client_factory=_factory(handler))
    result = await transport.send(
        configuration={
            "adapterType": "SENDGRID_API",
            "baseUrl": "https://sendgrid.example.test",
            "senderAddress": "noreply@example.com",
            "senderName": "心语助手",
            "timeoutMs": 10000,
        },
        credentials={"apiKey": "sendgrid-secret"},
        destination="user@example.com",
        subject="登录验证码",
        text_body="验证码 123456",
        html_body="<strong>123456</strong>",
    )

    assert result.provider_request_id == "sendgrid-request"
    request = requests[0]
    assert request.url.path == "/v3/mail/send"
    assert request.headers["authorization"] == "Bearer sendgrid-secret"
    payload = json.loads(request.content)
    assert payload["personalizations"][0]["to"][0]["email"] == "user@example.com"
    assert {item["type"] for item in payload["content"]} == {
        "text/plain",
        "text/html",
    }


@pytest.mark.asyncio
async def test_ses_transport_uses_signature_v4_without_leaking_secret() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, headers={"x-amzn-requestid": "ses-request"})

    fixed_now = datetime(2026, 8, 9, 12, 30, tzinfo=UTC)
    transport = EmailApiTransport(client_factory=_factory(handler), now_factory=lambda: fixed_now)
    result = await transport.send(
        configuration={
            "adapterType": "SES_API",
            "region": "us-east-1",
            "baseUrl": None,
            "senderAddress": "noreply@example.com",
            "senderName": "Love Reply",
            "timeoutMs": 10000,
        },
        credentials={
            "accessKeyId": "AKIDEXAMPLE",
            "accessKeySecret": "aws-secret-value",
        },
        destination="user@example.com",
        subject="Login code",
        text_body="Code 123456",
        html_body=None,
    )

    assert result.provider_request_id == "ses-request"
    request = requests[0]
    assert request.url.host == "email.us-east-1.amazonaws.com"
    assert request.url.path == "/v2/email/outbound-emails"
    assert request.headers["x-amz-date"] == "20260809T123000Z"
    assert (
        "Credential=AKIDEXAMPLE/20260809/us-east-1/ses/aws4_request"
        in request.headers["authorization"]
    )
    assert "aws-secret-value" not in request.headers["authorization"]


@pytest.mark.asyncio
async def test_resend_and_mailgun_use_their_native_protocols() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path.endswith("/emails"):
            return httpx.Response(200, json={"id": "resend-id"})
        return httpx.Response(200, json={"id": "mailgun-id"})

    transport = EmailApiTransport(client_factory=_factory(handler))
    resend = await transport.send(
        configuration={
            "adapterType": "RESEND_API",
            "baseUrl": None,
            "senderAddress": "noreply@example.com",
            "senderName": "Love Reply",
            "timeoutMs": 10000,
        },
        credentials={"apiKey": "resend-secret"},
        destination="user@example.com",
        subject="Code",
        text_body="123456",
        html_body=None,
    )
    mailgun = await transport.send(
        configuration={
            "adapterType": "MAILGUN_API",
            "baseUrl": "https://api.mailgun.net/v3/mg.example.com",
            "senderAddress": "noreply@example.com",
            "senderName": "Love Reply",
            "timeoutMs": 10000,
        },
        credentials={"apiKey": "mailgun-secret"},
        destination="user@example.com",
        subject="Code",
        text_body="123456",
        html_body=None,
    )

    assert resend.provider_request_id == "resend-id"
    assert mailgun.provider_request_id == "mailgun-id"
    assert requests[0].url.path == "/emails"
    assert requests[1].url.path == "/v3/mg.example.com/messages"
    assert requests[1].headers["authorization"].startswith("Basic ")


@pytest.mark.asyncio
async def test_aliyun_sms_signs_rpc_request() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"Code": "OK", "RequestId": "aliyun-request"})

    transport = SmsApiTransport(
        client_factory=_factory(handler),
        now_factory=lambda: datetime(2026, 8, 9, 12, 30, tzinfo=UTC),
        nonce_factory=lambda: "fixed-nonce",
    )
    result = await transport.send_login_code(
        configuration={
            "adapterType": "ALIYUN_SMS",
            "region": "cn-hangzhou",
            "applicationId": None,
            "signatureId": "心语助手",
            "templateId": "SMS_123456",
            "timeoutMs": 10000,
        },
        credentials={
            "accessKeyId": "aliyun-access-id",
            "accessKeySecret": "aliyun-secret",
        },
        phone_e164="+8613800000000",
        code="123456",
    )

    assert result.provider_request_id == "aliyun-request"
    form = parse_qs(requests[0].content.decode())
    assert form["Action"] == ["SendSms"]
    assert form["SignatureNonce"] == ["fixed-nonce"]
    assert form["TemplateParam"] == ['{"code":"123456"}']
    assert form["Signature"][0]
    assert "aliyun-secret" not in requests[0].content.decode()


@pytest.mark.asyncio
async def test_tencent_sms_uses_tc3_signature() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "Response": {
                    "RequestId": "tencent-request",
                    "SendStatusSet": [{"Code": "Ok"}],
                }
            },
        )

    transport = SmsApiTransport(
        client_factory=_factory(handler),
        now_factory=lambda: datetime(2026, 8, 9, 12, 30, tzinfo=UTC),
    )
    result = await transport.send_login_code(
        configuration={
            "adapterType": "TENCENT_SMS",
            "region": "ap-guangzhou",
            "applicationId": "1400000000",
            "signatureId": "心语助手",
            "templateId": "123456",
            "timeoutMs": 10000,
        },
        credentials={"secretId": "tencent-id", "secretKey": "tencent-secret"},
        phone_e164="+8613800000000",
        code="123456",
    )

    assert result.provider_request_id == "tencent-request"
    request = requests[0]
    assert request.headers["x-tc-action"] == "SendSms"
    assert request.headers["x-tc-version"] == "2021-01-11"
    assert "Credential=tencent-id/2026-08-09/sms/tc3_request" in request.headers["authorization"]
    assert "tencent-secret" not in request.headers["authorization"]
    payload = json.loads(request.content)
    assert payload["TemplateParamSet"] == ["123456"]


@pytest.mark.asyncio
async def test_provider_error_does_not_expose_body_or_credentials() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        del request
        return httpx.Response(503, text="sendgrid-secret and code 123456")

    transport = EmailApiTransport(client_factory=_factory(handler))
    with pytest.raises(ApiError) as captured:
        await transport.send(
            configuration={
                "adapterType": "SENDGRID_API",
                "baseUrl": None,
                "senderAddress": "noreply@example.com",
                "senderName": "Love Reply",
                "timeoutMs": 10000,
            },
            credentials={"apiKey": "sendgrid-secret"},
            destination="user@example.com",
            subject="Code",
            text_body="123456",
            html_body=None,
        )

    assert captured.value.retryable is True
    assert "sendgrid-secret" not in captured.value.message
    assert "123456" not in captured.value.message
