"""
GDPR repository - Data access for GDPR rights and compliance.
Handles Art. 15-22 rights, LOPDGDD Art. 33 blocking, and data exports.
"""

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select, text, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import (
    BlockedData,
    DataSubjectRequest,
    SecurityBreach,
)
from app.repositories.base import BaseRepository


class DataSubjectRequestRepository(BaseRepository[DataSubjectRequest]):
    """
    Repository for GDPR rights requests (ARSOPL).

    RGPD Art. 12.3: Response within 1 month
    """

    def __init__(self, session: AsyncSession):
        super().__init__(session, DataSubjectRequest)

    async def create_request(
        self,
        request_type: str,
        requester_type: str,
        requester_id: UUID | None = None,
        requester_email: str | None = None,
        request_details: str | None = None,
    ) -> DataSubjectRequest:
        """
        Create a new GDPR rights request.
        Automatically sets response deadline (RGPD Art. 12.3: 1 month).
        """
        now = datetime.now(UTC)
        return await self.create(
            {
                "request_type": request_type,
                "requester_type": requester_type,
                "requester_id": requester_id,
                "requester_email": requester_email,
                "request_details": request_details,
                "received_at": now,
                "response_due_date": now + timedelta(days=30),  # 1 month
                "status": "pending",
            }
        )

    async def get_pending_requests(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[DataSubjectRequest]:
        """Get all pending requests."""
        result = await self.session.execute(
            select(DataSubjectRequest)
            .where(DataSubjectRequest.status.in_(("pending", "in_progress")))
            .order_by(DataSubjectRequest.response_due_date)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_overdue_requests(self) -> Sequence[DataSubjectRequest]:
        """Get requests past their deadline (compliance violation)."""
        result = await self.session.execute(
            select(DataSubjectRequest)
            .where(DataSubjectRequest.status.in_(("pending", "in_progress")))
            .where(DataSubjectRequest.response_due_date < datetime.now(UTC))
            .order_by(DataSubjectRequest.response_due_date)
        )
        return result.scalars().all()

    async def extend_deadline(
        self,
        request_id: UUID,
        extension_reason: str,
        extra_months: int = 2,  # Max 2 months extension per RGPD
    ) -> DataSubjectRequest | None:
        """
        Extend deadline for complex requests.
        RGPD Art. 12.3: Can extend by 2 months for complex requests.
        """
        request = await self.get_by_id(request_id)
        if not request:
            return None

        new_deadline = request.response_due_date + timedelta(days=30 * extra_months)

        await self.session.execute(
            update(DataSubjectRequest)
            .where(DataSubjectRequest.id == request_id)
            .values(
                extended_deadline=new_deadline,
                extension_reason=extension_reason,
            )
        )

        await self.session.refresh(request)
        return request

    async def complete_request(
        self,
        request_id: UUID,
        response_type: str,
        response_details: str | None = None,
        denial_reason: str | None = None,
        export_file_path: str | None = None,
    ) -> DataSubjectRequest | None:
        """Complete a GDPR request."""
        request = await self.get_by_id(request_id)
        if not request:
            return None

        await self.session.execute(
            update(DataSubjectRequest)
            .where(DataSubjectRequest.id == request_id)
            .values(
                status="completed" if denial_reason is None else "rejected",
                responded_at=datetime.now(UTC),
                response_type=response_type,
                response_details=response_details,
                denial_reason=denial_reason,
                export_file_path=export_file_path,
            )
        )

        await self.session.refresh(request)
        return request


class BlockedDataRepository(BaseRepository[BlockedData]):
    """
    Repository for blocked data (LOPDGDD Art. 33).

    When data deletion is requested but legal retention is required,
    data is moved here with restricted access.
    """

    def __init__(self, session: AsyncSession):
        super().__init__(session, BlockedData)

    async def block_data(
        self,
        original_table: str,
        original_id: UUID,
        block_reason: str,
        block_legal_basis: str,
        data_encrypted: bytes,
        data_encryption_key_id: str,
        data_hash: str,
        unblock_date: Any,
        data_subject_type: str | None = None,
        data_subject_id: UUID | None = None,
        created_by: UUID | None = None,
        deletion_request_id: UUID | None = None,
    ) -> BlockedData:
        """
        Block data for legal retention (LOPDGDD Art. 33).
        """
        return await self.create(
            {
                "original_table": original_table,
                "original_id": original_id,
                "block_reason": block_reason,
                "block_legal_basis": block_legal_basis,
                "data_encrypted": data_encrypted,
                "data_encryption_key_id": data_encryption_key_id,
                "data_hash": data_hash,
                "unblock_date": unblock_date,
                "data_subject_type": data_subject_type,
                "data_subject_id": data_subject_id,
                "created_by": created_by,
                "deletion_request_id": deletion_request_id,
            }
        )

    async def get_blocked_for_subject(
        self,
        data_subject_type: str,
        data_subject_id: UUID,
    ) -> Sequence[BlockedData]:
        """Get all blocked data for a data subject."""
        result = await self.session.execute(
            select(BlockedData)
            .where(BlockedData.data_subject_type == data_subject_type)
            .where(BlockedData.data_subject_id == data_subject_id)
            .where(BlockedData.destroyed_at.is_(None))
        )
        return result.scalars().all()

    async def get_ready_for_destruction(self) -> Sequence[BlockedData]:
        """Get blocked data ready for permanent deletion."""
        result = await self.session.execute(
            select(BlockedData)
            .where(BlockedData.destroyed_at.is_(None))
            .where(BlockedData.unblock_date.isnot(None))
            .where(BlockedData.unblock_date <= datetime.now(UTC))
        )
        return result.scalars().all()

    async def log_access(
        self,
        blocked_id: UUID,
        accessor_type: str,
        accessor_id: str | None,
        reason: str,
    ) -> None:
        """
        Log access to blocked data (LOPDGDD Art. 33.3).
        Access is restricted to judicial authorities.
        """
        blocked = await self.get_by_id(blocked_id)
        if not blocked:
            return

        access_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "accessor_type": accessor_type,
            "accessor_id": accessor_id,
            "reason": reason,
        }

        current_log = blocked.access_log or []
        current_log.append(access_entry)

        await self.session.execute(
            update(BlockedData).where(BlockedData.id == blocked_id).values(access_log=current_log)
        )

    async def mark_destroyed(
        self,
        blocked_id: UUID,
        destroyed_by: UUID | None = None,
    ) -> None:
        """Mark blocked data as permanently destroyed."""
        await self.session.execute(
            update(BlockedData)
            .where(BlockedData.id == blocked_id)
            .values(
                status="destroyed",
                destroyed_at=datetime.now(UTC),
                destroyed_by=destroyed_by,
                # data_encrypted is NOT NULL — cannot clear it
            )
        )


class SecurityBreachRepository(BaseRepository[SecurityBreach]):
    """
    Repository for security breaches (RGPD Art. 33-34, NIS2 Art. 23).
    Maps to security_breaches table (sferaai.sql line 6430).
    """

    def __init__(self, session: AsyncSession):
        super().__init__(session, SecurityBreach)

    async def register_breach(
        self,
        breach_type: str,
        severity: str,
        nature: str,
        risk_level: str = "possible",
        approximate_records: int = 0,
        categories_affected: list[str] | None = None,
        detection_method: str | None = None,
    ) -> SecurityBreach | None:
        """
        Register a new security breach via raw SQL.
        Sets 72-hour notification deadline (RGPD Art. 33.1).

        Uses PRODUCTION column names:
          nature (not breach_description), approximate_records (not affected_records_count),
          categories_affected (not data_categories_affected), detection_method (direct column),
          detected_by = 'system' for automated detection.
        """

        now = datetime.now(UTC)
        deadline = now + timedelta(hours=72)

        try:
            result = await self.session.execute(
                text("""
                    INSERT INTO security_breaches (
                        breach_type, severity, nature, risk_level,
                        detected_at, detected_by, detection_method,
                        authority_notification_deadline,
                        approximate_records, categories_affected,
                        status
                    ) VALUES (
                        :breach_type, :severity, :nature, :risk_level,
                        :detected_at, 'system', :detection_method,
                        :deadline,
                        :records, CAST(:categories AS text[]),
                        'detected'
                    )
                    RETURNING id
                """),
                {
                    "breach_type": breach_type,
                    "severity": severity,
                    "nature": nature,
                    "risk_level": risk_level,
                    "detected_at": now,
                    "detection_method": detection_method,
                    "deadline": deadline,
                    "records": approximate_records,
                    "categories": categories_affected or [],
                },
            )
            breach_id = result.scalar()
            return await self.get_by_id(breach_id)
        except Exception as e:
            import logging

            logging.getLogger(__name__).error("Failed to register breach: %s", e)
            return None

    async def get_pending_notifications(self) -> Sequence[SecurityBreach]:
        """Get breaches pending authority notification."""
        result = await self.session.execute(
            select(SecurityBreach)
            .where(SecurityBreach.authority_notified_at.is_(None))
            .where(SecurityBreach.status.notin_(["resolved", "closed"]))
            .order_by(SecurityBreach.authority_notification_deadline)
        )
        return result.scalars().all()

    async def get_overdue_notifications(self) -> Sequence[SecurityBreach]:
        """Get breaches past the 72-hour deadline (compliance violation)."""
        result = await self.session.execute(
            select(SecurityBreach)
            .where(SecurityBreach.authority_notified_at.is_(None))
            .where(SecurityBreach.status.notin_(["resolved", "closed"]))
            .where(SecurityBreach.authority_notification_deadline < datetime.now(UTC))
        )
        return result.scalars().all()

    async def record_authority_notification(
        self,
        breach_id: UUID,
        reference: str | None = None,
    ) -> SecurityBreach | None:
        """Record that authority has been notified."""
        breach = await self.get_by_id(breach_id)
        if not breach:
            return None

        await self.session.execute(
            update(SecurityBreach)
            .where(SecurityBreach.id == breach_id)
            .values(
                authority_notified_at=datetime.now(UTC),
                authority_notification_reference=reference,
                status="authority_notified",
            )
        )

        await self.session.refresh(breach)
        return breach


class AuditLogRepository:
    """
    Repository for audit log (RGPD Art. 30, Art. 5.2).
    Note: Audit log is append-only, no updates or deletes.
    Uses raw SQL to match actual table structure.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def log_action(
        self,
        action: str,
        entity_type: str,
        user_id: UUID | None = None,
        entity_id: UUID | None = None,
        changed_fields: dict | None = None,
        change_summary: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        request_id: str | None = None,
        session_id: UUID | None = None,
        severity: str = "info",
        details: dict | None = None,
    ) -> UUID | None:
        """Create an audit log entry using actual SQL table columns.

        Uses a SAVEPOINT so that audit failures never abort the caller's transaction.
        The BEFORE INSERT trigger auto-computes current_hash, previous_hash,
        and timestamp_signature — do NOT pass them.
        """
        import json
        import logging

        try:
            # Use savepoint to isolate audit from caller's transaction
            await self.session.execute(text("SAVEPOINT audit_sp"))

            result = await self.session.execute(
                text("""
                    INSERT INTO audit_log (
                        user_id, action, entity_type, entity_id,
                        changed_fields, change_summary,
                        ip_address, user_agent, request_id, session_id,
                        severity, details
                    )
                    VALUES (
                        :user_id, :action, :entity_type, :entity_id,
                        CAST(:changed_fields AS JSONB), :change_summary,
                        :ip_address, :user_agent, :request_id, :session_id,
                        :severity, CAST(:details AS JSONB)
                    )
                    RETURNING id
                """),
                {
                    "user_id": str(user_id) if user_id else None,
                    "action": action,
                    "entity_type": entity_type,
                    "entity_id": str(entity_id) if entity_id else None,
                    "changed_fields": json.dumps(changed_fields) if changed_fields else None,
                    "change_summary": change_summary
                    or (f"{action} on {entity_type}" if entity_type else action),
                    "ip_address": ip_address,
                    "user_agent": user_agent,
                    "request_id": request_id,
                    "session_id": str(session_id) if session_id else None,
                    "severity": severity,
                    "details": json.dumps(details) if details else None,
                },
            )
            await self.session.execute(text("RELEASE SAVEPOINT audit_sp"))
            return result.scalar_one()
        except SQLAlchemyError as e:
            # Rollback only the savepoint, not the whole transaction
            try:
                await self.session.execute(text("ROLLBACK TO SAVEPOINT audit_sp"))
            except SQLAlchemyError:
                pass  # SAVEPOINT recovery — transaction may already be invalidated
            logging.getLogger(__name__).error("Failed to create audit log: %s", e)
            return None

    async def get_by_table_and_record(
        self,
        table_name: str,
        record_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[dict]:
        """Get audit trail for a specific record."""
        result = await self.session.execute(
            text("""
                SELECT id, user_id, action, entity_type, entity_id,
                       changed_fields, change_summary, ip_address,
                       created_at, severity
                FROM audit_log
                WHERE entity_type = :entity_type
                  AND entity_id::text = :entity_id
                ORDER BY created_at DESC
                OFFSET :skip LIMIT :limit
            """),
            {"entity_type": table_name, "entity_id": record_id, "skip": skip, "limit": limit},
        )
        return [dict(row._mapping) for row in result.fetchall()]

    async def get_by_user(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> list[dict]:
        """Get all audit log entries by a user."""
        result = await self.session.execute(
            text("""
                SELECT id, user_id, action, entity_type, entity_id,
                       changed_fields, change_summary, ip_address,
                       created_at, severity
                FROM audit_log
                WHERE user_id = :user_id
                ORDER BY created_at DESC
                OFFSET :skip LIMIT :limit
            """),
            {"user_id": str(user_id), "skip": skip, "limit": limit},
        )
        return [dict(row._mapping) for row in result.fetchall()]

    async def verify_integrity(self) -> dict[str, Any]:
        """
        Verify audit log integrity using hash chain.
        Returns integrity status.
        """
        try:
            result = await self.session.execute(
                text("SELECT * FROM verify_audit_log_integrity_summary()")
            )
            row = result.fetchone()
            if row:
                return dict(row._mapping)
        except SQLAlchemyError:
            pass
        return {"status": "unavailable", "message": "Integrity verification not available"}

    async def export_user_data_gdpr(self, user_id: UUID) -> dict[str, Any] | None:
        """Call PostgreSQL GDPR export function (Art. 15, 20)."""
        result = await self.session.execute(
            text("SELECT * FROM export_user_data_gdpr_compliant(:user_id)"),
            {"user_id": str(user_id)},
        )
        row = result.fetchone()
        return dict(row._mapping) if row else None

    async def execute_erasure_with_blocking(self, user_id: UUID) -> None:
        """Call PostgreSQL GDPR erasure function with blocking (Art. 17, LOPDGDD Art. 33)."""
        await self.session.execute(
            text("SELECT gdpr_right_to_erasure_with_blocking(:user_id)"),
            {"user_id": str(user_id)},
        )
