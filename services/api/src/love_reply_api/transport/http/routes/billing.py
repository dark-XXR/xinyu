"""权益、钱包、商品、订单、订阅和退款 HTTP 接口。"""

from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Form, Header, Path, Query, Request, Response, status

from love_reply_api.application.commerce import CommerceService
from love_reply_api.application.errors import ApiError
from love_reply_api.application.generation import GenerationService
from love_reply_api.infrastructure.generation_records import WalletLedgerRecord
from love_reply_api.schemas import SuccessEnvelope
from love_reply_api.transport.http.billing_schemas import (
    BenefitBalancesData,
    CancelSubscriptionRequest,
    CreateOrderRequest,
    CreatePaymentAttemptRequest,
    CreateRefundRequest,
    EntitlementData,
    EntitlementResponse,
    OrderData,
    OrderResponse,
    PaymentAttemptData,
    ProductData,
    ProductListData,
    ProductListResponse,
    ProductResponse,
    RefundData,
    RefundResponse,
    SubscriptionData,
    SubscriptionListData,
    SubscriptionListResponse,
    SubscriptionResponse,
    WalletData,
    WalletLedgerData,
    WalletLedgerEntryData,
    WalletLedgerResponse,
    WalletResponse,
    WalletSummaryData,
)
from love_reply_api.transport.http.dependencies import (
    AuthContext,
    get_auth_context,
    get_commerce_service,
    get_generation_service,
)

router = APIRouter(prefix="/v1")
webhook_router = APIRouter(prefix="/webhooks/v1/payments")


def _expected_version(value: str) -> int:
    try:
        version = int(value)
    except ValueError as exc:
        raise ApiError(
            status_code=400,
            code="INVALID_IF_MATCH",
            message="If-Match must contain a resource version.",
        ) from exc
    if version < 1:
        raise ApiError(
            status_code=400,
            code="INVALID_IF_MATCH",
            message="If-Match must contain a positive version.",
        )
    return version


def _payment_attempt(record: Any) -> PaymentAttemptData:
    values = {
        "paymentAttemptId": record.payment_attempt_id,
        "paymentMethod": record.payment_method,
        "status": record.status,
        "amountMinor": record.amount_minor,
        "currency": record.currency,
        "checkoutAction": record.checkout_action,
        "providerTransactionId": record.provider_transaction_id,
        "failureCode": record.failure_code,
        "createdAt": record.created_at,
        "updatedAt": record.updated_at,
    }
    return PaymentAttemptData.model_validate(values)


async def _order_data(service: CommerceService, record: Any) -> OrderData:
    return OrderData.model_validate(
        {
            "orderId": record.order_id,
            "status": record.status,
            "product": record.product_snapshot,
            "currency": record.currency,
            "amountMinor": record.amount_minor,
            "paidAmountMinor": record.paid_amount_minor,
            "paymentAttempts": [
                _payment_attempt(item) for item in await service.attempts(record.order_id)
            ],
            "entitlementGranted": record.entitlement_granted,
            "paidAt": record.paid_at,
            "expiresAt": record.expires_at,
            "resourceVersion": record.resource_version,
            "createdAt": record.created_at,
            "updatedAt": record.updated_at,
        }
    )


def _wallet_summary(energy_balance: int, energy_reserved: int) -> WalletSummaryData:
    return WalletSummaryData(
        energy_balance=energy_balance,
        energy_reserved=energy_reserved,
        energy_available=max(0, energy_balance - energy_reserved),
    )


def _ledger_entry(record: WalletLedgerRecord) -> WalletLedgerEntryData:
    return WalletLedgerEntryData.model_validate(record, from_attributes=True)


@router.get(
    "/entitlements",
    operation_id="getEntitlements",
    response_model=EntitlementResponse,
    tags=["ENTITLEMENT"],
)
async def get_entitlements(
    request: Request,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    service: Annotated[GenerationService, Depends(get_generation_service)],
) -> EntitlementResponse:
    entitlement, wallet = await service.get_entitlement(auth.user_id)
    data = EntitlementData(
        user_id=entitlement.user_id,
        plan_code=entitlement.plan_code,
        plan_expires_at=entitlement.plan_expires_at,
        benefits=BenefitBalancesData(
            text_remaining=max(0, entitlement.text_remaining - entitlement.text_reserved),
            vision_remaining=entitlement.vision_remaining,
            allowed_model_ids=entitlement.allowed_model_ids,
            allowed_style_ids=entitlement.allowed_style_ids,
        ),
        wallet=_wallet_summary(wallet.energy_balance, wallet.energy_reserved),
        resource_version=entitlement.resource_version,
        updated_at=max(entitlement.updated_at, wallet.updated_at),
    )
    return SuccessEnvelope(data=data, request_id=request.state.request_id)


