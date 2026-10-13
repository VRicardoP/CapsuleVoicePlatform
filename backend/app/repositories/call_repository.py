"""
Call repository - Data access for calls.
Handles call lifecycle with AI Act and RGPD compliance.
"""

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.call import Call, CallTrafficData
from app.models.transcription import Transcription
from app.repositories.base import BaseRepository


class CallRepository(BaseRepository[Call]):
    """
    Call repository with compliance tracking.

    AI Act compliance:
    - Art. 50.1: ai_disclosure_timestamp tracking
    - Art. 50.3: emotion_detection_disclosed
    - Art. 14: human_oversight tracking
    """

    def __init__(self, session: AsyncSession):
        super().__init__(session, Call)

    async def create_call(
        self,
        direction: str,
        caller_number: str | None = None,
        called_number: str | None = None,
        external_call_id: str | None = None,
        contact_id: UUID | None = None,
        agent_id: UUID | None = None,
        **kwargs: Any,
    ) -> Call:
        """
        Create a new call record.
        Also creates the required traffic data record for LGT compliance.
        """
        call_data = {
            "direction": direction,
            "caller_number": caller_number,
            "called_number": called_number,
            "external_call_id": external_call_id,
            "contact_id": contact_id,
            "agent_id": agent_id,
            "status": "initiated",
            "initiated_at": datetime.now(UTC),
            **kwargs,
        }
        call = await self.create(call_data)

        # Create traffic data record (LGT Art. 68)
        traffic_data = CallTrafficData(
            call_id=call.id,
            caller_cli=caller_number,
            called_number=called_number,
            call_start=call.initiated_at,
            legal_hold_until=call.initiated_at + timedelta(days=365),  # 12 months
        )
        self.session.add(traffic_data)
        await self.session.flush()

        return call

    async def update_status(
        self,
        call_id: UUID,
        status: str,
        **kwargs: Any,
    ) -> Call | None:
        """Update call status with timestamp tracking."""
        update_data = {"status": status}

        if status == "answered":
            update_data["answered_at"] = datetime.now(UTC)
        elif status in ("completed", "abandoned", "failed"):
            update_data["ended_at"] = datetime.now(UTC)

        update_data.update(kwargs)
        return await self.update(call_id, update_data)

    async def record_ai_disclosure(
        self,
        call_id: UUID,
        method: str = "ivr_message",
    ) -> Call | None:
        """
        Record AI disclosure (AI Act Art. 50.1).
        MUST be called BEFORE conversation starts.
        """
        return await self.update(
            call_id,
            {
                "ai_disclosure_timestamp": datetime.now(UTC),
                "ai_disclosure_method": method,
            },
        )

    async def record_emotion_disclosure(
        self,
        call_id: UUID,
    ) -> Call | None:
        """
        Record emotion detection disclosure (AI Act Art. 50.3).
        Required if sentiment analysis is used.
        """
        return await self.update(
            call_id,
            {"emotion_detection_disclosed": True},
        )

    async def record_recording_consent(
        self,
        call_id: UUID,
        consent: bool,
    ) -> Call | None:
        """Record recording consent (RGPD Art. 7)."""
        return await self.update(
            call_id,
            {
                "recording_consent": consent,
                "recording_consent_timestamp": datetime.now(UTC),
                "is_recorded": consent,
            },
        )

    async def update_sentiment(
        self,
        call_id: UUID,
        sentiment: str,
        score: float | None = None,
    ) -> Call | None:
        """Update call sentiment (requires consent check)."""
        # Verify emotion detection was disclosed
        call = await self.get_by_id(call_id)
        if not call:
            return None

        if not call.emotion_detection_disclosed:
            raise ValueError("AI Act Art. 50.3: emotion_detection_disclosed must be true")

        return await self.update(
            call_id,
            {
                "sentiment": sentiment,
                "sentiment_score": score,
            },
        )

    async def get_calls_by_contact(
        self,
        contact_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[Sequence[Call], int]:
        """Get paginated calls for a contact. Returns (items, total)."""
        base_filter = and_(Call.contact_id == contact_id, Call.deleted_at.is_(None))
        count_result = await self.session.execute(
            select(func.count()).select_from(Call).where(base_filter)
        )
        total = count_result.scalar_one()
        result = await self.session.execute(
            select(Call)
            .where(base_filter)
            .order_by(Call.initiated_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all(), total

    async def get_calls_by_agent(
        self,
        agent_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[Sequence[Call], int]:
        """Get paginated calls for an agent. Returns (items, total)."""
        base_filter = and_(Call.agent_id == agent_id, Call.deleted_at.is_(None))
        count_result = await self.session.execute(
            select(func.count()).select_from(Call).where(base_filter)
        )
        total = count_result.scalar_one()
        result = await self.session.execute(
            select(Call)
            .where(base_filter)
            .order_by(Call.initiated_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all(), total

    async def get_active_calls(self) -> Sequence[Call]:
        """Get all currently active calls."""
        active_statuses = ("initiated", "ringing", "answered", "on_hold")
        result = await self.session.execute(
            select(Call)
            .where(Call.status.in_(active_statuses))
            .where(Call.deleted_at.is_(None))
            .order_by(Call.initiated_at.desc())
        )
        return result.scalars().all()

    async def get_calls_requiring_human_review(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[Call]:
        """Get calls flagged for human oversight (AI Act Art. 14)."""
        result = await self.session.execute(
            select(Call)
            .where(Call.human_oversight_required.is_(True))
            .where(Call.human_override.is_(None))
            .where(Call.deleted_at.is_(None))
            .order_by(Call.initiated_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_calls_without_ai_disclosure(
        self,
        since: datetime | None = None,
    ) -> Sequence[Call]:
        """
        Get calls without AI disclosure (compliance violation check).
        AI Act Art. 50.1 requires disclosure BEFORE interaction.
        """
        query = select(Call).where(
            and_(
                Call.ai_disclosure_timestamp.is_(None),
                Call.status.in_(("answered", "completed")),
                Call.deleted_at.is_(None),
            )
        )
        if since:
            query = query.where(Call.initiated_at >= since)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_dashboard_stats(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict[str, Any]:
        """Get call statistics for dashboard."""
        result = await self.session.execute(
            text("""
                SELECT * FROM get_dashboard_metrics(:start_date, :end_date)
            """),
            {
                "start_date": start_date,
                "end_date": end_date,
            },
        )
        row = result.fetchone()
        if row:
            return dict(row._mapping)
        return {}

    async def list_filtered(
        self,
        direction: str | None = None,
        call_status: str | None = None,
        contact_id=None,
        agent_id=None,
        start_date=None,
        end_date=None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list, int]:
        """List calls with optional filters. Returns (items, total_count)."""
        filters = [Call.deleted_at.is_(None)]
        if direction:
            filters.append(Call.direction == direction)
        if call_status:
            filters.append(Call.status == call_status)
        if contact_id:
            filters.append(Call.contact_id == contact_id)
        if agent_id:
            filters.append(Call.agent_id == agent_id)
        if start_date:
            filters.append(Call.initiated_at >= start_date)
        if end_date:
            filters.append(Call.initiated_at <= end_date)

        query = select(Call)
        for f in filters:
            query = query.where(f)
        query = query.order_by(Call.initiated_at.desc()).offset(skip).limit(limit)

        result = await self.session.execute(query)
        items = list(result.scalars().all())
        total = await self.count(filters=filters)
        return items, total

    async def get_caller_by_external_id(self, external_call_id: str) -> str | None:
        """Get caller_number by external_call_id. Returns None if not found."""
        result = await self.session.execute(
            text(
                "SELECT caller_number FROM calls "
                "WHERE external_call_id = :ext_id AND deleted_at IS NULL "
                "ORDER BY initiated_at DESC LIMIT 1"
            ),
            {"ext_id": external_call_id},
        )
        row = result.fetchone()
        return row.caller_number if row else None

    async def get_recording_info(self, call_id) -> dict | None:
        """Get recording file path and metadata for a call."""
        result = await self.session.execute(
            text(
                "SELECT recording_file_path, is_recorded, initiated_at "
                "FROM calls WHERE id = :call_id AND deleted_at IS NULL"
            ),
            {"call_id": str(call_id)},
        )
        row = result.fetchone()
        if not row or not row.recording_file_path or not row.is_recorded:
            return None
        return {
            "recording_file_path": row.recording_file_path,
            "is_recorded": row.is_recorded,
            "initiated_at": row.initiated_at,
        }


class TranscriptionRepository(BaseRepository[Transcription]):
    """Repository for call transcriptions."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, Transcription)

    async def get_by_call(
        self,
        call_id: UUID,
        skip: int = 0,
        limit: int = 1000,
    ) -> Sequence[Transcription]:
        """Get all transcription segments for a call."""
        result = await self.session.execute(
            select(Transcription)
            .where(Transcription.call_id == call_id)
            .order_by(Transcription.segment_index)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def create_segment(
        self,
        call_id: UUID,
        segment_index: int,
        text: str,
        speaker_type: str,
        start_time_ms: int,
        end_time_ms: int,
        model_version: str | None = None,
        **kwargs: Any,
    ) -> Transcription:
        """Create a transcription segment."""
        return await self.create(
            {
                "call_id": call_id,
                "segment_index": segment_index,
                "text": text,
                "speaker_type": speaker_type,
                "start_time_ms": start_time_ms,
                "end_time_ms": end_time_ms,
                "model_version": model_version,
                "is_ai_generated": True,
                **kwargs,
            }
        )

    async def create_batch(
        self,
        call_id: UUID,
        segments: list[dict[str, Any]],
    ) -> list[Transcription]:
        """Create multiple transcription segments in batch."""
        objects = []
        for i, segment in enumerate(segments):
            segment["call_id"] = call_id
            if "segment_index" not in segment:
                segment["segment_index"] = i
            segment["is_ai_generated"] = True
            objects.append(self.model(**segment))
        self.session.add_all(objects)
        await self.session.flush()
        return objects

    async def get_full_transcript(self, call_id: UUID) -> str:
        """Get full transcript text for a call."""
        segments = await self.get_by_call(call_id)
        return "\n".join(f"[{s.speaker_type}]: {s.text}" for s in segments)

    async def get_segments_with_sensitive_data(
        self,
        call_id: UUID,
    ) -> Sequence[Transcription]:
        """Get segments flagged as containing sensitive data."""
        result = await self.session.execute(
            select(Transcription)
            .where(Transcription.call_id == call_id)
            .where(Transcription.contains_sensitive_data.is_(True))
            .order_by(Transcription.segment_index)
        )
        return result.scalars().all()

    async def update_traffic_data_duration(self, call_id: UUID, duration: int | None) -> None:
        """Update call traffic data with duration and destruction date."""
        await self.session.execute(
            text("""
                UPDATE call_traffic_data
                SET
                    call_duration_seconds = :duration,
                    scheduled_destruction_date = legal_hold_until
                WHERE call_id = :call_id
            """),
            {"call_id": str(call_id), "duration": duration},
        )


# Import timedelta for use in create_call
