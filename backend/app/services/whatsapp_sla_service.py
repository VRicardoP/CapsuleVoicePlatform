"""
WhatsApp SLA Check Service.

Background task that detects SLA breaches on open conversations
and records them in wa_sla_breaches.
"""

import logging
from datetime import UTC, datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.services.whatsapp_sse import sse_broadcaster

logger = logging.getLogger(__name__)


class SlaCheckService:
    """Periodically checks for SLA breaches on open conversations."""

    def __init__(self, session_maker: async_sessionmaker[AsyncSession]) -> None:
        self._session_maker = session_maker

    async def run_check_cycle(self) -> int:
        """Run a single SLA breach detection cycle.

        Returns the number of new breaches detected.
        """
        breaches_detected = 0

        async with self._session_maker() as db:
            now = datetime.now(UTC)

            # Find open conversations that have breached first-response SLA
            # i.e. no agent has responded yet AND the SLA time has elapsed
            first_response_breaches = await db.execute(
                text("""
                SELECT c.id as conversation_id, c.tenant_id, p.id as policy_id
                FROM wa_conversations c
                JOIN wa_sla_policies p
                    ON p.tenant_id = c.tenant_id
                    AND p.is_active = true
                    AND p.priority = c.priority
                WHERE c.status IN ('open', 'assigned')
                  AND c.sla_first_response_at IS NULL
                  AND c.sla_breached = false
                  AND c.created_at + (p.first_response_minutes || ' minutes')::interval < :now
                  AND NOT EXISTS (
                      SELECT 1 FROM wa_sla_breaches b
                      WHERE b.conversation_id = c.id
                        AND b.breach_type = 'first_response'
                  )
            """),
                {"now": now},
            )

            for row in first_response_breaches.fetchall():
                await db.execute(
                    text("""
                    INSERT INTO wa_sla_breaches (tenant_id, conversation_id, policy_id, breach_type, breached_at)
                    VALUES (CAST(:tid AS UUID), CAST(:cid AS UUID), CAST(:pid AS UUID), 'first_response', :now)
                """),
                    {
                        "tid": str(row.tenant_id),
                        "cid": str(row.conversation_id),
                        "pid": str(row.policy_id),
                        "now": now,
                    },
                )

                # Mark conversation as breached
                await db.execute(
                    text("""
                    UPDATE wa_conversations SET sla_breached = true
                    WHERE id = CAST(:cid AS UUID)
                """),
                    {"cid": str(row.conversation_id)},
                )

                breaches_detected += 1

                # Publish SSE event
                await sse_broadcaster.publish(
                    str(row.tenant_id),
                    "sla.breach",
                    {
                        "conversationId": str(row.conversation_id),
                        "policyId": str(row.policy_id),
                        "breachType": "first_response",
                        "breachedAt": now.isoformat(),
                    },
                )

            # Find conversations that have breached resolution SLA
            resolution_breaches = await db.execute(
                text("""
                SELECT c.id as conversation_id, c.tenant_id, p.id as policy_id
                FROM wa_conversations c
                JOIN wa_sla_policies p
                    ON p.tenant_id = c.tenant_id
                    AND p.is_active = true
                    AND p.priority = c.priority
                WHERE c.status IN ('open', 'assigned')
                  AND c.created_at + (p.resolution_minutes || ' minutes')::interval < :now
                  AND NOT EXISTS (
                      SELECT 1 FROM wa_sla_breaches b
                      WHERE b.conversation_id = c.id
                        AND b.breach_type = 'resolution'
                  )
            """),
                {"now": now},
            )

            for row in resolution_breaches.fetchall():
                await db.execute(
                    text("""
                    INSERT INTO wa_sla_breaches (tenant_id, conversation_id, policy_id, breach_type, breached_at)
                    VALUES (CAST(:tid AS UUID), CAST(:cid AS UUID), CAST(:pid AS UUID), 'resolution', :now)
                """),
                    {
                        "tid": str(row.tenant_id),
                        "cid": str(row.conversation_id),
                        "pid": str(row.policy_id),
                        "now": now,
                    },
                )

                breaches_detected += 1

                await sse_broadcaster.publish(
                    str(row.tenant_id),
                    "sla.breach",
                    {
                        "conversationId": str(row.conversation_id),
                        "policyId": str(row.policy_id),
                        "breachType": "resolution",
                        "breachedAt": now.isoformat(),
                    },
                )

            if breaches_detected > 0:
                await db.commit()

        return breaches_detected

    async def escalate_breaches(self) -> int:
        """Escalate unresolved SLA breaches.

        For breaches older than the policy threshold:
        - Notify via SSE with escalation level
        - Could be extended to send email notifications
        """
        escalated = 0

        async with self._session_maker() as db:
            now = datetime.now(UTC)

            # Find unresolved breaches older than 2x the SLA time (escalation trigger)
            result = await db.execute(
                text("""
                SELECT b.id, b.tenant_id, b.conversation_id, b.policy_id,
                       b.breach_type, b.breached_at,
                       p.escalation_email, p.first_response_minutes, p.resolution_minutes
                FROM wa_sla_breaches b
                JOIN wa_sla_policies p ON p.id = b.policy_id
                WHERE b.resolved_at IS NULL
                  AND b.breached_at + (
                      CASE b.breach_type
                          WHEN 'first_response' THEN p.first_response_minutes
                          WHEN 'resolution' THEN p.resolution_minutes
                      END || ' minutes'
                  )::interval < :now
            """),
                {"now": now},
            )

            for row in result.fetchall():
                escalated += 1
                await sse_broadcaster.publish(
                    str(row.tenant_id),
                    "sla.escalated",
                    {
                        "conversationId": str(row.conversation_id),
                        "policyId": str(row.policy_id),
                        "breachType": row.breach_type,
                        "escalationEmail": row.escalation_email,
                        "breachedAt": row.breached_at.isoformat() if row.breached_at else None,
                    },
                )

        return escalated
