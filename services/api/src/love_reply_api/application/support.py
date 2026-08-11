"""用户与管理员共用的客服工单业务服务。"""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from love_reply_api.application.errors import ApiError
from love_reply_api.infrastructure.platform_records import (
    AdminPlatformAuditRecord,
    SupportTicketMessageRecord,
    SupportTicketRecord,
)


class SupportService:
    """提供工单创建、会话、分派和状态流转，所有管理动作保留理由。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_tickets(
        self, *, user_id: str | None = None, status: str | None = None
    ) -> list[SupportTicketRecord]:
        statement = select(SupportTicketRecord).order_by(SupportTicketRecord.last_message_at.desc())
        if user_id is not None:
            statement = statement.where(SupportTicketRecord.user_id == user_id)
        if status is not None:
            statement = statement.where(SupportTicketRecord.status == status)
        return list((await self._session.scalars(statement)).all())

    async def create_ticket(
        self, *, user_id: str, category: str, subject: str, body: str
    ) -> SupportTicketRecord:
        now = datetime.now(UTC)
        ticket = SupportTicketRecord(
            ticket_id=f"tkt_{uuid4().hex}",
            user_id=user_id,
            category=category,
            subject=subject,
            status="OPEN",
            priority="NORMAL",
            assigned_admin_id=None,
            last_message_at=now,
            resource_version=1,
            created_at=now,
            updated_at=now,
        )
        self._session.add(ticket)
        # 模型未建立双向 ORM 关系，先落主记录以满足消息表外键顺序。
        await self._session.flush()
        self._session.add(self._message(ticket.ticket_id, "USER", user_id, body, False, now))
        await self._session.commit()
        return ticket

    async def get_ticket(
        self, *, ticket_id: str, user_id: str | None = None
    ) -> tuple[SupportTicketRecord, list[SupportTicketMessageRecord]]:
        ticket = await self._session.get(SupportTicketRecord, ticket_id)
        if ticket is None or (user_id is not None and ticket.user_id != user_id):
            raise ApiError(
                status_code=404, code="SUPPORT_TICKET_NOT_FOUND", message="Ticket not found."
            )
        messages = list(
            (
                await self._session.scalars(
                    select(SupportTicketMessageRecord)
                    .where(SupportTicketMessageRecord.ticket_id == ticket_id)
                    .order_by(SupportTicketMessageRecord.created_at)
                )
            ).all()
        )
        if user_id is not None:
            messages = [item for item in messages if not item.internal]
        return ticket, messages

    async def add_user_message(
        self, *, ticket_id: str, user_id: str, body: str
    ) -> SupportTicketRecord:
        ticket, _ = await self.get_ticket(ticket_id=ticket_id, user_id=user_id)
        if ticket.status in {"RESOLVED", "CLOSED"}:
            raise ApiError(
                status_code=409, code="SUPPORT_TICKET_CLOSED", message="Ticket is closed."
            )
        now = datetime.now(UTC)
        self._session.add(self._message(ticket_id, "USER", user_id, body, False, now))
        ticket.status = "WAITING_SUPPORT"
        ticket.last_message_at = now
        ticket.resource_version += 1
        ticket.updated_at = now
        await self._session.commit()
        return ticket

    async def admin_update(
        self,
        *,
        ticket_id: str,
        expected_version: int,
        admin_id: str,
        body: str | None,
        internal: bool,
        status: str,
        priority: str,
        assigned_admin_id: str | None,
        audit_reason: str,
    ) -> SupportTicketRecord:
        ticket = await self._session.scalar(
            select(SupportTicketRecord)
            .where(SupportTicketRecord.ticket_id == ticket_id)
            .with_for_update()
        )
        if ticket is None:
            raise ApiError(
                status_code=404, code="SUPPORT_TICKET_NOT_FOUND", message="Ticket not found."
            )
        if ticket.resource_version != expected_version:
            raise ApiError(
                status_code=409,
                code="RESOURCE_VERSION_CONFLICT",
                message="Resource version does not match.",
                details={"currentVersion": ticket.resource_version},
            )
        now = datetime.now(UTC)
        if body:
            self._session.add(self._message(ticket_id, "ADMIN", admin_id, body, internal, now))
            ticket.last_message_at = now
        ticket.status = status
        ticket.priority = priority
        ticket.assigned_admin_id = assigned_admin_id
        ticket.resource_version += 1
        ticket.updated_at = now
        self._session.add(
            AdminPlatformAuditRecord(
                audit_id=f"paud_{uuid4().hex}",
                resource_type="SUPPORT_TICKET",
                resource_id=ticket_id,
                admin_id=admin_id,
                action="SUPPORT_TICKET_UPDATED",
                audit_reason=audit_reason,
                metadata_json={"status": status, "priority": priority, "internal": internal},
                created_at=now,
            )
        )
        await self._session.commit()
        return ticket

    @staticmethod
    def _message(
        ticket_id: str, sender_type: str, sender_id: str, body: str, internal: bool, now: datetime
    ) -> SupportTicketMessageRecord:
        return SupportTicketMessageRecord(
            message_id=f"msg_{uuid4().hex}",
            ticket_id=ticket_id,
            sender_type=sender_type,
            sender_id=sender_id,
            body=body,
            internal=internal,
            created_at=now,
        )
