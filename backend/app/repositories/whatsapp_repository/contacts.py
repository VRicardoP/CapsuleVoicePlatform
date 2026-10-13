"""Contact-related repositories: segments, tags, internal notes."""

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy import delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.whatsapp import (
    WAContactSegment,
    WAContactTag,
    WAInternalNote,
    WASegment,
    WATag,
)
from app.repositories.base import BaseRepository


class WASegmentRepository(BaseRepository[WASegment]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, WASegment)

    async def list_by_tenant(self, tenant_id: UUID) -> Sequence[WASegment]:
        """List all segments for a tenant with real contact counts."""
        result = await self.session.execute(
            select(WASegment)
            .where(WASegment.tenant_id == tenant_id)
            .order_by(WASegment.sort_order, WASegment.name)
        )
        segments = result.scalars().all()

        counts_result = await self.session.execute(
            select(WAContactSegment.segment_id, func.count())
            .where(WAContactSegment.tenant_id == tenant_id)
            .group_by(WAContactSegment.segment_id)
        )
        count_map = dict(counts_result.all())
        for seg in segments:
            seg.contact_count = count_map.get(seg.id, 0)

        return segments

    async def get_by_slug(self, tenant_id: UUID, slug: str) -> WASegment | None:
        result = await self.session.execute(
            select(WASegment).where(and_(WASegment.tenant_id == tenant_id, WASegment.slug == slug))
        )
        return result.scalar_one_or_none()

    async def refresh_contact_count(self, segment_id: UUID) -> None:
        """Update the cached contact_count for a segment."""
        count_result = await self.session.execute(
            select(func.count())
            .select_from(WAContactSegment)
            .where(WAContactSegment.segment_id == segment_id)
        )
        count = count_result.scalar_one()
        segment = await self.get_by_id(segment_id)
        if segment:
            segment.contact_count = count
            await self.session.flush()

    async def assign_contact(
        self,
        tenant_id: UUID,
        contact_id: UUID,
        segment_ids: list[UUID],
        assigned_by: UUID | None = None,
    ) -> None:
        """Replace all segment assignments for a contact."""
        await self.session.execute(
            sa_delete(WAContactSegment).where(
                and_(
                    WAContactSegment.contact_id == contact_id,
                    WAContactSegment.tenant_id == tenant_id,
                )
            )
        )
        for seg_id in segment_ids:
            self.session.add(
                WAContactSegment(
                    tenant_id=tenant_id,
                    contact_id=contact_id,
                    segment_id=seg_id,
                    assigned_by=assigned_by,
                )
            )
        await self.session.flush()

    async def get_segments_for_contact(self, contact_id: UUID) -> Sequence[WASegment]:
        """Get all segments assigned to a contact."""
        result = await self.session.execute(
            select(WASegment)
            .join(WAContactSegment, WAContactSegment.segment_id == WASegment.id)
            .where(WAContactSegment.contact_id == contact_id)
            .order_by(WASegment.sort_order)
        )
        return result.scalars().all()

    async def get_segments_for_contacts(
        self, contact_ids: list[UUID]
    ) -> dict[UUID, list[WASegment]]:
        """Batch-load segments for multiple contacts in a single query."""
        if not contact_ids:
            return {}
        result = await self.session.execute(
            select(WAContactSegment.contact_id, WASegment)
            .join(WASegment, WAContactSegment.segment_id == WASegment.id)
            .where(WAContactSegment.contact_id.in_(contact_ids))
            .order_by(WASegment.sort_order)
        )
        mapping: dict[UUID, list[WASegment]] = {cid: [] for cid in contact_ids}
        for row in result.all():
            mapping[row.contact_id].append(row.WASegment)
        return mapping

    async def seed_system_segments(self, tenant_id: UUID) -> None:
        """Create system segments for a new tenant if they don't exist."""
        system_segments = [
            {
                "name": "Todos",
                "slug": "todos",
                "icon": "inbox",
                "color": "#6B7280",
                "sort_order": 0,
            },
            {
                "name": "Revisado",
                "slug": "revisado",
                "icon": "check-circle",
                "color": "#10B981",
                "sort_order": 1,
            },
            {
                "name": "Pendiente",
                "slug": "pendiente",
                "icon": "clock",
                "color": "#F59E0B",
                "sort_order": 2,
            },
            {
                "name": "Volver a contactar",
                "slug": "volver-a-contactar",
                "icon": "phone",
                "color": "#8B5CF6",
                "sort_order": 3,
            },
            {
                "name": "Cliente potencial",
                "slug": "cliente-potencial",
                "icon": "star",
                "color": "#3B82F6",
                "sort_order": 4,
            },
            {
                "name": "No interesado",
                "slug": "no-interesado",
                "icon": "x-circle",
                "color": "#EF4444",
                "sort_order": 5,
            },
            {
                "name": "Esperando respuesta",
                "slug": "esperando-respuesta",
                "icon": "message-circle",
                "color": "#EC4899",
                "sort_order": 6,
            },
        ]
        for seg_data in system_segments:
            existing = await self.get_by_slug(tenant_id, seg_data["slug"])
            if not existing:
                await self.create(
                    {
                        "tenant_id": tenant_id,
                        "is_system": True,
                        **seg_data,
                    }
                )


class WATagRepository(BaseRepository[WATag]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, WATag)

    async def list_by_tenant(self, tenant_id: UUID) -> Sequence[WATag]:
        result = await self.session.execute(
            select(WATag).where(WATag.tenant_id == tenant_id).order_by(WATag.name)
        )
        return result.scalars().all()

    async def get_tags_for_contacts(self, contact_ids: list[UUID]) -> dict[UUID, list[WATag]]:
        """Batch-load tags for multiple contacts in a single query."""
        if not contact_ids:
            return {}
        result = await self.session.execute(
            select(WAContactTag.contact_id, WATag)
            .join(WATag, WAContactTag.tag_id == WATag.id)
            .where(WAContactTag.contact_id.in_(contact_ids))
            .order_by(WATag.name)
        )
        mapping: dict[UUID, list[WATag]] = {cid: [] for cid in contact_ids}
        for row in result.all():
            mapping[row.contact_id].append(row.WATag)
        return mapping

    async def get_tags_for_contact(self, contact_id: UUID) -> Sequence[WATag]:
        result = await self.session.execute(
            select(WATag)
            .join(WAContactTag, WAContactTag.tag_id == WATag.id)
            .where(WAContactTag.contact_id == contact_id)
            .order_by(WATag.name)
        )
        return result.scalars().all()

    async def set_contact_tags(self, contact_id: UUID, tag_ids: list[UUID]) -> None:
        """Replace all tag assignments for a contact."""
        await self.session.execute(
            sa_delete(WAContactTag).where(WAContactTag.contact_id == contact_id)
        )
        for tag_id in tag_ids:
            self.session.add(WAContactTag(contact_id=contact_id, tag_id=tag_id))
        await self.session.flush()


class WAInternalNoteRepository(BaseRepository[WAInternalNote]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, WAInternalNote)

    async def list_by_conversation(self, conversation_id: UUID) -> Sequence[WAInternalNote]:
        result = await self.session.execute(
            select(WAInternalNote)
            .where(WAInternalNote.conversation_id == conversation_id)
            .order_by(WAInternalNote.created_at.asc())
        )
        return result.scalars().all()
