from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from love_reply_api.application.errors import ApiError
from love_reply_api.domain.identity import (
    AccountStatus,
    ConsentType,
    DataRequestStatus,
    DataRequestType,
)
from love_reply_api.infrastructure.identity_records import (
    AuthSessionRecord,
    ConsentRecord,
    DataRequestRecord,
    UserDeviceRecord,
    UserProfileRecord,
    UserRecord,
)

REQUIRED_CONSENTS = {
    ConsentType.TERMS_OF_SERVICE,
    ConsentType.PRIVACY_POLICY,
    ConsentType.SERVICE_REQUIRED,
}


class IdentityService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_user(self, user_id: str) -> tuple[UserRecord, UserProfileRecord]:
        user = await self._session.get(UserRecord, user_id)
        profile = await self._session.get(UserProfileRecord, user_id)
        if user is None or profile is None:
            raise ApiError(status_code=404, code="USER_NOT_FOUND", message="User was not found.")
        return user, profile

    async def update_user(
        self,
        *,
        user_id: str,
        expected_version: int,
        changes: dict[str, Any],
    ) -> tuple[UserRecord, UserProfileRecord]:
        user = await self._session.scalar(
            select(UserRecord).where(UserRecord.user_id == user_id).with_for_update()
        )
        profile = await self._session.get(UserProfileRecord, user_id)
        if user is None or profile is None:
            raise ApiError(status_code=404, code="USER_NOT_FOUND", message="User was not found.")
        if user.resource_version != expected_version:
            raise ApiError(
                status_code=409,
                code="RESOURCE_VERSION_CONFLICT",
                message="Account was updated by another request.",
                details={"currentResourceVersion": user.resource_version},
            )
        if "nickname" in changes:
            profile.nickname = changes["nickname"]
        if "avatar_url" in changes:
            profile.avatar_url = changes["avatar_url"]
        if "locale" in changes:
            user.locale = changes["locale"]
        if "time_zone" in changes:
            user.time_zone = changes["time_zone"]
        now = datetime.now(UTC)
        user.resource_version += 1
        user.updated_at = now
        profile.updated_at = now
        await self._session.commit()
        return user, profile

    async def list_devices(self, user_id: str) -> list[UserDeviceRecord]:
        rows = await self._session.scalars(
            select(UserDeviceRecord)
            .where(UserDeviceRecord.user_id == user_id, UserDeviceRecord.revoked_at.is_(None))
            .order_by(UserDeviceRecord.last_seen_at.desc())
        )
        return list(rows)

    async def revoke_device(self, *, user_id: str, device_id: str) -> None:
        now = datetime.now(UTC)
        device = await self._session.scalar(
            select(UserDeviceRecord).where(
                UserDeviceRecord.user_id == user_id,
                UserDeviceRecord.device_id == device_id,
                UserDeviceRecord.revoked_at.is_(None),
            )
        )
        if device is None:
            raise ApiError(
                status_code=404,
                code="DEVICE_NOT_FOUND",
                message="Device was not found.",
            )
        device.revoked_at = now
        await self._session.execute(
            update(AuthSessionRecord)
            .where(
                AuthSessionRecord.user_id == user_id,
                AuthSessionRecord.device_id == device_id,
                AuthSessionRecord.revoked_at.is_(None),
            )
            .values(revoked_at=now)
        )
        await self._session.commit()

    async def list_consents(self, user_id: str) -> list[ConsentRecord]:
        rows = await self._session.scalars(
            select(ConsentRecord)
            .where(ConsentRecord.user_id == user_id)
            .order_by(ConsentRecord.consent_type)
        )
        return list(rows)

    async def update_consent(
        self,
        *,
        user_id: str,
        consent_type: ConsentType,
        document_version: str,
        granted: bool,
    ) -> ConsentRecord:
        required = consent_type in REQUIRED_CONSENTS
        if required and not granted:
            raise ApiError(
                status_code=409,
                code="REQUIRED_CONSENT_CANNOT_BE_REVOKED",
                message="Required service consent cannot be revoked while the account is active.",
            )
        now = datetime.now(UTC)
        record = await self._session.scalar(
            select(ConsentRecord)
            .where(
                ConsentRecord.user_id == user_id,
                ConsentRecord.consent_type == consent_type.value,
            )
            .with_for_update()
        )
        if record is None:
            record = ConsentRecord(
                consent_id=f"cns_{uuid4().hex}",
                user_id=user_id,
                consent_type=consent_type.value,
                document_version=document_version,
                granted=granted,
                required=required,
                granted_at=now if granted else None,
                resource_version=1,
                updated_at=now,
            )
            self._session.add(record)
        else:
            record.document_version = document_version
            record.granted = granted
            record.granted_at = now if granted else None
            record.resource_version += 1
            record.updated_at = now
        await self._session.commit()
        return record

    async def request_export(self, user_id: str) -> DataRequestRecord:
        now = datetime.now(UTC)
        active = await self._session.scalar(
            select(DataRequestRecord).where(
                DataRequestRecord.user_id == user_id,
                DataRequestRecord.request_type == DataRequestType.EXPORT.value,
                DataRequestRecord.status.in_(
                    [
                        DataRequestStatus.REQUESTED.value,
                        DataRequestStatus.IDENTITY_VERIFIED.value,
                        DataRequestStatus.PROCESSING.value,
                    ]
                ),
            )
        )
        if active is not None:
            return active
        record = DataRequestRecord(
            request_id=f"dreq_{uuid4().hex}",
            user_id=user_id,
            request_type=DataRequestType.EXPORT.value,
            status=DataRequestStatus.REQUESTED.value,
            job_id=f"job_{uuid4().hex}",
            download_url=None,
            expires_at=None,
            cooling_off_ends_at=None,
            request_reason_code=None,
            rejection_reason_code=None,
            resource_version=1,
            created_at=now,
            updated_at=now,
        )
        self._session.add(record)
        await self._session.commit()
        return record

    async def get_data_request(self, *, user_id: str, request_id: str) -> DataRequestRecord:
        record = await self._session.scalar(
            select(DataRequestRecord).where(
                DataRequestRecord.user_id == user_id,
                DataRequestRecord.request_id == request_id,
            )
        )
        if record is None:
            raise ApiError(
                status_code=404,
                code="DATA_REQUEST_NOT_FOUND",
                message="Data request was not found.",
            )
        return record

    async def get_deletion(self, user_id: str) -> DataRequestRecord:
        record = await self._session.scalar(
            select(DataRequestRecord)
            .where(
                DataRequestRecord.user_id == user_id,
                DataRequestRecord.request_type == DataRequestType.DELETION.value,
            )
            .order_by(DataRequestRecord.created_at.desc())
        )
        if record is None:
            raise ApiError(
                status_code=404,
                code="DELETION_NOT_REQUESTED",
                message="Account deletion has not been requested.",
            )
        return record

    async def request_deletion(self, *, user_id: str, reason_code: str) -> DataRequestRecord:
        try:
            existing = await self.get_deletion(user_id)
        except ApiError as exc:
            if exc.code != "DELETION_NOT_REQUESTED":
                raise
        else:
            if existing.status not in {
                DataRequestStatus.COMPLETED.value,
                DataRequestStatus.REJECTED.value,
                DataRequestStatus.CANCELLED.value,
            }:
                return existing

        user = await self._session.scalar(
            select(UserRecord).where(UserRecord.user_id == user_id).with_for_update()
        )
        if user is None:
            raise ApiError(status_code=404, code="USER_NOT_FOUND", message="User was not found.")
        now = datetime.now(UTC)
        record = DataRequestRecord(
            request_id=f"dreq_{uuid4().hex}",
            user_id=user_id,
            request_type=DataRequestType.DELETION.value,
            status=DataRequestStatus.REQUESTED.value,
            job_id=None,
            download_url=None,
            expires_at=None,
            cooling_off_ends_at=now + timedelta(days=14),
            request_reason_code=reason_code,
            rejection_reason_code=None,
            resource_version=1,
            created_at=now,
            updated_at=now,
        )
        user.status = AccountStatus.DELETION_PENDING.value
        user.resource_version += 1
        user.updated_at = now
        self._session.add(record)
        await self._session.commit()
        return record

    async def cancel_deletion(self, user_id: str) -> None:
        record = await self.get_deletion(user_id)
        now = datetime.now(UTC)
        if (
            record.status != DataRequestStatus.REQUESTED.value
            or record.cooling_off_ends_at is None
            or record.cooling_off_ends_at <= now
        ):
            raise ApiError(
                status_code=409,
                code="DELETION_CANNOT_BE_CANCELLED",
                message="Deletion is outside the cancellation period.",
            )
        user = await self._session.scalar(
            select(UserRecord).where(UserRecord.user_id == user_id).with_for_update()
        )
        if user is None:
            raise ApiError(status_code=404, code="USER_NOT_FOUND", message="User was not found.")
        record.status = DataRequestStatus.CANCELLED.value
        record.resource_version += 1
        record.updated_at = now
        user.status = AccountStatus.ACTIVE.value
        user.resource_version += 1
        user.updated_at = now
        await self._session.commit()
