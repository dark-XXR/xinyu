"""统一合规审计服务。

服务把登录、支付、AI 内容、后台配置和网站运行事件写入同一追加式账本。敏感正文加密，
摘要和索引字段可检索；任何正文查看、导出或法务冻结操作都会形成新的审计事件。
"""

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from hmac import new as new_hmac
from typing import Any, cast
from uuid import uuid4

from sqlalchemy import Select, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from love_reply_api.application.errors import ApiError
from love_reply_api.application.security import SecretCipher
from love_reply_api.config import Settings
from love_reply_api.infrastructure.audit_records import (
    ComplianceAuditEventRecord,
    ComplianceAuditExportRecord,
)

_GENESIS_HASH = "0" * 64
_CHAIN_LOCK_KEY = 1_907_282_025
_SECRET_KEYS = {
    "password",
    "passwordhash",
    "passwd",
    "pwd",
    "code",
    "otp",
    "otpcode",
    "totpcode",
    "mfacode",
    "authcode",
    "passcode",
    "pincode",
    "onetimepassword",
    "verificationcode",
    "emailcode",
    "smscode",
    "token",
    "accesstoken",
    "refreshtoken",
    "idtoken",
    "authorization",
    "proxyauthorization",
    "sign",
    "signature",
    "secret",
    "clientsecret",
    "apikey",
    "merchantkey",
    "privatekey",
    "secretkey",
    "accesskey",
    "credential",
    "credentials",
}
_SECRET_KEY_SUFFIXES = (
    "password",
    "passwordhash",
    "passwd",
    "token",
    "secret",
    "apikey",
    "merchantkey",
    "privatekey",
    "secretkey",
    "authorization",
    "credential",
    "credentials",
    "signature",
)


@dataclass(frozen=True, slots=True)
class AuditPage:
    items: list[ComplianceAuditEventRecord]
    next_cursor: str | None
    has_more: bool


