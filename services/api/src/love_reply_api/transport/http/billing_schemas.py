from datetime import datetime
from typing import Literal

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
