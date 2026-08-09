"""易支付兼容网关的固定签名、下单、查询、退款和回调校验。

仅实现经过审查的 ``EPAY_MD5_CANONICAL`` 预设，不允许管理员上传脚本或表达式。
浏览器返回地址只负责导航，只有验签回调或主动查询结果才能进入订单结算流程。
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from hashlib import md5
from hmac import compare_digest
from json import JSONDecodeError
from re import fullmatch
from typing import Any
from urllib.parse import urlencode

from httpx import AsyncClient, HTTPError, Response, TimeoutException

from love_reply_api.application.errors import ApiError


@dataclass(frozen=True, slots=True)
class EpayCheckout:
    """客户端可打开的短期收银台地址；该地址不是付款凭证。"""

    checkout_url: str


@dataclass(frozen=True, slots=True)
class EpayPaymentState:
    """主动查询得到的脱敏支付状态。"""

    status: str
    order_id: str
    amount_minor: int
    payment_method: str
    provider_transaction_id: str | None


@dataclass(frozen=True, slots=True)
class EpayRefundState:
    """网关退款请求结果。"""

    succeeded: bool
    provider_refund_id: str | None


@dataclass(frozen=True, slots=True)
class EpayVerifiedCallback:
    """验签和字段规范化后的服务端回调事实。"""

    merchant_id: str
    provider_transaction_id: str
    order_id: str
    payment_method: str
    product_name: str
    amount_minor: int
    occurred_at: datetime | None
    payer_reference: str | None = None


class EpayTransport:
    """易支付兼容网关传输层。"""

    METHOD_CODES = {"ALIPAY": "alipay", "WECHAT_PAY": "wxpay"}
    PROVIDER_METHODS = {value: key for key, value in METHOD_CODES.items()}

    def __init__(
        self,
        client_factory: Callable[..., AsyncClient] = AsyncClient,
        now_factory: Callable[[], datetime] | None = None,
    ) -> None:
        self._client_factory = client_factory
        self._now = now_factory or (lambda: datetime.now(UTC))

    def create_checkout(
        self,
        *,
        configuration: dict[str, Any],
        credentials: dict[str, str],
        order_id: str,
        product_name: str,
        amount_minor: int,
        currency: str,
        payment_method: str,
    ) -> EpayCheckout:
        self._validate_currency(currency)
        provider_method = self._provider_method(configuration, payment_method)
        params = {
            "pid": str(configuration["merchantId"]),
            "type": provider_method,
            "out_trade_no": order_id,
            "notify_url": str(configuration["notifyUrl"]),
            "return_url": str(configuration["returnUrl"]),
            "name": product_name,
            "money": self._format_minor(amount_minor),
        }
        application_id = configuration.get("applicationId")
        if application_id:
            params["appid"] = str(application_id)
        signed = self._sign_params(params, credentials["merchantKey"])
        base_url = self._join(
            str(configuration["gatewayBaseUrl"]), str(configuration["submitPath"])
        )
        return EpayCheckout(checkout_url=f"{base_url}?{urlencode(signed)}")

    async def query(
        self,
        *,
        configuration: dict[str, Any],
        credentials: dict[str, str],
        order_id: str,
    ) -> EpayPaymentState:
        params = self._sign_params(
            {
                "act": "order",
                "pid": str(configuration["merchantId"]),
                "out_trade_no": order_id,
            },
            credentials["merchantKey"],
        )
        response = await self._post_form(
            url=self._join(str(configuration["gatewayBaseUrl"]), str(configuration["queryPath"])),
            params=params,
            timeout_ms=int(configuration["timeoutMs"]),
        )
        payload = self._provider_payload(response)
        if not self._success_code(payload.get("code")):
            raise self._provider_rejected(retryable=False)
        returned_order = str(payload.get("out_trade_no") or "")
        if returned_order != order_id:
            raise ApiError(
                status_code=409,
                code="PAYMENT_QUERY_CONFLICT",
                message="Payment provider returned another order reference.",
            )
        provider_method = str(payload.get("type") or "")
        method = self.PROVIDER_METHODS.get(provider_method)
        if method is None:
            raise self._invalid_response()
        amount_minor = self._parse_amount(payload.get("money"))
        terminal = str(payload.get("status")) in {"1", "TRADE_SUCCESS", "SUCCESS"}
        provider_transaction_id = payload.get("trade_no")
        return EpayPaymentState(
            status="SUCCEEDED" if terminal else "PENDING",
            order_id=returned_order,
            amount_minor=amount_minor,
            payment_method=method,
            provider_transaction_id=(
                str(provider_transaction_id) if provider_transaction_id is not None else None
            ),
        )

    async def health_check(
        self,
        *,
        configuration: dict[str, Any],
        credentials: dict[str, str],
    ) -> str | None:
        """用不存在的合成订单检查鉴权和查询端点，不创建真实交易。"""

        params = self._sign_params(
            {
                "act": "order",
                "pid": str(configuration["merchantId"]),
                "out_trade_no": "health_check_nonexistent",
            },
            credentials["merchantKey"],
        )
        response = await self._post_form(
            url=self._join(str(configuration["gatewayBaseUrl"]), str(configuration["queryPath"])),
            params=params,
            timeout_ms=int(configuration["timeoutMs"]),
        )
        # 业务层“不存在”仍说明网关可达且返回了结构化协议；HTML 或无效 JSON 视为失败。
        payload = self._provider_payload(response)
        request_id = payload.get("request_id") or payload.get("trace_id")
        return str(request_id) if request_id is not None else None

    async def refund(
        self,
        *,
        configuration: dict[str, Any],
        credentials: dict[str, str],
        order_id: str,
        provider_transaction_id: str,
        amount_minor: int,
        currency: str,
    ) -> EpayRefundState:
        self._validate_currency(currency)
        params = self._sign_params(
            {
                "pid": str(configuration["merchantId"]),
                "out_trade_no": order_id,
                "trade_no": provider_transaction_id,
                "money": self._format_minor(amount_minor),
            },
            credentials["merchantKey"],
        )
        response = await self._post_form(
            url=self._join(str(configuration["gatewayBaseUrl"]), str(configuration["refundPath"])),
            params=params,
            timeout_ms=int(configuration["timeoutMs"]),
        )
        payload = self._provider_payload(response)
        succeeded = self._success_code(payload.get("code"))
        if not succeeded:
            raise self._provider_rejected(retryable=False)
        refund_id = payload.get("refund_no") or payload.get("trade_no")
        return EpayRefundState(
            succeeded=True,
            provider_refund_id=str(refund_id) if refund_id is not None else None,
        )

    def verify_callback(
        self,
        *,
        configuration: dict[str, Any],
        credentials: dict[str, str],
        form: dict[str, str],
    ) -> EpayVerifiedCallback:
        required = {
            "pid",
            "trade_no",
            "out_trade_no",
            "type",
            "name",
            "money",
            "trade_status",
            "sign",
            "sign_type",
        }
        if required - form.keys():
            raise self._invalid_callback("Payment callback fields are incomplete.")
        if form["sign_type"].upper() != "MD5":
            raise self._invalid_callback("Payment callback signature type is unsupported.")
        if form["pid"] != str(configuration["merchantId"]):
            raise self._invalid_callback("Payment callback merchant does not match.")
        expected = self._signature(form, credentials["merchantKey"])
        if not compare_digest(expected.lower(), form["sign"].lower()):
            raise ApiError(
                status_code=400,
                code="PAYMENT_SIGNATURE_INVALID",
                message="Payment callback signature is invalid.",
            )
        if form["trade_status"] != "TRADE_SUCCESS":
            raise self._invalid_callback("Payment callback is not a successful terminal state.")
        payment_method = self.PROVIDER_METHODS.get(form["type"])
        if payment_method is None:
            raise self._invalid_callback("Payment callback method is unsupported.")
        occurred_at = self._callback_time(
            form.get("timestamp"), int(configuration["callbackTimeWindowSeconds"])
        )
        return EpayVerifiedCallback(
            merchant_id=form["pid"],
            provider_transaction_id=form["trade_no"],
            order_id=form["out_trade_no"],
            payment_method=payment_method,
            product_name=form["name"],
            amount_minor=self._parse_amount(form["money"]),
            occurred_at=occurred_at,
            # 部分易支付实现会返回已验签的付款方稳定标识；业务层只保存其服务端哈希。
            payer_reference=form.get("buyer_id") or form.get("buyer") or form.get("account"),
        )

    @classmethod
    def _sign_params(cls, params: dict[str, str], merchant_key: str) -> dict[str, str]:
        result = dict(params)
        result["sign"] = cls._signature(result, merchant_key)
        result["sign_type"] = "MD5"
        return result

    @staticmethod
    def _signature(params: dict[str, str], merchant_key: str) -> str:
        # 易支付标准预设：ASCII 键排序，排除签名字段和空值，末尾直接拼接商户密钥。
        canonical = "&".join(
            f"{key}={value}"
            for key, value in sorted(params.items())
            if key not in {"sign", "sign_type"} and value != ""
        )
        return md5(f"{canonical}{merchant_key}".encode()).hexdigest()  # noqa: S324

    def _callback_time(self, value: str | None, window_seconds: int) -> datetime | None:
        if value is None or value == "":
            return None
        try:
            timestamp = int(value)
            occurred_at = datetime.fromtimestamp(timestamp, UTC)
        except (OverflowError, OSError, ValueError) as exc:
            raise self._invalid_callback("Payment callback timestamp is invalid.") from exc
        difference = abs((self._now().astimezone(UTC) - occurred_at).total_seconds())
        if difference > window_seconds:
            raise ApiError(
                status_code=400,
                code="PAYMENT_CALLBACK_STALE",
                message="Payment callback is outside the configured time window.",
            )
        return occurred_at

    async def _post_form(
        self,
        *,
        url: str,
        params: dict[str, str],
        timeout_ms: int,
    ) -> Response:
        try:
            async with self._client_factory(
                timeout=timeout_ms / 1000,
                follow_redirects=False,
            ) as client:
                response = await client.post(url, data=params)
        except TimeoutException as exc:
            raise self._provider_unavailable("Payment provider request timed out.") from exc
        except HTTPError as exc:
            raise self._provider_unavailable("Payment provider network request failed.") from exc
        if response.status_code == 429 or response.status_code >= 500:
            raise self._provider_rejected(retryable=True)
        if response.status_code < 200 or response.status_code >= 300:
            raise self._provider_rejected(retryable=False)
        return response

    @staticmethod
    def _provider_payload(response: Response) -> dict[str, Any]:
        try:
            value = response.json()
        except (JSONDecodeError, ValueError) as exc:
            raise EpayTransport._invalid_response() from exc
        if not isinstance(value, dict):
            raise EpayTransport._invalid_response()
        return value

    @classmethod
    def _provider_method(cls, configuration: dict[str, Any], payment_method: str) -> str:
        enabled = configuration.get("paymentTypes")
        if not isinstance(enabled, list) or payment_method not in enabled:
            raise ApiError(
                status_code=400,
                code="PAYMENT_METHOD_UNAVAILABLE",
                message="Payment method is not enabled for this provider.",
            )
        result = cls.METHOD_CODES.get(payment_method)
        if result is None:
            raise ApiError(
                status_code=400,
                code="PAYMENT_METHOD_UNSUPPORTED",
                message="Payment method is unsupported.",
            )
        return result

    @staticmethod
    def _format_minor(amount_minor: int) -> str:
        if amount_minor < 0:
            raise ApiError(
                status_code=400,
                code="PAYMENT_AMOUNT_INVALID",
                message="Payment amount cannot be negative.",
            )
        return f"{amount_minor // 100}.{amount_minor % 100:02d}"

    @staticmethod
    def _parse_amount(value: object) -> int:
        text = str(value)
        if fullmatch(r"(?:0|[1-9][0-9]*)(?:\.[0-9]{1,2})?", text) is None:
            raise EpayTransport._invalid_callback("Payment amount format is invalid.")
        try:
            amount = Decimal(text)
        except InvalidOperation as exc:
            raise EpayTransport._invalid_callback("Payment amount format is invalid.") from exc
        return int(amount * 100)

    @staticmethod
    def _validate_currency(currency: str) -> None:
        # 当前审核的易支付预设只支持人民币，避免网关无币种字段时错误结算其他币种。
        if currency != "CNY":
            raise ApiError(
                status_code=400,
                code="PAYMENT_CURRENCY_UNSUPPORTED",
                message="The configured Epay preset supports CNY only.",
            )

    @staticmethod
    def _success_code(value: object) -> bool:
        return str(value).lower() in {"1", "ok", "success", "true"}

    @staticmethod
    def _join(base_url: str, path: str) -> str:
        return f"{base_url.rstrip('/')}/{path.lstrip('/')}"

    @staticmethod
    def _invalid_callback(message: str) -> ApiError:
        return ApiError(status_code=400, code="PAYMENT_CALLBACK_INVALID", message=message)

    @staticmethod
    def _invalid_response() -> ApiError:
        return ApiError(
            status_code=503,
            code="PAYMENT_PROVIDER_RESPONSE_INVALID",
            message="Payment provider response is invalid.",
            retryable=False,
        )

    @staticmethod
    def _provider_unavailable(message: str) -> ApiError:
        return ApiError(
            status_code=503,
            code="PAYMENT_PROVIDER_UNAVAILABLE",
            message=message,
            retryable=True,
        )

    @staticmethod
    def _provider_rejected(*, retryable: bool) -> ApiError:
        return ApiError(
            status_code=503,
            code="PAYMENT_PROVIDER_REJECTED",
            message="Payment provider rejected the request.",
            retryable=retryable,
        )
