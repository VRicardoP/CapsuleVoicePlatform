"""
Robinson List repository - LOPDGDD Art. 34 / Orden ETD/1286/2022.
Handles Robinson list check tracking and campaign management.
"""

import hashlib
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.robinson import Campaign, RobinsonCheck
from app.repositories.base import BaseRepository


class RobinsonCheckRepository(BaseRepository[RobinsonCheck]):
    """
    Robinson list check repository.

    Orden ETD/1286/2022:
    - Art. 4.1: MUST check before commercial communications
    - Art. 4.2: Check valid for MAX 30 days
    - Art. 6: MUST document all checks
    """

    def __init__(self, session: AsyncSession):
        super().__init__(session, RobinsonCheck)

    @staticmethod
    def hash_phone_number(phone: str) -> str:
        """Hash phone number for lookup."""
        normalized = "".join(c for c in phone if c.isdigit())
        return hashlib.sha256(normalized.encode()).hexdigest()

    async def get_valid_check(
        self,
        phone_number: str,
    ) -> RobinsonCheck | None:
        """
        Get a valid (non-expired) check for a phone number.
        Orden ETD/1286/2022 Art. 4.2: Valid for max 30 days.
        """
        phone_hash = self.hash_phone_number(phone_number)
        now = datetime.now(UTC)

        result = await self.session.execute(
            select(RobinsonCheck)
            .where(RobinsonCheck.phone_number_hash == phone_hash)
            .where(RobinsonCheck.valid_until > now)
            .order_by(RobinsonCheck.check_timestamp.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def is_listed(self, phone_number: str) -> bool | None:
        """
        Check if a phone number is on the Robinson list.
        Returns None if no valid check exists.
        """
        check = await self.get_valid_check(phone_number)
        if check:
            return check.is_listed
        return None

    async def record_check(
        self,
        phone_number: str,
        is_listed: bool,
        check_type: str = "phone",
        contact_id: UUID | None = None,
        campaign_id: UUID | None = None,
        purpose: str | None = None,
        checked_by_user_id: UUID | None = None,
        checked_by_system: str | None = None,
        api_request_id: str | None = None,
        api_response_time_ms: int | None = None,
        result_code: str | None = None,
    ) -> RobinsonCheck:
        """
        Record a Robinson list check.
        Orden ETD/1286/2022 Art. 6: Must document all checks.
        """
        now = datetime.now(UTC)
        phone_hash = self.hash_phone_number(phone_number)

        return await self.create(
            {
                "phone_number_hash": phone_hash,
                "check_type": check_type,
                "check_timestamp": now,
                "is_listed": is_listed,
                "result_code": result_code,
                "valid_until": now + timedelta(days=30),  # Art. 4.2: max 30 days
                "contact_id": contact_id,
                "campaign_id": campaign_id,
                "purpose": purpose,
                "checked_by_user_id": checked_by_user_id,
                "checked_by_system": checked_by_system,
                "api_request_id": api_request_id,
                "api_response_time_ms": api_response_time_ms,
            }
        )

    async def can_contact(
        self,
        phone_number: str,
        require_fresh_check: bool = False,
    ) -> tuple[bool, str]:
        """
        Check if a phone number can be contacted for commercial purposes.

        Returns:
            (can_contact, reason)
        """
        # Get existing check
        check = await self.get_valid_check(phone_number)

        if check is None:
            if require_fresh_check:
                return False, "no_valid_check"
            # No check exists - should perform one
            return False, "check_required"

        if check.is_listed:
            return False, "robinson_listed"

        return True, "not_listed"

    async def get_checks_for_campaign(
        self,
        campaign_id: UUID,
    ) -> Sequence[RobinsonCheck]:
        """Get all Robinson checks for a campaign."""
        result = await self.session.execute(
            select(RobinsonCheck)
            .where(RobinsonCheck.campaign_id == campaign_id)
            .order_by(RobinsonCheck.check_timestamp.desc())
        )
        return result.scalars().all()

    async def get_expiring_checks(
        self,
        days_until_expiry: int = 7,
    ) -> Sequence[RobinsonCheck]:
        """Get checks that will expire soon (for re-verification)."""
        expiry_date = datetime.now(UTC) + timedelta(days=days_until_expiry)

        result = await self.session.execute(
            select(RobinsonCheck)
            .where(RobinsonCheck.valid_until <= expiry_date)
            .where(RobinsonCheck.valid_until > datetime.now(UTC))
            .where(RobinsonCheck.is_listed.is_(False))  # Only non-listed numbers need re-check
            .order_by(RobinsonCheck.valid_until)
        )
        return result.scalars().all()

    async def get_compliance_stats(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict[str, Any]:
        """Get Robinson check compliance statistics."""
        result = await self.session.execute(
            text("""
                SELECT
                    COUNT(*) as total_checks,
                    COUNT(*) FILTER (WHERE is_listed = true) as listed_count,
                    COUNT(*) FILTER (WHERE is_listed = false) as not_listed_count,
                    COUNT(DISTINCT phone_number_hash) as unique_numbers,
                    COUNT(DISTINCT campaign_id) FILTER (WHERE campaign_id IS NOT NULL) as campaigns_checked
                FROM robinson_checks
                WHERE (:start_date IS NULL OR check_timestamp >= :start_date)
                AND (:end_date IS NULL OR check_timestamp <= :end_date)
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


class CampaignRepository(BaseRepository[Campaign]):
    """Repository for marketing campaigns."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, Campaign)

    async def get_active_campaigns(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[Campaign]:
        """Get all active campaigns."""
        result = await self.session.execute(
            select(Campaign)
            .where(Campaign.status == "active")
            .order_by(Campaign.start_date.desc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_campaigns_needing_robinson_check(self) -> Sequence[Campaign]:
        """Get campaigns that need Robinson list verification."""
        result = await self.session.execute(
            select(Campaign)
            .where(Campaign.status.in_(("draft", "scheduled", "active")))
            .where(Campaign.robinson_check_required.is_(True))
            .where(
                Campaign.robinson_last_batch_check.is_(None)
                | (
                    Campaign.robinson_last_batch_check
                    < datetime.now(UTC) - timedelta(days=30)
                )
            )
        )
        return result.scalars().all()

    async def update_robinson_check_timestamp(
        self,
        campaign_id: UUID,
        excluded_count: int = 0,
    ) -> Campaign | None:
        """Update Robinson check timestamp and exclusion count."""
        campaign = await self.get_by_id(campaign_id)
        if not campaign:
            return None

        await self.session.execute(
            update(Campaign)
            .where(Campaign.id == campaign_id)
            .values(
                robinson_last_batch_check=datetime.now(UTC),
                robinson_excluded=campaign.robinson_excluded + excluded_count,
            )
        )

        await self.session.refresh(campaign)
        return campaign

    async def get_campaign_stats(
        self,
        campaign_id: UUID,
    ) -> dict[str, Any]:
        """Get detailed campaign statistics."""
        result = await self.session.execute(
            text("""
                SELECT
                    c.id,
                    c.name,
                    c.status,
                    c.total_contacts,
                    c.robinson_excluded,
                    c.calls_made,
                    c.calls_connected,
                    CASE WHEN c.calls_made > 0
                         THEN ROUND(c.calls_connected::numeric / c.calls_made * 100, 2)
                         ELSE 0
                    END as connection_rate,
                    c.robinson_last_batch_check,
                    (SELECT COUNT(*) FROM robinson_checks rc WHERE rc.campaign_id = c.id) as robinson_checks_total
                FROM campaigns c
                WHERE c.id = :campaign_id
            """),
            {"campaign_id": str(campaign_id)},
        )
        row = result.fetchone()
        if row:
            return dict(row._mapping)
        return {}
