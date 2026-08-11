"""用户运营、网站基础配置和公告发布的管理员业务服务。"""

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from love_reply_api.application.errors import ApiError
from love_reply_api.infrastructure.generation_records import (
    EntitlementRecord,
    WalletAccountRecord,
    WalletLedgerRecord,
)
from love_reply_api.infrastructure.identity_records import (
    AuthSessionRecord,
    ConsentRecord,
    UserDeviceRecord,
    UserProfileRecord,
    UserRecord,
)
from love_reply_api.infrastructure.platform_records import (
    AdminPlatformAuditRecord,
    NoticeVersionRecord,
    SystemConfigVersionRecord,
)


@dataclass(frozen=True, slots=True)
class Page:
    items: list[Any]
    next_cursor: str | None
    has_more: bool


class AdminPlatformService:
    """集中处理平台运营数据，所有高风险写操作均保留业务审计。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_users(
        self, *, search: str | None, status: str | None, cursor: str | None, limit: int
    ) -> Page:
        statement = select(UserRecord).order_by(UserRecord.user_id)
        if cursor is not None:
            statement = statement.where(UserRecord.user_id > cursor)
        if status is not None:
            statement = statement.where(UserRecord.status == status)
        if search:
            term = f"%{search.strip().lower()}%"
            statement = statement.where(
                or_(
                    func.lower(UserRecord.user_id).like(term),
                    func.lower(func.coalesce(UserRecord.email_normalized, "")).like(term),
                    func.lower(func.coalesce(UserRecord.phone_e164, "")).like(term),
                )
            )
        rows = list((await self._session.scalars(statement.limit(limit + 1))).all())
        visible = rows[:limit]
        return Page(
            items=[await self.user_summary(item) for item in visible],
            next_cursor=visible[-1].user_id if len(rows) > limit and visible else None,
            has_more=len(rows) > limit,
        )

    async def user_summary(self, user: UserRecord) -> dict[str, Any]:
        profile = await self._session.get(UserProfileRecord, user.user_id)
        entitlement = await self._session.get(EntitlementRecord, user.user_id)
        wallet = await self._session.get(WalletAccountRecord, user.user_id)
        device_count = int(
            await self._session.scalar(
                select(func.count())
                .select_from(UserDeviceRecord)
                .where(
                    UserDeviceRecord.user_id == user.user_id,
                    UserDeviceRecord.revoked_at.is_(None),
                )
            )
            or 0
        )
        return {
            "user_id": user.user_id,
            "status": user.status,
            "masked_email": self._mask_email(user.email_normalized),
            "masked_phone": self._mask_phone(user.phone_e164),
            "nickname": profile.nickname if profile is not None else None,
            "locale": user.locale,
            "time_zone": user.time_zone,
            "plan_code": entitlement.plan_code if entitlement is not None else None,
            "plan_expires_at": entitlement.plan_expires_at if entitlement is not None else None,
            "text_remaining": entitlement.text_remaining if entitlement is not None else 0,
            "vision_remaining": entitlement.vision_remaining if entitlement is not None else 0,
            "energy_balance": wallet.energy_balance if wallet is not None else 0,
            "device_count": device_count,
            "resource_version": user.resource_version,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
        }

    async def get_user_detail(self, user_id: str) -> dict[str, Any]:
        user = await self._user(user_id)
        summary = await self.user_summary(user)
        devices = list(
            (
                await self._session.scalars(
                    select(UserDeviceRecord)
                    .where(UserDeviceRecord.user_id == user_id)
                    .order_by(UserDeviceRecord.last_seen_at.desc())
                )
            ).all()
        )
        consents = list(
            (
                await self._session.scalars(
                    select(ConsentRecord)
                    .where(ConsentRecord.user_id == user_id)
                    .order_by(ConsentRecord.consent_type)
                )
            ).all()
        )
        summary["devices"] = devices
        summary["consents"] = consents
        return summary

    async def get_user_entitlement(self, user_id: str) -> dict[str, Any]:
        await self._user(user_id)
        entitlement = await self._session.get(EntitlementRecord, user_id)
        wallet = await self._session.get(WalletAccountRecord, user_id)
        if entitlement is None or wallet is None:
            raise ApiError(
                status_code=404,
                code="USER_ENTITLEMENT_NOT_FOUND",
                message="User entitlement was not found.",
            )
        return {"entitlement": entitlement, "wallet": wallet}

    async def list_user_ledger(self, *, user_id: str, cursor: str | None, limit: int) -> Page:
        await self._user(user_id)
        statement = (
            select(WalletLedgerRecord)
            .where(WalletLedgerRecord.user_id == user_id)
            .order_by(
                WalletLedgerRecord.created_at.desc(), WalletLedgerRecord.ledger_entry_id.desc()
            )
        )
        if cursor is not None:
            statement = statement.where(WalletLedgerRecord.ledger_entry_id < cursor)
        rows = list((await self._session.scalars(statement.limit(limit + 1))).all())
        visible = rows[:limit]
        return Page(
            items=visible,
            next_cursor=visible[-1].ledger_entry_id if len(rows) > limit and visible else None,
            has_more=len(rows) > limit,
        )

    async def change_user_status(
        self,
        *,
        user_id: str,
        expected_version: int,
        target_status: str,
        admin_id: str,
        audit_reason: str,
    ) -> dict[str, Any]:
        user = await self._session.scalar(
            select(UserRecord).where(UserRecord.user_id == user_id).with_for_update()
        )
        if user is None:
            raise self._not_found("USER_NOT_FOUND", "User")
        self._assert_version(user.resource_version, expected_version)
        if user.status == "DELETION_PENDING":
            raise ApiError(
                status_code=409,
                code="USER_DELETION_PENDING",
                message="Deletion-pending users cannot be changed from the status console.",
            )
        previous_status = user.status
        if previous_status == target_status:
            raise ApiError(
                status_code=409, code="USER_STATUS_UNCHANGED", message="User status is unchanged."
            )
        now = datetime.now(UTC)
        user.status = target_status
        user.resource_version += 1
        user.updated_at = now
        if target_status == "SUSPENDED":
            await self._session.execute(
                update(AuthSessionRecord)
                .where(AuthSessionRecord.user_id == user_id, AuthSessionRecord.revoked_at.is_(None))
                .values(revoked_at=now)
            )
        self._audit(
            resource_type="USER",
            resource_id=user_id,
            admin_id=admin_id,
            action="USER_SUSPENDED" if target_status == "SUSPENDED" else "USER_RESTORED",
            reason=audit_reason,
            metadata={"previousStatus": previous_status, "targetStatus": target_status},
            now=now,
        )
        await self._session.commit()
        return await self.user_summary(user)

    async def get_system_config(self, *, published_only: bool = False) -> SystemConfigVersionRecord:
        statement = select(SystemConfigVersionRecord)
        if published_only:
            statement = statement.where(SystemConfigVersionRecord.status == "PUBLISHED")
        record = await self._session.scalar(
            statement.order_by(SystemConfigVersionRecord.version.desc()).limit(1)
        )
        if record is None:
            raise self._not_found("SYSTEM_CONFIG_NOT_FOUND", "System configuration")
        return record

    async def update_system_config(
        self,
        *,
        expected_version: int,
        configuration: dict[str, Any],
        admin_id: str,
        audit_reason: str,
    ) -> SystemConfigVersionRecord:
        latest = await self._session.scalar(
            select(SystemConfigVersionRecord)
            .order_by(SystemConfigVersionRecord.version.desc())
            .limit(1)
            .with_for_update()
        )
        if latest is None:
            raise self._not_found("SYSTEM_CONFIG_NOT_FOUND", "System configuration")
        self._assert_version(latest.resource_version, expected_version)
        now = datetime.now(UTC)
        if latest.status == "DRAFT":
            latest.configuration = configuration
            latest.resource_version += 1
            latest.updated_at = now
            draft = latest
        else:
            draft = SystemConfigVersionRecord(
                config_id=f"scfg_{uuid4().hex}",
                version=latest.version + 1,
                status="DRAFT",
                configuration=configuration,
                resource_version=1,
                created_by_admin_id=admin_id,
                published_by_admin_id=None,
                published_at=None,
                created_at=now,
                updated_at=now,
            )
            self._session.add(draft)
        self._audit(
            resource_type="SYSTEM_CONFIG",
            resource_id=draft.config_id,
            admin_id=admin_id,
            action="SYSTEM_CONFIG_DRAFT_SAVED",
            reason=audit_reason,
            metadata={"version": draft.version},
            now=now,
        )
        await self._session.commit()
        return draft

    async def publish_system_config(
        self, *, expected_version: int, admin_id: str, audit_reason: str
    ) -> SystemConfigVersionRecord:
        draft = await self._session.scalar(
            select(SystemConfigVersionRecord)
            .where(SystemConfigVersionRecord.status == "DRAFT")
            .order_by(SystemConfigVersionRecord.version.desc())
            .limit(1)
            .with_for_update()
        )
        if draft is None:
            raise ApiError(
                status_code=409,
                code="SYSTEM_CONFIG_DRAFT_REQUIRED",
                message="No system configuration draft is ready.",
            )
        self._assert_version(draft.resource_version, expected_version)
        now = datetime.now(UTC)
        await self._session.execute(
            update(SystemConfigVersionRecord)
            .where(SystemConfigVersionRecord.status == "PUBLISHED")
            .values(status="SUPERSEDED", updated_at=now)
        )
        draft.status = "PUBLISHED"
        draft.published_by_admin_id = admin_id
        draft.published_at = now
        draft.resource_version += 1
        draft.updated_at = now
        self._audit(
            resource_type="SYSTEM_CONFIG",
            resource_id=draft.config_id,
            admin_id=admin_id,
            action="SYSTEM_CONFIG_PUBLISHED",
            reason=audit_reason,
            metadata={"version": draft.version},
            now=now,
        )
        await self._session.commit()
        return draft

    async def list_notices(self) -> list[NoticeVersionRecord]:
        rows = list(
            (
                await self._session.scalars(
                    select(NoticeVersionRecord).order_by(
                        NoticeVersionRecord.notice_id, NoticeVersionRecord.version.desc()
                    )
                )
            ).all()
        )
        latest: dict[str, NoticeVersionRecord] = {}
        for row in rows:
            latest.setdefault(row.notice_id, row)
        return list(latest.values())

    async def create_notice(
        self, *, values: dict[str, Any], admin_id: str, audit_reason: str
    ) -> NoticeVersionRecord:
        now = datetime.now(UTC)
        notice_id = f"ntc_{uuid4().hex}"
        record = self._new_notice(
            notice_id=notice_id, version=1, values=values, admin_id=admin_id, now=now
        )
        self._session.add(record)
        self._audit(
            resource_type="NOTICE",
            resource_id=notice_id,
            admin_id=admin_id,
            action="NOTICE_DRAFT_CREATED",
            reason=audit_reason,
            metadata={"version": 1},
            now=now,
        )
        await self._session.commit()
        return record

    async def update_notice(
        self,
        *,
        notice_id: str,
        expected_version: int,
        values: dict[str, Any],
        admin_id: str,
        audit_reason: str,
    ) -> NoticeVersionRecord:
        latest = await self._latest_notice(notice_id, locked=True)
        self._assert_version(latest.resource_version, expected_version)
        now = datetime.now(UTC)
        if latest.status == "DRAFT":
            for key, value in values.items():
                setattr(latest, key, value)
            latest.resource_version += 1
            latest.updated_at = now
            draft = latest
        else:
            draft = self._new_notice(
                notice_id=notice_id,
                version=latest.version + 1,
                values=values,
                admin_id=admin_id,
                now=now,
            )
            self._session.add(draft)
        self._audit(
            resource_type="NOTICE",
            resource_id=notice_id,
            admin_id=admin_id,
            action="NOTICE_DRAFT_UPDATED",
            reason=audit_reason,
            metadata={"version": draft.version},
            now=now,
        )
        await self._session.commit()
        return draft

    async def publish_notice(
        self, *, notice_id: str, expected_version: int, admin_id: str, audit_reason: str
    ) -> NoticeVersionRecord:
        draft = await self._latest_notice(notice_id, locked=True)
        self._assert_version(draft.resource_version, expected_version)
        if draft.status != "DRAFT":
            raise ApiError(
                status_code=409,
                code="NOTICE_DRAFT_REQUIRED",
                message="Latest notice version is not a draft.",
            )
        now = datetime.now(UTC)
        await self._session.execute(
            update(NoticeVersionRecord)
            .where(
                NoticeVersionRecord.notice_id == notice_id,
                NoticeVersionRecord.status == "PUBLISHED",
            )
            .values(status="SUPERSEDED", updated_at=now)
        )
        draft.status = "PUBLISHED"
        draft.published_by_admin_id = admin_id
        draft.published_at = now
        draft.resource_version += 1
        draft.updated_at = now
        self._audit(
            resource_type="NOTICE",
            resource_id=notice_id,
            admin_id=admin_id,
            action="NOTICE_PUBLISHED",
            reason=audit_reason,
            metadata={"version": draft.version},
            now=now,
        )
        await self._session.commit()
        return draft

    async def revoke_notice(
        self, *, notice_id: str, expected_version: int, admin_id: str, audit_reason: str
    ) -> NoticeVersionRecord:
        record = await self._latest_notice(notice_id, locked=True)
        self._assert_version(record.resource_version, expected_version)
        if record.status != "PUBLISHED":
            raise ApiError(
                status_code=409, code="NOTICE_NOT_PUBLISHED", message="Notice is not published."
            )
        now = datetime.now(UTC)
        record.status = "REVOKED"
        record.revoked_at = now
        record.resource_version += 1
        record.updated_at = now
        self._audit(
            resource_type="NOTICE",
            resource_id=notice_id,
            admin_id=admin_id,
            action="NOTICE_REVOKED",
            reason=audit_reason,
            metadata={"version": record.version},
            now=now,
        )
        await self._session.commit()
        return record

    async def list_public_notices(
        self, *, platform: str, locale: str, client_version: str, now: datetime
    ) -> list[NoticeVersionRecord]:
        rows = list(
            (
                await self._session.scalars(
                    select(NoticeVersionRecord)
                    .where(
                        NoticeVersionRecord.status == "PUBLISHED",
                        NoticeVersionRecord.starts_at <= now,
                        or_(
                            NoticeVersionRecord.ends_at.is_(None), NoticeVersionRecord.ends_at > now
                        ),
                    )
                    .order_by(NoticeVersionRecord.starts_at.desc())
                )
            ).all()
        )
        return [
            row
            for row in rows
            if platform in row.target_platforms
            and (
                not row.target_locales
                or locale in row.target_locales
                or locale.split("-", 1)[0] in row.target_locales
            )
            and self._version_in_range(
                client_version,
                minimum=row.min_client_version,
                maximum=row.max_client_version,
            )
        ]

    async def _user(self, user_id: str) -> UserRecord:
        user = await self._session.get(UserRecord, user_id)
        if user is None:
            raise self._not_found("USER_NOT_FOUND", "User")
        return user

    async def _latest_notice(self, notice_id: str, *, locked: bool) -> NoticeVersionRecord:
        statement = (
            select(NoticeVersionRecord)
            .where(NoticeVersionRecord.notice_id == notice_id)
            .order_by(NoticeVersionRecord.version.desc())
            .limit(1)
        )
        if locked:
            statement = statement.with_for_update()
        record = await self._session.scalar(statement)
        if record is None:
            raise self._not_found("NOTICE_NOT_FOUND", "Notice")
        return record

    @staticmethod
    def _new_notice(
        *, notice_id: str, version: int, values: dict[str, Any], admin_id: str, now: datetime
    ) -> NoticeVersionRecord:
        return NoticeVersionRecord(
            notice_version_id=f"ntv_{uuid4().hex}",
            notice_id=notice_id,
            version=version,
            status="DRAFT",
            resource_version=1,
            created_by_admin_id=admin_id,
            published_by_admin_id=None,
            published_at=None,
            revoked_at=None,
            created_at=now,
            updated_at=now,
            **values,
        )

    def _audit(
        self,
        *,
        resource_type: str,
        resource_id: str,
        admin_id: str,
        action: str,
        reason: str,
        metadata: dict[str, Any],
        now: datetime,
    ) -> None:
        self._session.add(
            AdminPlatformAuditRecord(
                audit_id=f"paud_{uuid4().hex}",
                resource_type=resource_type,
                resource_id=resource_id,
                admin_id=admin_id,
                action=action,
                audit_reason=reason,
                metadata_json=metadata,
                created_at=now,
            )
        )

    @staticmethod
    def _assert_version(current: int, expected: int) -> None:
        if current != expected:
            raise ApiError(
                status_code=409,
                code="RESOURCE_VERSION_CONFLICT",
                message="Resource version does not match.",
                details={"currentVersion": current},
            )

    @staticmethod
    def _not_found(code: str, label: str) -> ApiError:
        return ApiError(status_code=404, code=code, message=f"{label} was not found.")

    @staticmethod
    def _mask_email(value: str | None) -> str | None:
        if value is None:
            return None
        local, domain = value.split("@", 1)
        return f"{local[:2]}***@{domain}"

    @staticmethod
    def _mask_phone(value: str | None) -> str | None:
        if value is None:
            return None
        return f"{value[:3]}****{value[-4:]}" if len(value) >= 8 else "***"

    @classmethod
    def _version_in_range(cls, value: str, *, minimum: str | None, maximum: str | None) -> bool:
        """比较语义版本核心号和预发布段；无法解析时关闭定向公告而非误投放。"""
        parsed = cls._version_key(value)
        if parsed is None:
            return False
        if minimum is not None:
            parsed_minimum = cls._version_key(minimum)
            if parsed_minimum is None or parsed < parsed_minimum:
                return False
        if maximum is not None:
            parsed_maximum = cls._version_key(maximum)
            if parsed_maximum is None or parsed > parsed_maximum:
                return False
        return True

    @staticmethod
    def _version_key(value: str) -> tuple[int, int, int, int, tuple[tuple[int, str], ...]] | None:
        match = re.fullmatch(
            r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
            r"(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?(?:\+[0-9A-Za-z.-]+)?",
            value,
        )
        if match is None:
            return None
        prerelease = match.group(4)
        # 正式版高于同核心号的预发布版；数字标识低于非数字标识。
        prerelease_key: tuple[tuple[int, str], ...] = ()
        release_rank = 1
        if prerelease is not None:
            release_rank = 0
            prerelease_key = tuple(
                (0, f"{int(part):020d}") if part.isdigit() else (1, part)
                for part in prerelease.split(".")
            )
        return (
            int(match.group(1)),
            int(match.group(2)),
            int(match.group(3)),
            release_rank,
            prerelease_key,
        )
