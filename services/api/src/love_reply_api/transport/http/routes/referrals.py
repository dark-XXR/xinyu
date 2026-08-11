"""邀请推广用户端与管理员端 HTTP 路由。"""

from typing import Annotated, Any, cast

from fastapi import APIRouter, Depends, Header, Path, Query, Request, status

from love_reply_api.application.errors import ApiError
from love_reply_api.application.referrals import ReferralService
from love_reply_api.schemas import SuccessEnvelope
from love_reply_api.transport.http.dependencies import (
    AdminContext,
    AuthContext,
    ClientContext,
    get_auth_context,
    get_client_context,
    get_referral_service,
    require_admin_permission,
)
from love_reply_api.transport.http.referral_schemas import (
    BindReferralRequest,
    PublishReferralCampaignRequest,
    ReferralCampaignData,
    ReferralCampaignListData,
    ReferralCampaignListResponse,
    ReferralCampaignResponse,
    ReferralCampaignVersionData,
    ReferralCampaignVersionListData,
    ReferralCampaignVersionListResponse,
    ReferralCampaignWriteRequest,
    ReferralInviteData,
    ReferralInviteListData,
    ReferralInviteListResponse,
    ReferralInviteResponse,
    ReferralProgramData,
    ReferralProgramResponse,
    ReferralRewardData,
    ReferralRewardListData,
    ReferralRewardListResponse,
    RollbackReferralCampaignRequest,
)

router = APIRouter()
Service = Annotated[ReferralService, Depends(get_referral_service)]
Auth = Annotated[AuthContext, Depends(get_auth_context)]
Client = Annotated[ClientContext, Depends(get_client_context)]
AdminRead = Annotated[AdminContext, Depends(require_admin_permission("REFERRAL_READ"))]
AdminWrite = Annotated[AdminContext, Depends(require_admin_permission("REFERRAL_WRITE"))]
AdminPublish = Annotated[AdminContext, Depends(require_admin_permission("REFERRAL_PUBLISH"))]
AdminRollback = Annotated[AdminContext, Depends(require_admin_permission("REFERRAL_ROLLBACK"))]


def _request_id(request: Request) -> str:
    return cast(str, request.state.request_id)


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


def _campaign_values(body: ReferralCampaignWriteRequest) -> dict[str, Any]:
    values = body.model_dump(exclude={"reward_rules", "anti_abuse_policy"})
    values["reward_rules"] = [
        item.model_dump(mode="json", by_alias=True) for item in body.reward_rules
    ]
    values["anti_abuse_policy"] = body.anti_abuse_policy.model_dump(mode="json", by_alias=True)
    return values


def _data(model: type[Any], record: object) -> Any:
    return model.model_validate(record, from_attributes=True)


@router.get(
    "/v1/referrals/program",
    operation_id="getReferralProgram",
    response_model=ReferralProgramResponse,
)
async def get_program(
    request: Request, auth: Auth, client: Client, service: Service
) -> ReferralProgramResponse:
    result = await service.get_program(user_id=auth.user_id, channel=client.platform)
    return SuccessEnvelope(data=_data(ReferralProgramData, result), request_id=_request_id(request))


@router.post(
    "/v1/referrals/bind",
    operation_id="bindReferralInvite",
    response_model=ReferralInviteResponse,
    status_code=status.HTTP_201_CREATED,
)
async def bind_referral(
    body: BindReferralRequest,
    request: Request,
    auth: Auth,
    service: Service,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
) -> ReferralInviteResponse:
    del idempotency_key
    record = await service.bind(
        invitee_user_id=auth.user_id, invite_code=body.invite_code, device_id=auth.device_id
    )
    return SuccessEnvelope(data=_data(ReferralInviteData, record), request_id=_request_id(request))


