"""
Endpoints HTTP Tool para agentes de voz Ultravox.

Permite al agente enviar plantillas WhatsApp aprobadas al llamante.
El tenant se resuelve por organization_slug (sin auth de sesión, igual que
el webhook de avisos).
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.models.whatsapp import WATemplate
from app.repositories.whatsapp_repository import (
    WAContactRepository,
    WAConversationRepository,
    WATenantSettingsRepository,
)
from app.services.aviso_service import _resolve_caller_phone, resolve_tenant_by_slug
from app.services.whatsapp_messaging_service import (
    MessageSendError,
    MessageValidationError,
    send_template_message,
)

logger = logging.getLogger(__name__)

router = APIRouter()


class EnvioWhatsappRequest(BaseModel):
    organization_slug: str
    call_id: str | None = None       # parámetro automático Ultravox (callId)
    phone_number: str | None = None  # fallback: se resuelve desde el call record
    template_name: str = "informacion_general"
    language: str = "es"


@router.post(
    "/functions/envio-whatsapp",
    status_code=200,
    summary="Enviar plantilla WhatsApp desde agente Ultravox",
    description=(
        "HTTP Tool para el agente de voz. Envía una plantilla aprobada "
        "al número indicado. El tenant se resuelve por organization_slug."
    ),
)
async def function_envio_whatsapp(
    payload: EnvioWhatsappRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    x_ultravox_call_id: Annotated[str | None, Header()] = None,
) -> dict:
    """Envía la plantilla WhatsApp solicitada por el agente Ultravox.

    Flujo:
    1. Resolver tenant por slug
    2. Verificar que WhatsApp está configurado para el tenant
    3. Buscar plantilla aprobada por nombre (prueba 'es', luego 'es_ES')
    4. Crear contacto WhatsApp si no existe
    5. Usar conversación abierta existente o crear una nueva
    6. Enviar plantilla vía Meta API
    """
    tenant_id = await resolve_tenant_by_slug(db, payload.organization_slug)
    if tenant_id is None:
        logger.warning("[envio_whatsapp] Slug no encontrado: %s", payload.organization_slug)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Organización no encontrada: '{payload.organization_slug}'",
        )

    ts_repo = WATenantSettingsRepository(db)
    ts = await ts_repo.get_by_tenant(tenant_id)
    if not ts:
        logger.warning("[envio_whatsapp] WhatsApp no configurado para tenant %s", tenant_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="WhatsApp no configurado para esta organización",
        )

    # call_id: primero el parámetro automático del body, luego el header
    effective_call_id = payload.call_id or x_ultravox_call_id
    phone_number = await _resolve_caller_phone(db, effective_call_id, payload.phone_number)
    if phone_number == "desconocido":
        # Número no disponible aún (llamada no registrada todavía o PBX sin CLI).
        # Se devuelve 200 para no interrumpir el flujo del agente.
        logger.warning(
            "[envio_whatsapp] Número no disponible para call_id=%s — no se envía plantilla",
            effective_call_id,
        )
        return {
            "success": False,
            "reason": "phone_unavailable",
            "message": "No se pudo obtener el número de teléfono. El mensaje no ha sido enviado.",
        }

    template = await _find_template(db, tenant_id, payload.template_name, payload.language)
    if not template:
        logger.error(
            "[envio_whatsapp] Plantilla '%s' no encontrada para tenant %s",
            payload.template_name,
            tenant_id,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plantilla '{payload.template_name}' no encontrada. Verifica nombre y que esté aprobada.",
        )
    if template.status != "approved":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Plantilla '{payload.template_name}' no está aprobada (estado: {template.status})",
        )

    contact_repo = WAContactRepository(db)
    contact, _ = await contact_repo.get_or_create_by_phone(tenant_id, phone_number)
    await db.flush()

    conv_repo = WAConversationRepository(db)
    conv = await conv_repo.get_open_for_contact(tenant_id, contact.id)
    if not conv:
        conv = await conv_repo.create(
            {
                "tenant_id": tenant_id,
                "contact_id": contact.id,
                "status": "open",
            }
        )
        await db.flush()

    try:
        wa_message = await send_template_message(
            db=db,
            tenant_id=tenant_id,
            conversation_id=conv.id,
            template_id=template.id,
            sender_user_id="ultravox_agent",
        )
    except MessageValidationError as e:
        logger.warning("[envio_whatsapp] Validación fallida: %s", e)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except MessageSendError as e:
        logger.error("[envio_whatsapp] Error al enviar plantilla: %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e),
        )

    logger.info(
        "[envio_whatsapp] Plantilla '%s' enviada a %s (call=%s)",
        payload.template_name,
        phone_number,
        effective_call_id,
    )
    return {
        "success": True,
        "message_id": str(wa_message.id),
        "template_name": payload.template_name,
        "phone_number": phone_number,
    }


async def _find_template(
    db: AsyncSession,
    tenant_id,
    name: str,
    language: str,
) -> WATemplate | None:
    """Busca plantilla aprobada por nombre. Prueba el idioma indicado y luego es_ES."""
    for lang in (language, "es_ES", "es"):
        result = await db.execute(
            select(WATemplate).where(
                WATemplate.tenant_id == tenant_id,
                WATemplate.name == name,
                WATemplate.language == lang,
            )
        )
        template = result.scalars().first()
        if template:
            return template
    # Último recurso: cualquier idioma
    result = await db.execute(
        select(WATemplate).where(
            WATemplate.tenant_id == tenant_id,
            WATemplate.name == name,
        )
    )
    return result.scalars().first()
