"""
WhatsApp Flow Execution Engine.

Processes automation flow steps sequentially when triggered by events.
Supports: send_message, wait, condition, assign_agent, add_tag, close.
"""

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

import httpx
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.tasks import create_logged_task
from app.models.whatsapp import WAContact, WAConversation, WAFlow
from app.services.whatsapp_service import whatsapp_service
from app.services.whatsapp_sse import sse_broadcaster

logger = logging.getLogger(__name__)


class FlowEngine:
    """Executes automation flow steps for a conversation."""

    def __init__(self, session_maker: async_sessionmaker[AsyncSession]) -> None:
        self._session_maker = session_maker

    async def check_triggers(
        self,
        tenant_id: UUID,
        trigger_type: str,
        conversation_id: UUID,
        message_text: str | None = None,
        is_new_conversation: bool = False,
    ) -> None:
        """Check if any active flow matches the trigger and execute it."""
        async with self._session_maker() as db:
            result = await db.execute(
                select(WAFlow).where(
                    WAFlow.tenant_id == tenant_id,
                    WAFlow.is_active == True,
                    WAFlow.trigger_type == trigger_type,
                )
            )
            flows = result.scalars().all()

            for flow in flows:
                if not self._matches_trigger(flow, trigger_type, message_text, is_new_conversation):
                    continue
                if await self._is_on_cooldown(db, flow, conversation_id):
                    logger.debug("Flow on cooldown, skipping", flow_id=str(flow.id), conversation_id=str(conversation_id))
                    continue
                # Execute in background to not block webhook processing
                create_logged_task(
                    self._execute_flow(flow.id, tenant_id, conversation_id),
                    name=f"flow-{flow.id}",
                )

    async def _is_on_cooldown(
        self,
        db: AsyncSession,
        flow: WAFlow,
        conversation_id: UUID,
    ) -> bool:
        """Devuelve True si ya se envió una plantilla automática en esta conversación dentro del cooldown."""
        config = flow.trigger_config or {}
        cooldown_hours = config.get("cooldown_hours")
        if not cooldown_hours:
            return False

        cutoff = datetime.now(UTC) - timedelta(hours=int(cooldown_hours))
        result = await db.execute(
            text("""
                SELECT 1 FROM wa_messages
                WHERE conversation_id = CAST(:cid AS UUID)
                  AND msg_type = 'template'
                  AND direction = 'outbound'
                  AND is_from_ai = TRUE
                  AND created_at > :cutoff
                LIMIT 1
            """),
            {"cid": str(conversation_id), "cutoff": cutoff},
        )
        return result.fetchone() is not None

    def _matches_trigger(
        self,
        flow: WAFlow,
        trigger_type: str,
        message_text: str | None,
        is_new_conversation: bool = False,
    ) -> bool:
        """Check if the trigger conditions match."""
        config = flow.trigger_config or {}

        # first_message_only: only trigger on the first message of a new conversation
        if config.get("first_message_only") and not is_new_conversation:
            return False

        if trigger_type == "keyword" and message_text:
            keywords = config.get("keywords", [])
            text_lower = message_text.lower()
            return any(kw.lower() in text_lower for kw in keywords)

        if trigger_type == "message_received":
            # Optional keyword filter
            keywords = config.get("keywords", [])
            if keywords and message_text:
                text_lower = message_text.lower()
                return any(kw.lower() in text_lower for kw in keywords)
            return True  # Match all messages if no keywords configured

        # Other triggers (conversation_opened, etc.) always match
        return True

    async def _execute_flow(
        self,
        flow_id: UUID,
        tenant_id: UUID,
        conversation_id: UUID,
    ) -> None:
        """Execute all steps in a flow sequentially."""
        try:
            async with self._session_maker() as db:
                flow = await db.get(WAFlow, flow_id)
                if not flow or not flow.is_active:
                    return

                steps = flow.steps if isinstance(flow.steps, list) else flow.steps.get("nodes", [])
                if not steps:
                    return

                # Get conversation and contact context
                conv = await db.get(WAConversation, conversation_id)
                if not conv:
                    return

                contact = await db.get(WAContact, conv.contact_id)

                # Get tenant settings for API calls
                ts_result = await db.execute(
                    text("""
                    SELECT phone_number_id, api_token_enc
                    FROM wa_tenant_settings
                    WHERE tenant_id = CAST(:tid AS UUID)
                """),
                    {"tid": str(tenant_id)},
                )
                ts = ts_result.fetchone()
                if not ts:
                    return

                context = {
                    "tenant_id": tenant_id,
                    "conversation_id": conversation_id,
                    "contact": contact,
                    "phone_number_id": ts.phone_number_id,
                    "token": ts.api_token_enc,
                }

                for step in steps:
                    step_type = step.get("type", "")
                    params = step.get("params", {})

                    try:
                        should_continue = await self._execute_step(
                            db,
                            step_type,
                            params,
                            context,
                            conv,
                            contact,
                        )
                        if not should_continue:
                            break
                    except (SQLAlchemyError, httpx.HTTPError, ValueError, KeyError):
                        logger.error(
                            "Flow step failed",
                            flow_id=str(flow_id),
                            step_type=step_type,
                            exc_info=True,
                        )
                        break

                # Update flow execution stats atomically to avoid race conditions
                await db.execute(
                    text("""
                        UPDATE wa_flows
                        SET last_triggered_at = NOW(),
                            execution_count = execution_count + 1
                        WHERE id = CAST(:fid AS UUID)
                    """),
                    {"fid": str(flow_id)},
                )
                await db.commit()

        except (SQLAlchemyError, httpx.HTTPError, ValueError, KeyError):
            logger.error("Flow execution failed", flow_id=str(flow_id), exc_info=True)

    async def _execute_step(
        self,
        db: AsyncSession,
        step_type: str,
        params: dict,
        context: dict,
        conv: WAConversation,
        contact: WAContact | None,
    ) -> bool:
        """Execute a single step. Returns True to continue, False to stop."""

        if step_type == "send_message":
            text_val = self._substitute_vars(
                params.get("text", ""),
                contact,
                context,
            )
            if text_val:
                await whatsapp_service.send_text_message(
                    phone_number_id=context["phone_number_id"],
                    to=contact.phone_e164 if contact else "",
                    text=text_val,
                    token=context["token"],
                )
            return True

        elif step_type == "send_template":
            template_name = params.get("template_name")
            language = params.get("language", "es")
            if template_name and contact:
                result = await whatsapp_service.send_template_message(
                    phone_number_id=context["phone_number_id"],
                    to=contact.phone_e164,
                    template_name=template_name,
                    language=language,
                    token=context["token"],
                )
                # Record the outbound message in DB and notify via SSE
                from app.repositories.whatsapp_repository import WAMessageRepository

                msg_repo = WAMessageRepository(db)
                provider_msg_id = None
                if result and "messages" in result:
                    provider_msg_id = result["messages"][0].get("id")
                wa_msg = await msg_repo.create(
                    {
                        "tenant_id": context["tenant_id"],
                        "conversation_id": context["conversation_id"],
                        "direction": "outbound",
                        "msg_type": "template",
                        "text_body": f"[Plantilla: {template_name}]",
                        "provider_message_id": provider_msg_id,
                        "delivery_status": "sent",
                        "is_from_ai": True,
                    }
                )
                now = datetime.now(UTC)
                conv.last_message_text = f"[Plantilla: {template_name}]"
                conv.last_message_at = now
                conv.window_expires_at = now + timedelta(hours=24)
                await db.flush()

                await sse_broadcaster.publish(
                    str(context["tenant_id"]),
                    "message.new",
                    {
                        "conversationId": str(context["conversation_id"]),
                        "message": {
                            "id": str(wa_msg.id),
                            "direction": "outbound",
                            "msg_type": "template",
                            "text_body": f"[Plantilla: {template_name}]",
                            "delivery_status": "sent",
                            # El front usa is_from_ai para NO contar la
                            # auto-respuesta como atendida por el centro: en BD
                            # tampoco se toca last_outbound_at.
                            "is_from_ai": True,
                            "created_at": wa_msg.created_at.isoformat(),
                        },
                    },
                )
            return True

        elif step_type == "wait":
            seconds = params.get("seconds", 0)
            minutes = params.get("minutes", 0)
            hours = params.get("hours", 0)
            total = seconds + (minutes * 60) + (hours * 3600)
            if total > 0:
                # Cap at 24 hours to prevent indefinite waits
                total = min(total, 86400)
                await asyncio.sleep(total)
            return True

        elif step_type == "condition":
            field = params.get("field", "")
            operator = params.get("operator", "equals")
            value = params.get("value", "")

            actual_value = ""
            if field == "contact.opt_in_status" and contact:
                actual_value = contact.opt_in_status
            elif field == "conversation.status":
                actual_value = conv.status
            elif field == "conversation.priority":
                actual_value = conv.priority
            elif field == "contact.source" and contact:
                actual_value = contact.source

            if operator == "equals":
                return actual_value == value
            elif operator == "not_equals":
                return actual_value != value
            elif operator == "contains":
                return value in actual_value
            return True

        elif step_type == "assign_agent":
            agent_id = params.get("agent_id")
            if agent_id:
                conv.assignee_user_id = UUID(agent_id)
                conv.status = "assigned"
                await db.flush()
            return True

        elif step_type == "add_tag":
            tag = params.get("tag")
            if tag and contact:
                current_tags = list(contact.tags or [])
                if tag not in current_tags:
                    current_tags.append(tag)
                    contact.tags = current_tags
                    await db.flush()
            return True

        elif step_type == "close":
            conv.status = "closed"
            await db.flush()
            return True

        else:
            logger.warning("Unknown flow step type: %s", step_type)
            return True

    @staticmethod
    def _substitute_vars(
        text_val: str,
        contact: WAContact | None,
        context: dict,
    ) -> str:
        """Replace {{variable}} placeholders with actual values."""
        if not text_val:
            return text_val

        replacements = {
            "contact.name": (contact.display_name or contact.phone_e164) if contact else "",
            "contact.phone": contact.phone_e164 if contact else "",
            "conversation.id": str(context.get("conversation_id", "")),
        }

        result = text_val
        for key, val in replacements.items():
            result = result.replace("{{" + key + "}}", val)
        return result
