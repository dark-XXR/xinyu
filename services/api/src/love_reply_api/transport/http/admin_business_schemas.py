"""管理员商业接口请求与响应模型，字段与 admin-business OpenAPI 保持一致。"""

from datetime import datetime
from typing import Literal

from pydantic import Field

from love_reply_api.schemas import ApiModel, SuccessEnvelope
from love_reply_api.transport.http.billing_schemas import OrderData, ProductData, RefundData


class BenefitGrantRequest(ApiModel):
    text_quota: int = Field(ge=0)
    vision_quota: int = Field(ge=0)
    energy_amount: int = Field(ge=0)
    allowed_model_ids: list[str]
    allowed_style_ids: list[str]
    deep_analysis_enabled: bool = False


class AdminProductWriteRequest(ApiModel):
    product_code: str = Field(pattern=r"^[A-Z][A-Z0-9_]{1,63}$")
    product_type: Literal["PLAN", "ENERGY_PACK"]
    display_name: str = Field(min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=500)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    amount_minor: int = Field(ge=0)
    region: str = Field(min_length=2, max_length=16)
    sales_channels: list[Literal["ANDROID", "ADMIN_ASSISTED"]] = Field(min_length=1)
    renewal_type: Literal["NONE", "PROVIDER_MANDATE"]
    term_days: int | None = Field(default=None, ge=1)
    benefit_window_days: int = Field(ge=1)
    benefits: BenefitGrantRequest
    audit_reason: str = Field(min_length=8, max_length=500)


class AdminProductPublishRequest(ApiModel):
    effective_at: datetime
    expires_at: datetime | None = None
    audit_reason: str = Field(min_length=8, max_length=500)


class AdminProductRollbackRequest(ApiModel):
    target_product_version_id: str
    effective_at: datetime
    audit_reason: str = Field(min_length=8, max_length=500)


class AdminProductData(ProductData):
    resource_version: int = Field(ge=1)
    created_by_admin_id: str
    published_by_admin_id: str | None
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AdminProductListData(ApiModel):
    items: list[AdminProductData]
    next_cursor: str | None
    has_more: bool


class AdminOrderData(ApiModel):
    user_id: str
    order: OrderData


class AdminOrderListData(ApiModel):
    items: list[AdminOrderData]
    next_cursor: str | None
    has_more: bool


class AdminRefundData(RefundData):
    user_id: str
    provider_refund_id: str | None
    reviewed_by_admin_id: str | None
    executed_by_admin_id: str | None


class AdminRefundListData(ApiModel):
    items: list[AdminRefundData]
    next_cursor: str | None
    has_more: bool


class AdminRefundDecisionRequest(ApiModel):
    decision: Literal["APPROVE", "REJECT"]
    rejection_reason_code: str | None = Field(default=None, pattern=r"^[A-Z][A-Z0-9_]*$")
    audit_reason: str = Field(min_length=8, max_length=500)


class AdminRefundExecuteRequest(ApiModel):
    audit_reason: str = Field(min_length=8, max_length=500)


class PaymentReconciliationRequest(ApiModel):
    stale_before: datetime
    max_orders: int = Field(ge=1, le=500)
    audit_reason: str = Field(min_length=8, max_length=500)


class PaymentReconciliationData(ApiModel):
    reconciliation_id: str
    scanned_count: int
    settled_count: int
    recovered_count: int
    conflict_count: int
    started_at: datetime
    completed_at: datetime


class EntitlementAdjustmentRequest(ApiModel):
    user_id: str
    unit: Literal["ENERGY", "TEXT_QUOTA", "VISION_QUOTA", "PLAN_DAYS"]
    delta: int
    reason_code: str = Field(pattern=r"^[A-Z][A-Z0-9_]*$")
    audit_reason: str = Field(min_length=8, max_length=500)


class EntitlementAdjustmentData(ApiModel):
    adjustment_id: str
    user_id: str
    unit: str
    delta: int
    reason_code: str
    created_by_admin_id: str
    wallet_ledger_entry_id: str | None
    created_at: datetime


AdminProductResponse = SuccessEnvelope[AdminProductData]
AdminProductListResponse = SuccessEnvelope[AdminProductListData]
AdminOrderResponse = SuccessEnvelope[AdminOrderData]
AdminOrderListResponse = SuccessEnvelope[AdminOrderListData]
AdminRefundResponse = SuccessEnvelope[AdminRefundData]
AdminRefundListResponse = SuccessEnvelope[AdminRefundListData]
PaymentReconciliationResponse = SuccessEnvelope[PaymentReconciliationData]
EntitlementAdjustmentResponse = SuccessEnvelope[EntitlementAdjustmentData]
