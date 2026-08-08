from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Request

from love_reply_api.application.generation import GenerationService
from love_reply_api.infrastructure.generation_records import WalletLedgerRecord
from love_reply_api.schemas import SuccessEnvelope
from love_reply_api.transport.http.billing_schemas import (
    BenefitBalancesData,
    EntitlementData,
    EntitlementResponse,
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
    get_generation_service,
)

router = APIRouter(prefix="/v1")


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
