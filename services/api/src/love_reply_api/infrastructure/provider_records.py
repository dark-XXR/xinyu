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


class ProviderRecord(Base):
    __tablename__ = "providers"

    provider_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    provider_name: Mapped[str] = mapped_column(String(128), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    configuration: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    data_region: Mapped[str | None] = mapped_column(String(64))
    retention_statement: Mapped[str | None] = mapped_column(String(500))
    retry_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False)
    rollout_percentage: Mapped[int] = mapped_column(Integer, nullable=False)
    active_credential_version_id: Mapped[str | None] = mapped_column(String(64))
    published_resource_version: Mapped[int | None] = mapped_column(BigInteger)
    published_rollout_percentage: Mapped[int] = mapped_column(Integer, nullable=False)
    published_effective_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_health_status: Mapped[str | None] = mapped_column(String(32))
    effective_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resource_version: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ProviderCredentialVersionRecord(Base):
    __tablename__ = "provider_credential_versions"

    credential_version_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    provider_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("providers.provider_id", ondelete="CASCADE"), nullable=False,
        index=True,
    )
    encrypted_payload: Mapped[str] = mapped_column(Text, nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(128), nullable=False)
    rotated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by_admin_id: Mapped[str] = mapped_column(String(64), nullable=False)


class ProviderVersionRecord(Base):
    __tablename__ = "provider_versions"
    __table_args__ = (
        UniqueConstraint(
            "provider_id", "resource_version", name="uq_provider_version_number"
        ),
    )

    provider_version_id: Mapped[str] = mapped_column(String(96), primary_key=True)
    provider_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("providers.provider_id", ondelete="CASCADE"), nullable=False,
        index=True,
    )
    resource_version: Mapped[int] = mapped_column(BigInteger, nullable=False)
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    was_published: Mapped[bool] = mapped_column(Boolean, nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    created_by_admin_id: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ProviderHealthCheckRecord(Base):
    __tablename__ = "provider_health_checks"

    health_check_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    provider_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("providers.provider_id", ondelete="CASCADE"), nullable=False,
        index=True,
    )
    provider_resource_version: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    redacted_summary: Mapped[str] = mapped_column(String(500), nullable=False)
    provider_request_id: Mapped[str | None] = mapped_column(String(128))
    created_by_admin_id: Mapped[str] = mapped_column(String(64), nullable=False)


class ProviderAuditRecord(Base):
    __tablename__ = "provider_audit_records"

    audit_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    provider_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("providers.provider_id", ondelete="CASCADE"), nullable=False,
        index=True,
    )
    admin_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    audit_reason: Mapped[str] = mapped_column(String(500), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