@router.get(
    "/v1/referrals/invites",
    operation_id="listReferralInvites",
    response_model=ReferralInviteListResponse,
)
async def list_invites(
    request: Request,
    auth: Auth,
    service: Service,
    cursor: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ReferralInviteListResponse:
    page = await service.list_invites(inviter_user_id=auth.user_id, cursor=cursor, limit=limit)
    return SuccessEnvelope(
        data=ReferralInviteListData(
            items=[_data(ReferralInviteData, item) for item in page.items],
            next_cursor=page.next_cursor,
            has_more=page.has_more,
        ),
        request_id=_request_id(request),
    )


@router.get(
    "/v1/referrals/rewards",
    operation_id="listReferralRewards",
    response_model=ReferralRewardListResponse,
)
async def list_rewards(
    request: Request,
    auth: Auth,
    service: Service,
    cursor: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ReferralRewardListResponse:
    page = await service.list_rewards(user_id=auth.user_id, cursor=cursor, limit=limit)
    return SuccessEnvelope(
        data=ReferralRewardListData(
            items=[_data(ReferralRewardData, item) for item in page.items],
            next_cursor=page.next_cursor,
            has_more=page.has_more,
        ),
        request_id=_request_id(request),
    )


@router.get(
    "/admin/v1/referral-campaigns",
    operation_id="listAdminReferralCampaigns",
    response_model=ReferralCampaignListResponse,
)
async def list_campaigns(
    request: Request,
    context: AdminRead,
    service: Service,
    cursor: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ReferralCampaignListResponse:
    del context
    page = await service.list_campaigns(cursor=cursor, limit=limit)
    return SuccessEnvelope(
        data=ReferralCampaignListData(
            items=[_data(ReferralCampaignData, item) for item in page.items],
            next_cursor=page.next_cursor,
            has_more=page.has_more,
        ),
        request_id=_request_id(request),
    )


@router.post(
    "/admin/v1/referral-campaigns",
    operation_id="createAdminReferralCampaign",
    response_model=ReferralCampaignResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_campaign(
    body: ReferralCampaignWriteRequest,
    request: Request,
    context: AdminWrite,
    service: Service,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
) -> ReferralCampaignResponse:
    del idempotency_key
    record = await service.create_campaign(
        admin_id=context.admin.admin_id, values=_campaign_values(body)
    )
    return SuccessEnvelope(
        data=_data(ReferralCampaignData, record), request_id=_request_id(request)
    )


@router.get(
    "/admin/v1/referral-campaigns/{campaignId}",
    operation_id="getAdminReferralCampaign",
    response_model=ReferralCampaignResponse,
)
async def get_campaign(
    campaign_id: Annotated[str, Path(alias="campaignId")],
    request: Request,
    context: AdminRead,
    service: Service,
) -> ReferralCampaignResponse:
    del context
    return SuccessEnvelope(
        data=_data(ReferralCampaignData, await service.get_campaign(campaign_id=campaign_id)),
        request_id=_request_id(request),
    )


@router.get(
    "/admin/v1/referral-campaigns/{campaignId}/versions",
    operation_id="listAdminReferralCampaignVersions",
    response_model=ReferralCampaignVersionListResponse,
)
async def list_campaign_versions(
    campaign_id: Annotated[str, Path(alias="campaignId")],
    request: Request,
    context: AdminRead,
    service: Service,
) -> ReferralCampaignVersionListResponse:
    del context
    versions = await service.list_campaign_versions(campaign_id=campaign_id)
    items: list[ReferralCampaignVersionData] = []
    for version in versions:
        snapshot = version.snapshot
        items.append(
            ReferralCampaignVersionData(
                campaign_version_id=version.campaign_version_id,
                campaign_id=version.campaign_id,
                version=version.version,
                campaign_code=str(snapshot["campaignCode"]),
                display_name=str(snapshot["displayName"]),
                description=str(snapshot["description"]),
                region=str(snapshot["region"]),
                sales_channels=list(snapshot["salesChannels"]),
                binding_window_hours=int(snapshot["bindingWindowHours"]),
                max_qualified_invites_per_inviter=int(
                    snapshot["maxQualifiedInvitesPerInviter"]
                ),
                reward_rules=list(snapshot["rewardRules"]),
                anti_abuse_policy=dict(snapshot["antiAbusePolicy"]),
                was_published=version.was_published,
                action=version.action,
                created_by_admin_id=version.created_by_admin_id,
                created_at=version.created_at,
            )
        )
    return SuccessEnvelope(
        data=ReferralCampaignVersionListData(items=items),
        request_id=_request_id(request),
    )


@router.patch(
    "/admin/v1/referral-campaigns/{campaignId}",
    operation_id="updateAdminReferralCampaign",
    response_model=ReferralCampaignResponse,
)
async def update_campaign(
    campaign_id: Annotated[str, Path(alias="campaignId")],
    body: ReferralCampaignWriteRequest,
    request: Request,
    context: AdminWrite,
    service: Service,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    if_match: Annotated[str, Header(alias="If-Match")],
) -> ReferralCampaignResponse:
    del idempotency_key
    record = await service.update_campaign(
        campaign_id=campaign_id,
        expected_version=_expected_version(if_match),
        admin_id=context.admin.admin_id,
        values=_campaign_values(body),
    )
    return SuccessEnvelope(
        data=_data(ReferralCampaignData, record), request_id=_request_id(request)
    )


@router.post(
    "/admin/v1/referral-campaigns/{campaignId}/publish",
    operation_id="publishAdminReferralCampaign",
    response_model=ReferralCampaignResponse,
)
async def publish_campaign(
    campaign_id: Annotated[str, Path(alias="campaignId")],
    body: PublishReferralCampaignRequest,
    request: Request,
    context: AdminPublish,
    service: Service,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    if_match: Annotated[str, Header(alias="If-Match")],
) -> ReferralCampaignResponse:
    del idempotency_key
    record = await service.publish_campaign(
        campaign_id=campaign_id,
        expected_version=_expected_version(if_match),
        admin_id=context.admin.admin_id,
        **body.model_dump(),
    )
    return SuccessEnvelope(
        data=_data(ReferralCampaignData, record), request_id=_request_id(request)
    )


@router.post(
    "/admin/v1/referral-campaigns/{campaignId}/rollback",
    operation_id="rollbackAdminReferralCampaign",
    response_model=ReferralCampaignResponse,
)
async def rollback_campaign(
    campaign_id: Annotated[str, Path(alias="campaignId")],
    body: RollbackReferralCampaignRequest,
    request: Request,
    context: AdminRollback,
    service: Service,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    if_match: Annotated[str, Header(alias="If-Match")],
) -> ReferralCampaignResponse:
    del idempotency_key
    record = await service.rollback_campaign(
        campaign_id=campaign_id,
        expected_version=_expected_version(if_match),
        admin_id=context.admin.admin_id,
        **body.model_dump(),
    )
    return SuccessEnvelope(
        data=_data(ReferralCampaignData, record), request_id=_request_id(request)
    )
