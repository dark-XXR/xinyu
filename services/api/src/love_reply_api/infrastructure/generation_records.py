from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from love_reply_api.infrastructure.database import Base


class EntitlementRecord(Base):
    __tablename__ = "user_entitlements"

    user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True
    )
    plan_code: Mapped[str] = mapped_column(String(64), nullable=False)
    plan_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    text_remaining: Mapped[int] = mapped_column(BigInteger, nullable=False)
    text_reserved: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    vision_remaining: Mapped[int] = mapped_column(BigInteger, nullable=False)
    allowed_model_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    allowed_style_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    resource_version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class WalletAccountRecord(Base):
    __tablename__ = "wallet_accounts"

    user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True
    )
    energy_balance: Mapped[int] = mapped_column(BigInteger, nullable=False)
    energy_reserved: Mapped[int] = mapped_column(BigInteger, nullable=False)
    resource_version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class WalletLedgerRecord(Base):
    __tablename__ = "wallet_ledger"

    ledger_entry_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True
    )
    generation_id: Mapped[str | None] = mapped_column(String(64), index=True)
    entry_type: Mapped[str] = mapped_column(String(32), nullable=False)
    energy_delta: Mapped[int] = mapped_column(BigInteger, nullable=False)
    reserved_delta: Mapped[int] = mapped_column(BigInteger, nullable=False)
    balance_after: Mapped[int] = mapped_column(BigInteger, nullable=False)
    reserved_after: Mapped[int] = mapped_column(BigInteger, nullable=False)
    reason_code: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class GenerationQuoteRecord(Base):
    __tablename__ = "generation_quotes"

    quote_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True
    )
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    input_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    context_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    model_id: Mapped[str] = mapped_column(String(128), nullable=False)
    estimated_energy: Mapped[int] = mapped_column(BigInteger, nullable=False)
    charged_from: Mapped[str] = mapped_column(String(32), nullable=False)
    entitlement_version: Mapped[int] = mapped_column(BigInteger, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class GenerationTaskRecord(Base):
    __tablename__ = "generation_tasks"
    __table_args__ = (
        UniqueConstraint("user_id", "client_request_id", name="uq_generation_user_request"),
    )

    generation_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True
    )
    parent_generation_id: Mapped[str | None] = mapped_column(String(64), index=True)
    quote_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    client_request_id: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    input_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    context_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    model_id: Mapped[str] = mapped_column(String(128), nullable=False)
    save_to_history: Mapped[bool] = mapped_column(Boolean, nullable=False)
    charged_from: Mapped[str] = mapped_column(String(32), nullable=False)
    reserved_energy: Mapped[int] = mapped_column(BigInteger, nullable=False)
    analysis_data: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    failure_code: Mapped[str | None] = mapped_column(String(64))
    risk_event_id: Mapped[str | None] = mapped_column(String(64))
    resource_version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class GenerationUsageRecord(Base):
    __tablename__ = "generation_usage"

    generation_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("generation_tasks.generation_id", ondelete="CASCADE"),
        primary_key=True,
    )
    model_id: Mapped[str] = mapped_column(String(128), nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    reserved_energy: Mapped[int] = mapped_column(BigInteger, nullable=False)
    charged_energy: Mapped[int] = mapped_column(BigInteger, nullable=False)
    charged_from: Mapped[str] = mapped_column(String(32), nullable=False)
    settled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ReplyCandidateRecord(Base):
    __tablename__ = "reply_candidates"

    candidate_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    generation_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("generation_tasks.generation_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    strategy: Mapped[str] = mapped_column(String(32), nullable=False)
    style_id: Mapped[str] = mapped_column(String(64), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    safety_status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CandidateActionRecord(Base):
    __tablename__ = "candidate_actions"
    __table_args__ = (
        UniqueConstraint("user_id", "client_action_id", name="uq_candidate_action_user_client"),
    )

    action_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False
    )
    candidate_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("reply_candidates.candidate_id", ondelete="CASCADE"), nullable=False
    )
    client_action_id: Mapped[str] = mapped_column(String(128), nullable=False)
    action_type: Mapped[str] = mapped_column(String(32), nullable=False)
    outcome_code: Mapped[str | None] = mapped_column(String(32))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RiskAppealRecord(Base):
    __tablename__ = "risk_appeals"
    __table_args__ = (
        UniqueConstraint("user_id", "risk_event_id", name="uq_risk_appeal_user_event"),
    )

    appeal_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    risk_event_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True
    )
    reason_code: Mapped[str] = mapped_column(String(64), nullable=False)
    comment: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class GenerationEventRecord(Base):
    __tablename__ = "generation_events"
    __table_args__ = (
        UniqueConstraint("generation_id", "sequence", name="uq_generation_event_sequence"),
    )

    event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    generation_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("generation_tasks.generation_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sequence: Mapped[int] = mapped_column(BigInteger, nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
