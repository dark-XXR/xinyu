from datetime import datetime
from typing import Any

from sqlalchemy import JSON, BigInteger, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from love_reply_api.infrastructure.database import Base


class AdminUserRecord(Base):
    __tablename__ = "admin_users"

    admin_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    login_name_normalized: Mapped[str] = mapped_column(String(254), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    mfa_secret_ciphertext: Mapped[str] = mapped_column(Text, nullable=False)
    last_totp_counter: Mapped[int | None] = mapped_column(BigInteger)
    account_status: Mapped[str] = mapped_column(String(32), nullable=False)
    mfa_status: Mapped[str] = mapped_column(String(32), nullable=False)
    roles: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    permissions: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resource_version: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AdminMfaChallengeRecord(Base):
    __tablename__ = "admin_mfa_challenges"

    challenge_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    admin_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("admin_users.admin_id", ondelete="CASCADE"), nullable=False
    )
    attempts: Mapped[int] = mapped_column(Integer, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AdminSessionRecord(Base):
    __tablename__ = "admin_sessions"

    session_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    admin_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("admin_users.admin_id", ondelete="CASCADE"), nullable=False,
        index=True,
    )
    token_family_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    refresh_token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    mfa_verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rotated_to_session_id: Mapped[str | None] = mapped_column(String(64))
    reuse_detected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AdminSecurityPolicyRecord(Base):
    __tablename__ = "admin_security_policy_versions"

    policy_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    version: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    configuration: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