@router.get(
    "/wallet",
    operation_id="getWallet",
    response_model=WalletResponse,
    tags=["WALLET"],
)
async def get_wallet(
    request: Request,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    service: Annotated[GenerationService, Depends(get_generation_service)],
) -> WalletResponse:
    _, wallet = await service.get_entitlement(auth.user_id)
    summary = _wallet_summary(wallet.energy_balance, wallet.energy_reserved)
    return SuccessEnvelope(
        data=WalletData(
            **summary.model_dump(),
            resource_version=wallet.resource_version,
            updated_at=wallet.updated_at,
        ),
        request_id=request.state.request_id,
    )


@router.get(
    "/wallet/ledger",
    operation_id="listWalletLedger",
    response_model=WalletLedgerResponse,
    tags=["WALLET"],
)
async def list_wallet_ledger(
    request: Request,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    service: Annotated[GenerationService, Depends(get_generation_service)],
    cursor: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    entry_type: Annotated[
        Literal["CREDIT", "RESERVATION", "SETTLEMENT", "RELEASE", "ADJUSTMENT", "REFUND"] | None,
        Query(alias="entryType"),
    ] = None,
) -> WalletLedgerResponse:
    records, has_more = await service.list_ledger(
        user_id=auth.user_id,
        limit=limit,
        cursor=cursor,
        entry_type=entry_type,
    )
    return SuccessEnvelope(
        data=WalletLedgerData(
            items=[_ledger_entry(record) for record in records],
            next_cursor=records[-1].ledger_entry_id if has_more and records else None,
            has_more=has_more,
        ),
        request_id=request.state.request_id,
    )


@router.get(
    "/products", operation_id="listProducts", response_model=ProductListResponse, tags=["PRODUCT"]
)
async def list_products(
    request: Request,
    service: Annotated[CommerceService, Depends(get_commerce_service)],
    region: Annotated[str, Query(min_length=2, max_length=16)],
) -> ProductListResponse:
    items = await service.list_products(region=region, channel="ANDROID")
    catalog_version = max((item.version for item in items), default=1)
    return SuccessEnvelope(
        data=ProductListData(
            catalog_version=catalog_version,
            items=[ProductData.model_validate(item, from_attributes=True) for item in items],
        ),
        request_id=request.state.request_id,
    )


@router.get(
    "/products/{productVersionId}",
    operation_id="getProduct",
    response_model=ProductResponse,
    tags=["PRODUCT"],
)
async def get_product(
    product_version_id: Annotated[str, Path(alias="productVersionId")],
    request: Request,
    service: Annotated[CommerceService, Depends(get_commerce_service)],
) -> ProductResponse:
    return SuccessEnvelope(
        data=ProductData.model_validate(
            await service.get_product(product_version_id=product_version_id), from_attributes=True
        ),
        request_id=request.state.request_id,
    )


