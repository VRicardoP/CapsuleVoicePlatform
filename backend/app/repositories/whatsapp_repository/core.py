"""Core repositories: tenant settings, contacts, conversations, messages, events."""

import logging
from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.whatsapp import (
    WAContact,
    WAContactSegment,
    WAContactTag,
    WAConversation,
    WAEvent,
    WAMessage,
    WATenantSettings,
)
from app.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class WATenantSettingsRepository(BaseRepository[WATenantSettings]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, WATenantSettings)

    async def get_by_tenant(self, tenant_id: UUID) -> WATenantSettings | None:
        result = await self.session.execute(
            select(WATenantSettings).where(WATenantSettings.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_by_phone_number_id(self, phone_number_id: str) -> WATenantSettings | None:
        result = await self.session.execute(
            select(WATenantSettings).where(WATenantSettings.phone_number_id == phone_number_id)
        )
        return result.scalar_one_or_none()


class WAContactRepository(BaseRepository[WAContact]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, WAContact)

    async def list_by_tenant(
        self,
        tenant_id: UUID,
        search: str | None = None,
        segment_id: UUID | None = None,
        tag_id: UUID | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[Sequence[WAContact], int]:
        """List contacts with optional filters."""
        query = select(WAContact).where(WAContact.tenant_id == tenant_id)
        count_query = (
            select(func.count()).select_from(WAContact).where(WAContact.tenant_id == tenant_id)
        )

        if search:
            pattern = f"%{search}%"
            filt = or_(
                WAContact.display_name.ilike(pattern),
                WAContact.phone_e164.ilike(pattern),
                WAContact.email.ilike(pattern),
            )
            query = query.where(filt)
            count_query = count_query.where(filt)

        if segment_id:
            sub = select(WAContactSegment.contact_id).where(
                WAContactSegment.segment_id == segment_id
            )
            query = query.where(WAContact.id.in_(sub))
            count_query = count_query.where(WAContact.id.in_(sub))

        if tag_id:
            sub = select(WAContactTag.contact_id).where(WAContactTag.tag_id == tag_id)
            query = query.where(WAContact.id.in_(sub))
            count_query = count_query.where(WAContact.id.in_(sub))

        query = query.order_by(WAContact.created_at.desc()).offset(skip).limit(limit)
        result = await self.session.execute(query)
        items = result.scalars().all()
        total_result = await self.session.execute(count_query)
        total = total_result.scalar_one()
        return items, total

    @staticmethod
    def _normalize_phone(phone: str) -> str:
        """Normalize phone to E.164: strip spaces/dashes, ensure leading +."""
        phone = phone.strip().replace(" ", "").replace("-", "")
        if not phone.startswith("+"):
            phone = f"+{phone}"
        return phone

    async def get_or_create_by_phone(
        self,
        tenant_id: UUID,
        phone_e164: str,
        display_name: str | None = None,
    ) -> tuple[WAContact, bool]:
        """Get existing contact or create new one. Returns (contact, created)."""
        normalized = self._normalize_phone(phone_e164)
        # Match both with and without '+' to prevent duplicates
        bare = normalized.lstrip("+")
        result = await self.session.execute(
            select(WAContact).where(
                and_(
                    WAContact.tenant_id == tenant_id,
                    WAContact.phone_e164.in_([normalized, bare]),
                )
            )
        )
        contact = result.scalar_one_or_none()
        if contact:
            # Fix stored phone to normalized format if needed
            if contact.phone_e164 != normalized:
                contact.phone_e164 = normalized
            if display_name and not contact.display_name:
                contact.display_name = display_name
            await self.session.flush()
            return contact, False

        contact = await self.create(
            {
                "tenant_id": tenant_id,
                "phone_e164": normalized,
                "display_name": display_name,
                "source": "inbound",
            }
        )
        return contact, True


class WAConversationRepository(BaseRepository[WAConversation]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, WAConversation)

    async def list_by_tenant(
        self,
        tenant_id: UUID,
        status: str | None = None,
        assignee_user_id: UUID | None = None,
        segment_id: UUID | None = None,
        search: str | None = None,
        unanswered: bool | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[Sequence[WAConversation], int]:
        """List conversations with contact, returning (items, total).

        Unanswered conversations (last inbound message has no later outbound reply)
        are always sorted to the top. Pass `unanswered=True` to also restrict the
        result to only those conversations.
        """
        query = (
            select(WAConversation)
            .options(joinedload(WAConversation.contact))
            .where(WAConversation.tenant_id == tenant_id)
        )
        count_query = (
            select(func.count())
            .select_from(WAConversation)
            .where(WAConversation.tenant_id == tenant_id)
        )

        if status:
            query = query.where(WAConversation.status == status)
            count_query = count_query.where(WAConversation.status == status)
        if assignee_user_id:
            query = query.where(WAConversation.assignee_user_id == assignee_user_id)
            count_query = count_query.where(WAConversation.assignee_user_id == assignee_user_id)

        if segment_id:
            contact_ids_in_segment = select(WAContactSegment.contact_id).where(
                WAContactSegment.segment_id == segment_id
            )
            query = query.where(WAConversation.contact_id.in_(contact_ids_in_segment))
            count_query = count_query.where(WAConversation.contact_id.in_(contact_ids_in_segment))

        if search:
            pattern = f"%{search}%"
            matching_contacts = select(WAContact.id).where(
                and_(
                    WAContact.tenant_id == tenant_id,
                    or_(
                        WAContact.display_name.ilike(pattern),
                        WAContact.phone_e164.ilike(pattern),
                    ),
                )
            )
            query = query.where(WAConversation.contact_id.in_(matching_contacts))
            count_query = count_query.where(WAConversation.contact_id.in_(matching_contacts))

        # Unanswered: customer wrote last but we never replied (or replied earlier)
        unanswered_filter = and_(
            WAConversation.last_inbound_at.is_not(None),
            or_(
                WAConversation.last_outbound_at.is_(None),
                WAConversation.last_inbound_at > WAConversation.last_outbound_at,
            ),
        )

        if unanswered:
            query = query.where(unanswered_filter)
            count_query = count_query.where(unanswered_filter)

        # Always rank unanswered conversations first (0 = unanswered, 1 = answered)
        unanswered_rank = case((unanswered_filter, 0), else_=1)
        query = (
            query.order_by(
                unanswered_rank.asc(),
                WAConversation.updated_at.desc(),
            )
            .offset(skip)
            .limit(limit)
        )

        result = await self.session.execute(query)
        items = result.unique().scalars().all()

        total_result = await self.session.execute(count_query)
        total = total_result.scalar_one()

        return items, total

    async def get_with_contact(self, conversation_id: UUID) -> WAConversation | None:
        """Get conversation with eagerly loaded contact."""
        result = await self.session.execute(
            select(WAConversation)
            .options(joinedload(WAConversation.contact))
            .where(WAConversation.id == conversation_id)
        )
        return result.unique().scalar_one_or_none()

    async def get_open_for_contact(
        self,
        tenant_id: UUID,
        contact_id: UUID,
    ) -> WAConversation | None:
        """Get the open/assigned conversation for a contact, if any."""
        result = await self.session.execute(
            select(WAConversation)
            .where(
                and_(
                    WAConversation.tenant_id == tenant_id,
                    WAConversation.contact_id == contact_id,
                    WAConversation.status.in_(["open", "assigned"]),
                )
            )
            .order_by(WAConversation.updated_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def increment_unread(self, conversation_id: UUID) -> None:
        """Increment unread count and message count atomically."""
        conv = await self.get_by_id(conversation_id)
        if conv:
            conv.unread_count += 1
            conv.message_count += 1
            await self.session.flush()


class WAMessageRepository(BaseRepository[WAMessage]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, WAMessage)

    async def list_by_conversation(
        self,
        conversation_id: UUID,
        before: datetime | None = None,
        limit: int = 50,
    ) -> tuple[list[WAMessage], bool]:
        """Cursor-based pagination for messages. Returns (messages, has_more)."""
        query = select(WAMessage).where(WAMessage.conversation_id == conversation_id)

        if before:
            query = query.where(WAMessage.created_at < before)

        query = query.order_by(WAMessage.created_at.desc()).limit(limit + 1)

        result = await self.session.execute(query)
        messages = list(result.scalars().all())

        has_more = len(messages) > limit
        if has_more:
            messages = messages[:limit]

        messages.reverse()
        return messages, has_more

    async def get_by_provider_id(self, provider_message_id: str) -> WAMessage | None:
        """Find message by Meta's wamid."""
        result = await self.session.execute(
            select(WAMessage).where(WAMessage.provider_message_id == provider_message_id)
        )
        return result.scalar_one_or_none()


class WAEventRepository(BaseRepository[WAEvent]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, WAEvent)

    async def is_duplicate(self, provider_event_id: str) -> bool:
        """Check if this event was already processed (idempotency layer 1)."""
        result = await self.session.execute(
            select(func.count())
            .select_from(WAEvent)
            .where(WAEvent.provider_event_id == provider_event_id)
        )
        return result.scalar_one() > 0

    async def create_event(
        self,
        provider_event_id: str,
        event_type: str,
        payload_raw: dict,
        tenant_id: UUID | None = None,
        meta_phone_number_id: str | None = None,
    ) -> WAEvent | None:
        """Create event, returns None if duplicate."""
        if await self.is_duplicate(provider_event_id):
            return None

        return await self.create(
            {
                "provider_event_id": provider_event_id,
                "event_type": event_type,
                "payload_raw": payload_raw,
                "tenant_id": tenant_id,
                "meta_phone_number_id": meta_phone_number_id,
            }
        )
