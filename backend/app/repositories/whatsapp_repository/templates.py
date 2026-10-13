"""Template repository."""

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.whatsapp import WATemplate
from app.repositories.base import BaseRepository


class WATemplateRepository(BaseRepository[WATemplate]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, WATemplate)

    async def list_by_tenant(
        self,
        tenant_id: UUID,
        status: str | None = None,
        category: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[Sequence[WATemplate], int]:
        query = select(WATemplate).where(WATemplate.tenant_id == tenant_id)
        count_query = (
            select(func.count()).select_from(WATemplate).where(WATemplate.tenant_id == tenant_id)
        )
        if status:
            query = query.where(WATemplate.status == status)
            count_query = count_query.where(WATemplate.status == status)
        if category:
            query = query.where(WATemplate.category == category)
            count_query = count_query.where(WATemplate.category == category)

        query = query.order_by(WATemplate.updated_at.desc()).offset(skip).limit(limit)
        result = await self.session.execute(query)
        items = result.scalars().all()
        total_result = await self.session.execute(count_query)
        total = total_result.scalar_one()
        return items, total

    async def get_by_meta_id(
        self,
        tenant_id: UUID,
        meta_template_id: str,
    ) -> WATemplate | None:
        result = await self.session.execute(
            select(WATemplate).where(
                WATemplate.tenant_id == tenant_id,
                WATemplate.meta_template_id == meta_template_id,
            )
        )
        return result.scalars().first()

    async def get_by_name_lang(
        self,
        tenant_id: UUID,
        name: str,
        language: str,
    ) -> WATemplate | None:
        result = await self.session.execute(
            select(WATemplate).where(
                WATemplate.tenant_id == tenant_id,
                WATemplate.name == name,
                WATemplate.language == language,
            )
        )
        return result.scalars().first()

    async def delete_stale_synced(self, tenant_id: UUID, active_meta_ids: set[str]) -> int:
        """Elimina plantillas locales cuyo meta_template_id ya no existe en Meta.

        Solo afecta a plantillas con meta_template_id (sincronizadas previamente).
        Las plantillas draft sin meta_template_id no se tocan.
        """
        result = await self.session.execute(
            delete(WATemplate)
            .where(
                WATemplate.tenant_id == tenant_id,
                WATemplate.meta_template_id.isnot(None),
                WATemplate.meta_template_id.not_in(active_meta_ids)
                if active_meta_ids
                else WATemplate.meta_template_id.isnot(None),
            )
            .returning(WATemplate.id)
        )
        return len(result.all())
