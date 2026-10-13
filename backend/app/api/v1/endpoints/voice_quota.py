"""
Endpoints de visibilidad de cuotas de voz por tenant.

Permite a client_admin ver el consumo mensual de minutos inbound/outbound
y los límites configurados para su organización.
"""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.authorization import Principal
from app.core.dependencies import get_current_principal, get_db_with_rls, require_permission
from app.services.voice_quota_service import VoiceQuotaService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/me/voice-quota")
async def get_my_voice_quota_status(
    db: AsyncSession = Depends(get_db_with_rls),
    principal: Annotated[Principal, Depends(get_current_principal)] = ...,
    _perm=Depends(require_permission("dashboard.calls.view")),
):
    """Estado de cuota de voz del mes actual del tenant autenticado.

    Devuelve minutos usados, reservados, restantes y el límite configurado,
    separado por dirección (inbound / outbound).
    """
    svc = VoiceQuotaService(db)
    return await svc.get_status(principal.organization_id)


@router.get("/{org_id}/voice-quota")
async def get_voice_quota_status(
    org_id: UUID,
    db: AsyncSession = Depends(get_db_with_rls),
    _perm=Depends(require_permission("dashboard.calls.view")),
):
    """Estado de cuota de voz del mes actual para una organización.

    Devuelve minutos usados, reservados, restantes y el límite configurado,
    separado por dirección (inbound / outbound).
    """
    svc = VoiceQuotaService(db)
    return await svc.get_status(org_id)
