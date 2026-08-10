"""统一合规审计、敏感内容披露和依法导出记录。

审计事件只允许追加，不提供删除接口。敏感正文使用应用数据密钥加密，列表检索只读取摘要与
结构化索引；事件哈希链用于发现数据库历史记录被绕过应用直接修改的情况。
"""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, BigInteger, Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from love_reply_api.infrastructure.database import Base


class ComplianceAuditEventRecord(Base):
    __tablename__ = "compliance_audit_events"

    event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(96), nullable=False, index=True)
    outcome: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    actor_type: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    actor_id: Mapped[str | None] = mapped_column(String(128), index=True)
    user_id: Mapped[str | None] = mapped_column(String(64), index=True)
    admin_id: Mapped[str | None] = mapped_column(String(64), index=True)
    session_id: Mapped[str | None] = mapped_column(String(64), index=True)
    request_id: Mapped[str | None] = mapped_column(String(128), index=True)
    client_platform: Mapped[str | None] = mapped_column(String(32))
    client_version: Mapped[str | None] = mapped_column(String(64))
    source_ip_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    resource_type: Mapped[str | None] = mapped_column(String(48), index=True)
    resource_id: Mapped[str | None] = mapped_column(String(128), index=True)
    order_id: Mapped[str | None] = mapped_column(String(64), index=True)
    generation_id: Mapped[str | None] = mapped_column(String(64), index=True)
    provider_id: Mapped[str | None] = mapped_column(String(64), index=True)
    summary: Mapped[str] = mapped_column(String(500), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    contains_sensitive_content: Mapped[bool] = mapped_column(Boolean, nullable=False)
    sensitive_payload_ciphertext: Mapped[str | None] = mapped_column(Text)
    sensitive_payload_digest: Mapped[str | None] = mapped_column(String(64))
    retention_until: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    legal_hold: Mapped[bool] = mapped_column(Boolean, nullable=False, index=True)
    previous_event_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    event_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)


class ComplianceAuditExportRecord(Base):
    """监管/法务导出任务的不可变清单；导出正文仍加密保存并具有短期有效期。"""

    __tablename__ = "compliance_audit_exports"

    export_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    created_by_admin_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    audit_reason: Mapped[str] = mapped_column(String(500), nullable=False)
    filters_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    include_sensitive_content: Mapped[bool] = mapped_column(Boolean, nullable=False)
    event_count: Mapped[int] = mapped_column(BigInteger, nullable=False)
    bundle_ciphertext: Mapped[str] = mapped_column(Text, nullable=False)
    bundle_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
