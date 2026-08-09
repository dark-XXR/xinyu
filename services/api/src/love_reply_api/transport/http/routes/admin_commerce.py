"""管理员商品、订单、退款、对账和人工权益调整 HTTP 接口。"""

from typing import Annotated, Any, cast

from fastapi import APIRouter, Depends, Header, Path, Query, Request, status

from love_reply_api.application.commerce_admin import CommerceAdminService
from love_reply_api.application.errors import ApiError
from love_reply_api.schemas import SuccessEnvelope
from love_reply_api.transport.http.admin_business_schemas import (
    AdminOrderData,
    AdminOrderListData,
    AdminOrderListResponse,
    AdminOrderResponse,
    AdminProductData,
    AdminProductListData,
    AdminProductListResponse,
    AdminProductPublishRequest,
    AdminProductResponse,
    AdminProductRollbackRequest,
    AdminProductWriteRequest,
    AdminRefundData,
    AdminRefundDecisionRequest,
    AdminRefundExecuteRequest,
    AdminRefundListData,
    AdminRefundListResponse,
    AdminRefundResponse,
    EntitlementAdjustmentData,
    EntitlementAdjustmentRequest,
    EntitlementAdjustmentResponse,
    PaymentReconciliationData,
    PaymentReconciliationRequest,
    PaymentReconciliationResponse,
)
from love_reply_api.transport.http.billing_schemas import OrderData, PaymentAttemptData
from love_reply_api.transport.http.dependencies import (
    AdminContext,
    get_commerce_admin_service,
    require_admin_permission,
)

router = APIRouter(prefix="/admin/v1", tags=["ADMIN_COMMERCE"])
Service = Annotated[CommerceAdminService, Depends(get_commerce_admin_service)]
ProductRead = Annotated[AdminContext, Depends(require_admin_permission("PRODUCT_READ"))]
ProductWrite = Annotated[AdminContext, Depends(require_admin_permission("PRODUCT_WRITE"))]
ProductPublish = Annotated[AdminContext, Depends(require_admin_permission("PRODUCT_PUBLISH"))]
ProductRollback = Annotated[AdminContext, Depends(require_admin_permission("PRODUCT_ROLLBACK"))]
OrderRead = Annotated[AdminContext, Depends(require_admin_permission("ORDER_READ"))]
RefundRead = Annotated[AdminContext, Depends(require_admin_permission("REFUND_READ"))]
RefundApprove = Annotated[AdminContext, Depends(require_admin_permission("REFUND_APPROVE"))]
RefundExecute = Annotated[AdminContext, Depends(require_admin_permission("REFUND_EXECUTE"))]
Reconcile = Annotated[AdminContext, Depends(require_admin_permission("RECONCILIATION_RUN"))]
Adjust = Annotated[AdminContext, Depends(require_admin_permission("ENTITLEMENT_ADJUST"))]


def _request_id(request: Request) -> str:
    return cast(str, request.state.request_id)


def _expected_version(value: str) -> int:
    try:
        result = int(value)
    except ValueError as exc:
        raise ApiError(
            status_code=400,
            code="INVALID_IF_MATCH",
            message="If-Match must contain a resource version.",
        ) from exc
    if result < 1:
        raise ApiError(
            status_code=400,
            code="INVALID_IF_MATCH",
            message="If-Match must contain a positive version.",
        )
    return result


def _product_values(body: AdminProductWriteRequest) -> dict[str, Any]:
    values = body.model_dump(exclude={"audit_reason"})
    values["benefits"] = body.benefits.model_dump(mode="json", by_alias=True)
    return values


def _product_data(record: Any) -> AdminProductData:
    return AdminProductData.model_validate(record, from_attributes=True)


def _refund_data(record: Any) -> AdminRefundData:
    return AdminRefundData.model_validate(record, from_attributes=True)


