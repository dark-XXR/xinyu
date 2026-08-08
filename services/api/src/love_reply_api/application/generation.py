import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import Any, Protocol
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from love_reply_api.application.errors import ApiError
from love_reply_api.config import Settings
from love_reply_api.domain.generation import (
    TERMINAL_GENERATION_STATUSES,
    ChargedFrom,
    GenerationStatus,
    ReplyStrategy,
    SafetyStatus,
)
from love_reply_api.infrastructure.generation_records import (
    CandidateActionRecord,
    EntitlementRecord,
    GenerationEventRecord,
    GenerationQuoteRecord,
    GenerationTaskRecord,
    GenerationUsageRecord,
    ReplyCandidateRecord,
    RiskAppealRecord,
    WalletAccountRecord,
    WalletLedgerRecord,
)


@dataclass(frozen=True, slots=True)
class GeneratedCandidate:
    strategy: ReplyStrategy
    style_id: str
    text: str
    safety_status: SafetyStatus


@dataclass(frozen=True, slots=True)
class ModelGeneration:
    possible_intent: str
    emotion: str
    uncertainty_note: str
    risk_tips: list[str]
    candidates: list[GeneratedCandidate]
    input_tokens: int
    output_tokens: int


class AiProvider(Protocol):
    async def generate(
        self,
        *,
        input_data: dict[str, Any],
        context_data: dict[str, Any],
        model_id: str,
    ) -> ModelGeneration: ...


class UnavailableAiProvider:
    async def generate(
        self,
        *,
        input_data: dict[str, Any],
        context_data: dict[str, Any],
        model_id: str,
    ) -> ModelGeneration:
        del input_data, context_data, model_id
        raise ApiError(
            status_code=503,
            code="AI_PROVIDER_UNAVAILABLE",
            message="AI generation provider is not configured.",
            retryable=True,
        )


@dataclass(frozen=True, slots=True)
class QuoteResult:
    record: GenerationQuoteRecord
    available_model_ids: list[str]


