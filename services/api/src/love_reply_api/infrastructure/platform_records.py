"""网站配置、公告版本和平台运营审计数据库模型。"""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, BigInteger, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from love_reply_api.infrastructure.database import Base


class SystemConfigVersionRecord(Base):
    """网站与 App 基础信息的不可变发布版本。"""

    __tablename__ = "system_config_versions"

    config_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    configuration: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    resource_version: Mapped[int] = mapped_column(BigInteger, nullable=False)
    # 系统初始化版本可能早于首位管理员创建，因此这里保留审计主体 ID 而不建立外键。
    created_by_admin_id: Mapped[str] = mapped_column(String(64), nullable=False)
    published_by_admin_id: Mapped[str | None] = mapped_column(String(64))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class NoticeVersionRecord(Base):
    """公告逻辑 ID 下的版本记录；已发布事实不会被草稿覆盖。"""

    __tablename__ = "notice_versions"
    __table_args__ = (
        UniqueConstraint("notice_id", "version", name="uq_notice_versions_notice_version"),
    )

    notice_version_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    notice_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    version: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    notice_type: Mapped[str] = mapped_column(String(32), nullable=False)
    target_platforms: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    target_locales: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    min_client_version: Mapped[str | None] = mapped_column(String(64))
    max_client_version: Mapped[str | None] = mapped_column(String(64))
    display_frequency: Mapped[str] = mapped_column(String(32), nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    resource_version: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_by_admin_id: Mapped[str] = mapped_column(String(64), nullable=False)
    published_by_admin_id: Mapped[str | None] = mapped_column(String(64))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AdminPlatformAuditRecord(Base):
    """用户状态、公告和网站配置变更的追加式业务审计。"""

    __tablename__ = "admin_platform_audits"

    audit_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    resource_type: Mapped[str] = mapped_column(String(48), nullable=False, index=True)
    resource_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    admin_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    audit_reason: Mapped[str] = mapped_column(String(500), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )


class MediaAssetRecord(Base):
    """由本站接收并管理的图片资源元数据，文件内容不进入数据库。"""

    __tablename__ = "media_assets"

    asset_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    purpose: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    storage_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    original_file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    width_pixels: Mapped[int] = mapped_column(nullable=False)
    height_pixels: Mapped[int] = mapped_column(nullable=False)
    sha256_digest: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    owner_user_id: Mapped[str | None] = mapped_column(String(64), index=True)
    created_by_admin_id: Mapped[str | None] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )


class SupportTicketRecord(Base):
    """客服工单主记录，仅保存队列状态和非秘密业务摘要。"""

    __tablename__ = "support_tickets"

    ticket_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True
    )
    category: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    subject: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    priority: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    assigned_admin_id: Mapped[str | None] = mapped_column(String(64), index=True)
    last_message_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resource_version: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SupportTicketMessageRecord(Base):
    """客服往来消息；正文进入合规访问日志时仍按敏感内容策略处理。"""

    __tablename__ = "support_ticket_messages"

    message_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    ticket_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("support_tickets.ticket_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sender_type: Mapped[str] = mapped_column(String(16), nullable=False)
    sender_id: Mapped[str] = mapped_column(String(64), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    internal: Mapped[bool] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