def _attempt_data(record: Any) -> PaymentAttemptData:
    return PaymentAttemptData.model_validate(
        {
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
    )


async def _order_data(service: CommerceAdminService, record: Any) -> AdminOrderData:
    order = OrderData.model_validate(
        {
            "orderId": record.order_id,
            "status": record.status,
            "product": record.product_snapshot,
            "currency": record.currency,
            "amountMinor": record.amount_minor,
            "paidAmountMinor": record.paid_amount_minor,
            "paymentAttempts": [
                _attempt_data(item) for item in await service.attempts(order_id=record.order_id)
            ],
            "entitlementGranted": record.entitlement_granted,
            "paidAt": record.paid_at,
            "expiresAt": record.expires_at,
            "resourceVersion": record.resource_version,
            "createdAt": record.created_at,
            "updatedAt": record.updated_at,
        }
    )
    return AdminOrderData(user_id=record.user_id, order=order)


@router.get("/products", operation_id="listAdminProducts", response_model=AdminProductListResponse)
async def list_products(
    request: Request,
    context: ProductRead,
    service: Service,
    cursor: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> AdminProductListResponse:
    del context
    page = await service.list_products(cursor=cursor, limit=limit)
    return SuccessEnvelope(
        data=AdminProductListData(
            items=[_product_data(item) for item in page.items],
            next_cursor=page.next_cursor,
            has_more=page.has_more,
        ),
        request_id=_request_id(request),
    )


@router.post(
    "/products",
    operation_id="createAdminProduct",
    response_model=AdminProductResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_product(
    body: AdminProductWriteRequest,
    request: Request,
    context: ProductWrite,
    service: Service,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
) -> AdminProductResponse:
    del idempotency_key
    record = await service.create_product(
        admin_id=context.admin.admin_id,
        audit_reason=body.audit_reason,
        values=_product_values(body),
    )
    return SuccessEnvelope(data=_product_data(record), request_id=_request_id(request))


@router.get(
    "/products/{productVersionId}",
    operation_id="getAdminProduct",
    response_model=AdminProductResponse,
)
async def get_product(
    product_version_id: Annotated[str, Path(alias="productVersionId")],
    request: Request,
    context: ProductRead,
    service: Service,
) -> AdminProductResponse:
    del context
    return SuccessEnvelope(
        data=_product_data(await service.get_product(product_version_id=product_version_id)),
        request_id=_request_id(request),
    )


@router.patch(
    "/products/{productVersionId}",
    operation_id="updateAdminProduct",
    response_model=AdminProductResponse,
)
async def update_product(
    product_version_id: Annotated[str, Path(alias="productVersionId")],
    body: AdminProductWriteRequest,
    request: Request,
    context: ProductWrite,
    service: Service,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    if_match: Annotated[str, Header(alias="If-Match")],
) -> AdminProductResponse:
    del idempotency_key
    record = await service.update_product(
        product_version_id=product_version_id,
        expected_version=_expected_version(if_match),
        admin_id=context.admin.admin_id,
        audit_reason=body.audit_reason,
        values=_product_values(body),
    )
    return SuccessEnvelope(data=_product_data(record), request_id=_request_id(request))


@router.post(
    "/products/{productVersionId}/publish",
    operation_id="publishAdminProduct",
    response_model=AdminProductResponse,
)
async def publish_product(
    product_version_id: Annotated[str, Path(alias="productVersionId")],
    body: AdminProductPublishRequest,
    request: Request,
    context: ProductPublish,
    service: Service,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    if_match: Annotated[str, Header(alias="If-Match")],
) -> AdminProductResponse:
    del idempotency_key
    record = await service.publish_product(
        product_version_id=product_version_id,
        expected_version=_expected_version(if_match),
        admin_id=context.admin.admin_id,
        **body.model_dump(),
    )
    return SuccessEnvelope(data=_product_data(record), request_id=_request_id(request))


@router.post(
    "/products/{productCode}/rollback",
    operation_id="rollbackAdminProduct",
    response_model=AdminProductResponse,
)
async def rollback_product(
    product_code: Annotated[str, Path(alias="productCode")],
    body: AdminProductRollbackRequest,
    request: Request,
    context: ProductRollback,
    service: Service,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
) -> AdminProductResponse:
    del idempotency_key
    record = await service.rollback_product(
        product_code=product_code,
        admin_id=context.admin.admin_id,
        **body.model_dump(),
    )
    return SuccessEnvelope(data=_product_data(record), request_id=_request_id(request))


@router.get("/orders", operation_id="listAdminOrders", response_model=AdminOrderListResponse)
async def list_orders(
    request: Request,
    context: OrderRead,
    service: Service,
    cursor: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> AdminOrderListResponse:
    del context
    page = await service.list_orders(cursor=cursor, limit=limit)
    return SuccessEnvelope(
        data=AdminOrderListData(
            items=[await _order_data(service, item) for item in page.items],
            next_cursor=page.next_cursor,
            has_more=page.has_more,
        ),
        request_id=_request_id(request),
    )


@router.get("/orders/{orderId}", operation_id="getAdminOrder", response_model=AdminOrderResponse)
async def get_order(
    order_id: Annotated[str, Path(alias="orderId")],
    request: Request,
    context: OrderRead,
    service: Service,
) -> AdminOrderResponse:
    del context
    return SuccessEnvelope(
        data=await _order_data(service, await service.get_order(order_id=order_id)),
        request_id=_request_id(request),
    )


@router.get("/refunds", operation_id="listAdminRefunds", response_model=AdminRefundListResponse)
async def list_refunds(
    request: Request,
    context: RefundRead,
    service: Service,
    cursor: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> AdminRefundListResponse:
    del context
    page = await service.list_refunds(cursor=cursor, limit=limit)
    return SuccessEnvelope(
        data=AdminRefundListData(
            items=[_refund_data(item) for item in page.items],
            next_cursor=page.next_cursor,
            has_more=page.has_more,
        ),
        request_id=_request_id(request),
    )


@router.get(
    "/refunds/{refundId}", operation_id="getAdminRefund", response_model=AdminRefundResponse
)
async def get_refund(
    refund_id: Annotated[str, Path(alias="refundId")],
    request: Request,
    context: RefundRead,
    service: Service,
) -> AdminRefundResponse:
    del context
    return SuccessEnvelope(
        data=_refund_data(await service.get_refund(refund_id=refund_id)),
        request_id=_request_id(request),
    )


@router.post(
    "/refunds/{refundId}/decision",
    operation_id="decideAdminRefund",
    response_model=AdminRefundResponse,
)
async def decide_refund(
    refund_id: Annotated[str, Path(alias="refundId")],
    body: AdminRefundDecisionRequest,
    request: Request,
    context: RefundApprove,
    service: Service,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    if_match: Annotated[str, Header(alias="If-Match")],
) -> AdminRefundResponse:
    del idempotency_key
    record = await service.decide_refund(
        refund_id=refund_id,
        expected_version=_expected_version(if_match),
        admin_id=context.admin.admin_id,
        **body.model_dump(),
    )
    return SuccessEnvelope(data=_refund_data(record), request_id=_request_id(request))


@router.post(
    "/refunds/{refundId}/execute",
    operation_id="executeAdminRefund",
    response_model=AdminRefundResponse,
)
async def execute_refund(
    refund_id: Annotated[str, Path(alias="refundId")],
    body: AdminRefundExecuteRequest,
    request: Request,
    context: RefundExecute,
    service: Service,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    if_match: Annotated[str, Header(alias="If-Match")],
) -> AdminRefundResponse:
    del idempotency_key
    record = await service.execute_refund(
        refund_id=refund_id,
        expected_version=_expected_version(if_match),
        admin_id=context.admin.admin_id,
        audit_reason=body.audit_reason,
    )
    return SuccessEnvelope(data=_refund_data(record), request_id=_request_id(request))


@router.post(
    "/payment-reconciliations",
    operation_id="runAdminPaymentReconciliation",
    response_model=PaymentReconciliationResponse,
)
async def run_reconciliation(
    body: PaymentReconciliationRequest,
    request: Request,
    context: Reconcile,
    service: Service,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
) -> PaymentReconciliationResponse:
    del idempotency_key
    record = await service.run_reconciliation(admin_id=context.admin.admin_id, **body.model_dump())
    return SuccessEnvelope(
        data=PaymentReconciliationData.model_validate(record, from_attributes=True),
        request_id=_request_id(request),
    )


@router.post(
    "/entitlement-adjustments",
    operation_id="createAdminEntitlementAdjustment",
    response_model=EntitlementAdjustmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def adjust_entitlement(
    body: EntitlementAdjustmentRequest,
    request: Request,
    context: Adjust,
    service: Service,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
) -> EntitlementAdjustmentResponse:
    if body.delta == 0:
        raise ApiError(
            status_code=400,
            code="ADJUSTMENT_DELTA_INVALID",
            message="Adjustment delta cannot be zero.",
        )
    record = await service.adjust_entitlement(
        idempotency_key=idempotency_key,
        admin_id=context.admin.admin_id,
        **body.model_dump(),
    )
    return SuccessEnvelope(
        data=EntitlementAdjustmentData.model_validate(record, from_attributes=True),
        request_id=_request_id(request),
    )
