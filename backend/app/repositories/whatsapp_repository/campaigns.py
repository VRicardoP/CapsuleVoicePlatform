"""Campaign repositories."""

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.whatsapp import WACampaign, WACampaignRecipient
from app.repositories.base import BaseRepository


class WACampaignRepository(BaseRepository[WACampaign]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, WACampaign)

    async def list_by_tenant(
        self,
        tenant_id: UUID,
        status: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[Sequence[WACampaign], int]:
        query = (
            select(WACampaign)
            .options(joinedload(WACampaign.template), joinedload(WACampaign.catalog_item))
            .where(WACampaign.tenant_id == tenant_id)
        )
        count_query = (
            select(func.count()).select_from(WACampaign).where(WACampaign.tenant_id == tenant_id)
        )
        if status:
            query = query.where(WACampaign.status == status)
            count_query = count_query.where(WACampaign.status == status)

        query = query.order_by(WACampaign.updated_at.desc()).offset(skip).limit(limit)
        result = await self.session.execute(query)
        items = result.unique().scalars().all()
        total_result = await self.session.execute(count_query)
        total = total_result.scalar_one()
        return items, total

    async def get_with_template(self, campaign_id: UUID) -> WACampaign | None:
        result = await self.session.execute(
            select(WACampaign)
            .options(joinedload(WACampaign.template), joinedload(WACampaign.catalog_item))
            .where(WACampaign.id == campaign_id)
        )
        return result.unique().scalar_one_or_none()


class WACampaignRecipientRepository(BaseRepository[WACampaignRecipient]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, WACampaignRecipient)

    async def reset_all_pending(self, campaign_id: UUID) -> int:
        """Reset all recipients of a campaign to pending status (for relaunch)."""
        result = await self.session.execute(
            update(WACampaignRecipient)
            .where(WACampaignRecipient.campaign_id == campaign_id)
            .values(
                status="pending",
                sent_at=None,
                delivered_at=None,
                read_at=None,
                failed_at=None,
                error_detail=None,
            )
        )
        return result.rowcount

    async def list_by_campaign(
        self,
        campaign_id: UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[Sequence[WACampaignRecipient], int]:
        query = (
            select(WACampaignRecipient)
            .options(joinedload(WACampaignRecipient.contact))
            .where(WACampaignRecipient.campaign_id == campaign_id)
            .order_by(WACampaignRecipient.status)
            .offset(skip)
            .limit(limit)
        )
        count_query = (
            select(func.count())
            .select_from(WACampaignRecipient)
            .where(WACampaignRecipient.campaign_id == campaign_id)
        )
        result = await self.session.execute(query)
        items = result.unique().scalars().all()
        total_result = await self.session.execute(count_query)
        total = total_result.scalar_one()
        return items, total
