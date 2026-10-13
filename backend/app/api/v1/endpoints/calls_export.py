"""Endpoint de exportación de llamadas a XLSX.

Devuelve un Excel con las llamadas inbound de los últimos N días para el
panel del dashboard. Separado de `calls.py` y `calls_recordings.py` por
SRP (CLAUDE.md §1).
"""

import logging
import urllib.parse
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_with_rls, require_permission
from app.services.calls_export_service import export_recent_calls_xlsx

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/export.xlsx",
    summary="Exportar llamadas a Excel",
    description=(
        "Descarga un fichero XLSX con las llamadas inbound de los últimos N días. "
        "Columnas: Nombre, Teléfono, Fecha, Hora, Resumen."
    ),
    dependencies=[Depends(require_permission("dashboard.calls.view"))],
)
async def export_calls_xlsx(
    db: Annotated[AsyncSession, Depends(get_db_with_rls)],
    days: int = Query(7, ge=1, le=365, description="Días hacia atrás a exportar"),
) -> StreamingResponse:
    """Genera y devuelve el XLSX como descarga."""
    xlsx_bytes = await export_recent_calls_xlsx(db, days=days)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M")
    filename = f"llamadas_{days}d_{timestamp}.xlsx"

    # Soporte de filenames con caracteres no-ASCII (RFC 6266)
    ascii_safe = filename.encode("ascii", "ignore").decode() or "llamadas.xlsx"
    quoted = urllib.parse.quote(filename)

    return StreamingResponse(
        iter([xlsx_bytes]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{ascii_safe}"; filename*=UTF-8\'\'{quoted}'
            ),
        },
    )
