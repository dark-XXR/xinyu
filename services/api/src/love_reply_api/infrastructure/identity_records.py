from datetime import datetime

from sqlalchemy import (
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


class UserRecord(Base):
    __tablename__ = "users"

    user_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    phone_e164: Mapped[str | None] = mapped_column(String(20), unique=True)
    email_normalized: Mapped[str | None] = mapped_column(String(254), unique=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    locale: Mapped[str] = mapped_column(String(35), nullable=False)
    time_zone: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class UserProfileRecord(Base):
    __tablename__ = "user_profiles"

    user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True
    )
    nickname: Mapped[str | None] = mapped_column(String(64))
    avatar_url: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class UserDeviceRecord(Base):
    __tablename__ = "user_devices"
    __table_args__ = (
        UniqueConstraint("user_id", "device_id", name="uq_user_devices_owner_device"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False
    )
    device_id: Mapped[str] = mapped_column(String(128), nullable=False)
    platform: Mapped[str] = mapped_column(String(32), nullable=False)
    model: Mapped[str | None] = mapped_column(String(128))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SmsChallengeRecord(Base):
    __tablename__ = "sms_challenges"

    challenge_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    phone_e164: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    purpose: Mapped[str] = mapped_column(String(32), nullable=False)
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class EmailChallengeRecord(Base):
    __tablename__ = "email_challenges"

    challenge_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    email_normalized: Mapped[str] = mapped_column(String(254), nullable=False, index=True)
    purpose: Mapped[str] = mapped_column(String(32), nullable=False)
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AuthSessionRecord(Base):
    __tablename__ = "auth_sessions"

    session_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True
    )
    device_id: Mapped[str] = mapped_column(String(128), nullable=False)
    refresh_token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rotated_to_session_id: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ConsentRecord(Base):
    __tablename__ = "consent_records"
    __table_args__ = (UniqueConstraint("user_id", "consent_type", name="uq_consent_user_type"),)

    consent_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True
    )
    consent_type: Mapped[str] = mapped_column(String(64), nullable=False)
    document_version: Mapped[str] = mapped_column(String(64), nullable=False)
    granted: Mapped[bool] = mapped_column(Boolean, nullable=False)
    required: Mapped[bool] = mapped_column(Boolean, nullable=False)
    granted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resource_version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DataRequestRecord(Base):
    __tablename__ = "data_requests"

    request_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True
    )
    request_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    job_id: Mapped[str | None] = mapped_column(String(64))
    download_url: Mapped[str | None] = mapped_column(Text)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cooling_off_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    request_reason_code: Mapped[str | None] = mapped_column(String(64))
    rejection_reason_code: Mapped[str | None] = mapped_column(String(64))
    resource_version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"
    __table_args__ = (
        UniqueConstraint(
            "actor_key",
            "http_method",
            "normalized_path",
            "idempotency_key",
            name="uq_idempotency_scope_key",
        ),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    actor_key: Mapped[str] = mapped_column(String(64), nullable=False)
    http_method: Mapped[str] = mapped_column(String(16), nullable=False)
    normalized_path: Mapped[str] = mapped_column(String(255), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    state: Mapped[str] = mapped_column(String(16), nullable=False)
    response_status: Mapped[int | None] = mapped_column(Integer)
    response_ciphertext: Mapped[str | None] = mapped_column(Text)
    response_content_type: Mapped[str | None] = mapped_column(String(128))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