class GenerationService:
    def __init__(self, *, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings

    @staticmethod
    def request_hash(
        *,
        input_data: dict[str, Any],
        context_data: dict[str, Any],
        model_id: str,
    ) -> str:
        canonical = json.dumps(
            {"input": input_data, "context": context_data, "modelId": model_id},
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        return sha256(canonical.encode("utf-8")).hexdigest()

    async def get_entitlement(self, user_id: str) -> tuple[EntitlementRecord, WalletAccountRecord]:
        entitlement = await self._session.get(EntitlementRecord, user_id)
        wallet = await self._session.get(WalletAccountRecord, user_id)
        if entitlement is None or wallet is None:
            raise ApiError(
                status_code=409,
                code="ENTITLEMENT_NOT_INITIALIZED",
                message="User entitlement is not initialized.",
            )
        return entitlement, wallet

    async def list_ledger(
        self,
        *,
        user_id: str,
        limit: int,
        cursor: str | None,
        entry_type: str | None,
    ) -> tuple[list[WalletLedgerRecord], bool]:
        statement = (
            select(WalletLedgerRecord)
            .where(WalletLedgerRecord.user_id == user_id)
            .order_by(
                WalletLedgerRecord.created_at.desc(),
                WalletLedgerRecord.ledger_entry_id.desc(),
            )
            .limit(limit + 1)
        )
        if cursor is not None:
            statement = statement.where(WalletLedgerRecord.ledger_entry_id < cursor)
        if entry_type is not None:
            statement = statement.where(WalletLedgerRecord.entry_type == entry_type)
        rows = list(await self._session.scalars(statement))
        return rows[:limit], len(rows) > limit

    async def quote(
        self,
        *,
        user_id: str,
        input_data: dict[str, Any],
        context_data: dict[str, Any],
        requested_model_id: str | None,
    ) -> QuoteResult:
        entitlement, wallet = await self.get_entitlement(user_id)
        model_id = requested_model_id or self._settings.default_model_id
        if model_id not in entitlement.allowed_model_ids:
            raise ApiError(
                status_code=409,
                code="MODEL_NOT_ENTITLED",
                message="Selected model is not available for this entitlement.",
            )
        requested_styles = set(context_data.get("styleIds", []))
        if not requested_styles <= set(entitlement.allowed_style_ids):
            raise ApiError(
                status_code=409,
                code="STYLE_NOT_ENTITLED",
                message="One or more selected styles are unavailable.",
            )
        text = str(input_data.get("text", ""))
        estimated_energy = min(5000, max(100, len(text) * 2 + 300))
        available_text = entitlement.text_remaining - entitlement.text_reserved
        if available_text > 0:
            charged_from = ChargedFrom.SUBSCRIPTION
        elif wallet.energy_balance - wallet.energy_reserved >= estimated_energy:
            charged_from = ChargedFrom.WALLET
        else:
            raise ApiError(
                status_code=409,
                code="INSUFFICIENT_ENTITLEMENT",
                message="No text quota or wallet energy is available.",
                details={"requiredEnergy": estimated_energy},
            )
        now = datetime.now(UTC)
        record = GenerationQuoteRecord(
            quote_id=f"quo_{uuid4().hex}",
            user_id=user_id,
            request_hash=self.request_hash(
                input_data=input_data,
                context_data=context_data,
                model_id=model_id,
            ),
            input_data=input_data,
            context_data=context_data,
            model_id=model_id,
            estimated_energy=estimated_energy,
            charged_from=charged_from.value,
            entitlement_version=entitlement.resource_version,
            expires_at=now + timedelta(seconds=self._settings.quote_ttl_seconds),
            consumed_at=None,
            created_at=now,
        )
        self._session.add(record)
        await self._session.commit()
        return QuoteResult(record=record, available_model_ids=entitlement.allowed_model_ids)

    async def create(
        self,
        *,
        user_id: str,
        quote_id: str,
        client_request_id: str,
        input_data: dict[str, Any],
        context_data: dict[str, Any],
        model_id: str,
        save_to_history: bool,
        parent_generation_id: str | None = None,
    ) -> GenerationTaskRecord:
        now = datetime.now(UTC)
        existing = await self._session.scalar(
            select(GenerationTaskRecord).where(
                GenerationTaskRecord.user_id == user_id,
                GenerationTaskRecord.client_request_id == client_request_id,
            )
        )
        if existing is not None:
            return existing
        quote = await self._session.scalar(
            select(GenerationQuoteRecord)
            .where(
                GenerationQuoteRecord.quote_id == quote_id,
                GenerationQuoteRecord.user_id == user_id,
            )
            .with_for_update()
        )
        if quote is None:
            raise ApiError(status_code=404, code="QUOTE_NOT_FOUND", message="Quote was not found.")
        if quote.consumed_at is not None:
            raise ApiError(
                status_code=409,
                code="QUOTE_ALREADY_CONSUMED",
                message="Quote has already been consumed.",
            )
        if quote.expires_at <= now:
            raise ApiError(status_code=409, code="QUOTE_EXPIRED", message="Quote has expired.")
        actual_hash = self.request_hash(
            input_data=input_data,
            context_data=context_data,
            model_id=model_id,
        )
        if actual_hash != quote.request_hash:
            raise ApiError(
                status_code=409,
                code="QUOTE_REQUEST_MISMATCH",
                message="Generation request does not match its quote.",
            )
        entitlement = await self._session.scalar(
            select(EntitlementRecord).where(EntitlementRecord.user_id == user_id).with_for_update()
        )
        wallet = await self._session.scalar(
            select(WalletAccountRecord)
            .where(WalletAccountRecord.user_id == user_id)
            .with_for_update()
        )
        if entitlement is None or wallet is None:
            raise ApiError(
                status_code=409,
                code="ENTITLEMENT_NOT_INITIALIZED",
                message="User entitlement is not initialized.",
            )
        if entitlement.resource_version != quote.entitlement_version:
            raise ApiError(
                status_code=409,
                code="ENTITLEMENT_VERSION_CONFLICT",
                message="Entitlement changed after the quote was created.",
            )
        generation_id = f"gen_{uuid4().hex}"
        if quote.charged_from == ChargedFrom.SUBSCRIPTION.value:
            if entitlement.text_remaining - entitlement.text_reserved < 1:
                raise ApiError(
                    status_code=409,
                    code="INSUFFICIENT_ENTITLEMENT",
                    message="Text quota is no longer available.",
                )
            entitlement.text_reserved += 1
            entitlement.resource_version += 1
            entitlement.updated_at = now
        else:
            if wallet.energy_balance - wallet.energy_reserved < quote.estimated_energy:
                raise ApiError(
                    status_code=409,
                    code="INSUFFICIENT_ENTITLEMENT",
                    message="Wallet energy is no longer available.",
                )
            wallet.energy_reserved += quote.estimated_energy
            wallet.resource_version += 1
            wallet.updated_at = now
            self._session.add(
                self._ledger(
                    user_id=user_id,
                    generation_id=generation_id,
                    entry_type="RESERVATION",
                    energy_delta=0,
                    reserved_delta=quote.estimated_energy,
                    wallet=wallet,
                    now=now,
                )
            )
        task = GenerationTaskRecord(
            generation_id=generation_id,
            user_id=user_id,
            parent_generation_id=parent_generation_id,
            quote_id=quote.quote_id,
            client_request_id=client_request_id,
            status=GenerationStatus.QUOTA_RESERVED.value,
            input_data=input_data,
            context_data=context_data,
            model_id=model_id,
            save_to_history=save_to_history,
            charged_from=quote.charged_from,
            reserved_energy=quote.estimated_energy,
            analysis_data=None,
            failure_code=None,
            risk_event_id=None,
            resource_version=1,
            created_at=now,
            updated_at=now,
        )
        quote.consumed_at = now
        self._session.add(task)
        await self._session.flush()
        await self._append_event(
            task,
            "task.accepted",
            {"generationId": generation_id, "reservedEnergy": quote.estimated_energy},
            now,
        )
        await self._session.commit()
        return task

    async def process(self, *, generation_id: str, provider: AiProvider) -> None:
        task = await self._owned_task_for_update(generation_id=generation_id, user_id=None)
        if task.status != GenerationStatus.QUOTA_RESERVED.value:
            return
        try:
            for status in (
                GenerationStatus.PARSING,
                GenerationStatus.ANALYZING,
                GenerationStatus.GENERATING,
                GenerationStatus.FILTERING,
            ):
                await self._transition(task, status)
            generated = await provider.generate(
                input_data=task.input_data,
                context_data=task.context_data,
                model_id=task.model_id,
            )
            await self._succeed(task=task, generated=generated)
        except Exception as exc:
            await self.fail_and_release(
                generation_id=generation_id,
                failure_code="MODEL_GENERATION_FAILED",
            )
            raise exc

    async def cancel(self, *, user_id: str, generation_id: str) -> GenerationTaskRecord:
        task = await self._owned_task_for_update(generation_id=generation_id, user_id=user_id)
        if GenerationStatus(task.status) in TERMINAL_GENERATION_STATUSES:
            raise ApiError(
                status_code=409,
                code="GENERATION_NOT_CANCELLABLE",
                message="Generation is already in a terminal state.",
            )
        await self._release(
            task=task, terminal_status=GenerationStatus.CANCELLED, failure_code=None
        )
        return task

    async def fail_and_release(self, *, generation_id: str, failure_code: str) -> None:
        await self._session.rollback()
        task = await self._owned_task_for_update(generation_id=generation_id, user_id=None)
        if GenerationStatus(task.status) in TERMINAL_GENERATION_STATUSES:
            return
        await self._release(
            task=task,
            terminal_status=GenerationStatus.FAILED,
            failure_code=failure_code,
        )

    async def get_task(self, *, user_id: str, generation_id: str) -> GenerationTaskRecord:
        task = await self._session.scalar(
            select(GenerationTaskRecord).where(
                GenerationTaskRecord.generation_id == generation_id,
                GenerationTaskRecord.user_id == user_id,
            )
        )
        if task is None:
            raise ApiError(
                status_code=404,
                code="GENERATION_NOT_FOUND",
                message="Generation was not found.",
            )
        return task

    async def get_candidates(self, generation_id: str) -> list[ReplyCandidateRecord]:
        rows = await self._session.scalars(
            select(ReplyCandidateRecord)
            .where(ReplyCandidateRecord.generation_id == generation_id)
            .order_by(ReplyCandidateRecord.created_at, ReplyCandidateRecord.candidate_id)
        )
        return list(rows)

    async def get_usage(self, generation_id: str) -> GenerationUsageRecord | None:
        return await self._session.get(GenerationUsageRecord, generation_id)

    async def get_events(
        self, *, user_id: str, generation_id: str, after_sequence: int
    ) -> list[GenerationEventRecord]:
        await self.get_task(user_id=user_id, generation_id=generation_id)
        rows = await self._session.scalars(
            select(GenerationEventRecord)
            .where(
                GenerationEventRecord.generation_id == generation_id,
                GenerationEventRecord.sequence > after_sequence,
                GenerationEventRecord.expires_at > datetime.now(UTC),
            )
            .order_by(GenerationEventRecord.sequence)
        )
        return list(rows)

    async def regenerate(
        self,
        *,
        user_id: str,
        parent_generation_id: str,
        quote_id: str,
        client_request_id: str,
    ) -> GenerationTaskRecord:
        await self.get_task(user_id=user_id, generation_id=parent_generation_id)
        quote = await self._owned_quote(user_id=user_id, quote_id=quote_id)
        return await self.create(
            user_id=user_id,
            quote_id=quote.quote_id,
            client_request_id=client_request_id,
            input_data=quote.input_data,
            context_data=quote.context_data,
            model_id=quote.model_id,
            save_to_history=True,
            parent_generation_id=parent_generation_id,
        )

    async def refine_candidate(
        self,
        *,
        user_id: str,
        candidate_id: str,
        quote_id: str,
        client_request_id: str,
        instruction_code: str | None,
        custom_instruction: str | None,
    ) -> GenerationTaskRecord:
        candidate = await self._owned_candidate(user_id=user_id, candidate_id=candidate_id)
        parent = await self.get_task(user_id=user_id, generation_id=candidate.generation_id)
        quote = await self._owned_quote(user_id=user_id, quote_id=quote_id)
        context_data = dict(quote.context_data)
        context_data["refinement"] = {
            "candidateId": candidate_id,
            "sourceText": candidate.text,
            "instructionCode": instruction_code,
            "customInstruction": custom_instruction,
        }
        quote.context_data = context_data
        quote.request_hash = self.request_hash(
            input_data=quote.input_data,
            context_data=context_data,
            model_id=quote.model_id,
        )
        await self._session.commit()
        return await self.create(
            user_id=user_id,
            quote_id=quote.quote_id,
            client_request_id=client_request_id,
            input_data=quote.input_data,
            context_data=context_data,
            model_id=quote.model_id,
            save_to_history=parent.save_to_history,
            parent_generation_id=parent.generation_id,
        )

    async def record_candidate_action(
        self,
        *,
        user_id: str,
        candidate_id: str,
        client_action_id: str,
        action_type: str,
        outcome_code: str | None,
        occurred_at: datetime,
    ) -> CandidateActionRecord:
        await self._owned_candidate(user_id=user_id, candidate_id=candidate_id)
        existing = await self._session.scalar(
            select(CandidateActionRecord).where(
                CandidateActionRecord.user_id == user_id,
                CandidateActionRecord.client_action_id == client_action_id,
            )
        )
        if existing is not None:
            if existing.candidate_id != candidate_id or existing.action_type != action_type:
                raise ApiError(
                    status_code=409,
                    code="CLIENT_ACTION_ID_REUSED",
                    message="Client action identifier was reused for different data.",
                )
            return existing
        now = datetime.now(UTC)
        action = CandidateActionRecord(
            action_id=f"act_{uuid4().hex}",
            user_id=user_id,
            candidate_id=candidate_id,
            client_action_id=client_action_id,
            action_type=action_type,
            outcome_code=outcome_code,
            occurred_at=occurred_at,
            recorded_at=now,
        )
        self._session.add(action)
        await self._session.commit()
        return action

    async def appeal_risk_event(
        self,
        *,
        user_id: str,
        risk_event_id: str,
        reason_code: str,
        comment: str | None,
    ) -> RiskAppealRecord:
        task = await self._session.scalar(
            select(GenerationTaskRecord).where(
                GenerationTaskRecord.user_id == user_id,
                GenerationTaskRecord.risk_event_id == risk_event_id,
            )
        )
        if task is None:
            raise ApiError(
                status_code=404,
                code="RISK_EVENT_NOT_FOUND",
                message="Risk event was not found.",
            )
        existing = await self._session.scalar(
            select(RiskAppealRecord).where(
                RiskAppealRecord.user_id == user_id,
                RiskAppealRecord.risk_event_id == risk_event_id,
            )
        )
        if existing is not None:
            return existing
        now = datetime.now(UTC)
        appeal = RiskAppealRecord(
            appeal_id=f"apl_{uuid4().hex}",
            risk_event_id=risk_event_id,
            user_id=user_id,
            reason_code=reason_code,
            comment=comment,
            status="SUBMITTED",
            created_at=now,
            updated_at=now,
        )
        self._session.add(appeal)
        await self._session.commit()
        return appeal

    async def _owned_quote(
        self, *, user_id: str, quote_id: str
    ) -> GenerationQuoteRecord:
        quote = await self._session.scalar(
            select(GenerationQuoteRecord).where(
                GenerationQuoteRecord.user_id == user_id,
                GenerationQuoteRecord.quote_id == quote_id,
            )
        )
        if quote is None:
            raise ApiError(status_code=404, code="QUOTE_NOT_FOUND", message="Quote was not found.")
        return quote

    async def _owned_candidate(
        self, *, user_id: str, candidate_id: str
    ) -> ReplyCandidateRecord:
        candidate = await self._session.scalar(
            select(ReplyCandidateRecord)
            .join(
                GenerationTaskRecord,
                GenerationTaskRecord.generation_id == ReplyCandidateRecord.generation_id,
            )
            .where(
                ReplyCandidateRecord.candidate_id == candidate_id,
                GenerationTaskRecord.user_id == user_id,
            )
        )
        if candidate is None:
            raise ApiError(
                status_code=404,
                code="CANDIDATE_NOT_FOUND",
                message="Candidate was not found.",
            )
        return candidate

    async def _owned_task_for_update(
        self, *, generation_id: str, user_id: str | None
    ) -> GenerationTaskRecord:
        conditions = [GenerationTaskRecord.generation_id == generation_id]
        if user_id is not None:
            conditions.append(GenerationTaskRecord.user_id == user_id)
        task = await self._session.scalar(
            select(GenerationTaskRecord).where(*conditions).with_for_update()
        )
        if task is None:
            raise ApiError(
                status_code=404,
                code="GENERATION_NOT_FOUND",
                message="Generation was not found.",
            )
        return task

    async def _transition(self, task: GenerationTaskRecord, status: GenerationStatus) -> None:
        now = datetime.now(UTC)
        task.status = status.value
        task.resource_version += 1
        task.updated_at = now
        await self._append_event(task, "task.stage", {"stage": status.value}, now)
        await self._session.commit()

    async def _succeed(self, *, task: GenerationTaskRecord, generated: ModelGeneration) -> None:
        expected_strategies = {ReplyStrategy.SAFE, ReplyStrategy.PUSH_PULL, ReplyStrategy.DIRECT}
        if (
            len(generated.candidates) != 3
            or {item.strategy for item in generated.candidates} != expected_strategies
        ):
            raise ValueError("AI provider must return exactly one candidate per strategy")
        if any(item.safety_status != SafetyStatus.PASSED for item in generated.candidates):
            raise ValueError("AI provider returned a candidate that did not pass safety checks")

        task = await self._owned_task_for_update(
            generation_id=task.generation_id,
            user_id=task.user_id,
        )
        entitlement = await self._session.scalar(
            select(EntitlementRecord)
            .where(EntitlementRecord.user_id == task.user_id)
            .with_for_update()
        )
        wallet = await self._session.scalar(
            select(WalletAccountRecord)
            .where(WalletAccountRecord.user_id == task.user_id)
            .with_for_update()
        )
        if entitlement is None or wallet is None:
            raise RuntimeError("reservation owner is missing")
        now = datetime.now(UTC)
        charged_energy = min(
            task.reserved_energy,
            max(100, generated.input_tokens + generated.output_tokens * 2),
        )
        if task.charged_from == ChargedFrom.SUBSCRIPTION.value:
            entitlement.text_reserved -= 1
            entitlement.text_remaining -= 1
            entitlement.resource_version += 1
            entitlement.updated_at = now
        else:
            wallet.energy_reserved -= task.reserved_energy
            wallet.energy_balance -= charged_energy
            wallet.resource_version += 1
            wallet.updated_at = now
            self._session.add(
                self._ledger(
                    user_id=task.user_id,
                    generation_id=task.generation_id,
                    entry_type="SETTLEMENT",
                    energy_delta=-charged_energy,
                    reserved_delta=-task.reserved_energy,
                    wallet=wallet,
                    now=now,
                )
            )

        analysis = {
            "possibleIntent": generated.possible_intent,
            "emotion": generated.emotion,
            "uncertaintyNote": generated.uncertainty_note,
            "riskTips": generated.risk_tips,
        }
        task.analysis_data = analysis
        task.status = GenerationStatus.SUCCEEDED.value
        task.resource_version += 1
        task.updated_at = now
        await self._append_event(task, "analysis.completed", analysis, now)
        for generated_candidate in generated.candidates:
            candidate = ReplyCandidateRecord(
                candidate_id=f"can_{uuid4().hex}",
                generation_id=task.generation_id,
                strategy=generated_candidate.strategy.value,
                style_id=generated_candidate.style_id,
                text=generated_candidate.text,
                safety_status=generated_candidate.safety_status.value,
                created_at=now,
            )
            self._session.add(candidate)
            await self._append_event(
                task,
                "candidate.completed",
                {
                    "candidate": {
                        "candidateId": candidate.candidate_id,
                        "strategy": candidate.strategy,
                        "styleId": candidate.style_id,
                        "text": candidate.text,
                        "safetyStatus": candidate.safety_status,
                    }
                },
                now,
            )
        usage = GenerationUsageRecord(
            generation_id=task.generation_id,
            model_id=task.model_id,
            input_tokens=generated.input_tokens,
            output_tokens=generated.output_tokens,
            reserved_energy=task.reserved_energy,
            charged_energy=charged_energy,
            charged_from=task.charged_from,
            settled_at=now,
        )
        self._session.add(usage)
        await self._append_event(
            task,
            "usage.settled",
            {
                "modelId": usage.model_id,
                "inputTokens": usage.input_tokens,
                "outputTokens": usage.output_tokens,
                "reservedEnergy": usage.reserved_energy,
                "chargedEnergy": usage.charged_energy,
                "chargedFrom": usage.charged_from,
            },
            now,
        )
        await self._append_event(
            task,
            "task.completed",
            {"resourceVersion": task.resource_version},
            now,
        )
        await self._session.commit()

    async def _release(
        self,
        *,
        task: GenerationTaskRecord,
        terminal_status: GenerationStatus,
        failure_code: str | None,
    ) -> None:
        entitlement = await self._session.scalar(
            select(EntitlementRecord)
            .where(EntitlementRecord.user_id == task.user_id)
            .with_for_update()
        )
        wallet = await self._session.scalar(
            select(WalletAccountRecord)
            .where(WalletAccountRecord.user_id == task.user_id)
            .with_for_update()
        )
        if entitlement is None or wallet is None:
            raise RuntimeError("reservation owner is missing")
        now = datetime.now(UTC)
        if task.charged_from == ChargedFrom.SUBSCRIPTION.value:
            entitlement.text_reserved = max(0, entitlement.text_reserved - 1)
            entitlement.resource_version += 1
            entitlement.updated_at = now
        else:
            wallet.energy_reserved = max(0, wallet.energy_reserved - task.reserved_energy)
            wallet.resource_version += 1
            wallet.updated_at = now
            self._session.add(
                self._ledger(
                    user_id=task.user_id,
                    generation_id=task.generation_id,
                    entry_type="RELEASE",
                    energy_delta=0,
                    reserved_delta=-task.reserved_energy,
                    wallet=wallet,
                    now=now,
                )
            )
        task.status = terminal_status.value
        task.failure_code = failure_code
        task.resource_version += 1
        task.updated_at = now
        event_type = (
            "task.failed" if terminal_status == GenerationStatus.FAILED else "task.completed"
        )
        payload = (
            {"failureCode": failure_code, "recoverable": True}
            if terminal_status == GenerationStatus.FAILED
            else {"resourceVersion": task.resource_version}
        )
        await self._append_event(task, event_type, payload, now)
        await self._session.commit()

    async def _append_event(
        self,
        task: GenerationTaskRecord,
        event_type: str,
        payload: dict[str, Any],
        now: datetime,
    ) -> None:
        current = await self._session.scalar(
            select(func.coalesce(func.max(GenerationEventRecord.sequence), 0)).where(
                GenerationEventRecord.generation_id == task.generation_id
            )
        )
        sequence = int(current or 0) + 1
        self._session.add(
            GenerationEventRecord(
                event_id=f"evt_{uuid4().hex}",
                generation_id=task.generation_id,
                sequence=sequence,
                event_type=event_type,
                payload=payload,
                occurred_at=now,
                expires_at=now + timedelta(seconds=self._settings.generation_event_ttl_seconds),
            )
        )
        await self._session.flush()

    @staticmethod
    def _ledger(
        *,
        user_id: str,
        generation_id: str,
        entry_type: str,
        energy_delta: int,
        reserved_delta: int,
        wallet: WalletAccountRecord,
        now: datetime,
    ) -> WalletLedgerRecord:
        return WalletLedgerRecord(
            ledger_entry_id=f"led_{uuid4().hex}",
            user_id=user_id,
            generation_id=generation_id,
            entry_type=entry_type,
            energy_delta=energy_delta,
            reserved_delta=reserved_delta,
            balance_after=wallet.energy_balance,
            reserved_after=wallet.energy_reserved,
            reason_code=None,
            created_at=now,
        )
