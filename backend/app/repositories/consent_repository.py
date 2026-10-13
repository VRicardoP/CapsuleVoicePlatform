"""
Consent repository - Data access for consent management.
RGPD Art. 6, 7 and LOPDGDD Art. 6 compliance.
"""

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.consent import (
    CallProcessingConsent,
    ConsentVersion,
    DataConsent,
)
from app.repositories.base import BaseRepository


class ConsentRepository(BaseRepository[DataConsent]):
    """
    Consent repository with RGPD compliance tracking.

    Uses polymorphic data_subject_id/data_subject_type model.
    Active consent = consent_given=True AND revoked_at IS NULL.

    RGPD Art. 7.1: Must demonstrate consent was given
    RGPD Art. 7.3: Withdrawal must be as easy as giving consent
    """

    def __init__(self, session: AsyncSession):
        super().__init__(session, DataConsent)

    async def get_active_consent(
        self,
        data_subject_id: UUID | None = None,
        data_subject_type: str | None = None,
        purpose_id: UUID | None = None,
        # Legacy compat: accept user_id/contact_id and map to polymorphic
        user_id: UUID | None = None,
        contact_id: UUID | None = None,
        scope: str | None = None,
    ) -> DataConsent | None:
        """Get active consent for a subject and purpose."""
        # Map legacy params to polymorphic
        if user_id and not data_subject_id:
            data_subject_id = user_id
            data_subject_type = "user"
        elif contact_id and not data_subject_id:
            data_subject_id = contact_id
            data_subject_type = "contact"

        query = select(DataConsent).where(
            DataConsent.consent_given.is_(True),
            DataConsent.revoked_at.is_(None),
        )

        if data_subject_id:
            query = query.where(DataConsent.data_subject_id == data_subject_id)
        if data_subject_type:
            query = query.where(DataConsent.data_subject_type == data_subject_type)
        if purpose_id:
            query = query.where(DataConsent.purpose_id == purpose_id)

        # Check not expired
        query = query.where(
            or_(
                DataConsent.expires_at.is_(None),
                DataConsent.expires_at > datetime.now(UTC),
            )
        )

        result = await self.session.execute(query.limit(1))
        return result.scalar_one_or_none()

    async def get_all_consents_for_subject(
        self,
        data_subject_id: UUID | None = None,
        data_subject_type: str | None = None,
        include_revoked: bool = False,
        # Legacy compat
        user_id: UUID | None = None,
        contact_id: UUID | None = None,
    ) -> Sequence[DataConsent]:
        """Get all consents for a data subject."""
        # Map legacy params
        if user_id and not data_subject_id:
            data_subject_id = user_id
            data_subject_type = "user"
        elif contact_id and not data_subject_id:
            data_subject_id = contact_id
            data_subject_type = "contact"

        query = select(DataConsent)

        if data_subject_id:
            query = query.where(DataConsent.data_subject_id == data_subject_id)
        if data_subject_type:
            query = query.where(DataConsent.data_subject_type == data_subject_type)
        if not include_revoked:
            query = query.where(
                DataConsent.consent_given.is_(True),
                DataConsent.revoked_at.is_(None),
            )

        result = await self.session.execute(query.order_by(DataConsent.obtained_at.desc()))
        return result.scalars().all()

    async def grant_consent(
        self,
        data_subject_id: UUID,
        data_subject_type: str,
        purpose_id: UUID,
        consent_version_id: UUID,
        obtained_method: str,
        evidence_type: str | None = None,
        evidence_reference: str | None = None,
        evidence_hash: str | None = None,
        ip_address: str | None = None,
        **kwargs: Any,
    ) -> DataConsent:
        """
        Grant a new consent.

        RGPD Art. 7.1: Stores evidence of consent
        LOPDGDD Art. 6.3: Records consent method and proof
        """
        return await self.create(
            {
                "data_subject_id": data_subject_id,
                "data_subject_type": data_subject_type,
                "purpose_id": purpose_id,
                "consent_version_id": consent_version_id,
                "consent_given": True,
                "obtained_at": datetime.now(UTC),
                "obtained_method": obtained_method,
                "evidence_type": evidence_type,
                "evidence_reference": evidence_reference,
                "evidence_hash": evidence_hash,
                "ip_address": ip_address,
                **kwargs,
            }
        )

    async def withdraw_consent(
        self,
        consent_id: UUID,
        revoked_method: str = "user_request",
        revoked_reason: str | None = None,
    ) -> DataConsent | None:
        """
        Withdraw a consent.

        RGPD Art. 7.3: Withdrawal must be as easy as giving consent.
        """
        consent = await self.get_by_id(consent_id)
        if not consent:
            return None

        await self.session.execute(
            update(DataConsent)
            .where(DataConsent.id == consent_id)
            .values(
                revoked_at=datetime.now(UTC),
                revoked_method=revoked_method,
                revoked_reason=revoked_reason,
            )
        )

        await self.session.refresh(consent)
        return consent

    async def check_consent(
        self,
        data_subject_id: UUID,
        data_subject_type: str,
        purpose_id: UUID | None = None,
    ) -> bool:
        """
        Check if valid consent exists for a subject.
        Used by middleware for consent verification.
        """
        consent = await self.get_active_consent(
            data_subject_id=data_subject_id,
            data_subject_type=data_subject_type,
            purpose_id=purpose_id,
        )
        return consent is not None

    async def get_expiring_consents(
        self,
        days_until_expiry: int = 30,
    ) -> Sequence[DataConsent]:
        """Get consents that will expire soon (for renewal notices)."""
        expiry_date = datetime.now(UTC) + timedelta(days=days_until_expiry)

        result = await self.session.execute(
            select(DataConsent)
            .where(DataConsent.consent_given.is_(True))
            .where(DataConsent.revoked_at.is_(None))
            .where(DataConsent.expires_at.isnot(None))
            .where(DataConsent.expires_at <= expiry_date)
            .order_by(DataConsent.expires_at)
        )
        return result.scalars().all()


