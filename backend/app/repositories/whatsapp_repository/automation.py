"""Automation repositories: macros, SLA, webhooks, surveys, flows, integrations, widget."""

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.whatsapp import (
    WAFlow,
    WAIntegration,
    WAMacro,
    WASlaBreach,
    WASlaPolicy,
    WASurvey,
    WASurveyResponse,
    WAWebhookConfig,
    WAWebhookLog,
    WAWidgetConfig,
)
from app.repositories.base import BaseRepository


class WAMacroRepository(BaseRepository[WAMacro]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, WAMacro)

    async def list_by_tenant(
        self,
        tenant_id: UUID,
        category: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[Sequence[WAMacro], int]:
        query = select(WAMacro).where(WAMacro.tenant_id == tenant_id)
        count_query = (
            select(func.count()).select_from(WAMacro).where(WAMacro.tenant_id == tenant_id)
        )
        if category:
            query = query.where(WAMacro.category == category)
            count_query = count_query.where(WAMacro.category == category)
        query = query.order_by(WAMacro.sort_order, WAMacro.name).offset(skip).limit(limit)
        result = await self.session.execute(query)
        total_result = await self.session.execute(count_query)
        return result.scalars().all(), total_result.scalar_one()


class WASlaPolicyRepository(BaseRepository[WASlaPolicy]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, WASlaPolicy)

    async def list_by_tenant(self, tenant_id: UUID) -> Sequence[WASlaPolicy]:
        result = await self.session.execute(
            select(WASlaPolicy)
            .where(WASlaPolicy.tenant_id == tenant_id)
            .order_by(WASlaPolicy.created_at.desc())
        )
        return result.scalars().all()


class WASlaBreachRepository(BaseRepository[WASlaBreach]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, WASlaBreach)

    async def list_by_tenant(
        self,
        tenant_id: UUID,
        policy_id: UUID | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[Sequence[WASlaBreach], int]:
        query = select(WASlaBreach).where(WASlaBreach.tenant_id == tenant_id)
        count_query = (
            select(func.count()).select_from(WASlaBreach).where(WASlaBreach.tenant_id == tenant_id)
        )
        if policy_id:
            query = query.where(WASlaBreach.policy_id == policy_id)
            count_query = count_query.where(WASlaBreach.policy_id == policy_id)
        query = query.order_by(WASlaBreach.breached_at.desc()).offset(skip).limit(limit)
        result = await self.session.execute(query)
        total_result = await self.session.execute(count_query)
        return result.scalars().all(), total_result.scalar_one()

    async def resolve_by_conversation(self, conversation_id: UUID) -> int:
        """Resolve all open SLA breaches for a conversation.

        Sets resolved_at to now for all breaches where resolved_at IS NULL.
        Returns the number of breaches resolved.
        """
        result = await self.session.execute(
            update(WASlaBreach)
            .where(
                WASlaBreach.conversation_id == conversation_id,
                WASlaBreach.resolved_at.is_(None),
            )
            .values(resolved_at=datetime.now(UTC))
        )
        return result.rowcount


class WAWebhookConfigRepository(BaseRepository[WAWebhookConfig]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, WAWebhookConfig)

    async def list_by_tenant(self, tenant_id: UUID) -> Sequence[WAWebhookConfig]:
        result = await self.session.execute(
            select(WAWebhookConfig)
            .where(WAWebhookConfig.tenant_id == tenant_id)
            .order_by(WAWebhookConfig.created_at.desc())
        )
        return result.scalars().all()


class WAWebhookLogRepository(BaseRepository[WAWebhookLog]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, WAWebhookLog)

    async def list_by_webhook(
        self,
        webhook_id: UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[Sequence[WAWebhookLog], int]:
        query = (
            select(WAWebhookLog)
            .where(WAWebhookLog.webhook_id == webhook_id)
            .order_by(WAWebhookLog.sent_at.desc())
            .offset(skip)
            .limit(limit)
        )
        count_query = (
            select(func.count())
            .select_from(WAWebhookLog)
            .where(WAWebhookLog.webhook_id == webhook_id)
        )
        result = await self.session.execute(query)
        total_result = await self.session.execute(count_query)
        return result.scalars().all(), total_result.scalar_one()


class WASurveyRepository(BaseRepository[WASurvey]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, WASurvey)

    async def list_by_tenant(
        self,
        tenant_id: UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[Sequence[WASurvey], int]:
        query = (
            select(WASurvey)
            .where(WASurvey.tenant_id == tenant_id)
            .order_by(WASurvey.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        count_query = (
            select(func.count()).select_from(WASurvey).where(WASurvey.tenant_id == tenant_id)
        )
        result = await self.session.execute(query)
        total_result = await self.session.execute(count_query)
        return result.scalars().all(), total_result.scalar_one()


class WASurveyResponseRepository(BaseRepository[WASurveyResponse]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, WASurveyResponse)

    async def list_by_survey(
        self,
        survey_id: UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[Sequence[WASurveyResponse], int]:
        query = (
            select(WASurveyResponse)
            .where(WASurveyResponse.survey_id == survey_id)
            .order_by(WASurveyResponse.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        count_query = (
            select(func.count())
            .select_from(WASurveyResponse)
            .where(WASurveyResponse.survey_id == survey_id)
        )
        result = await self.session.execute(query)
        total_result = await self.session.execute(count_query)
        return result.scalars().all(), total_result.scalar_one()


class WAFlowRepository(BaseRepository[WAFlow]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, WAFlow)

    async def list_by_tenant(
        self,
        tenant_id: UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[Sequence[WAFlow], int]:
        query = (
            select(WAFlow)
            .where(WAFlow.tenant_id == tenant_id)
            .order_by(WAFlow.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        count_query = select(func.count()).select_from(WAFlow).where(WAFlow.tenant_id == tenant_id)
        result = await self.session.execute(query)
        total_result = await self.session.execute(count_query)
        return result.scalars().all(), total_result.scalar_one()


class WAIntegrationRepository(BaseRepository[WAIntegration]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, WAIntegration)

    async def list_by_tenant(
        self,
        tenant_id: UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[Sequence[WAIntegration], int]:
        query = (
            select(WAIntegration)
            .where(WAIntegration.tenant_id == tenant_id)
            .order_by(WAIntegration.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        count_query = (
            select(func.count())
            .select_from(WAIntegration)
            .where(WAIntegration.tenant_id == tenant_id)
        )
        result = await self.session.execute(query)
        total_result = await self.session.execute(count_query)
        return result.scalars().all(), total_result.scalar_one()


class WAWidgetConfigRepository(BaseRepository[WAWidgetConfig]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, WAWidgetConfig)

    async def get_by_tenant(self, tenant_id: UUID) -> WAWidgetConfig | None:
        result = await self.session.execute(
            select(WAWidgetConfig).where(WAWidgetConfig.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def upsert(self, tenant_id: UUID, data: dict) -> WAWidgetConfig:
        existing = await self.get_by_tenant(tenant_id)
        if existing:
            for k, v in data.items():
                if hasattr(existing, k) and v is not None:
                    setattr(existing, k, v)
            await self.session.flush()
            await self.session.refresh(existing)
            return existing
        return await self.create({"tenant_id": tenant_id, **data})
