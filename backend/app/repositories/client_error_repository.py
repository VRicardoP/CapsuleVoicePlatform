"""Repository for client error logs (no ORM model — raw SQL)."""

import json
import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class ClientErrorRepository:
    """CRUD for client_error_logs table."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        api_key_id: UUID | None,
        client_version: str | None,
        error_type: str,
        error_message: str,
        method: str | None = None,
        endpoint: str | None = None,
        request_payload: dict | None = None,
        response_status: int | None = None,
        response_body: str | None = None,
        call_id: str | None = None,
        error_timestamp: datetime | None = None,
        stack_trace: str | None = None,
        environment: str | None = None,
        extra_context: dict | None = None,
        reported_from_ip: str | None = None,
    ) -> str | None:
        """Insert a client error log. Returns the error ID."""
        result = await self.session.execute(
            text("""
                INSERT INTO client_error_logs (
                    api_key_id, client_version, error_type, error_message,
                    method, endpoint, request_payload, response_status,
                    response_body, call_id, error_timestamp, stack_trace,
                    environment, extra_context, reported_from_ip
                ) VALUES (
                    :api_key_id, :client_version, :error_type, :error_message,
                    :method, :endpoint, :request_payload, :response_status,
                    :response_body, :call_id, :error_timestamp, :stack_trace,
                    :environment, :extra_context, :ip
                )
                RETURNING id
            """),
            {
                "api_key_id": api_key_id,
                "client_version": client_version,
                "error_type": error_type,
                "error_message": error_message,
                "method": method,
                "endpoint": endpoint,
                "request_payload": json.dumps(request_payload) if request_payload else None,
                "response_status": response_status,
                "response_body": response_body[:1000] if response_body else None,
                "call_id": call_id,
                "error_timestamp": error_timestamp,
                "stack_trace": stack_trace,
                "environment": environment,
                "extra_context": json.dumps(extra_context) if extra_context else None,
                "ip": reported_from_ip,
            },
        )
        row = result.fetchone()
        return str(row[0]) if row else None

    async def list_errors(
        self,
        days: int = 7,
        error_type: str | None = None,
        resolved: bool | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[dict[str, Any]], int]:
        """List client errors with filters. Returns (items, total)."""
        where_clauses = ["error_timestamp >= NOW() - :days * INTERVAL '1 day'"]
        params: dict[str, Any] = {
            "days": days,
            "limit": page_size,
            "offset": (page - 1) * page_size,
        }

        if error_type:
            where_clauses.append("error_type = :error_type")
            params["error_type"] = error_type
        if resolved is not None:
            where_clauses.append("resolved = :resolved")
            params["resolved"] = resolved

        where_sql = " AND ".join(where_clauses)

        count_result = await self.session.execute(
            text(f"SELECT COUNT(*) FROM client_error_logs WHERE {where_sql}"),
            params,
        )
        total = count_result.scalar() or 0

        result = await self.session.execute(
            text(f"""
                SELECT id, client_version, error_type, error_message, endpoint,
                       response_status, call_id, error_timestamp, reported_at,
                       environment, resolved, resolved_at
                FROM client_error_logs
                WHERE {where_sql}
                ORDER BY error_timestamp DESC
                LIMIT :limit OFFSET :offset
            """),
            params,
        )

        items = [dict(row._mapping) for row in result.fetchall()]
        return items, total


class CustomerContextRepository:
    """Repository for customer context queries (AI agent)."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_customer_context(self, contact_id: UUID) -> dict[str, Any] | None:
        """Get decrypted customer context with consent info."""
        result = await self.session.execute(
            text("""
                SELECT
                    c.id as contact_id,
                    decrypt_pii_with_metadata(c.phone) as phone,
                    decrypt_pii_with_metadata(c.email) as email,
                    decrypt_pii_with_metadata(c.full_name) as full_name,
                    c.marketing_opt_out,
                    c.profiling_opt_out,
                    c.processing_restricted,
                    c.robinson_status,
                    (SELECT COUNT(*) FROM calls WHERE contact_id = c.id) as previous_calls_count,
                    (SELECT MAX(initiated_at) FROM calls WHERE contact_id = c.id) as last_call_date,
                    (SELECT array_agg(dpp.code)
                     FROM contact_consents cc
                     JOIN data_consents dc ON dc.id = cc.consent_id
                     JOIN data_processing_purposes dpp ON dpp.id = dc.purpose_id
                     WHERE cc.contact_id = c.id
                       AND dc.consent_given = true
                       AND dc.revoked_at IS NULL
                       AND (dc.expires_at IS NULL OR dc.expires_at > NOW())
                    ) as active_consents
                FROM contacts c
                WHERE c.id = :contact_id AND c.deleted_at IS NULL
            """),
            {"contact_id": str(contact_id)},
        )
        row = result.fetchone()
        return dict(row._mapping) if row else None

    async def check_consent(self, contact_id: UUID, scope: str) -> dict[str, Any] | None:
        """Check if contact has valid consent for a scope. Returns consent info or None."""
        result = await self.session.execute(
            text("""
                SELECT dc.obtained_at, dc.expires_at
                FROM contact_consents cc
                JOIN data_consents dc ON dc.id = cc.consent_id
                JOIN data_processing_purposes dpp ON dpp.id = dc.purpose_id
                WHERE cc.contact_id = :contact_id
                  AND dpp.code = :scope
                  AND dc.consent_given = true
                  AND dc.revoked_at IS NULL
                  AND (dc.expires_at IS NULL OR dc.expires_at > NOW())
                LIMIT 1
            """),
            {"contact_id": str(contact_id), "scope": scope},
        )
        row = result.fetchone()
        return dict(row._mapping) if row else None
