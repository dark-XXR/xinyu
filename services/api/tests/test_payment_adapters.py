"""易支付签名、查询、退款和回调校验的无网络单元测试。"""

from datetime import UTC, datetime
from hashlib import md5
from typing import Any
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
from love_reply_api.application.errors import ApiError
from love_reply_api.application.payment_adapters import EpayTransport

CONFIGURATION: dict[str, Any] = {
    "adapterType": "EPAY_COMPAT",
    "gatewayBaseUrl": "https://pay.example.test",
    "submitPath": "/submit.php",
    "queryPath": "/api/query",
    "refundPath": "/api/refund",
    "merchantId": "merchant-1001",
    "applicationId": "app-2002",
    "paymentTypes": ["ALIPAY", "WECHAT_PAY"],
    "signingPreset": "EPAY_MD5_CANONICAL",
    "callbackAckText": "success",
    "notifyUrl": "https://api.example.test/webhooks/v1/payments/epay/prv_payment",
    "returnUrl": "https://app.example.test/payment/result",
    "callbackTimeWindowSeconds": 600,
    "timeoutMs": 10000,
}
CREDENTIALS = {"merchantKey": "merchant-secret"}
NOW = datetime(2026, 8, 9, 12, 30, tzinfo=UTC)


def _factory(handler: Any) -> Any:
    def factory(**kwargs: Any) -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=httpx.MockTransport(handler), **kwargs)

    return factory


def _signed_callback(**overrides: str) -> dict[str, str]:
    form = {
        "pid": "merchant-1001",
        "trade_no": "provider-trade-1",
        "out_trade_no": "ord_00000001",
        "type": "alipay",
        "name": "VIP Standard Monthly",
        "money": "19.90",
        "trade_status": "TRADE_SUCCESS",
        "timestamp": str(int(NOW.timestamp())),
        "sign_type": "MD5",
    }
    form.update(overrides)
    canonical = "&".join(
        f"{key}={value}"
        for key, value in sorted(form.items())
        if key not in {"sign", "sign_type"} and value != ""
    )
    form["sign"] = md5(f"{canonical}merchant-secret".encode()).hexdigest()  # noqa: S324
    return form


def test_checkout_url_binds_immutable_order_facts() -> None:
    transport = EpayTransport(now_factory=lambda: NOW)
    result = transport.create_checkout(
        configuration=CONFIGURATION,
        credentials=CREDENTIALS,
        order_id="ord_00000001",
        product_name="VIP Standard Monthly",
        amount_minor=1990,
        currency="CNY",
        payment_method="ALIPAY",
    )

    parsed = urlsplit(result.checkout_url)
    assert parsed.path == "/submit.php"
    query = {key: values[0] for key, values in parse_qs(parsed.query).items()}
    assert query["out_trade_no"] == "ord_00000001"
    assert query["money"] == "19.90"
    assert query["type"] == "alipay"
    assert query["notify_url"] == CONFIGURATION["notifyUrl"]
    assert query["return_url"] == CONFIGURATION["returnUrl"]
    assert query["sign_type"] == "MD5"
    assert "merchant-secret" not in result.checkout_url
    assert query["sign"]


def test_callback_uses_constant_fact_validation_and_exact_minor_units() -> None:
    transport = EpayTransport(now_factory=lambda: NOW)
    callback = transport.verify_callback(
        configuration=CONFIGURATION,
        credentials=CREDENTIALS,
        form=_signed_callback(buyer_id="payer-fixture-01"),
    )

    assert callback.merchant_id == "merchant-1001"
    assert callback.order_id == "ord_00000001"
    assert callback.amount_minor == 1990
    assert callback.payment_method == "ALIPAY"
    assert callback.occurred_at == NOW
    assert callback.payer_reference == "payer-fixture-01"


@pytest.mark.parametrize(
    ("override", "expected_code"),
    [
        ({"sign": "0" * 32}, "PAYMENT_SIGNATURE_INVALID"),
        ({"pid": "another-merchant"}, "PAYMENT_CALLBACK_INVALID"),
        ({"trade_status": "WAIT_BUYER_PAY"}, "PAYMENT_CALLBACK_INVALID"),
        ({"money": "19.999"}, "PAYMENT_CALLBACK_INVALID"),
    ],
)
def test_callback_rejects_conflicting_or_invalid_facts(
    override: dict[str, str], expected_code: str
) -> None:
    transport = EpayTransport(now_factory=lambda: NOW)
    form = _signed_callback(**override)
    if "sign" in override:
        form["sign"] = override["sign"]
    with pytest.raises(ApiError) as captured:
        transport.verify_callback(
            configuration=CONFIGURATION,
            credentials=CREDENTIALS,
            form=form,
        )
    assert captured.value.code == expected_code


def test_callback_rejects_stale_timestamp() -> None:
    transport = EpayTransport(now_factory=lambda: NOW)
    stale = str(int(NOW.timestamp()) - 601)
    with pytest.raises(ApiError) as captured:
        transport.verify_callback(
            configuration=CONFIGURATION,
            credentials=CREDENTIALS,
            form=_signed_callback(timestamp=stale),
        )
    assert captured.value.code == "PAYMENT_CALLBACK_STALE"


@pytest.mark.asyncio
async def test_query_and_refund_map_provider_results_without_trusting_browser() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/api/query":
            return httpx.Response(
                200,
                json={
                    "code": 1,
                    "status": 1,
                    "trade_no": "provider-trade-1",
                    "out_trade_no": "ord_00000001",
                    "type": "wxpay",
                    "money": "19.90",
                },
            )
        return httpx.Response(
            200,
            json={"code": 1, "refund_no": "provider-refund-1"},
        )

    transport = EpayTransport(client_factory=_factory(handler), now_factory=lambda: NOW)
    payment = await transport.query(
        configuration=CONFIGURATION,
        credentials=CREDENTIALS,
        order_id="ord_00000001",
    )
    refund = await transport.refund(
        configuration=CONFIGURATION,
        credentials=CREDENTIALS,
        order_id="ord_00000001",
        provider_transaction_id="provider-trade-1",
        amount_minor=990,
        currency="CNY",
    )

    assert payment.status == "SUCCEEDED"
    assert payment.amount_minor == 1990
    assert payment.payment_method == "WECHAT_PAY"
    assert refund.succeeded is True
    assert refund.provider_refund_id == "provider-refund-1"
    query_form = parse_qs(requests[0].content.decode())
    refund_form = parse_qs(requests[1].content.decode())
    assert query_form["out_trade_no"] == ["ord_00000001"]
    assert refund_form["money"] == ["9.90"]
    assert query_form["sign"][0]
    assert refund_form["sign"][0]
    assert "merchant-secret" not in requests[0].content.decode()


@pytest.mark.asyncio
async def test_provider_error_body_and_merchant_key_are_redacted() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        del request
        return httpx.Response(503, text="merchant-secret order ord_00000001")

    transport = EpayTransport(client_factory=_factory(handler))
    with pytest.raises(ApiError) as captured:
        await transport.query(
            configuration=CONFIGURATION,
            credentials=CREDENTIALS,
            order_id="ord_00000001",
        )

    assert captured.value.retryable is True
    assert "merchant-secret" not in captured.value.message
    assert "ord_00000001" not in captured.value.message
