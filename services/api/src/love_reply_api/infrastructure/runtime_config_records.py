from datetime import datetime
from typing import Any

from sqlalchemy import JSON, BigInteger, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from love_reply_api.infrastructure.database import Base


class RuntimeConfigVersionRecord(Base):
    __tablename__ = "runtime_config_versions"

    config_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    models: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    styles: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    generation_policy: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    free_entitlement: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    feature_flags: Mapped[dict[str, bool]] = mapped_column(JSON, nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
