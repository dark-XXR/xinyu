from __future__ import annotations

from base64 import urlsafe_b64decode, urlsafe_b64encode
from dataclasses import dataclass
from datetime import UTC, datetime
from math import ceil
from typing import Any, Generic, TypeVar
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from love_reply_api.application.errors import ApiError
from love_reply_api.infrastructure.ai_gateway_records import (
    AiAuditRecord,
    AiEvaluationRunRecord,
    AiModelMappingRecord,
    AiPromptRecord,
    AiResourceVersionRecord,
    AiRiskPolicyRecord,
    AiRouteRecord,
)
from love_reply_api.infrastructure.provider_records import (
    ProviderRecord,
    ProviderVersionRecord,
)

RecordT = TypeVar("RecordT")


@dataclass(frozen=True, slots=True)
class Page(Generic[RecordT]):
    items: list[RecordT]
    next_cursor: str | None
    has_more: bool


class AiGatewayAdminService:
    def __init__(self, *, session: AsyncSession) -> None:
        self._session = session

    async def list_model_mappings(
        self, *, cursor: str | None, limit: int
    ) -> Page[AiModelMappingRecord]:
        return await self._page(
            AiModelMappingRecord, AiModelMappingRecord.model_mapping_id, cursor, limit
        )

    async def get_model_mapping(self, *, model_mapping_id: str) -> AiModelMappingRecord:
        record = await self._session.get(AiModelMappingRecord, model_mapping_id)
        if record is None:
            raise self._not_found("AI_MODEL_MAPPING_NOT_FOUND", "AI model mapping")
        return record

    async def create_model_mapping(self, *, admin_id: str, **values: Any) -> AiModelMappingRecord:
        await self._validate_provider(str(values["provider_id"]))
        now = datetime.now(UTC)
        record = AiModelMappingRecord(
            model_mapping_id=f"aim_{uuid4().hex}",
            status="DRAFT",
            resource_version=1,
            effective_at=None,
            created_at=now,
            updated_at=now,
            **values,
        )
        self._session.add(record)
        self._audit(
            "MODEL_MAPPING",
            record.model_mapping_id,
            admin_id,
            "CREATED",
            "AI model mapping draft created.",
            {"resourceVersion": 1},
            now,
        )
        await self._session.commit()
        return record

    async def update_model_mapping(
        self, *, model_mapping_id: str, expected_version: int, admin_id: str, **values: Any
    ) -> AiModelMappingRecord:
        record = await self._locked(
            AiModelMappingRecord,
            AiModelMappingRecord.model_mapping_id,
            model_mapping_id,
            "AI_MODEL_MAPPING_NOT_FOUND",
            "AI model mapping",
        )
        self._assert_version(record.resource_version, expected_version)
        await self._validate_provider(str(values["provider_id"]))
        for name, value in values.items():
            setattr(record, name, value)
        record.status = "DRAFT"
        record.effective_at = None
        self._advance(record)
        self._audit(
            "MODEL_MAPPING",
            model_mapping_id,
            admin_id,
            "UPDATED",
            "AI model mapping draft updated.",
            {"resourceVersion": record.resource_version},
            record.updated_at,
        )
        await self._session.commit()
        return record

    async def list_routes(self, *, cursor: str | None, limit: int) -> Page[AiRouteRecord]:
        return await self._page(AiRouteRecord, AiRouteRecord.route_id, cursor, limit)

    async def get_route(self, *, route_id: str) -> AiRouteRecord:
        record = await self._session.get(AiRouteRecord, route_id)
        if record is None:
            raise self._not_found("AI_ROUTE_NOT_FOUND", "AI route")
        return record

    async def create_route(self, *, admin_id: str, **values: Any) -> AiRouteRecord:
        now = datetime.now(UTC)
        record = AiRouteRecord(
            route_id=f"air_{uuid4().hex}",
            version=1,
            status="DRAFT",
            rollout_percentage=0,
            effective_at=None,
            published_version=None,
            published_snapshot=None,
            published_rollout_percentage=0,
            published_effective_at=None,
            resource_version=1,
            created_at=now,
            updated_at=now,
            **values,
        )
        self._session.add(record)
        await self._session.flush()
        self._record_resource_version(
            "ROUTE", record.route_id, 1, self._route_snapshot(record), admin_id, "CREATE", now
        )
        self._audit(
            "ROUTE",
            record.route_id,
            admin_id,
            "CREATED",
            "AI route draft created.",
            {"version": 1},
            now,
        )
        await self._session.commit()
        return record

    async def update_route(
        self, *, route_id: str, expected_version: int, admin_id: str, **values: Any
    ) -> AiRouteRecord:
        record = await self._locked(
            AiRouteRecord, AiRouteRecord.route_id, route_id, "AI_ROUTE_NOT_FOUND", "AI route"
        )
        self._assert_version(record.resource_version, expected_version)
        for name, value in values.items():
            setattr(record, name, value)
        record.version = await self._next_config_version("ROUTE", route_id)
        record.status = "DRAFT"
        record.rollout_percentage = 0
        record.effective_at = None
        self._advance(record)
        self._record_resource_version(
            "ROUTE",
            route_id,
            record.version,
            self._route_snapshot(record),
            admin_id,
            "UPDATE",
            record.updated_at,
        )
        self._audit(
            "ROUTE",
            route_id,
            admin_id,
            "UPDATED",
            "AI route draft updated.",
            {"version": record.version, "resourceVersion": record.resource_version},
            record.updated_at,
        )
        await self._session.commit()
        return record

    async def list_prompts(self, *, cursor: str | None, limit: int) -> Page[AiPromptRecord]:
        return await self._page(AiPromptRecord, AiPromptRecord.prompt_id, cursor, limit)

    async def get_prompt(self, *, prompt_id: str) -> AiPromptRecord:
        record = await self._session.get(AiPromptRecord, prompt_id)
        if record is None:
            raise self._not_found("AI_PROMPT_NOT_FOUND", "AI prompt")
        return record

    async def create_prompt(self, *, admin_id: str, **values: Any) -> AiPromptRecord:
        now = datetime.now(UTC)
        record = AiPromptRecord(
            prompt_id=f"aip_{uuid4().hex}",
            version=1,
            status="DRAFT",
            effective_at=None,
            published_version=None,
            published_snapshot=None,
            published_rollout_percentage=0,
            published_effective_at=None,
            resource_version=1,
            created_at=now,
            updated_at=now,
            **values,
        )
        self._session.add(record)
        await self._session.flush()
        self._record_resource_version(
            "PROMPT", record.prompt_id, 1, self._prompt_snapshot(record), admin_id, "CREATE", now
        )
        self._audit(
            "PROMPT",
            record.prompt_id,
            admin_id,
            "CREATED",
            "AI prompt draft created.",
            {"version": 1},
            now,
        )
        await self._session.commit()
        return record

    async def update_prompt(
        self, *, prompt_id: str, expected_version: int, admin_id: str, **values: Any
    ) -> AiPromptRecord:
        record = await self._locked(
            AiPromptRecord, AiPromptRecord.prompt_id, prompt_id, "AI_PROMPT_NOT_FOUND", "AI prompt"
        )
        self._assert_version(record.resource_version, expected_version)
        for name, value in values.items():
            setattr(record, name, value)
        record.version = await self._next_config_version("PROMPT", prompt_id)
        record.status = "DRAFT"
        record.effective_at = None
        self._advance(record)
        self._record_resource_version(
            "PROMPT",
            prompt_id,
            record.version,
            self._prompt_snapshot(record),
            admin_id,
            "UPDATE",
            record.updated_at,
        )
        self._audit(
            "PROMPT",
            prompt_id,
            admin_id,
            "UPDATED",
            "AI prompt draft updated.",
            {"version": record.version, "resourceVersion": record.resource_version},
            record.updated_at,
        )
        await self._session.commit()
        return record

    async def list_risk_policies(
        self, *, cursor: str | None, limit: int
    ) -> Page[AiRiskPolicyRecord]:
        return await self._page(
            AiRiskPolicyRecord, AiRiskPolicyRecord.risk_policy_id, cursor, limit
        )

    async def get_risk_policy(self, *, risk_policy_id: str) -> AiRiskPolicyRecord:
        record = await self._session.get(AiRiskPolicyRecord, risk_policy_id)
        if record is None:
            raise self._not_found("AI_RISK_POLICY_NOT_FOUND", "AI risk policy")
        return record

    async def create_risk_policy(self, *, admin_id: str, **values: Any) -> AiRiskPolicyRecord:
        now = datetime.now(UTC)
        record = AiRiskPolicyRecord(
            risk_policy_id=f"aik_{uuid4().hex}",
            version=1,
            status="DRAFT",
            effective_at=None,
            published_version=None,
            published_snapshot=None,
            published_rollout_percentage=0,
            published_effective_at=None,
            resource_version=1,
            created_at=now,
            updated_at=now,
            **values,
        )
        self._session.add(record)
        await self._session.flush()
        self._record_resource_version(
            "RISK_POLICY",
            record.risk_policy_id,
            1,
            self._risk_snapshot(record),
            admin_id,
            "CREATE",
            now,
        )
        self._audit(
            "RISK_POLICY",
            record.risk_policy_id,
            admin_id,
            "CREATED",
            "AI risk policy draft created.",
            {"version": 1},
            now,
        )
        await self._session.commit()
        return record

    async def update_risk_policy(
        self, *, risk_policy_id: str, expected_version: int, admin_id: str, **values: Any
    ) -> AiRiskPolicyRecord:
        record = await self._locked(
            AiRiskPolicyRecord,
            AiRiskPolicyRecord.risk_policy_id,
            risk_policy_id,
            "AI_RISK_POLICY_NOT_FOUND",
            "AI risk policy",
        )
        self._assert_version(record.resource_version, expected_version)
        for name, value in values.items():
            setattr(record, name, value)
        record.version = await self._next_config_version("RISK_POLICY", risk_policy_id)
        record.status = "DRAFT"
        record.effective_at = None
        self._advance(record)
        self._record_resource_version(
            "RISK_POLICY",
            risk_policy_id,
            record.version,
            self._risk_snapshot(record),
            admin_id,
            "UPDATE",
            record.updated_at,
        )
        self._audit(
            "RISK_POLICY",
            risk_policy_id,
            admin_id,
            "UPDATED",
            "AI risk policy draft updated.",
            {"version": record.version, "resourceVersion": record.resource_version},
            record.updated_at,
        )
        await self._session.commit()
        return record

    async def create_evaluation_run(
        self,
        *,
        admin_id: str,
        prompt_id: str,
        route_id: str,
        suite_ids: list[str],
        evaluator_logical_model_id: str,
        max_cost_microunits: int,
    ) -> AiEvaluationRunRecord:
        prompt = await self.get_prompt(prompt_id=prompt_id)
        route = await self.get_route(route_id=route_id)
        if prompt.scenario != route.scenario:
            raise ApiError(
                status_code=409,
                code="AI_EVALUATION_SCENARIO_MISMATCH",
                message="Prompt and route scenarios do not match.",
            )
        evaluator = await self._session.scalar(
            select(AiModelMappingRecord)
            .where(
                AiModelMappingRecord.logical_model_id == evaluator_logical_model_id,
                AiModelMappingRecord.enabled.is_(True),
            )
            .limit(1)
        )
        if evaluator is None:
            raise ApiError(
                status_code=409,
                code="AI_EVALUATOR_MODEL_UNAVAILABLE",
                message="Evaluator logical model is not configured.",
            )
        risk_versions: dict[str, int] = {}
        for policy_id in {route.safety_policy_id, prompt.safety_policy_id} - {None}:
            policy = await self.get_risk_policy(risk_policy_id=str(policy_id))
            risk_versions[policy.risk_policy_id] = policy.version
        now = datetime.now(UTC)
        record = AiEvaluationRunRecord(
            evaluation_run_id=f"aie_{uuid4().hex}",
            prompt_id=prompt_id,
            prompt_version=prompt.version,
            prompt_resource_version=prompt.resource_version,
            route_id=route_id,
            route_version=route.version,
            route_resource_version=route.resource_version,
            risk_policy_versions=risk_versions,
            suite_ids=suite_ids,
            evaluator_logical_model_id=evaluator_logical_model_id,
            max_cost_microunits=max_cost_microunits,
            status="QUEUED",
            passed=False,
            total_cases=0,
            completed_cases=0,
            score=0,
            safety_passed=False,
            cost_microunits=0,
            failure_code=None,
            created_by_admin_id=admin_id,
            created_at=now,
            updated_at=now,
        )
        self._session.add(record)
        self._audit(
            "EVALUATION",
            record.evaluation_run_id,
            admin_id,
            "QUEUED",
            "AI evaluation run queued.",
            {
                "promptVersion": prompt.version,
                "routeVersion": route.version,
                "maxCostMicrounits": max_cost_microunits,
            },
            now,
        )
        await self._session.commit()
        return record

    async def get_evaluation_run(self, *, evaluation_run_id: str) -> AiEvaluationRunRecord:
        record = await self._session.get(AiEvaluationRunRecord, evaluation_run_id)
        if record is None:
            raise self._not_found("AI_EVALUATION_RUN_NOT_FOUND", "AI evaluation run")
        return record

    async def publish_route(
        self,
        *,
        route_id: str,
        expected_version: int,
        admin_id: str,
        rollout_percentage: int,
        effective_at: datetime,
        evaluation_run_id: str,
        audit_reason: str,
    ) -> AiRouteRecord:
        route = await self._locked(
            AiRouteRecord, AiRouteRecord.route_id, route_id, "AI_ROUTE_NOT_FOUND", "AI route"
        )
        self._assert_version(route.resource_version, expected_version)
        evaluation = await self._gate(evaluation_run_id)
        if (
            evaluation.route_id != route_id
            or evaluation.route_version != route.version
            or evaluation.route_resource_version != route.resource_version
        ):
            raise self._gate_mismatch()
        mappings = await self._validated_route_mappings(route)
        risk = await self.get_risk_policy(risk_policy_id=route.safety_policy_id)
        if evaluation.risk_policy_versions.get(risk.risk_policy_id) != risk.version:
            raise self._gate_mismatch()
        if risk.published_version != risk.version:
            raise ApiError(
                status_code=409,
                code="AI_RISK_POLICY_NOT_PUBLISHED",
                message="Route safety policy must be published before the route.",
            )
        await self._assert_route_budget(route, mappings)
        snapshot = self._route_snapshot(route)
        snapshot["modelMappings"] = [self._mapping_snapshot(item) for item in mappings]
        snapshot["riskPolicy"] = self._risk_snapshot(risk)
        await self._mark_published(
            "ROUTE", route_id, route.version, snapshot, rollout_percentage, effective_at
        )
        now = datetime.now(UTC)
        for mapping in mappings:
            mapping.status = "ACTIVE"
            mapping.effective_at = effective_at
            mapping.resource_version += 1
            mapping.updated_at = now
        route.status = "ACTIVE"
        route.rollout_percentage = rollout_percentage
        route.effective_at = effective_at
        route.published_version = route.version
        route.published_snapshot = snapshot
        route.published_rollout_percentage = rollout_percentage
        route.published_effective_at = effective_at
        self._advance(route)
        self._audit(
            "ROUTE",
            route_id,
            admin_id,
            "PUBLISHED",
            audit_reason,
            {
                "version": route.version,
                "evaluationRunId": evaluation_run_id,
                "rolloutPercentage": rollout_percentage,
            },
            route.updated_at,
        )
        await self._session.commit()
        return route

    async def publish_prompt(
        self,
        *,
        prompt_id: str,
        expected_version: int,
        admin_id: str,
        effective_at: datetime,
        evaluation_run_id: str,
        audit_reason: str,
        rollout_percentage: int,
    ) -> AiPromptRecord:
        prompt = await self._locked(
            AiPromptRecord, AiPromptRecord.prompt_id, prompt_id, "AI_PROMPT_NOT_FOUND", "AI prompt"
        )
        self._assert_version(prompt.resource_version, expected_version)
        evaluation = await self._gate(evaluation_run_id)
        if (
            evaluation.prompt_id != prompt_id
            or evaluation.prompt_version != prompt.version
            or evaluation.prompt_resource_version != prompt.resource_version
        ):
            raise self._gate_mismatch()
        snapshot = self._prompt_snapshot(prompt)
        if prompt.safety_policy_id is not None:
            risk = await self.get_risk_policy(risk_policy_id=prompt.safety_policy_id)
            if evaluation.risk_policy_versions.get(risk.risk_policy_id) != risk.version:
                raise self._gate_mismatch()
            if risk.published_version != risk.version:
                raise ApiError(
                    status_code=409,
                    code="AI_RISK_POLICY_NOT_PUBLISHED",
                    message="Prompt safety policy must be published before the prompt.",
                )
            snapshot["riskPolicy"] = self._risk_snapshot(risk)
        await self._mark_published(
            "PROMPT",
            prompt_id,
            prompt.version,
            snapshot,
            rollout_percentage,
            effective_at,
        )
        prompt.status = "ACTIVE"
        prompt.effective_at = effective_at
        prompt.published_version = prompt.version
        prompt.published_snapshot = snapshot
        prompt.published_rollout_percentage = rollout_percentage
        prompt.published_effective_at = effective_at
        self._advance(prompt)
        self._audit(
            "PROMPT",
            prompt_id,
            admin_id,
            "PUBLISHED",
            audit_reason,
            {
                "version": prompt.version,
                "evaluationRunId": evaluation_run_id,
                "rolloutPercentage": rollout_percentage,
            },
            prompt.updated_at,
        )
        await self._session.commit()
        return prompt

    async def publish_risk_policy(
        self,
        *,
        risk_policy_id: str,
        expected_version: int,
        admin_id: str,
        rollout_percentage: int,
        effective_at: datetime,
        evaluation_run_id: str,
        audit_reason: str,
    ) -> AiRiskPolicyRecord:
        policy = await self._locked(
            AiRiskPolicyRecord,
            AiRiskPolicyRecord.risk_policy_id,
            risk_policy_id,
            "AI_RISK_POLICY_NOT_FOUND",
            "AI risk policy",
        )
        self._assert_version(policy.resource_version, expected_version)
        evaluation = await self._gate(evaluation_run_id)
        if evaluation.risk_policy_versions.get(risk_policy_id) != policy.version:
            raise self._gate_mismatch()
        snapshot = self._risk_snapshot(policy)
        await self._mark_published(
            "RISK_POLICY",
            risk_policy_id,
            policy.version,
            snapshot,
            rollout_percentage,
            effective_at,
        )
        policy.status = "ACTIVE"
        policy.effective_at = effective_at
        policy.published_version = policy.version
        policy.published_snapshot = snapshot
        policy.published_rollout_percentage = rollout_percentage
        policy.published_effective_at = effective_at
        self._advance(policy)
        self._audit(
            "RISK_POLICY",
            risk_policy_id,
            admin_id,
            "PUBLISHED",
            audit_reason,
            {
                "version": policy.version,
                "evaluationRunId": evaluation_run_id,
                "rolloutPercentage": rollout_percentage,
            },
            policy.updated_at,
        )
        await self._session.commit()
        return policy

    async def rollback_route(
        self,
        *,
        route_id: str,
        expected_version: int,
        admin_id: str,
        target_version: int,
        audit_reason: str,
    ) -> AiRouteRecord:
        route = await self._locked(
            AiRouteRecord, AiRouteRecord.route_id, route_id, "AI_ROUTE_NOT_FOUND", "AI route"
        )
        self._assert_version(route.resource_version, expected_version)
        version = await self._published_version("ROUTE", route_id, target_version)
        self._apply_route(route, version.snapshot)
        route.status = "ACTIVE"
        route.version = target_version
        route.rollout_percentage = 100
        route.effective_at = datetime.now(UTC)
        route.published_version = target_version
        route.published_snapshot = version.snapshot
        route.published_rollout_percentage = 100
        route.published_effective_at = route.effective_at
        self._advance(route)
        self._audit(
            "ROUTE",
            route_id,
            admin_id,
            "ROLLED_BACK",
            audit_reason,
            {"targetVersion": target_version},
            route.updated_at,
        )
        await self._session.commit()
        return route

    async def rollback_prompt(
        self,
        *,
        prompt_id: str,
        expected_version: int,
        admin_id: str,
        target_version: int,
        audit_reason: str,
    ) -> AiPromptRecord:
        prompt = await self._locked(
            AiPromptRecord, AiPromptRecord.prompt_id, prompt_id, "AI_PROMPT_NOT_FOUND", "AI prompt"
        )
        self._assert_version(prompt.resource_version, expected_version)
        version = await self._published_version("PROMPT", prompt_id, target_version)
        self._apply_prompt(prompt, version.snapshot)
        prompt.status = "ACTIVE"
        prompt.version = target_version
        prompt.effective_at = datetime.now(UTC)
        prompt.published_version = target_version
        prompt.published_snapshot = version.snapshot
        prompt.published_rollout_percentage = 100
        prompt.published_effective_at = prompt.effective_at
        self._advance(prompt)
        self._audit(
            "PROMPT",
            prompt_id,
            admin_id,
            "ROLLED_BACK",
            audit_reason,
            {"targetVersion": target_version},
            prompt.updated_at,
        )
        await self._session.commit()
        return prompt

    async def rollback_risk_policy(
        self,
        *,
        risk_policy_id: str,
        expected_version: int,
        admin_id: str,
        target_version: int,
        audit_reason: str,
    ) -> AiRiskPolicyRecord:
        policy = await self._locked(
            AiRiskPolicyRecord,
            AiRiskPolicyRecord.risk_policy_id,
            risk_policy_id,
            "AI_RISK_POLICY_NOT_FOUND",
            "AI risk policy",
        )
        self._assert_version(policy.resource_version, expected_version)
        version = await self._published_version("RISK_POLICY", risk_policy_id, target_version)
        self._apply_risk(policy, version.snapshot)
        policy.status = "ACTIVE"
        policy.version = target_version
        policy.effective_at = datetime.now(UTC)
        policy.published_version = target_version
        policy.published_snapshot = version.snapshot
        policy.published_rollout_percentage = 100
        policy.published_effective_at = policy.effective_at
        self._advance(policy)
        self._audit(
            "RISK_POLICY",
            risk_policy_id,
            admin_id,
            "ROLLED_BACK",
            audit_reason,
            {"targetVersion": target_version},
            policy.updated_at,
        )
        await self._session.commit()
        return policy

    async def _validated_route_mappings(self, route: AiRouteRecord) -> list[AiModelMappingRecord]:
        ids = [str(target["modelMappingId"]) for target in route.targets]
        rows = list(
            (
                await self._session.scalars(
                    select(AiModelMappingRecord).where(
                        AiModelMappingRecord.model_mapping_id.in_(ids)
                    )
                )
            ).all()
        )
        by_id = {row.model_mapping_id: row for row in rows}
        if len(by_id) != len(ids):
            raise ApiError(
                status_code=409,
                code="AI_ROUTE_MAPPING_INVALID",
                message="Route references a missing model mapping.",
            )
        ordered = [by_id[item] for item in ids]
        for mapping in ordered:
            if not mapping.enabled or mapping.logical_model_id != route.logical_model_id:
                raise ApiError(
                    status_code=409,
                    code="AI_ROUTE_MAPPING_INVALID",
                    message="Route model mappings are disabled or use another logical model.",
                )
            await self._validate_provider(mapping.provider_id, published=True)
            if (
                route.max_output_tokens > mapping.max_output_tokens
                or route.max_input_tokens + route.max_output_tokens > mapping.context_window_tokens
            ):
                raise ApiError(
                    status_code=409,
                    code="AI_ROUTE_TOKEN_LIMIT_INVALID",
                    message="Route token limits exceed a target model limit.",
                )
        return ordered

    async def _assert_route_budget(
        self, route: AiRouteRecord, mappings: list[AiModelMappingRecord]
    ) -> None:
        providers: dict[str, tuple[ProviderRecord, ProviderVersionRecord]] = {}
        for mapping in mappings:
            provider = await self._validate_provider(mapping.provider_id, published=True)
            version = await self._session.scalar(
                select(ProviderVersionRecord).where(
                    ProviderVersionRecord.provider_id == provider.provider_id,
                    ProviderVersionRecord.resource_version == provider.published_resource_version,
                    ProviderVersionRecord.was_published.is_(True),
                )
            )
            assert version is not None
            providers[mapping.model_mapping_id] = (provider, version)
        mapping_by_id = {item.model_mapping_id: item for item in mappings}
        attempts_left = route.total_attempt_limit
        worst_cost = 0
        for target in sorted(route.targets, key=lambda item: -int(item["priority"])):
            mapping = mapping_by_id[str(target["modelMappingId"])]
            _, provider_version = providers[mapping.model_mapping_id]
            attempt_count = (
                min(int(target["retryLimit"]), int(provider_version.snapshot["retryLimit"])) + 1
            )
            attempt_count = min(attempt_count, attempts_left)
            per_attempt = ceil(
                (
                    route.max_input_tokens * mapping.input_cost_microunits_per_million_tokens
                    + route.max_output_tokens * mapping.output_cost_microunits_per_million_tokens
                )
                / 1_000_000
            )
            worst_cost += attempt_count * per_attempt
            attempts_left -= attempt_count
            if attempts_left == 0:
                break
        if attempts_left > 0:
            raise ApiError(
                status_code=409,
                code="AI_ROUTE_ATTEMPT_LIMIT_INVALID",
                message="Route total attempt limit exceeds provider retry capacity.",
            )
        if worst_cost > route.budget_ceiling_microunits:
            raise ApiError(
                status_code=409,
                code="AI_ROUTE_BUDGET_UNSAFE",
                message="Route budget cannot cover its worst-case configured attempts.",
                details={"requiredBudgetMicrounits": worst_cost},
            )

    async def _validate_provider(
        self, provider_id: str, *, published: bool = False
    ) -> ProviderRecord:
        provider = await self._session.get(ProviderRecord, provider_id)
        if provider is None or provider.kind != "AI":
            raise ApiError(
                status_code=409,
                code="AI_PROVIDER_REFERENCE_INVALID",
                message="Model mapping must reference an AI provider.",
            )
        if published and provider.published_resource_version is None:
            raise ApiError(
                status_code=409,
                code="AI_PROVIDER_NOT_PUBLISHED",
                message="Route targets must use published AI providers.",
            )
        return provider

    async def _gate(self, evaluation_run_id: str) -> AiEvaluationRunRecord:
        evaluation = await self.get_evaluation_run(evaluation_run_id=evaluation_run_id)
        if (
            evaluation.status != "SUCCEEDED"
            or not evaluation.passed
            or not evaluation.safety_passed
            or evaluation.cost_microunits > evaluation.max_cost_microunits
        ):
            raise ApiError(
                status_code=409,
                code="AI_EVALUATION_GATE_FAILED",
                message="A matching successful evaluation run is required for publication.",
            )
        return evaluation

    @staticmethod
    def _gate_mismatch() -> ApiError:
        return ApiError(
            status_code=409,
            code="AI_EVALUATION_VERSION_MISMATCH",
            message="Evaluation run does not match the resource version being published.",
        )

    async def _mark_published(
        self,
        resource_type: str,
        resource_id: str,
        version: int,
        snapshot: dict[str, Any],
        rollout_percentage: int,
        effective_at: datetime,
    ) -> None:
        record = await self._version(resource_type, resource_id, version)
        assert record is not None
        record.snapshot = snapshot
        record.was_published = True
        record.rollout_percentage = rollout_percentage
        record.effective_at = effective_at

    async def _published_version(
        self, resource_type: str, resource_id: str, version: int
    ) -> AiResourceVersionRecord:
        record = await self._version(resource_type, resource_id, version, required=False)
        if record is None or not record.was_published:
            raise ApiError(
                status_code=409,
                code="AI_ROLLBACK_TARGET_INVALID",
                message="Rollback target is not a previously published version.",
            )
        return record

    async def _version(
        self, resource_type: str, resource_id: str, version: int, *, required: bool = True
    ) -> AiResourceVersionRecord | None:
        record = await self._session.scalar(
            select(AiResourceVersionRecord).where(
                AiResourceVersionRecord.resource_type == resource_type,
                AiResourceVersionRecord.resource_id == resource_id,
                AiResourceVersionRecord.version == version,
            )
        )
        if record is None and required:
            raise ApiError(
                status_code=409,
                code="AI_RESOURCE_VERSION_MISSING",
                message="AI resource version history is incomplete.",
            )
        return record

    async def _next_config_version(self, resource_type: str, resource_id: str) -> int:
        current = await self._session.scalar(
            select(func.max(AiResourceVersionRecord.version)).where(
                AiResourceVersionRecord.resource_type == resource_type,
                AiResourceVersionRecord.resource_id == resource_id,
            )
        )
        return int(current or 0) + 1

    def _record_resource_version(
        self,
        resource_type: str,
        resource_id: str,
        version: int,
        snapshot: dict[str, Any],
        admin_id: str,
        action: str,
        now: datetime,
    ) -> None:
        self._session.add(
            AiResourceVersionRecord(
                resource_version_id=f"aiv_{uuid4().hex}",
                resource_type=resource_type,
                resource_id=resource_id,
                version=version,
                snapshot=snapshot,
                was_published=False,
                rollout_percentage=None,
                effective_at=None,
                action=action,
                created_by_admin_id=admin_id,
                created_at=now,
            )
        )

    def _audit(
        self,
        resource_type: str,
        resource_id: str,
        admin_id: str,
        action: str,
        reason: str,
        metadata: dict[str, Any],
        now: datetime,
    ) -> None:
        self._session.add(
            AiAuditRecord(
                audit_id=f"aia_{uuid4().hex}",
                resource_type=resource_type,
                resource_id=resource_id,
                admin_id=admin_id,
                action=action,
                audit_reason=reason,
                metadata_json=metadata,
                created_at=now,
            )
        )

    async def _page(
        self, model: type[RecordT], id_column: Any, cursor: str | None, limit: int
    ) -> Page[RecordT]:
        after_id = self._decode_cursor(cursor) if cursor is not None else None
        statement = select(model).order_by(id_column).limit(limit + 1)
        if after_id is not None:
            statement = statement.where(id_column > after_id)
        records = list((await self._session.scalars(statement)).all())
        selected = records[:limit]
        has_more = len(records) > limit
        next_cursor = (
            self._encode_cursor(str(getattr(selected[-1], id_column.key)))
            if has_more and selected
            else None
        )
        return Page(items=selected, next_cursor=next_cursor, has_more=has_more)

    async def _locked(
        self, model: type[RecordT], id_column: Any, resource_id: str, code: str, label: str
    ) -> RecordT:
        record = await self._session.scalar(
            select(model).where(id_column == resource_id).with_for_update()
        )
        if record is None:
            raise self._not_found(code, label)
        return record

    @staticmethod
    def _assert_version(actual: int, expected: int) -> None:
        if actual != expected:
            raise ApiError(
                status_code=409,
                code="RESOURCE_VERSION_CONFLICT",
                message="Resource version does not match If-Match.",
                details={"currentResourceVersion": actual},
            )

    @staticmethod
    def _advance(record: Any) -> None:
        record.resource_version += 1
        record.updated_at = datetime.now(UTC)

    @staticmethod
    def _not_found(code: str, label: str) -> ApiError:
        return ApiError(status_code=404, code=code, message=f"{label} was not found.")

    @staticmethod
    def _encode_cursor(value: str) -> str:
        return urlsafe_b64encode(value.encode()).decode().rstrip("=")

    @staticmethod
    def _decode_cursor(value: str) -> str:
        try:
            return urlsafe_b64decode(value + "=" * (-len(value) % 4)).decode()
        except (ValueError, UnicodeDecodeError) as exc:
            raise ApiError(
                status_code=400, code="INVALID_CURSOR", message="Cursor is invalid."
            ) from exc

    @staticmethod
    def _mapping_snapshot(record: AiModelMappingRecord) -> dict[str, Any]:
        return {
            "modelMappingId": record.model_mapping_id,
            "logicalModelId": record.logical_model_id,
            "providerId": record.provider_id,
            "providerModelName": record.provider_model_name,
            "inputModalities": record.input_modalities,
            "outputModalities": record.output_modalities,
            "contextWindowTokens": record.context_window_tokens,
            "maxOutputTokens": record.max_output_tokens,
            "inputCostMicrounitsPerMillionTokens": record.input_cost_microunits_per_million_tokens,
            "outputCostMicrounitsPerMillionTokens": (
                record.output_cost_microunits_per_million_tokens
            ),
            "currency": record.currency,
            "qualityTier": record.quality_tier,
            "dataRegion": record.data_region,
            "retentionPolicy": record.retention_policy,
            "enabled": record.enabled,
        }

    @staticmethod
    def _route_snapshot(record: AiRouteRecord) -> dict[str, Any]:
        return {
            "scenario": record.scenario,
            "logicalModelId": record.logical_model_id,
            "targets": record.targets,
            "maxInputTokens": record.max_input_tokens,
            "maxOutputTokens": record.max_output_tokens,
            "budgetCeilingMicrounits": record.budget_ceiling_microunits,
            "totalAttemptLimit": record.total_attempt_limit,
            "safetyPolicyId": record.safety_policy_id,
        }

    @staticmethod
    def _prompt_snapshot(record: AiPromptRecord) -> dict[str, Any]:
        return {
            "promptCode": record.prompt_code,
            "scenario": record.scenario,
            "systemTemplate": record.system_template,
            "userTemplate": record.user_template,
            "allowedInputFields": record.allowed_input_fields,
            "outputSchema": record.output_schema,
            "safetyPolicyId": record.safety_policy_id,
        }

    @staticmethod
    def _risk_snapshot(record: AiRiskPolicyRecord) -> dict[str, Any]:
        return {
            "policyCode": record.policy_code,
            "blockedCategories": record.blocked_categories,
            "reviewCategories": record.review_categories,
            "inputModerationEnabled": record.input_moderation_enabled,
            "outputModerationEnabled": record.output_moderation_enabled,
            "promptInjectionAction": record.prompt_injection_action,
            "minimumSafetyScore": record.minimum_safety_score,
            "allowAppeals": record.allow_appeals,
        }

    @staticmethod
    def _apply_route(record: AiRouteRecord, value: dict[str, Any]) -> None:
        record.scenario = str(value["scenario"])
        record.logical_model_id = str(value["logicalModelId"])
        record.targets = list(value["targets"])
        record.max_input_tokens = int(value["maxInputTokens"])
        record.max_output_tokens = int(value["maxOutputTokens"])
        record.budget_ceiling_microunits = int(value["budgetCeilingMicrounits"])
        record.total_attempt_limit = int(value["totalAttemptLimit"])
        record.safety_policy_id = str(value["safetyPolicyId"])

    @staticmethod
    def _apply_prompt(record: AiPromptRecord, value: dict[str, Any]) -> None:
        record.prompt_code = str(value["promptCode"])
        record.scenario = str(value["scenario"])
        record.system_template = str(value["systemTemplate"])
        record.user_template = str(value["userTemplate"])
        record.allowed_input_fields = list(value["allowedInputFields"])
        record.output_schema = dict(value["outputSchema"])
        record.safety_policy_id = value["safetyPolicyId"]

    @staticmethod
    def _apply_risk(record: AiRiskPolicyRecord, value: dict[str, Any]) -> None:
        record.policy_code = str(value["policyCode"])
        record.blocked_categories = list(value["blockedCategories"])
        record.review_categories = list(value["reviewCategories"])
        record.input_moderation_enabled = bool(value["inputModerationEnabled"])
        record.output_moderation_enabled = bool(value["outputModerationEnabled"])
        record.prompt_injection_action = str(value["promptInjectionAction"])
        record.minimum_safety_score = float(value["minimumSafetyScore"])
        record.allow_appeals = bool(value["allowAppeals"])