class ComplianceAuditService:
    def __init__(self, *, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings
        self._cipher = SecretCipher(settings)
        self._integrity_key = settings.audit_integrity_key.get_secret_value().encode("utf-8")

    @staticmethod
    def _canonical(value: Any) -> str:
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)

    @classmethod
    def sanitize_metadata(cls, value: Any, *, depth: int = 0) -> Any:
        """删除凭据类字段并限制深度、数组长度和文本长度，防止日志反向泄密。"""

        if depth > 6:
            return "[DEPTH_LIMIT]"
        if isinstance(value, dict):
            normalized_items = {
                "".join(character for character in str(key).lower() if character.isalnum()): item
                for key, item in value.items()
            }
            descriptor_name = normalized_items.get("name") or normalized_items.get(
                "credentialname"
            )
            descriptor_key = normalized_items.get("key")
            descriptor_label = descriptor_name or descriptor_key
            descriptor_is_secret = False
            if isinstance(descriptor_label, str):
                normalized_label = "".join(
                    character
                    for character in descriptor_label.lower()
                    if character.isalnum()
                )
                descriptor_is_secret = (
                    normalized_label in _SECRET_KEYS
                    or normalized_label.endswith(_SECRET_KEY_SUFFIXES)
                )
            sanitized: dict[str, Any] = {}
            for key, item in list(value.items())[:100]:
                key_text = str(key)
                # 统一去掉大小写、下划线和连字符后判断，覆盖 verification_code、
                # otpCode、Authorization、client-secret 等常见写法，同时避免把
                # statusCode 这类普通业务字段误判为验证码。
                normalized_key = "".join(
                    character for character in key_text.lower() if character.isalnum()
                )
                is_secret = normalized_key in _SECRET_KEYS or normalized_key.endswith(
                    _SECRET_KEY_SUFFIXES
                )
                # 凭据轮换接口使用 {name: "apiKey", value: "..."} 描述密钥；
                # value 本身没有敏感字段名，必须结合 name/key 的语义一并遮蔽。
                is_descriptor_value = descriptor_is_secret and normalized_key in {
                    "value",
                    "credentialvalue",
                }
                sanitized[key_text] = (
                    "[REDACTED]"
                    if is_secret or is_descriptor_value
                    else cls.sanitize_metadata(item, depth=depth + 1)
                )
            return sanitized
        if isinstance(value, (list, tuple)):
            return [cls.sanitize_metadata(item, depth=depth + 1) for item in value[:100]]
        if isinstance(value, str):
            return value[:2000]
        if isinstance(value, (int, float, bool)) or value is None:
            return value
        return str(value)[:2000]

    def _event_hash(self, *, previous_hash: str, material: dict[str, Any]) -> str:
        return new_hmac(
            self._integrity_key,
            f"{previous_hash}.{self._canonical(material)}".encode(),
            sha256,
        ).hexdigest()

    @staticmethod
    def _record_material(record: ComplianceAuditEventRecord) -> dict[str, Any]:
        """重建写入时的核心摘要材料，用于逐条验证历史事件未被修改。"""

        return {
            "eventId": record.event_id,
            "occurredAt": record.occurred_at.isoformat(),
            "ingestedAt": record.ingested_at.isoformat(),
            "category": record.category,
            "eventType": record.event_type,
            "outcome": record.outcome,
            "severity": record.severity,
            "actorType": record.actor_type,
            "actorId": record.actor_id,
            "userId": record.user_id,
            "adminId": record.admin_id,
            "sessionId": record.session_id,
            "requestId": record.request_id,
            "clientPlatform": record.client_platform,
            "clientVersion": record.client_version,
            "sourceIpHash": record.source_ip_hash,
            "resourceType": record.resource_type,
            "resourceId": record.resource_id,
            "orderId": record.order_id,
            "generationId": record.generation_id,
            "providerId": record.provider_id,
            "summary": record.summary,
            "metadata": record.metadata_json,
            "sensitivePayloadDigest": record.sensitive_payload_digest,
            "retentionUntil": record.retention_until.isoformat(),
        }

    async def record_event(
        self,
        *,
        category: str,
        event_type: str,
        outcome: str,
        severity: str,
        actor_type: str,
        summary: str,
        occurred_at: datetime | None = None,
        actor_id: str | None = None,
        user_id: str | None = None,
        admin_id: str | None = None,
        session_id: str | None = None,
        request_id: str | None = None,
        client_platform: str | None = None,
        client_version: str | None = None,
        source_ip: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        order_id: str | None = None,
        generation_id: str | None = None,
        provider_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        sensitive_payload: dict[str, Any] | None = None,
        retention_days: int | None = None,
        legal_hold: bool = False,
        commit: bool = False,
    ) -> ComplianceAuditEventRecord:
        now = occurred_at or datetime.now(UTC)
        clean_metadata = self.sanitize_metadata(metadata or {})
        clean_sensitive = (
            self.sanitize_metadata(sensitive_payload) if sensitive_payload is not None else None
        )
        sensitive_json = self._canonical(clean_sensitive) if clean_sensitive is not None else None
        sensitive_digest = (
            sha256(sensitive_json.encode("utf-8")).hexdigest() if sensitive_json else None
        )
        effective_retention = retention_days or (
            self._settings.audit_sensitive_content_retention_days
            if sensitive_json is not None
            else self._settings.audit_default_retention_days
        )
        retention_until = now + timedelta(days=effective_retention)
        source_ip_hash = (
            new_hmac(self._integrity_key, source_ip.encode(), sha256).hexdigest()
            if source_ip
            else None
        )

        # PostgreSQL 事务级锁保证并发写入仍然形成单一确定的哈希链。
        await self._session.execute(
            text("SELECT pg_advisory_xact_lock(:lock_key)"), {"lock_key": _CHAIN_LOCK_KEY}
        )
        # 入库时间必须在取得链锁后生成，保证排序顺序与前向哈希顺序完全一致。
        ingested_at = datetime.now(UTC)
        previous = await self._session.scalar(
            select(ComplianceAuditEventRecord.event_hash)
            .order_by(
                ComplianceAuditEventRecord.ingested_at.desc(),
                ComplianceAuditEventRecord.event_id.desc(),
            )
            .limit(1)
        )
        event_id = f"cae_{uuid4().hex}"
        material = {
            "eventId": event_id,
            "occurredAt": now.isoformat(),
            "ingestedAt": ingested_at.isoformat(),
            "category": category,
            "eventType": event_type,
            "outcome": outcome,
            "severity": severity,
            "actorType": actor_type,
            "actorId": actor_id,
            "userId": user_id,
            "adminId": admin_id,
            "sessionId": session_id,
            "requestId": request_id,
            "clientPlatform": client_platform,
            "clientVersion": client_version,
            "sourceIpHash": source_ip_hash,
            "resourceType": resource_type,
            "resourceId": resource_id,
            "orderId": order_id,
            "generationId": generation_id,
            "providerId": provider_id,
            "summary": summary[:500],
            "metadata": clean_metadata,
            "sensitivePayloadDigest": sensitive_digest,
            "retentionUntil": retention_until.isoformat(),
        }
        record = ComplianceAuditEventRecord(
            event_id=event_id,
            occurred_at=now,
            ingested_at=ingested_at,
            category=category,
            event_type=event_type,
            outcome=outcome,
            severity=severity,
            actor_type=actor_type,
            actor_id=actor_id,
            user_id=user_id,
            admin_id=admin_id,
            session_id=session_id,
            request_id=request_id,
            client_platform=client_platform,
            client_version=client_version,
            source_ip_hash=source_ip_hash,
            resource_type=resource_type,
            resource_id=resource_id,
            order_id=order_id,
            generation_id=generation_id,
            provider_id=provider_id,
            summary=summary[:500],
            metadata_json=clean_metadata,
            contains_sensitive_content=sensitive_json is not None,
            sensitive_payload_ciphertext=self._cipher.encrypt(sensitive_json)
            if sensitive_json
            else None,
            sensitive_payload_digest=sensitive_digest,
            retention_until=retention_until,
            legal_hold=legal_hold,
            previous_event_hash=previous or _GENESIS_HASH,
            event_hash=self._event_hash(previous_hash=previous or _GENESIS_HASH, material=material),
        )
        self._session.add(record)
        if commit:
            await self._session.commit()
        else:
            await self._session.flush()
        return record

    @staticmethod
    def _filters(
        statement: Select[tuple[ComplianceAuditEventRecord]],
        *,
        category: str | None,
        event_type: str | None,
        outcome: str | None,
        user_id: str | None,
        admin_id: str | None,
        request_id: str | None,
        resource_type: str | None,
        resource_id: str | None,
        order_id: str | None,
        generation_id: str | None,
        from_time: datetime | None,
        to_time: datetime | None,
    ) -> Select[tuple[ComplianceAuditEventRecord]]:
        values = {
            ComplianceAuditEventRecord.category: category,
            ComplianceAuditEventRecord.event_type: event_type,
            ComplianceAuditEventRecord.outcome: outcome,
            ComplianceAuditEventRecord.user_id: user_id,
            ComplianceAuditEventRecord.admin_id: admin_id,
            ComplianceAuditEventRecord.request_id: request_id,
            ComplianceAuditEventRecord.resource_type: resource_type,
            ComplianceAuditEventRecord.resource_id: resource_id,
            ComplianceAuditEventRecord.order_id: order_id,
            ComplianceAuditEventRecord.generation_id: generation_id,
        }
        for column, value in values.items():
            if value is not None:
                statement = statement.where(column == value)
        if from_time is not None:
            statement = statement.where(ComplianceAuditEventRecord.occurred_at >= from_time)
        if to_time is not None:
            statement = statement.where(ComplianceAuditEventRecord.occurred_at <= to_time)
        return statement

    async def list_events(
        self, *, limit: int, cursor: str | None = None, **filters: Any
    ) -> AuditPage:
        statement = self._filters(select(ComplianceAuditEventRecord), **filters)
        if cursor is not None:
            cursor_record = await self._session.get(ComplianceAuditEventRecord, cursor)
            if cursor_record is None:
                raise ApiError(
                    status_code=400, code="AUDIT_CURSOR_INVALID", message="Audit cursor is invalid."
                )
            statement = statement.where(
                (ComplianceAuditEventRecord.occurred_at < cursor_record.occurred_at)
                | (
                    (ComplianceAuditEventRecord.occurred_at == cursor_record.occurred_at)
                    & (ComplianceAuditEventRecord.event_id < cursor_record.event_id)
                )
            )
        rows = list(
            await self._session.scalars(
                statement.order_by(
                    ComplianceAuditEventRecord.occurred_at.desc(),
                    ComplianceAuditEventRecord.event_id.desc(),
                ).limit(limit + 1)
            )
        )
        items = rows[:limit]
        return AuditPage(
            items=items,
            next_cursor=items[-1].event_id if len(rows) > limit else None,
            has_more=len(rows) > limit,
        )

    async def reveal_sensitive(
        self, *, event_id: str, admin_id: str, session_id: str, audit_reason: str, request_id: str
    ) -> dict[str, Any]:
        record = await self._session.get(ComplianceAuditEventRecord, event_id)
        if record is None:
            raise ApiError(
                status_code=404, code="AUDIT_EVENT_NOT_FOUND", message="Audit event was not found."
            )
        if record.sensitive_payload_ciphertext is None:
            raise ApiError(
                status_code=409,
                code="AUDIT_CONTENT_NOT_AVAILABLE",
                message="Audit event has no sensitive content.",
            )
        payload = cast(
            dict[str, Any], json.loads(self._cipher.decrypt(record.sensitive_payload_ciphertext))
        )
        if self._canonical(payload) != self._canonical(self.sanitize_metadata(payload)):
            raise ApiError(
                status_code=409,
                code="AUDIT_CONTENT_INTEGRITY_FAILED",
                message="Audit sensitive content failed integrity validation.",
            )
        digest = sha256(self._canonical(payload).encode()).hexdigest()
        if digest != record.sensitive_payload_digest:
            raise ApiError(
                status_code=409,
                code="AUDIT_CONTENT_INTEGRITY_FAILED",
                message="Audit sensitive content failed integrity validation.",
            )
        await self.record_event(
            category="ADMIN",
            event_type="AUDIT_SENSITIVE_CONTENT_READ",
            outcome="SUCCEEDED",
            severity="HIGH",
            actor_type="ADMIN",
            actor_id=admin_id,
            admin_id=admin_id,
            session_id=session_id,
            request_id=request_id,
            resource_type="AUDIT_EVENT",
            resource_id=event_id,
            summary="管理员查看了受保护的审计正文",
            metadata={"auditReason": audit_reason},
            commit=True,
        )
        return payload

    async def set_legal_hold(
        self,
        *,
        event_id: str,
        enabled: bool,
        admin_id: str,
        session_id: str,
        audit_reason: str,
        request_id: str,
    ) -> ComplianceAuditEventRecord:
        record = await self._session.get(ComplianceAuditEventRecord, event_id)
        if record is None:
            raise ApiError(
                status_code=404, code="AUDIT_EVENT_NOT_FOUND", message="Audit event was not found."
            )
        record.legal_hold = enabled
        await self.record_event(
            category="ADMIN",
            event_type="AUDIT_LEGAL_HOLD_CHANGED",
            outcome="SUCCEEDED",
            severity="HIGH",
            actor_type="ADMIN",
            actor_id=admin_id,
            admin_id=admin_id,
            session_id=session_id,
            request_id=request_id,
            resource_type="AUDIT_EVENT",
            resource_id=event_id,
            summary="管理员变更了审计事件法务冻结状态",
            metadata={"enabled": enabled, "auditReason": audit_reason},
            commit=True,
        )
        return record

    async def verify_chain(self) -> tuple[bool, str | None, int]:
        rows = list(
            await self._session.scalars(
                select(ComplianceAuditEventRecord).order_by(
                    ComplianceAuditEventRecord.ingested_at, ComplianceAuditEventRecord.event_id
                )
            )
        )
        previous = _GENESIS_HASH
        for index, record in enumerate(rows):
            if record.previous_event_hash != previous:
                return False, record.event_id, index
            expected = self._event_hash(
                previous_hash=previous, material=self._record_material(record)
            )
            if expected != record.event_hash:
                return False, record.event_id, index
            if record.sensitive_payload_ciphertext is not None:
                try:
                    sensitive_json = self._cipher.decrypt(record.sensitive_payload_ciphertext)
                except ApiError:
                    return False, record.event_id, index
                if sha256(sensitive_json.encode()).hexdigest() != record.sensitive_payload_digest:
                    return False, record.event_id, index
            previous = record.event_hash
        return True, None, len(rows)

    async def create_export(
        self,
        *,
        admin_id: str,
        session_id: str,
        request_id: str,
        audit_reason: str,
        include_sensitive_content: bool,
        filters: dict[str, Any],
    ) -> ComplianceAuditExportRecord:
        limit = self._settings.audit_max_export_rows
        page = await self.list_events(limit=limit, cursor=None, **filters)
        exported: list[dict[str, Any]] = []
        for item in page.items:
            value: dict[str, Any] = {
                "eventId": item.event_id,
                "occurredAt": item.occurred_at.isoformat(),
                "category": item.category,
                "eventType": item.event_type,
                "outcome": item.outcome,
                "severity": item.severity,
                "actorType": item.actor_type,
                "actorId": item.actor_id,
                "userId": item.user_id,
                "adminId": item.admin_id,
                "sessionId": item.session_id,
                "requestId": item.request_id,
                "resourceType": item.resource_type,
                "resourceId": item.resource_id,
                "orderId": item.order_id,
                "generationId": item.generation_id,
                "providerId": item.provider_id,
                "summary": item.summary,
                "metadata": item.metadata_json,
                "eventHash": item.event_hash,
                "previousEventHash": item.previous_event_hash,
                "retentionUntil": item.retention_until.isoformat(),
                "legalHold": item.legal_hold,
            }
            if include_sensitive_content and item.sensitive_payload_ciphertext is not None:
                value["sensitiveContent"] = json.loads(
                    self._cipher.decrypt(item.sensitive_payload_ciphertext)
                )
            exported.append(value)
        bundle = self._canonical(
            {
                "schemaVersion": "1.0",
                "generatedAt": datetime.now(UTC).isoformat(),
                "truncated": page.has_more,
                "events": exported,
            }
        )
        now = datetime.now(UTC)
        record = ComplianceAuditExportRecord(
            export_id=f"caex_{uuid4().hex}",
            created_by_admin_id=admin_id,
            audit_reason=audit_reason,
            filters_json=self.sanitize_metadata(filters),
            include_sensitive_content=include_sensitive_content,
            event_count=len(exported),
            bundle_ciphertext=self._cipher.encrypt(bundle),
            bundle_digest=sha256(bundle.encode("utf-8")).hexdigest(),
            created_at=now,
            expires_at=now + timedelta(seconds=self._settings.audit_export_ttl_seconds),
        )
        self._session.add(record)
        await self.record_event(
            category="ADMIN",
            event_type="AUDIT_EXPORT_CREATED",
            outcome="SUCCEEDED",
            severity="HIGH",
            actor_type="ADMIN",
            actor_id=admin_id,
            admin_id=admin_id,
            session_id=session_id,
            request_id=request_id,
            resource_type="AUDIT_EXPORT",
            resource_id=record.export_id,
            summary="管理员创建了合规审计导出包",
            metadata={
                "auditReason": audit_reason,
                "includeSensitiveContent": include_sensitive_content,
                "eventCount": len(exported),
                "truncated": page.has_more,
            },
        )
        await self._session.commit()
        return record

    async def read_export(
        self, *, export_id: str, admin_id: str, session_id: str, request_id: str, audit_reason: str
    ) -> dict[str, Any]:
        record = await self._session.get(ComplianceAuditExportRecord, export_id)
        if record is None:
            raise ApiError(
                status_code=404,
                code="AUDIT_EXPORT_NOT_FOUND",
                message="Audit export was not found.",
            )
        if record.expires_at <= datetime.now(UTC):
            raise ApiError(
                status_code=410, code="AUDIT_EXPORT_EXPIRED", message="Audit export has expired."
            )
        bundle = cast(dict[str, Any], json.loads(self._cipher.decrypt(record.bundle_ciphertext)))
        if sha256(self._canonical(bundle).encode()).hexdigest() != record.bundle_digest:
            raise ApiError(
                status_code=409,
                code="AUDIT_EXPORT_INTEGRITY_FAILED",
                message="Audit export failed integrity validation.",
            )
        await self.record_event(
            category="ADMIN",
            event_type="AUDIT_EXPORT_READ",
            outcome="SUCCEEDED",
            severity="HIGH",
            actor_type="ADMIN",
            actor_id=admin_id,
            admin_id=admin_id,
            session_id=session_id,
            request_id=request_id,
            resource_type="AUDIT_EXPORT",
            resource_id=export_id,
            summary="管理员读取了合规审计导出包",
            metadata={"auditReason": audit_reason, "bundleDigest": record.bundle_digest},
            commit=True,
        )
        return bundle