class CallConsentRepository(BaseRepository[CallProcessingConsent]):
    """
    Repository for call processing consents.
    Maps to sferaai.sql line 1330.

    Links calls to specific purposes and data_consents.
    RGPD Art. 5.1.b: Purpose limitation per call.
    """

    def __init__(self, session: AsyncSession):
        super().__init__(session, CallProcessingConsent)

    async def get_call_consents(
        self,
        call_id: UUID,
    ) -> Sequence[CallProcessingConsent]:
        """Get all enabled processing consents for a call."""
        result = await self.session.execute(
            select(CallProcessingConsent)
            .where(CallProcessingConsent.call_id == call_id)
            .where(CallProcessingConsent.processing_enabled.is_(True))
            .order_by(CallProcessingConsent.created_at)
        )
        return result.scalars().all()

    async def check_call_consent(
        self,
        call_id: UUID,
        purpose_id: UUID,
    ) -> bool:
        """Check if enabled consent exists for a call and purpose."""
        result = await self.session.execute(
            select(CallProcessingConsent)
            .where(CallProcessingConsent.call_id == call_id)
            .where(CallProcessingConsent.purpose_id == purpose_id)
            .where(CallProcessingConsent.processing_enabled.is_(True))
            .limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def link_call_consent(
        self,
        call_id: UUID,
        purpose_id: UUID,
        consent_id: UUID,
        retention_until: Any = None,
    ) -> CallProcessingConsent:
        """Link a call to a consent and purpose (UNIQUE call_id+purpose_id)."""
        return await self.create(
            {
                "call_id": call_id,
                "purpose_id": purpose_id,
                "consent_id": consent_id,
                "processing_enabled": True,
                "retention_until": retention_until,
            }
        )

    async def mark_processing_started(
        self,
        call_id: UUID,
        purpose_id: UUID,
    ) -> CallProcessingConsent | None:
        """Mark processing as started for a call+purpose."""
        result = await self.session.execute(
            select(CallProcessingConsent)
            .where(CallProcessingConsent.call_id == call_id)
            .where(CallProcessingConsent.purpose_id == purpose_id)
            .limit(1)
        )
        consent = result.scalar_one_or_none()
        if not consent:
            return None

        await self.session.execute(
            update(CallProcessingConsent)
            .where(CallProcessingConsent.id == consent.id)
            .values(processing_started_at=datetime.now(UTC))
        )
        await self.session.refresh(consent)
        return consent

    async def mark_processing_completed(
        self,
        call_id: UUID,
        purpose_id: UUID,
    ) -> CallProcessingConsent | None:
        """Mark processing as completed for a call+purpose."""
        result = await self.session.execute(
            select(CallProcessingConsent)
            .where(CallProcessingConsent.call_id == call_id)
            .where(CallProcessingConsent.purpose_id == purpose_id)
            .limit(1)
        )
        consent = result.scalar_one_or_none()
        if not consent:
            return None

        await self.session.execute(
            update(CallProcessingConsent)
            .where(CallProcessingConsent.id == consent.id)
            .values(processing_completed_at=datetime.now(UTC))
        )
        await self.session.refresh(consent)
        return consent

    async def disable_processing(
        self,
        consent_id: UUID,
    ) -> CallProcessingConsent | None:
        """Disable processing for a call consent."""
        consent = await self.get_by_id(consent_id)
        if not consent:
            return None

        await self.session.execute(
            update(CallProcessingConsent)
            .where(CallProcessingConsent.id == consent_id)
            .values(processing_enabled=False)
        )
        await self.session.refresh(consent)
        return consent


class ConsentVersionRepository(BaseRepository[ConsentVersion]):
    """Repository for consent text versions."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, ConsentVersion)

    async def get_active_version(
        self,
        purpose_id: UUID,
        language: str = "es",
    ) -> ConsentVersion | None:
        """Get the current active consent version for a purpose."""
        result = await self.session.execute(
            select(ConsentVersion)
            .where(ConsentVersion.purpose_id == purpose_id)
            .where(ConsentVersion.language == language)
            .where(ConsentVersion.is_active.is_(True))
            .where(
                or_(
                    ConsentVersion.effective_until.is_(None),
                    ConsentVersion.effective_until > datetime.now(UTC),
                )
            )
            .order_by(ConsentVersion.effective_from.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
