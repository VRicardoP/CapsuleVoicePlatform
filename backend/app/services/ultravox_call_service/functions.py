"""Ultravox function endpoint service methods.

Encapsulates all SQL operations for the Ultravox HTTP tool function endpoints
(ai-disclosure, consent, escalation, customer-context).
"""

import hashlib
import json
import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class UltravoxFunctionsMixin:
    """Service methods for Ultravox function endpoints."""

    @staticmethod
    async def record_ai_disclosure(
        db: AsyncSession,
        call_id: UUID,
        emotion_disclosed: bool = False,
    ) -> datetime:
        """Record AI disclosure on a call (AI Act Art. 50.1).

        Returns the disclosure timestamp.
        """
        now = datetime.now(UTC)
        await db.execute(
            text("""
                UPDATE calls SET
                    ai_disclosure_timestamp = :timestamp,
                    ai_disclosure_method = 'ultravox_agent',
                    emotion_detection_disclosed = :emotion_disclosed,
                    updated_at = NOW()
                WHERE id = :call_id
            """),
            {"call_id": call_id, "timestamp": now, "emotion_disclosed": emotion_disclosed},
        )
        await db.commit()
        return now

    @staticmethod
    async def record_consent(
        db: AsyncSession,
        call_id: UUID,
        consent_given: bool,
        consent_type: str = "recording",
    ) -> datetime:
        """Record consent on a call (RGPD Art. 7).

        Returns the recording timestamp.
        """
        now = datetime.now(UTC)
        if consent_type == "recording":
            await db.execute(
                text("""
                    UPDATE calls SET
                        recording_consent = :consent,
                        recording_consent_timestamp = :timestamp,
                        updated_at = NOW()
                    WHERE id = :call_id
                """),
                {"call_id": call_id, "consent": consent_given, "timestamp": now},
            )
        await db.commit()
        logger.info(
            "Consent recorded for call %s: type=%s, given=%s", call_id, consent_type, consent_given
        )
        return now

    @staticmethod
    async def request_escalation(
        db: AsyncSession,
        call_id: UUID,
        ultravox_call_id: str,
        reason: str,
        priority: str,
        context: str | None,
    ) -> UUID:
        """Request human escalation for a call.

        Updates the call with escalation notes and logs an AI decision.
        Returns the escalation_id.
        """
        escalation_id = uuid4()

        await db.execute(
            text("""
                UPDATE calls SET
                    human_oversight_required = true,
                    disposition_notes = COALESCE(disposition_notes, '') || :escalation_note,
                    updated_at = NOW()
                WHERE id = :call_id
            """),
            {
                "call_id": call_id,
                "escalation_note": f"\n[ESCALATION] Reason: {reason}, Priority: {priority}, Context: {context or 'N/A'}",
            },
        )

        try:
            async with db.begin_nested():
                await db.execute(
                    text("""
                        INSERT INTO ai_decision_logs (
                            id, call_id, decision_category,
                            model_id, model_version, model_provider,
                            input_reference,
                            decision_type, decision_value, confidence_score,
                            risk_level,
                            human_oversight_required, human_review_completed,
                            human_override,
                            action_executed, involves_employee,
                            is_emotion_analysis,
                            created_at, decision_details
                        ) VALUES (
                            :id, :call_id, 'service',
                            'ultravox-agent', '1.0', 'ultravox',
                            :ultravox_call_id,
                            'escalation', :decision_value, 1.0,
                            'high',
                            true, false,
                            NULL,
                            true, false,
                            false,
                            NOW(), CAST(:decision_details AS JSONB)
                        )
                    """),
                    {
                        "id": escalation_id,
                        "call_id": call_id,
                        "ultravox_call_id": ultravox_call_id,
                        "decision_value": f"Transferencia solicitada: {reason}",
                        "decision_details": json.dumps(
                            {
                                "action_type": "transfer",
                                "status": "success",
                                "reason": reason,
                                "priority": priority,
                                "context": context,
                            }
                        ),
                    },
                )
        except SQLAlchemyError as e:
            logger.error("Error saving escalation ai_decision_log: %s", e)

        await db.commit()
        return escalation_id

    @staticmethod
    async def get_customer_context(
        db: AsyncSession,
        phone_number: str,
    ) -> dict[str, Any] | None:
        """Get customer context by phone number.

        Returns a dict with customer info, or None if not found.
        Keys: contact_id, full_name, previous_calls_count, last_call_date, active_consents
        """
        phone_hash = hashlib.sha256(phone_number.encode()).hexdigest()[:32]

        result = await db.execute(
            text("""
                SELECT c.id, c.full_name as full_name,
                       (SELECT COUNT(*) FROM calls WHERE caller_number = :phone_number) as call_count,
                       (SELECT MAX(initiated_at) FROM calls WHERE caller_number = :phone_number) as last_call
                FROM contacts c WHERE c.phone_hash = :phone_hash AND c.deleted_at IS NULL LIMIT 1
            """),
            {"phone_hash": phone_hash, "phone_number": phone_number},
        )
        row = result.fetchone()

        if not row:
            return None

        consent_result = await db.execute(
            text("""
                SELECT DISTINCT consent_type FROM data_consents
                WHERE contact_id = :contact_id AND consent_given = true AND revoked_at IS NULL
            """),
            {"contact_id": row[0]},
        )
        consents = [r[0] for r in consent_result.fetchall()]

        return {
            "contact_id": str(row[0]),
            "full_name": row[1],
            "previous_calls_count": row[2] or 0,
            "last_call_date": row[3].isoformat() if row[3] else None,
            "active_consents": consents,
        }
