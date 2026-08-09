"""主流邮件 API 与短信供应商的真实网络适配器。

邮件支持 Amazon SES v2、SendGrid、Resend 和 Mailgun；短信支持阿里云和腾讯云。
本模块只接收解密后的短生命周期凭据，错误信息不得包含密钥、验证码或供应商响应正文。
"""

from __future__ import annotations

from base64 import b64encode
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import formataddr
from hashlib import sha1, sha256
from hmac import new as new_hmac
from json import JSONDecodeError, dumps
from typing import Any
from urllib.parse import parse_qsl, quote, urlsplit
from uuid import uuid4

from httpx import AsyncClient, HTTPError, Response, TimeoutException

from love_reply_api.application.errors import ApiError


@dataclass(frozen=True, slots=True)
class DeliveryResult:
    """供应商已接受请求后的脱敏结果。"""

    provider_request_id: str | None


class EmailApiTransport:
    """把统一邮件内容转换成各供应商的原生请求。"""

    def __init__(
        self,
        client_factory: Callable[..., AsyncClient] = AsyncClient,
        now_factory: Callable[[], datetime] | None = None,
    ) -> None:
        self._client_factory = client_factory
        self._now = now_factory or (lambda: datetime.now(UTC))

    async def send(
        self,
        *,
        configuration: dict[str, Any],
        credentials: dict[str, str],
        destination: str,
        subject: str,
        text_body: str,
        html_body: str | None,
    ) -> DeliveryResult:
        adapter_type = str(configuration["adapterType"])
        if adapter_type == "SES_API":
            return await self._send_ses(
                configuration=configuration,
                credentials=credentials,
                destination=destination,
                subject=subject,
                text_body=text_body,
                html_body=html_body,
            )
        if adapter_type == "SENDGRID_API":
            return await self._send_sendgrid(
                configuration=configuration,
                credentials=credentials,
                destination=destination,
                subject=subject,
                text_body=text_body,
                html_body=html_body,
            )
        if adapter_type == "RESEND_API":
            return await self._send_resend(
                configuration=configuration,
                credentials=credentials,
                destination=destination,
                subject=subject,
                text_body=text_body,
                html_body=html_body,
            )
        if adapter_type == "MAILGUN_API":
            return await self._send_mailgun(
                configuration=configuration,
                credentials=credentials,
                destination=destination,
                subject=subject,
                text_body=text_body,
                html_body=html_body,
            )
        raise self._configuration_error("Email API adapter is not supported.")

    async def _send_ses(
        self,
        *,
        configuration: dict[str, Any],
        credentials: dict[str, str],
        destination: str,
        subject: str,
        text_body: str,
        html_body: str | None,
    ) -> DeliveryResult:
        region = configuration.get("region")
        if not isinstance(region, str) or not region:
            raise self._configuration_error("Amazon SES region is required.")
        base_url = str(configuration.get("baseUrl") or f"https://email.{region}.amazonaws.com")
        url = self._join(base_url, "/v2/email/outbound-emails")
        body: dict[str, Any] = {
            "FromEmailAddress": self._sender(configuration),
            "Destination": {"ToAddresses": [destination]},
            "Content": {
                "Simple": {
                    "Subject": {"Data": subject, "Charset": "UTF-8"},
                    "Body": {
                        "Text": {"Data": text_body, "Charset": "UTF-8"},
                    },
                }
            },
        }
        if html_body is not None:
            body["Content"]["Simple"]["Body"]["Html"] = {
                "Data": html_body,
                "Charset": "UTF-8",
            }
        payload = dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        try:
            access_key_id = credentials["accessKeyId"]
            access_key_secret = credentials["accessKeySecret"]
        except KeyError as exc:
            raise self._configuration_error("Amazon SES credentials are incomplete.") from exc
        headers = self._aws_signature_v4(
            url=url,
            payload=payload,
            access_key_id=access_key_id,
            access_key_secret=access_key_secret,
            region=region,
        )
        response = await self._post(
            url=url,
            headers=headers,
            content=payload,
            timeout_ms=int(configuration["timeoutMs"]),
        )
        self._require_status(response, {200})
        return DeliveryResult(self._request_id(response))

    async def _send_sendgrid(
        self,
        *,
        configuration: dict[str, Any],
        credentials: dict[str, str],
        destination: str,
        subject: str,
        text_body: str,
        html_body: str | None,
    ) -> DeliveryResult:
        url = self._join(
            str(configuration.get("baseUrl") or "https://api.sendgrid.com"),
            "/v3/mail/send",
        )
        content = [{"type": "text/plain", "value": text_body}]
        if html_body is not None:
            content.append({"type": "text/html", "value": html_body})
        body = {
            "personalizations": [{"to": [{"email": destination}]}],
            "from": {
                "email": str(configuration["senderAddress"]),
                "name": str(configuration["senderName"]),
            },
            "subject": subject,
            "content": content,
        }
        response = await self._post_json(
            url=url,
            headers={"Authorization": f"Bearer {credentials['apiKey']}"},
            body=body,
            timeout_ms=int(configuration["timeoutMs"]),
        )
        self._require_status(response, {200, 202})
        return DeliveryResult(self._request_id(response))

    async def _send_resend(
        self,
        *,
        configuration: dict[str, Any],
        credentials: dict[str, str],
        destination: str,
        subject: str,
        text_body: str,
        html_body: str | None,
    ) -> DeliveryResult:
        url = self._join(
            str(configuration.get("baseUrl") or "https://api.resend.com"),
            "/emails",
        )
        body: dict[str, Any] = {
            "from": self._sender(configuration),
            "to": [destination],
            "subject": subject,
            "text": text_body,
        }
        if html_body is not None:
            body["html"] = html_body
        response = await self._post_json(
            url=url,
            headers={"Authorization": f"Bearer {credentials['apiKey']}"},
            body=body,
            timeout_ms=int(configuration["timeoutMs"]),
        )
        self._require_status(response, {200, 201, 202})
        payload = self._json_object(response)
        request_id = payload.get("id")
        return DeliveryResult(str(request_id) if request_id is not None else None)

    async def _send_mailgun(
        self,
        *,
        configuration: dict[str, Any],
        credentials: dict[str, str],
        destination: str,
        subject: str,
        text_body: str,
        html_body: str | None,
    ) -> DeliveryResult:
        base_url = configuration.get("baseUrl")
        if not isinstance(base_url, str) or not base_url:
            raise self._configuration_error(
                "Mailgun base URL must include the sending domain path."
            )
        data = {
            "from": self._sender(configuration),
            "to": destination,
            "subject": subject,
            "text": text_body,
        }
        if html_body is not None:
            data["html"] = html_body
        response = await self._post_form(
            url=self._join(base_url, "/messages"),
            data=data,
            auth=("api", credentials["apiKey"]),
            timeout_ms=int(configuration["timeoutMs"]),
        )
        self._require_status(response, {200, 202})
        payload = self._json_object(response)
        request_id = payload.get("id")
        return DeliveryResult(str(request_id) if request_id is not None else None)

    def _aws_signature_v4(
        self,
        *,
        url: str,
        payload: bytes,
        access_key_id: str,
        access_key_secret: str,
        region: str,
    ) -> dict[str, str]:
        """按照 AWS Signature Version 4 对 SES v2 请求签名。"""

        now = self._now().astimezone(UTC)
        amz_date = now.strftime("%Y%m%dT%H%M%SZ")
        date_stamp = now.strftime("%Y%m%d")
        parsed = urlsplit(url)
        host = parsed.netloc
        payload_hash = sha256(payload).hexdigest()
        canonical_uri = quote(parsed.path or "/", safe="/-_.~")
        canonical_query = "&".join(
            f"{quote(key, safe='-_.~')}={quote(value, safe='-_.~')}"
            for key, value in sorted(parse_qsl(parsed.query, keep_blank_values=True))
        )
        canonical_headers = (
            "content-type:application/json\n"
            f"host:{host}\n"
            f"x-amz-content-sha256:{payload_hash}\n"
            f"x-amz-date:{amz_date}\n"
        )
        signed_headers = "content-type;host;x-amz-content-sha256;x-amz-date"
        canonical_request = "\n".join(
            [
                "POST",
                canonical_uri,
                canonical_query,
                canonical_headers,
                signed_headers,
                payload_hash,
            ]
        )
        credential_scope = f"{date_stamp}/{region}/ses/aws4_request"
        string_to_sign = "\n".join(
            [
                "AWS4-HMAC-SHA256",
                amz_date,
                credential_scope,
                sha256(canonical_request.encode()).hexdigest(),
            ]
        )
        date_key = new_hmac(
            f"AWS4{access_key_secret}".encode(), date_stamp.encode(), sha256
        ).digest()
        region_key = new_hmac(date_key, region.encode(), sha256).digest()
        service_key = new_hmac(region_key, b"ses", sha256).digest()
        signing_key = new_hmac(service_key, b"aws4_request", sha256).digest()
        signature = new_hmac(signing_key, string_to_sign.encode(), sha256).hexdigest()
        authorization = (
            f"AWS4-HMAC-SHA256 Credential={access_key_id}/{credential_scope}, "
            f"SignedHeaders={signed_headers}, Signature={signature}"
        )
        return {
            "Authorization": authorization,
            "Content-Type": "application/json",
            "Host": host,
            "X-Amz-Content-Sha256": payload_hash,
            "X-Amz-Date": amz_date,
        }

    async def _post_json(
        self,
        *,
        url: str,
        headers: dict[str, str],
        body: dict[str, Any],
        timeout_ms: int,
    ) -> Response:
        return await self._request(
            lambda client: client.post(url, headers=headers, json=body),
            timeout_ms=timeout_ms,
        )

    async def _post(
        self,
        *,
        url: str,
        headers: dict[str, str],
        content: bytes,
        timeout_ms: int,
    ) -> Response:
        return await self._request(
            lambda client: client.post(url, headers=headers, content=content),
            timeout_ms=timeout_ms,
        )

    async def _post_form(
        self,
        *,
        url: str,
        data: dict[str, str],
        auth: tuple[str, str],
        timeout_ms: int,
    ) -> Response:
        return await self._request(
            lambda client: client.post(url, data=data, auth=auth),
            timeout_ms=timeout_ms,
        )

    async def _request(
        self,
        request: Callable[[AsyncClient], Any],
        *,
        timeout_ms: int,
    ) -> Response:
        try:
            async with self._client_factory(
                timeout=timeout_ms / 1000,
                follow_redirects=False,
            ) as client:
                response = await request(client)
        except TimeoutException as exc:
            raise self._delivery_error("Provider request timed out.", retryable=True) from exc
        except HTTPError as exc:
            raise self._delivery_error("Provider network request failed.", retryable=True) from exc
        if not isinstance(response, Response):
            raise self._delivery_error("Provider response is invalid.", retryable=False)
        return response

    @staticmethod
    def _sender(configuration: dict[str, Any]) -> str:
        return formataddr((str(configuration["senderName"]), str(configuration["senderAddress"])))

    @staticmethod
    def _join(base_url: str, path: str) -> str:
        return f"{base_url.rstrip('/')}/{path.lstrip('/')}"

    @staticmethod
    def _json_object(response: Response) -> dict[str, Any]:
        try:
            value = response.json()
        except (JSONDecodeError, ValueError) as exc:
            raise EmailApiTransport._delivery_error(
                "Provider response is invalid.", retryable=False
            ) from exc
        if not isinstance(value, dict):
            raise EmailApiTransport._delivery_error(
                "Provider response is invalid.", retryable=False
            )
        return value

    @staticmethod
    def _require_status(response: Response, accepted: set[int]) -> None:
        if response.status_code in accepted:
            return
        retryable = response.status_code == 429 or response.status_code >= 500
        raise EmailApiTransport._delivery_error(
            "Provider rejected the delivery request.", retryable=retryable
        )

    @staticmethod
    def _request_id(response: Response) -> str | None:
        value = (
            response.headers.get("x-request-id")
            or response.headers.get("x-amzn-requestid")
            or response.headers.get("request-id")
        )
        return str(value) if value is not None else None

    @staticmethod
    def _configuration_error(message: str) -> ApiError:
        return ApiError(
            status_code=503,
            code="PROVIDER_CONFIGURATION_INVALID",
            message=message,
            retryable=False,
        )

    @staticmethod
    def _delivery_error(message: str, *, retryable: bool) -> ApiError:
        return ApiError(
            status_code=503,
            code="PROVIDER_UNAVAILABLE",
            message=message,
            retryable=retryable,
        )