@router.post(
    "/orders",
    operation_id="createOrder",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["ORDER"],
)
async def create_order(
    body: CreateOrderRequest,
    request: Request,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    service: Annotated[CommerceService, Depends(get_commerce_service)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
) -> OrderResponse:
    del idempotency_key
    order = await service.create_order(user_id=auth.user_id, **body.model_dump())
    return SuccessEnvelope(
        data=await _order_data(service, order), request_id=request.state.request_id
    )


@router.get(
    "/orders/{orderId}", operation_id="getOrder", response_model=OrderResponse, tags=["ORDER"]
)
async def get_order(
    order_id: Annotated[str, Path(alias="orderId")],
    request: Request,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    service: Annotated[CommerceService, Depends(get_commerce_service)],
) -> OrderResponse:
    return SuccessEnvelope(
        data=await _order_data(
            service, await service.get_order(user_id=auth.user_id, order_id=order_id)
        ),
        request_id=request.state.request_id,
    )


@router.post(
    "/orders/{orderId}/payment-attempts",
    operation_id="createPaymentAttempt",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["ORDER"],
)
async def create_payment_attempt(
    order_id: Annotated[str, Path(alias="orderId")],
    body: CreatePaymentAttemptRequest,
    request: Request,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    service: Annotated[CommerceService, Depends(get_commerce_service)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    if_match: Annotated[str, Header(alias="If-Match")],
) -> OrderResponse:
    del idempotency_key
    order = await service.create_payment_attempt(
        user_id=auth.user_id,
        order_id=order_id,
        expected_version=_expected_version(if_match),
        payment_method=body.payment_method,
    )
    return SuccessEnvelope(
        data=await _order_data(service, order), request_id=request.state.request_id
    )


@router.post(
    "/orders/{orderId}/sync-payment",
    operation_id="syncOrderPayment",
    response_model=OrderResponse,
    tags=["ORDER"],
)
async def sync_order_payment(
    order_id: Annotated[str, Path(alias="orderId")],
    request: Request,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    service: Annotated[CommerceService, Depends(get_commerce_service)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    if_match: Annotated[str, Header(alias="If-Match")],
) -> OrderResponse:
    del idempotency_key
    order = await service.sync_payment(
        user_id=auth.user_id, order_id=order_id, expected_version=_expected_version(if_match)
    )
    return SuccessEnvelope(
        data=await _order_data(service, order), request_id=request.state.request_id
    )


@router.get(
    "/subscriptions",
    operation_id="listSubscriptions",
    response_model=SubscriptionListResponse,
    tags=["SUBSCRIPTION"],
)
async def list_subscriptions(
    request: Request,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    service: Annotated[CommerceService, Depends(get_commerce_service)],
) -> SubscriptionListResponse:
    records = await service.list_subscriptions(user_id=auth.user_id)
    return SuccessEnvelope(
        data=SubscriptionListData(
            items=[SubscriptionData.model_validate(item, from_attributes=True) for item in records]
        ),
        request_id=request.state.request_id,
    )


@router.post(
    "/subscriptions/{subscriptionId}/cancel",
    operation_id="cancelSubscription",
    response_model=SubscriptionResponse,
    tags=["SUBSCRIPTION"],
)
async def cancel_subscription(
    subscription_id: Annotated[str, Path(alias="subscriptionId")],
    body: CancelSubscriptionRequest,
    request: Request,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    service: Annotated[CommerceService, Depends(get_commerce_service)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    if_match: Annotated[str, Header(alias="If-Match")],
) -> SubscriptionResponse:
    del idempotency_key
    record = await service.cancel_subscription(
        user_id=auth.user_id,
        subscription_id=subscription_id,
        expected_version=_expected_version(if_match),
        cancel_at_period_end=body.cancel_at_period_end,
    )
    return SuccessEnvelope(
        data=SubscriptionData.model_validate(record, from_attributes=True),
        request_id=request.state.request_id,
    )


@router.post(
    "/refunds",
    operation_id="createRefund",
    response_model=RefundResponse,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["REFUND"],
)
async def create_refund(
    body: CreateRefundRequest,
    request: Request,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    service: Annotated[CommerceService, Depends(get_commerce_service)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
) -> RefundResponse:
    del idempotency_key
    record = await service.create_refund(user_id=auth.user_id, **body.model_dump())
    return SuccessEnvelope(
        data=RefundData.model_validate(record, from_attributes=True),
        request_id=request.state.request_id,
    )


@router.get(
    "/refunds/{refundId}", operation_id="getRefund", response_model=RefundResponse, tags=["REFUND"]
)
async def get_refund(
    refund_id: Annotated[str, Path(alias="refundId")],
    request: Request,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
    service: Annotated[CommerceService, Depends(get_commerce_service)],
) -> RefundResponse:
    return SuccessEnvelope(
        data=RefundData.model_validate(
            await service.get_refund(user_id=auth.user_id, refund_id=refund_id),
            from_attributes=True,
        ),
        request_id=request.state.request_id,
    )


@webhook_router.post(
    "/epay/{providerId}", operation_id="receiveEpayCallback", tags=["PAYMENT_WEBHOOK"]
)
async def receive_epay_callback(
    provider_id: Annotated[str, Path(alias="providerId")],
    service: Annotated[CommerceService, Depends(get_commerce_service)],
    pid: Annotated[str, Form()],
    trade_no: Annotated[str, Form()],
    out_trade_no: Annotated[str, Form()],
    type_: Annotated[str, Form(alias="type")],
    name: Annotated[str, Form()],
    money: Annotated[str, Form()],
    trade_status: Annotated[str, Form()],
    sign: Annotated[str, Form()],
    sign_type: Annotated[str, Form()],
    timestamp_: Annotated[str | None, Form(alias="timestamp")] = None,
    buyer_id: Annotated[str | None, Form()] = None,
    buyer: Annotated[str | None, Form()] = None,
    account: Annotated[str | None, Form()] = None,
) -> Response:
    form = {
        "pid": pid,
        "trade_no": trade_no,
        "out_trade_no": out_trade_no,
        "type": type_,
        "name": name,
        "money": money,
        "trade_status": trade_status,
        "sign": sign,
        "sign_type": sign_type,
    }
    if timestamp_ is not None:
        form["timestamp"] = timestamp_
    for key, value in (("buyer_id", buyer_id), ("buyer", buyer), ("account", account)):
        if value is not None:
            form[key] = value
    ack = await service.receive_callback(provider_id=provider_id, form=form)
    return Response(content=ack, media_type="text/plain")
