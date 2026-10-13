"""Commerce repositories: pipeline, deals, catalog, orders."""

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.whatsapp import (
    WACatalogItem,
    WADeal,
    WAOrder,
    WAPipelineStage,
)
from app.repositories.base import BaseRepository


class WAPipelineStageRepository(BaseRepository[WAPipelineStage]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, WAPipelineStage)

    async def list_by_tenant(self, tenant_id: UUID) -> Sequence[WAPipelineStage]:
        result = await self.session.execute(
            select(WAPipelineStage)
            .where(WAPipelineStage.tenant_id == tenant_id)
            .order_by(WAPipelineStage.sort_order)
        )
        return result.scalars().all()

    async def seed_default_stages(self, tenant_id: UUID) -> None:
        """Create default pipeline stages if none exist."""
        existing = await self.list_by_tenant(tenant_id)
        if existing:
            return
        defaults = [
            {"name": "Nuevo Lead", "color": "#6B7280", "sort_order": 0, "is_default": True},
            {"name": "Contactado", "color": "#3B82F6", "sort_order": 1},
            {"name": "Interesado", "color": "#8B5CF6", "sort_order": 2},
            {"name": "Propuesta", "color": "#F59E0B", "sort_order": 3},
            {"name": "Ganado", "color": "#10B981", "sort_order": 4, "is_won": True},
            {"name": "Perdido", "color": "#EF4444", "sort_order": 5, "is_lost": True},
        ]
        for stage_data in defaults:
            await self.create({"tenant_id": tenant_id, **stage_data})


class WADealRepository(BaseRepository[WADeal]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, WADeal)

    async def list_by_tenant(
        self,
        tenant_id: UUID,
        stage_id: UUID | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[Sequence[WADeal], int]:
        query = (
            select(WADeal)
            .options(joinedload(WADeal.stage), joinedload(WADeal.contact))
            .where(WADeal.tenant_id == tenant_id)
        )
        count_query = select(func.count()).select_from(WADeal).where(WADeal.tenant_id == tenant_id)
        if stage_id:
            query = query.where(WADeal.stage_id == stage_id)
            count_query = count_query.where(WADeal.stage_id == stage_id)

        query = query.order_by(WADeal.updated_at.desc()).offset(skip).limit(limit)
        result = await self.session.execute(query)
        items = result.unique().scalars().all()
        total_result = await self.session.execute(count_query)
        total = total_result.scalar_one()
        return items, total

    async def get_with_relations(self, deal_id: UUID) -> WADeal | None:
        result = await self.session.execute(
            select(WADeal)
            .options(joinedload(WADeal.stage), joinedload(WADeal.contact))
            .where(WADeal.id == deal_id)
        )
        return result.unique().scalar_one_or_none()

    async def get_analytics(self, tenant_id: UUID) -> dict:
        """Get pipeline analytics: totals per stage, won/lost counts."""
        stages_repo = WAPipelineStageRepository(self.session)
        stages = await stages_repo.list_by_tenant(tenant_id)

        total_deals = 0
        total_value = 0
        won_deals = 0
        won_value = 0
        lost_deals = 0
        stage_stats = []

        for stage in stages:
            count_result = await self.session.execute(
                select(func.count(), func.coalesce(func.sum(WADeal.value), 0))
                .select_from(WADeal)
                .where(and_(WADeal.tenant_id == tenant_id, WADeal.stage_id == stage.id))
            )
            row = count_result.fetchone()
            deal_count = row[0]
            deal_value = row[1]
            total_deals += deal_count
            total_value += deal_value
            if stage.is_won:
                won_deals += deal_count
                won_value += deal_value
            if stage.is_lost:
                lost_deals += deal_count

            stage_stats.append(
                {
                    "id": stage.id,
                    "name": stage.name,
                    "color": stage.color,
                    "sort_order": stage.sort_order,
                    "is_default": stage.is_default,
                    "is_won": stage.is_won,
                    "is_lost": stage.is_lost,
                    "deal_count": deal_count,
                    "deal_value": deal_value,
                }
            )

        conversion_rate = (won_deals / total_deals * 100) if total_deals > 0 else 0
        return {
            "total_deals": total_deals,
            "total_value": total_value,
            "won_deals": won_deals,
            "won_value": won_value,
            "lost_deals": lost_deals,
            "conversion_rate": round(conversion_rate, 1),
            "stages": stage_stats,
        }


class WACatalogItemRepository(BaseRepository[WACatalogItem]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, WACatalogItem)

    async def list_by_tenant(
        self,
        tenant_id: UUID,
        status: str | None = None,
        category: str | None = None,
        search: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[Sequence[WACatalogItem], int]:
        query = select(WACatalogItem).where(WACatalogItem.tenant_id == tenant_id)
        count_query = (
            select(func.count())
            .select_from(WACatalogItem)
            .where(WACatalogItem.tenant_id == tenant_id)
        )
        if status:
            query = query.where(WACatalogItem.status == status)
            count_query = count_query.where(WACatalogItem.status == status)
        if category:
            query = query.where(WACatalogItem.category == category)
            count_query = count_query.where(WACatalogItem.category == category)
        if search:
            pattern = f"%{search}%"
            filt = or_(
                WACatalogItem.name.ilike(pattern),
                WACatalogItem.sku.ilike(pattern),
            )
            query = query.where(filt)
            count_query = count_query.where(filt)

        query = query.order_by(WACatalogItem.name).offset(skip).limit(limit)
        result = await self.session.execute(query)
        items = result.scalars().all()
        total_result = await self.session.execute(count_query)
        total = total_result.scalar_one()
        return items, total


class WAOrderRepository(BaseRepository[WAOrder]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, WAOrder)

    async def list_by_tenant(
        self,
        tenant_id: UUID,
        status: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[Sequence[WAOrder], int]:
        query = (
            select(WAOrder)
            .options(joinedload(WAOrder.items), joinedload(WAOrder.contact))
            .where(WAOrder.tenant_id == tenant_id)
        )
        count_query = (
            select(func.count()).select_from(WAOrder).where(WAOrder.tenant_id == tenant_id)
        )
        if status:
            query = query.where(WAOrder.status == status)
            count_query = count_query.where(WAOrder.status == status)

        query = query.order_by(WAOrder.created_at.desc()).offset(skip).limit(limit)
        result = await self.session.execute(query)
        items = result.unique().scalars().all()
        total_result = await self.session.execute(count_query)
        total = total_result.scalar_one()
        return items, total

    async def get_with_items(self, order_id: UUID) -> WAOrder | None:
        result = await self.session.execute(
            select(WAOrder)
            .options(joinedload(WAOrder.items), joinedload(WAOrder.contact))
            .where(WAOrder.id == order_id)
        )
        return result.unique().scalar_one_or_none()