class SmsApiTransport:
    """阿里云和腾讯云短信原生签名与发送适配器。"""

    def __init__(
        self,
        client_factory: Callable[..., AsyncClient] = AsyncClient,
        now_factory: Callable[[], datetime] | None = None,
        nonce_factory: Callable[[], str] | None = None,
    ) -> None:
        self._client_factory = client_factory
        self._now = now_factory or (lambda: datetime.now(UTC))
        self._nonce = nonce_factory or (lambda: uuid4().hex)

    async def send_login_code(
        self,
        *,
        configuration: dict[str, Any],
        credentials: dict[str, str],
        phone_e164: str,
        code: str,
    ) -> DeliveryResult:
        adapter_type = str(configuration["adapterType"])
        if adapter_type == "ALIYUN_SMS":
            return await self._send_aliyun(
                configuration=configuration,
                credentials=credentials,
                phone_e164=phone_e164,
                code=code,
            )
        if adapter_type == "TENCENT_SMS":
            return await self._send_tencent(
                configuration=configuration,
                credentials=credentials,
                phone_e164=phone_e164,
                code=code,
            )
        raise EmailApiTransport._configuration_error("SMS adapter is not supported.")

    async def _send_aliyun(
        self,
        *,
        configuration: dict[str, Any],
        credentials: dict[str, str],
        phone_e164: str,
        code: str,
    ) -> DeliveryResult:
        now = self._now().astimezone(UTC)
        params = {
            "AccessKeyId": credentials["accessKeyId"],
            "Action": "SendSms",
            "Format": "JSON",
            "PhoneNumbers": phone_e164,
            "RegionId": str(configuration["region"]),
            "SignName": str(configuration["signatureId"]),
            "SignatureMethod": "HMAC-SHA1",
            "SignatureNonce": self._nonce(),
            "SignatureVersion": "1.0",
            "TemplateCode": str(configuration["templateId"]),
            "TemplateParam": dumps({"code": code}, separators=(",", ":")),
            "Timestamp": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "Version": "2017-05-25",
        }
        canonical_query = "&".join(
            f"{self._aliyun_quote(key)}={self._aliyun_quote(value)}"
            for key, value in sorted(params.items())
        )
        string_to_sign = f"POST&%2F&{self._aliyun_quote(canonical_query)}"
        signature = b64encode(
            new_hmac(
                f"{credentials['accessKeySecret']}&".encode(),
                string_to_sign.encode(),
                sha1,
            ).digest()
        ).decode()
        params["Signature"] = signature
        response = await self._request(
            url="https://dysmsapi.aliyuncs.com/",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data=params,
            content=None,
            timeout_ms=int(configuration["timeoutMs"]),
        )
        EmailApiTransport._require_status(response, {200})
        payload = EmailApiTransport._json_object(response)
        if payload.get("Code") != "OK":
            raise EmailApiTransport._delivery_error(
                "SMS provider rejected the delivery request.",
                retryable=self._aliyun_retryable(payload.get("Code")),
            )
        request_id = payload.get("RequestId")
        return DeliveryResult(str(request_id) if request_id is not None else None)

    async def _send_tencent(
        self,
        *,
        configuration: dict[str, Any],
        credentials: dict[str, str],
        phone_e164: str,
        code: str,
    ) -> DeliveryResult:
        application_id = configuration.get("applicationId")
        if not isinstance(application_id, str) or not application_id:
            raise EmailApiTransport._configuration_error("Tencent SMS application ID is required.")
        host = "sms.tencentcloudapi.com"
        url = f"https://{host}"
        body = {
            "PhoneNumberSet": [phone_e164],
            "SmsSdkAppId": application_id,
            "SignName": str(configuration["signatureId"]),
            "TemplateId": str(configuration["templateId"]),
            "TemplateParamSet": [code],
        }
        payload = dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        now = self._now().astimezone(UTC)
        timestamp = int(now.timestamp())
        date_stamp = now.strftime("%Y-%m-%d")
        authorization = self._tencent_authorization(
            host=host,
            payload=payload,
            timestamp=timestamp,
            date_stamp=date_stamp,
            secret_id=credentials["secretId"],
            secret_key=credentials["secretKey"],
        )
        response = await self._request(
            url=url,
            headers={
                "Authorization": authorization,
                "Content-Type": "application/json; charset=utf-8",
                "Host": host,
                "X-TC-Action": "SendSms",
                "X-TC-Region": str(configuration["region"]),
                "X-TC-Timestamp": str(timestamp),
                "X-TC-Version": "2021-01-11",
            },
            data=None,
            content=payload,
            timeout_ms=int(configuration["timeoutMs"]),
        )
        EmailApiTransport._require_status(response, {200})
        payload_json = EmailApiTransport._json_object(response)
        result = payload_json.get("Response")
        if not isinstance(result, dict):
            raise EmailApiTransport._delivery_error(
                "SMS provider response is invalid.", retryable=False
            )
        error = result.get("Error")
        statuses = result.get("SendStatusSet")
        accepted = (
            error is None
            and isinstance(statuses, list)
            and bool(statuses)
            and isinstance(statuses[0], dict)
            and statuses[0].get("Code") == "Ok"
        )
        if not accepted:
            error_code = error.get("Code") if isinstance(error, dict) else None
            raise EmailApiTransport._delivery_error(
                "SMS provider rejected the delivery request.",
                retryable=self._tencent_retryable(error_code),
            )
        request_id = result.get("RequestId")
        return DeliveryResult(str(request_id) if request_id is not None else None)

    @staticmethod
    def _tencent_authorization(
        *,
        host: str,
        payload: bytes,
        timestamp: int,
        date_stamp: str,
        secret_id: str,
        secret_key: str,
    ) -> str:
        """按照腾讯云 TC3-HMAC-SHA256 规则生成 Authorization。"""

        canonical_headers = f"content-type:application/json; charset=utf-8\nhost:{host}\n"
        signed_headers = "content-type;host"
        canonical_request = "\n".join(
            [
                "POST",
                "/",
                "",
                canonical_headers,
                signed_headers,
                sha256(payload).hexdigest(),
            ]
        )
        credential_scope = f"{date_stamp}/sms/tc3_request"
        string_to_sign = "\n".join(
            [
                "TC3-HMAC-SHA256",
                str(timestamp),
                credential_scope,
                sha256(canonical_request.encode()).hexdigest(),
            ]
        )
        date_key = new_hmac(f"TC3{secret_key}".encode(), date_stamp.encode(), sha256).digest()
        service_key = new_hmac(date_key, b"sms", sha256).digest()
        signing_key = new_hmac(service_key, b"tc3_request", sha256).digest()
        signature = new_hmac(signing_key, string_to_sign.encode(), sha256).hexdigest()
        return (
            f"TC3-HMAC-SHA256 Credential={secret_id}/{credential_scope}, "
            f"SignedHeaders={signed_headers}, Signature={signature}"
        )

    async def _request(
        self,
        *,
        url: str,
        headers: dict[str, str],
        data: dict[str, str] | None,
        content: bytes | None,
        timeout_ms: int,
    ) -> Response:
        try:
            async with self._client_factory(
                timeout=timeout_ms / 1000,
                follow_redirects=False,
            ) as client:
                response = await client.post(
                    url,
                    headers=headers,
                    data=data,
                    content=content,
                )
        except TimeoutException as exc:
            raise EmailApiTransport._delivery_error(
                "SMS provider request timed out.", retryable=True
            ) from exc
        except HTTPError as exc:
            raise EmailApiTransport._delivery_error(
                "SMS provider network request failed.", retryable=True
            ) from exc
        return response

    @staticmethod
    def _aliyun_quote(value: object) -> str:
        return quote(str(value), safe="-_.~")

    @staticmethod
    def _aliyun_retryable(code: object) -> bool:
        return str(code) in {
            "isp.SYSTEM_ERROR",
            "isv.BUSINESS_LIMIT_CONTROL",
            "isv.AMOUNT_NOT_ENOUGH",
        }

    @staticmethod
    def _tencent_retryable(code: object) -> bool:
        return str(code) in {
            "InternalError",
            "InternalError.RequestTimeException",
            "LimitExceeded.PhoneNumberDailyLimit",
            "RequestLimitExceeded",
        }
