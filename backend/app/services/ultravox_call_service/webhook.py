"""Ultravox webhook processing mixin."""

import hashlib
import hmac
import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import httpx
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings as app_settings
from app.voice.handlers import parse_ultravox_webhook

from .recording import UltravoxRecordingMixin
from .zadarma import UltravoxZadarmaMixin

logger = logging.getLogger(__name__)

WEBHOOK_FORWARD_URL = app_settings.ultravox_webhook_forward_url or None
WEBHOOK_SECRET = app_settings.ultravox_webhook_secret or None
ULTRAVOX_API_KEY = app_settings.ultravox_api_key or None


class UltravoxWebhookMixin:
    """Core webhook processing methods."""

    @staticmethod
    def validate_signature(
        payload: bytes,
        signature: str,
        timestamp: str,
        secret: str,
    ) -> bool:
        """Validate Ultravox webhook signature using HMAC-SHA256."""
        if not secret or not signature or not timestamp:
            return False

        message = f"{timestamp}.{payload.decode('utf-8')}"
        expected = hmac.new(
            secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(expected, signature)

    @staticmethod
    def map_disconnection_to_status(end_reason: str | None) -> str:
        """Map Ultravox end_reason to CapsuleCorp call status.

        Valid status values: initiated, ringing, answered, on_hold,
        transferred, completed, abandoned, voicemail, failed
        """
        mapping = {
            # Ultravox actual values
            "hangup": "completed",
            "unjoined": "abandoned",
            "timeout": "abandoned",
            "error": "failed",
            # Legacy/alternative values
            "user_hangup": "completed",
            "agent_hangup": "completed",
            "call_transfer": "transferred",
            "voicemail_reached": "voicemail",
            "inactivity": "voicemail",
            "max_duration_reached": "completed",
            "dial_failed": "failed",
            "call_failed": "failed",
            "client_disconnected": "completed",
        }
        return mapping.get(end_reason or "", "completed")

    @staticmethod
    def map_sentiment(sentiment: str | None) -> str | None:
        """Map Ultravox sentiment to CapsuleCorp format."""
        if not sentiment:
            return None
        sentiment_lower = sentiment.lower()
        if sentiment_lower in ("positive", "neutral", "negative"):
            return sentiment_lower
        return "neutral"

    @staticmethod
    def extract_phone_from_medium(medium: Any) -> str | None:
        """Extract phone number from Ultravox medium object.

        Medium can be:
        - {"sip": {"incoming": {"from": "+34612345678", "to": "+34911234567"}}}
        - {"telnyx": {"from": "+34612345678", "to": "+34911234567"}}
        - {"twilio": {"from": "+34612345678", "to": "+34911234567"}}
        """
        if not medium or not isinstance(medium, dict):
            return None

        # Try SIP incoming
        if "sip" in medium:
            sip = medium["sip"]
            if isinstance(sip, dict):
                incoming = sip.get("incoming", {})
                if isinstance(incoming, dict):
                    return incoming.get("from") or incoming.get("callerNumber")

        # Try Telnyx
        if "telnyx" in medium:
            telnyx = medium["telnyx"]
            if isinstance(telnyx, dict):
                return telnyx.get("from") or telnyx.get("callerNumber")

        # Try Twilio
        if "twilio" in medium:
            twilio = medium["twilio"]
            if isinstance(twilio, dict):
                return twilio.get("from") or twilio.get("callerNumber")

        return None

    @staticmethod
    def resolve_ultravox_call_id(
        header_call_id: str | None,
        payload: dict[str, Any],
    ) -> str:
        """Resolve Ultravox call ID from header, payload, or generate one."""
        if header_call_id:
            return header_call_id
        if isinstance(payload.get("call"), dict):
            cid = payload["call"].get("call_id")
            if cid:
                return cid
        if payload.get("call_id"):
            return payload["call_id"]
        return f"ultravox_{uuid4().hex[:12]}"

    @staticmethod
    def get_function_arg(payload: dict[str, Any], key: str, default: Any = None) -> Any:
        """Extract a function argument from Ultravox payload (supports args wrapper and flat format)."""
        if "args" in payload and isinstance(payload["args"], dict):
            return payload["args"].get(key, default)
        return payload.get(key, default)

    # -----------------------------------------------------------------------
    # Call status updates (moved from endpoint inline SQL)
    # -----------------------------------------------------------------------

    @staticmethod
    async def update_call_phone_numbers(
        db: AsyncSession,
        call_id: UUID,
        caller_number: str | None,
        called_number: str | None,
    ) -> None:
        """Update caller/called numbers on a call if currently NULL."""
        if not caller_number and not called_number:
            return
        await db.execute(
            text("""
                UPDATE calls SET
                    caller_number = COALESCE(:caller_number, caller_number),
                    called_number = COALESCE(:called_number, called_number),
                    updated_at = NOW()
                WHERE id = :call_id
                AND (caller_number IS NULL OR called_number IS NULL)
            """),
            {
                "call_id": call_id,
                "caller_number": caller_number,
                "called_number": called_number,
            },
        )

    @staticmethod
    async def mark_call_started(db: AsyncSession, call_id: UUID) -> None:
        """Mark a call as answered with answered_at timestamp (call.started event)."""
        await db.execute(
            text(
                "UPDATE calls SET status = 'answered', answered_at = NOW(), updated_at = NOW() WHERE id = :call_id"
            ),
            {"call_id": call_id},
        )

    @staticmethod
    async def mark_call_joined(db: AsyncSession, call_id: UUID) -> None:
        """Mark a call as answered (call.joined event)."""
        await db.execute(
            text("UPDATE calls SET status = 'answered', updated_at = NOW() WHERE id = :call_id"),
            {"call_id": call_id},
        )

    @staticmethod
    async def update_call_billed(
        db: AsyncSession,
        call_id: UUID,
        sentiment: str | None,
        summary: str | None,
    ) -> None:
        """Update call with billing analysis data (call.billed event)."""
        await db.execute(
            text(
                "UPDATE calls SET sentiment = COALESCE(:sentiment, sentiment), ai_summary = :summary, updated_at = NOW() WHERE id = :call_id"
            ),
            {"call_id": call_id, "sentiment": sentiment, "summary": summary},
        )

    # -----------------------------------------------------------------------
    # Ultravox API interactions
    # -----------------------------------------------------------------------

    @staticmethod
    async def get_most_recent_active_call(db: AsyncSession) -> tuple[UUID, str] | None:
        """Get the most recent active call. Returns (call_id, external_call_id) or None."""
        result = await db.execute(
            text("""
                SELECT id, external_call_id FROM calls
                WHERE status IN ('initiated', 'answered')
                AND created_at > NOW() - INTERVAL '1 hour'
                ORDER BY created_at DESC
                LIMIT 1
            """)
        )
        row = result.fetchone()
        return (row[0], row[1]) if row else None

    @staticmethod
    async def get_or_create_call(
        db: AsyncSession,
        ultravox_call_id: str,
        call_data: dict[str, Any],
        use_active_call_if_generated_id: bool = False,
    ) -> UUID | None:
        """Get existing call by Ultravox ID or create a new one.

        If use_active_call_if_generated_id is True and ultravox_call_id starts with 'ultravox_',
        try to find an existing active call first. If none found, return None instead of
        creating a phantom call. The caller should handle None gracefully.
        """
        # If it's a generated ID (from function calls without explicit call_id),
        # try to find an existing active call. Never create phantom calls.
        if use_active_call_if_generated_id and ultravox_call_id.startswith("ultravox_"):
            active_call = await UltravoxWebhookMixin.get_most_recent_active_call(db)
            if active_call:
                logger.debug(
                    "Using existing active call: %s (external: %s)", active_call[0], active_call[1]
                )
                return active_call[0]
            logger.warning(
                "No active call found for generated ID %s — skipping to avoid phantom call",
                ultravox_call_id,
            )
            return None

        # Check if call already exists
        existing_result = await db.execute(
            text("SELECT id FROM calls WHERE external_call_id = :external_id"),
            {"external_id": ultravox_call_id},
        )
        existing_row = existing_result.fetchone()
        if existing_row:
            return existing_row[0]

        call_id = uuid4()
        direction = call_data.get("direction") or "inbound"
        caller_number_value = call_data.get("from_number") or None
        called_number_value = call_data.get("called_number") or call_data.get("to_number") or None

        # Pick a "system user" whose id will be stored as calls.agent_id for
        # this row. Post-permissions-migration the legacy role 'admin' no
        # longer exists in new tenants — the equivalents are 'superadmin' and
        # 'client_admin'. Match any admin-level role, preferring the most
        # privileged one; fall back to any active user so inbound/outbound
        # webhooks never 500 just because nobody has an admin role.
        user_result = await db.execute(
            text("""
                SELECT id FROM users
                WHERE is_active = true
                ORDER BY
                    CASE role
                        WHEN 'superadmin'   THEN 1
                        WHEN 'admin'        THEN 2
                        WHEN 'client_admin' THEN 3
                        WHEN 'user'         THEN 4
                        ELSE 5
                    END
                LIMIT 1
            """)
        )
        user_row = user_result.fetchone()
        system_user_id = user_row[0] if user_row else None

        if not system_user_id:
            raise ValueError("No system user found for Ultravox calls")

        now = datetime.now(UTC)

        result = await db.execute(
            text("""
                INSERT INTO calls (
                    id, external_call_id, direction, caller_number, called_number,
                    status, initiated_at, duration_seconds,
                    agent_id, is_recorded,
                    emotion_detection_disclosed, human_oversight_required,
                    is_employee_call, age_verification_asked,
                    created_at, updated_at
                ) VALUES (
                    :id, :external_id, :direction, :caller_number, :called_number,
                    'initiated', :initiated_at, 0,
                    :agent_id, false,
                    false, false,
                    false, false,
                    NOW(), NOW()
                )
                ON CONFLICT (external_call_id) DO UPDATE SET updated_at = NOW()
                RETURNING id
            """),
            {
                "id": call_id,
                "external_id": ultravox_call_id,
                "direction": direction,
                "caller_number": caller_number_value,
                "called_number": called_number_value,
                "initiated_at": now,
                "agent_id": system_user_id,
            },
        )

        row = result.fetchone()
        return row[0]

    @staticmethod
    async def save_transcript_segments(
        db: AsyncSession,
        call_id: UUID,
        messages: list[dict[str, Any]],
    ) -> int:
        """Save transcript segments from Ultravox messages. Returns count saved."""
        transcript_messages = [
            m for m in messages if m.get("role") in ("MESSAGE_ROLE_AGENT", "MESSAGE_ROLE_USER")
        ]
        if not transcript_messages:
            logger.info("Ultravox: no messages found for transcript")
            return 0

        for idx, msg in enumerate(transcript_messages):
            content = msg.get("text", "").strip()
            if not content:
                continue

            speaker_type = "agent" if msg.get("role") == "MESSAGE_ROLE_AGENT" else "customer"
            start_ms = 0
            end_ms = 0
            timespan = msg.get("timespan", {})
            if timespan:
                try:
                    start_ms = int(float(timespan.get("start", "0s").replace("s", "")) * 1000)
                except ValueError:
                    pass
                try:
                    end_ms = int(float(timespan.get("end", "0s").replace("s", "")) * 1000)
                except ValueError:
                    end_ms = start_ms

            await db.execute(
                text("""
                    INSERT INTO transcriptions (
                        call_id, segment_index, start_time_ms, end_time_ms,
                        speaker_type, text, language, is_ai_generated,
                        is_reviewed, contains_sensitive_data, sensitive_data_redacted
                    ) VALUES (
                        :call_id, :segment_index, :start_ms, :end_ms,
                        :speaker_type, :text, 'es', true,
                        false, false, false
                    )
                """),
                {
                    "call_id": call_id,
                    "segment_index": idx,
                    "start_ms": start_ms,
                    "end_ms": end_ms,
                    "speaker_type": speaker_type,
                    "text": content,
                },
            )

        logger.info("Ultravox: saved %d transcript segments", len(transcript_messages))
        return len(transcript_messages)

    @staticmethod
    async def save_tool_call_actions(
        db: AsyncSession,
        call_id: UUID,
        messages: list[dict[str, Any]],
    ) -> int:
        """Extract tool calls from Ultravox messages and save as ai_decision_logs."""
        from .tool_actions import save_tool_call_actions

        return await save_tool_call_actions(db, call_id, messages)

    # -----------------------------------------------------------------------
    # High-level orchestration
    # -----------------------------------------------------------------------

    @staticmethod
    async def handle_call_ended(
        db: AsyncSession,
        call_id: UUID,
        call_data,
        ultravox_call_id: str,
        caller_number: str | None,
        background_tasks,
    ) -> str | None:
        """Handle call.ended event. Returns updated caller_number."""
        now = datetime.now(UTC)
        duration_seconds = None
        if call_data.duration_ms:
            duration_seconds = call_data.duration_ms // 1000
        elif call_data.created and call_data.ended:
            duration_seconds = int((call_data.ended - call_data.created).total_seconds())

        # Default consent to True (AI Act Art. 50 compliance)
        consent_given = True
        if call_data.call_analysis and call_data.call_analysis.custom_variables:
            explicit_consent = call_data.call_analysis.custom_variables.get("consent_given")
            if explicit_consent is not None:
                consent_given = bool(explicit_consent)

        status_value = UltravoxWebhookMixin.map_disconnection_to_status(call_data.end_reason)
        sentiment = (
            UltravoxWebhookMixin.map_sentiment(call_data.call_analysis.sentiment)
            if call_data.call_analysis
            else None
        )

        # Calls that were never answered have no real conversation duration
        no_conversation = status_value in ("abandoned", "voicemail", "failed")
        if no_conversation:
            duration_seconds = 0

        await db.execute(
            text("""
                UPDATE calls SET
                    status = :status, ended_at = NOW(),
                    duration_seconds = COALESCE(:duration, duration_seconds, 0),
                    answered_at = CASE WHEN :no_conv THEN NULL ELSE answered_at END,
                    sentiment = COALESCE(:sentiment, sentiment),
                    recording_consent = COALESCE(recording_consent, :consent),
                    updated_at = NOW()
                WHERE id = :call_id
            """),
            {
                "call_id": call_id,
                "status": status_value,
                "duration": duration_seconds,
                "sentiment": sentiment,
                "consent": consent_given,
                "no_conv": no_conversation,
            },
        )

        # Determine direction from DB for Zadarma type selection
        dir_result = await db.execute(
            text("SELECT direction FROM calls WHERE id = :call_id"),
            {"call_id": call_id},
        )
        current_direction = dir_result.scalar() or "inbound"

        # Try Zadarma for caller phone number if missing
        if not caller_number:
            logger.debug("Ultravox: no phone number, checking Zadarma cache...")
            zadarma_caller = UltravoxZadarmaMixin.lookup_zadarma_caller(
                called_number=call_data.to_number,
                approximate_start_time=call_data.created,
            )
            if not zadarma_caller and duration_seconds:
                logger.debug("Ultravox: cache miss, trying Zadarma Statistics API...")
                zadarma_caller = await UltravoxZadarmaMixin.fetch_zadarma_caller_number(
                    call_end_time=call_data.ended or now,
                    duration_seconds=duration_seconds,
                    called_number=call_data.to_number,
                    call_type="out" if current_direction == "outbound" else "in",
                )
            if zadarma_caller:
                caller_number = zadarma_caller
                await db.execute(
                    text(
                        "UPDATE calls SET caller_number = :caller_number, updated_at = NOW() WHERE id = :call_id AND caller_number IS NULL"
                    ),
                    {"call_id": call_id, "caller_number": caller_number},
                )
                logger.info(
                    "Ultravox: updated call with Zadarma phone number: %s***", caller_number[:6]
                )

        # Check consent from DB
        consent_result = await db.execute(
            text("SELECT recording_consent FROM calls WHERE id = :call_id"),
            {"call_id": call_id},
        )
        has_consent = consent_result.scalar()

        # Fetch call summary
        api_data = await UltravoxRecordingMixin.fetch_call_details(ultravox_call_id)
        if api_data:
            summary = api_data.get("shortSummary") or api_data.get("summary")
            if summary:
                await db.execute(
                    text(
                        "UPDATE calls SET ai_summary = :summary, updated_at = NOW() WHERE id = :call_id"
                    ),
                    {"call_id": call_id, "summary": summary},
                )
                logger.info("Ultravox: saved call summary")

        # Fetch all messages (transcript + tool calls)
        all_messages = await UltravoxRecordingMixin.fetch_messages(
            ultravox_call_id, include_tool_calls=True
        )

        # Save transcript (consent required)
        # Wrapped in SAVEPOINT so failures don't rollback the status update
        if has_consent:
            logger.info("Ultravox: saving transcript for call %s (consent given)", ultravox_call_id)
            try:
                async with db.begin_nested():
                    await UltravoxWebhookMixin.save_transcript_segments(db, call_id, all_messages)
            except SQLAlchemyError as e:
                logger.error("Ultravox: failed to save transcript (non-fatal): %s", e)
        else:
            logger.info("Ultravox: skipping transcript (no consent)")

        # Save tool call actions (always — operational logs)
        # Wrapped in SAVEPOINT so failures don't rollback the status update
        tool_messages = [
            m
            for m in all_messages
            if m.get("role") in ("MESSAGE_ROLE_TOOL_CALL", "MESSAGE_ROLE_TOOL_RESULT")
        ]
        if tool_messages:
            try:
                async with db.begin_nested():
                    saved_actions = await UltravoxWebhookMixin.save_tool_call_actions(
                        db, call_id, tool_messages
                    )
                    logger.info("Ultravox: saved %d tool call actions", saved_actions)
            except SQLAlchemyError as e:
                logger.error("Ultravox: failed to save tool actions (non-fatal): %s", e)

        # Recording download in background
        if app_settings.recording_enabled and ULTRAVOX_API_KEY:
            background_tasks.add_task(
                UltravoxRecordingMixin.process_recording_background,
                ultravox_call_id=ultravox_call_id,
                db_call_id=str(call_id),
                api_key=ULTRAVOX_API_KEY,
            )

        return caller_number

    @staticmethod
    async def forward_to_n8n(
        payload: dict[str, Any],
        caller_number: str | None,
        call_id: UUID,
        db: AsyncSession,
    ) -> None:
        """Forward normalized webhook event to n8n."""
        if not WEBHOOK_FORWARD_URL:
            return
        try:
            normalized_event = parse_ultravox_webhook(payload)
            if not normalized_event:
                return
            normalized_event.caller_phone = caller_number
            normalized_event.ai_disclosed = True

            call_result = await db.execute(
                text("SELECT sentiment, ai_summary FROM calls WHERE id = :call_id"),
                {"call_id": call_id},
            )
            row = call_result.fetchone()
            if row:
                normalized_event.sentiment = row.sentiment
                normalized_event.summary = row.ai_summary

            from app.core.http_clients import ultravox_client

            await ultravox_client.post(
                WEBHOOK_FORWARD_URL,
                json=normalized_event.to_n8n_payload(),
                headers={"Content-Type": "application/json"},
            )
            logger.debug("Ultravox: forwarded normalized %s to n8n", normalized_event.event)
        except (httpx.HTTPError, SQLAlchemyError, ValueError) as e:
            logger.error("Error forwarding webhook: %s", e)
