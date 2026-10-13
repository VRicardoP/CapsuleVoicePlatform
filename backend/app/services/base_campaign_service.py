"""Base class for campaign orchestration services.

Shared infrastructure for WhatsApp, Outbound, and Newsletter campaign
services: active campaign tracking, start/pause/cancel lifecycle, and
session maker management.
"""

import logging
from abc import ABC, abstractmethod
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = logging.getLogger(__name__)


class BaseCampaignService(ABC):
    """Base campaign orchestrator with shared lifecycle management."""

    def __init__(self, session_maker: async_sessionmaker[AsyncSession]) -> None:
        self._session_maker = session_maker
        self._active_campaigns: dict[UUID, bool] = {}

    def is_active(self, campaign_id: UUID) -> bool:
        """Check if a campaign is active and should continue processing."""
        return self._active_campaigns.get(campaign_id, False)

    async def start_campaign(self, campaign_id: UUID) -> None:
        """Start a campaign. Delegates to _run_campaign for implementation."""
        if campaign_id in self._active_campaigns:
            logger.warning("Campaign %s already active, skipping", campaign_id)
            return

        self._active_campaigns[campaign_id] = True
        try:
            await self._run_campaign(campaign_id)
        except Exception:
            logger.error("Campaign %s failed", campaign_id, exc_info=True)
            await self._on_failure(campaign_id)
        finally:
            self._active_campaigns.pop(campaign_id, None)

    def pause_campaign(self, campaign_id: UUID) -> None:
        """Signal a running campaign to pause after current item."""
        if campaign_id in self._active_campaigns:
            self._active_campaigns[campaign_id] = False

    def cancel_campaign(self, campaign_id: UUID) -> None:
        """Signal a running campaign to stop."""
        if campaign_id in self._active_campaigns:
            self._active_campaigns[campaign_id] = False

    @abstractmethod
    async def _run_campaign(self, campaign_id: UUID) -> None:
        """Implement the actual sending/dispatching loop."""

    @abstractmethod
    async def _on_failure(self, campaign_id: UUID) -> None:
        """Handle campaign-level failure (e.g. set status to cancelled)."""
