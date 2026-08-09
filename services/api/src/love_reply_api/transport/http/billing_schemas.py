from datetime import datetime
from typing import Any, Literal

from pydantic import Field

from love_reply_api.schemas import ApiModel, SuccessEnvelope


class BenefitBalancesData(ApiModel):
    text_remaining: int = Field(ge=0)
    vision_remaining: int = Field(ge=0)
    allowed_model_ids: list[str]
    allowed_style_ids: list[str]


class WalletSummaryData(ApiModel):
    energy_balance: int = Field(ge=0)
    energy_reserved: int = Field(ge=0)
    energy_available: int = Field(ge=0)


class EntitlementData(ApiModel):
    user_id: str
    plan_code: str
    plan_expires_at: datetime | None
    benefits: BenefitBalancesData
    wallet: WalletSummaryData
    resource_version: int = Field(ge=1)
    updated_at: datetime


class WalletData(WalletSummaryData):
    currency: Literal["ENERGY"] = "ENERGY"
    resource_version: int = Field(ge=1)
    updated_at: datetime


class WalletLedgerEntryData(ApiModel):
    ledger_entry_id: str
    entry_type: Literal["CREDIT", "RESERVATION", "SETTLEMENT", "RELEASE", "ADJUSTMENT", "REFUND"]
    generation_id: str | None
    energy_delta: int
    reserved_delta: int
    balance_after: int = Field(ge=0)
    reserved_after: int = Field(ge=0)
    reason_code: str | None
    created_at: datetime


class WalletLedgerData(ApiModel):
    items: list[WalletLedgerEntryData]
    next_cursor: str | None
    has_more: bool


EntitlementResponse = SuccessEnvelope[EntitlementData]
WalletResponse = SuccessEnvelope[WalletData]
WalletLedgerResponse = SuccessEnvelope[WalletLedgerData]


class ProductData(ApiModel):
    product_version_id: str
    product_code: str
    version: int
    product_type: str
    display_name: str
    description: str | None
    currency: str
    amount_minor: int
    region: str
    sales_channels: list[str]
    renewal_type: str
    term_days: int | None
    benefit_window_days: int
    benefits: dict[str, Any]
    status: str
    effective_at: datetime
    expires_at: datetime | None


class ProductListData(ApiModel):
    catalog_version: int
    items: list[ProductData]


class CreateOrderRequest(ApiModel):
    product_version_id: str
    payment_method: Literal["ALIPAY", "WECHAT_PAY"]


class CreatePaymentAttemptRequest(ApiModel):
    payment_method: Literal["ALIPAY", "WECHAT_PAY"]


class CheckoutActionData(ApiModel):
    action_type: str
    value: str
    expires_at: datetime


class PaymentAttemptData(ApiModel):
    payment_attempt_id: str
    payment_method: str
    status: str
    amount_minor: int
    currency: str
    checkout_action: CheckoutActionData | None
    provider_transaction_id: str | None
    failure_code: str | None
    created_at: datetime
    updated_at: datetime


class OrderData(ApiModel):
    order_id: str
    status: str
    product: dict[str, Any]
    currency: str
    amount_minor: int
    paid_amount_minor: int
    payment_attempts: list[PaymentAttemptData]
    entitlement_granted: bool
    paid_at: datetime | None
    expires_at: datetime
    resource_version: int
    created_at: datetime
    updated_at: datetime


class SubscriptionData(ApiModel):
    subscription_id: str
    product_code: str
    product_version_id: str
    status: str
    renewal_type: str
    current_period_starts_at: datetime
    current_period_ends_at: datetime
    auto_renew: bool
    cancel_at_period_end: bool
    resource_version: int
    created_at: datetime
    updated_at: datetime


class SubscriptionListData(ApiModel):
    items: list[SubscriptionData]


class CancelSubscriptionRequest(ApiModel):
    cancel_at_period_end: bool


class CreateRefundRequest(ApiModel):
    order_id: str
    amount_minor: int = Field(ge=1)
    reason_code: str
    comment: str | None = Field(default=None, max_length=500)


class RefundData(ApiModel):
    refund_id: str
    order_id: str
    status: str
    currency: str
    requested_amount_minor: int
    refunded_amount_minor: int
    reason_code: str
    entitlement_recovery_status: str
    rejection_reason_code: str | None
    resource_version: int
    created_at: datetime
    updated_at: datetime


ProductResponse = SuccessEnvelope[ProductData]
ProductListResponse = SuccessEnvelope[ProductListData]
OrderResponse = SuccessEnvelope[OrderData]
SubscriptionResponse = SuccessEnvelope[SubscriptionData]
SubscriptionListResponse = SuccessEnvelope[SubscriptionListData]
RefundResponse = SuccessEnvelope[RefundData]
