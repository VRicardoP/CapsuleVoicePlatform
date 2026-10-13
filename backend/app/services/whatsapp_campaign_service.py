"""
WhatsApp Campaign Sending Service.

Background task that sends template messages to campaign recipients
with rate limiting and progress tracking via SSE.
"""

import asyncio
import logging
from datetime import UTC, datetime
from uuid import UUID

import httpx
from sqlalchemy import and_, func, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.whatsapp import (
    WACampaign,
    WACampaignRecipient,
    WACatalogItem,
    WAContact,
    WAContactSegment,
    WAConversation,
    WAMessage,
    WATemplate,
    WATenantSettings,
)
from app.services.base_campaign_service import BaseCampaignService
from app.services.whatsapp_service import whatsapp_service
from app.services.whatsapp_sse import sse_broadcaster

logger = logging.getLogger(__name__)

# Rate limit: 80 messages/second (Meta allows ~80/s for Business API tier)
# We use conservative 10/s to avoid hitting limits
SEND_RATE_LIMIT = 10
SEND_SEMAPHORE = asyncio.Semaphore(SEND_RATE_LIMIT)


class CampaignSendingService(BaseCampaignService):
    """Orchestrates campaign message sending as a background task."""

    async def _run_campaign(self, campaign_id: UUID) -> None:
        """Populate recipients and begin sending."""
        await self._populate_recipients(campaign_id)
        await self._send_loop(campaign_id)

    async def _on_failure(self, campaign_id: UUID) -> None:
        await self._update_campaign_status(campaign_id, "cancelled")

    async def _populate_recipients(self, campaign_id: UUID) -> None:
        """Resolve audience_filter into campaign_recipients rows."""
        async with self._session_maker() as db:
            campaign = await db.get(WACampaign, campaign_id)
            if not campaign:
                return

            audience = campaign.audience_filter or {}
            segment_ids: list[str] = audience.get("segment_ids", [])

            # Build contact query
            query = select(WAContact.id).where(WAContact.tenant_id == campaign.tenant_id)

            # Filter by segments if specified
            if segment_ids:
                query = query.where(
                    WAContact.id.in_(
                        select(WAContactSegment.contact_id).where(
                            WAContactSegment.segment_id.in_(segment_ids)
                        )
                    )
                )

            result = await db.execute(query)
            contact_ids = result.scalars().all()

            # Create recipient records (skip duplicates)
            existing = await db.execute(
                select(WACampaignRecipient.contact_id).where(
                    WACampaignRecipient.campaign_id == campaign_id
                )
            )
            existing_ids = set(existing.scalars().all())

            new_recipients = []
            for cid in contact_ids:
                if cid not in existing_ids:
                    new_recipients.append(
                        WACampaignRecipient(
                            campaign_id=campaign_id,
                            contact_id=cid,
                            status="pending",
                        )
                    )

            if new_recipients:
                db.add_all(new_recipients)

            campaign.total_recipients = len(existing_ids) + len(new_recipients)
            await db.commit()

            logger.info(
                "Campaign %s: %d recipients populated",
                campaign_id,
                campaign.total_recipients,
            )

    async def _send_loop(self, campaign_id: UUID) -> None:
        """Send template messages to all pending recipients."""
        async with self._session_maker() as db:
            campaign = await db.get(WACampaign, campaign_id)
            if not campaign or campaign.status != "sending":
                return

            # Get template
            template = await db.get(WATemplate, campaign.template_id)
            if not template or template.status != "approved":
                logger.error("Campaign %s: template not approved", campaign_id)
                await self._update_campaign_status(campaign_id, "cancelled")
                return

            # Get catalog item (if attached)
            catalog_item: WACatalogItem | None = None
            if campaign.catalog_item_id:
                catalog_item = await db.get(WACatalogItem, campaign.catalog_item_id)

            # Get tenant settings
            ts_result = await db.execute(
                select(WATenantSettings).where(WATenantSettings.tenant_id == campaign.tenant_id)
            )
            ts = ts_result.scalar_one_or_none()
            if not ts:
                logger.error("Campaign %s: no tenant settings", campaign_id)
                await self._update_campaign_status(campaign_id, "cancelled")
                return

            tenant_id_str = str(campaign.tenant_id)

        # Process in batches to avoid holding a session open too long
        batch_size = 50
        offset = 0

        while self.is_active(campaign_id):
            async with self._session_maker() as db:
                result = await db.execute(
                    select(WACampaignRecipient)
                    .where(
                        WACampaignRecipient.campaign_id == campaign_id,
                        WACampaignRecipient.status == "pending",
                    )
                    .limit(batch_size)
                )
                recipients = result.scalars().all()

                if not recipients:
                    break

                for recipient in recipients:
                    if not self.is_active(campaign_id):
                        break

                    # Get contact phone
                    contact = await db.get(WAContact, recipient.contact_id)
                    if not contact:
                        recipient.status = "failed"
                        recipient.error_detail = "Contact not found"
                        recipient.failed_at = datetime.now(UTC)
                        await db.execute(
                            text(
                                "UPDATE wa_campaigns SET failed_count = failed_count + 1 WHERE id = CAST(:cid AS UUID)"
                            ),
                            {"cid": str(campaign_id)},
                        )
                        await db.commit()
                        continue

                    # Skip opted-out or blocked contacts
                    if contact.opt_in_status in ("opted_out", "blocked"):
                        recipient.status = "skipped"
                        recipient.error_detail = f"Contact {contact.opt_in_status}"
                        recipient.failed_at = datetime.now(UTC)
                        await db.commit()
                        continue

                    async with SEND_SEMAPHORE:
                        await self._send_to_recipient(
                            db,
                            campaign_id,
                            recipient,
                            contact,
                            template,
                            ts,
                            tenant_id_str,
                            catalog_item,
                        )

                    # Brief pause between sends
                    await asyncio.sleep(0.1)

                offset += batch_size

        # Check if completed
        await self._check_completion(campaign_id)

    @staticmethod
    def _count_body_variables(body_text: str | None) -> int:
        """Count {{N}} placeholders in template body text."""
        if not body_text:
            return 0
        import re

        return len(re.findall(r"\{\{\d+\}\}", body_text))

    @staticmethod
    def _build_template_components(
        template: WATemplate,
        catalog_item: WACatalogItem | None = None,
    ) -> list[dict] | None:
        """Build Meta API components array from template DB fields.

        When a catalog_item is attached:
        - Header image is only sent if template header_type is IMAGE/VIDEO/DOCUMENT
        - Body variables are filled with catalog data, matching the exact count
          of {{N}} placeholders in the template body
        - Button URL variable is sent if template has a dynamic URL button
        """
        components: list[dict] = []
        ht = (template.header_type or "").upper()
        is_media_header = ht in ("IMAGE", "VIDEO", "DOCUMENT")

        # --- Header component ---
        header_url = None
        if is_media_header:
            if catalog_item and catalog_item.image_url:
                header_url = catalog_item.image_url
            elif template.header_content:
                url = template.header_content
                if "scontent.whatsapp.net" not in url:
                    header_url = url

        if header_url and is_media_header:
            media_type = ht.lower()
            components.append(
                {
                    "type": "header",
                    "parameters": [
                        {
                            "type": media_type,
                            media_type: {"link": header_url},
                        }
                    ],
                }
            )

        # --- Body variables from catalog item ---
        if catalog_item:
            num_vars = CampaignSendingService._count_body_variables(template.body_text)
            if num_vars > 0:
                price_str = f"{catalog_item.price:.2f} {catalog_item.currency}"
                available_values = [
                    catalog_item.name,
                    price_str,
                    catalog_item.description or "",
                ]
                # Pad or trim to match exact variable count
                body_params = []
                for i in range(num_vars):
                    val = available_values[i] if i < len(available_values) else ""
                    body_params.append({"type": "text", "text": val})
                components.append(
                    {
                        "type": "body",
                        "parameters": body_params,
                    }
                )

        # --- Button URL variable from catalog item ---
        if catalog_item and catalog_item.product_url:
            components.append(
                {
                    "type": "button",
                    "sub_type": "url",
                    "index": "0",
                    "parameters": [
                        {
                            "type": "text",
                            "text": catalog_item.product_url,
                        }
                    ],
                }
            )

        return components if components else None

    async def _send_to_recipient(
        self,
        db: AsyncSession,
        campaign_id: UUID,
        recipient: WACampaignRecipient,
        contact: WAContact,
        template: WATemplate,
        ts: WATenantSettings,
        tenant_id_str: str,
        catalog_item: WACatalogItem | None = None,
    ) -> None:
        """Send a single template message to a recipient."""
        now = datetime.now(UTC)
        count_field = "sent_count"
        try:
            result = await whatsapp_service.send_template_message(
                phone_number_id=ts.phone_number_id,
                to=contact.phone_e164,
                template_name=template.name,
                language=template.language,
                token=whatsapp_service.get_token(ts),
                components=self._build_template_components(template, catalog_item),
            )
            recipient.status = "sent"
            recipient.sent_at = now

            # Extract wamid from Meta response
            wamid = None
            meta_messages = result.get("messages", []) if isinstance(result, dict) else []
            if meta_messages:
                wamid = meta_messages[0].get("id")

            # Find or create conversation for the contact
            tenant_id = UUID(tenant_id_str)
            conv = await self._get_or_create_conversation(
                db,
                tenant_id,
                contact.id,
                now,
            )

            # Record message in wa_messages so it appears in the inbox
            wa_msg = WAMessage(
                tenant_id=tenant_id,
                conversation_id=conv.id,
                direction="outbound",
                msg_type="template",
                provider_message_id=wamid,
                text_body=template.body_text,
                delivery_status="sent",
                sent_at=now,
            )
            db.add(wa_msg)

            # Update conversation preview
            conv.last_message_text = f"[Campaña: {template.name}]"
            conv.last_message_at = now
            conv.last_outbound_at = now
            conv.message_count += 1
            if conv.status == "closed":
                conv.status = "open"

        except (httpx.HTTPError, SQLAlchemyError, ValueError) as e:
            logger.warning(
                "Campaign %s: failed to send to %s: %s",
                campaign_id,
                contact.phone_e164,
                str(e),
            )
            recipient.status = "failed"
            recipient.error_detail = str(e)[:500]
            recipient.failed_at = now
            count_field = "failed_count"

        # Atomic increment — avoids fetching the campaign object per recipient
        await db.execute(
            text(
                f"UPDATE wa_campaigns SET {count_field} = {count_field} + 1 WHERE id = CAST(:cid AS UUID)"
            ),
            {"cid": str(campaign_id)},
        )
        await db.commit()

        # Read fresh counts for SSE progress (single lightweight query)
        row = (
            await db.execute(
                text(
                    "SELECT sent_count, failed_count, total_recipients FROM wa_campaigns WHERE id = CAST(:cid AS UUID)"
                ),
                {"cid": str(campaign_id)},
            )
        ).fetchone()
        if row:
            await sse_broadcaster.publish(
                tenant_id_str,
                "campaign.progress",
                {
                    "campaignId": str(campaign_id),
                    "sent": row.sent_count,
                    "failed": row.failed_count,
                    "total": row.total_recipients,
                },
            )

    @staticmethod
    async def _get_or_create_conversation(
        db: AsyncSession,
        tenant_id: UUID,
        contact_id: UUID,
        now: datetime,
    ) -> WAConversation:
        """Find the most recent conversation for a contact, or create one."""
        result = await db.execute(
            select(WAConversation)
            .where(
                and_(
                    WAConversation.tenant_id == tenant_id,
                    WAConversation.contact_id == contact_id,
                )
            )
            .order_by(WAConversation.updated_at.desc())
            .limit(1)
        )
        conv = result.scalar_one_or_none()
        if conv:
            return conv

        conv = WAConversation(
            tenant_id=tenant_id,
            contact_id=contact_id,
            status="open",
            last_message_at=now,
        )
        db.add(conv)
        await db.flush()
        return conv

    async def _check_completion(self, campaign_id: UUID) -> None:
        """Mark campaign as completed if all recipients processed."""
        async with self._session_maker() as db:
            campaign = await db.get(WACampaign, campaign_id)
            if not campaign:
                return

            pending_count = await db.execute(
                select(func.count())
                .select_from(WACampaignRecipient)
                .where(
                    WACampaignRecipient.campaign_id == campaign_id,
                    WACampaignRecipient.status == "pending",
                )
            )
            pending = pending_count.scalar_one()

            if pending == 0 and campaign.status == "sending":
                campaign.status = "completed"
                campaign.completed_at = datetime.now(UTC)
                await db.commit()

                await sse_broadcaster.publish(
                    str(campaign.tenant_id),
                    "campaign.completed",
                    {"campaignId": str(campaign_id)},
                )
                logger.info("Campaign %s completed", campaign_id)
            elif not self.is_active(campaign_id):
                # Was paused or cancelled externally
                pass

    async def _update_campaign_status(self, campaign_id: UUID, status: str) -> None:
        """Update campaign status directly."""
        async with self._session_maker() as db:
            campaign = await db.get(WACampaign, campaign_id)
            if campaign:
                campaign.status = status
                if status == "completed":
                    campaign.completed_at = datetime.now(UTC)
                await db.commit()
