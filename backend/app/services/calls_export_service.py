"""Servicio de exportación de llamadas inbound/AI a XLSX.

Genera un Excel con las llamadas recientes (por defecto últimos 7 días) con
columnas: Nombre, Teléfono, Fecha, Hora, Resumen.

- Nombre: se desencripta de `contacts.full_name` si la call tiene `contact_id`;
  queda vacío si la call no tiene contacto asociado (el agente de voz de
  algunos tenants no enlaza con `contacts`).
- Teléfono: número del interlocutor (cliente), texto plano sin cifrar en BD.
  En inbound es `caller_number`; en outbound es `called_number` (porque en
  outbound `caller_number` es el caller ID propio, p.ej. el número Zadarma).
- Fecha / Hora: `initiated_at` en zona Europe/Madrid.
- Resumen: `calls.ai_summary` (puede ser largo: se aplica wrap_text).
"""

import io
import logging
from datetime import UTC, datetime

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.encryption_service import EncryptionService

logger = logging.getLogger(__name__)

_HEADER_FILL = PatternFill(start_color="1F2937", end_color="1F2937", fill_type="solid")
_HEADER_FONT = Font(bold=True, color="FFFFFF")
_HEADER_ALIGN = Alignment(horizontal="center", vertical="center")
_WRAP = Alignment(wrap_text=True, vertical="top")


def _fmt_date(dt: datetime | None) -> str:
    if not dt:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone().strftime("%d/%m/%Y")


def _fmt_time(dt: datetime | None) -> str:
    if not dt:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone().strftime("%H:%M")


async def export_recent_calls_xlsx(db: AsyncSession, days: int = 7) -> bytes:
    """Genera un XLSX con las llamadas de los últimos `days` días.

    El XLSX incluye: Nombre, Teléfono, Fecha, Hora, Resumen.

    Devuelve los bytes del fichero listo para StreamingResponse.
    """
    days = max(1, min(int(days), 365))

    result = await db.execute(
        text(
            """
            SELECT
                c.id,
                -- Teléfono del interlocutor (cliente), NO el numero propio:
                --   inbound  -> caller_number (quien nos llama)
                --   outbound -> called_number (a quien llamamos)
                -- En outbound, caller_number es nuestro caller ID Zadarma, no el cliente.
                CASE
                    WHEN c.direction = 'outbound'
                        THEN COALESCE(c.called_number, c.caller_number)
                    ELSE COALESCE(c.caller_number, c.called_number)
                END AS contact_number,
                c.initiated_at,
                c.ai_summary,
                ct.full_name AS contact_full_name
            FROM calls c
            LEFT JOIN contacts ct ON ct.id = c.contact_id AND ct.deleted_at IS NULL
            WHERE c.deleted_at IS NULL
              AND c.initiated_at >= NOW() - make_interval(days => :days)
            ORDER BY c.initiated_at DESC
            """
        ),
        {"days": days},
    )
    rows = result.fetchall()

    encryption = EncryptionService(db)

    wb = Workbook()
    ws = wb.active
    ws.title = f"Llamadas {days}d"

    headers = ["Nombre", "Teléfono", "Fecha", "Hora", "Resumen"]
    for col, header in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = _HEADER_FONT
        cell.fill = _HEADER_FILL
        cell.alignment = _HEADER_ALIGN

    for row_idx, row in enumerate(rows, start=2):
        nombre = ""
        if row.contact_full_name:
            try:
                nombre = await encryption.decrypt_pii(row.contact_full_name) or ""
            except (ValueError, TypeError, OSError):
                # Si el JSONB no tiene formato esperado por decrypt_pii_with_metadata,
                # dejamos vacío en vez de romper toda la exportación.
                nombre = ""

        ws.cell(row=row_idx, column=1, value=nombre)
        ws.cell(row=row_idx, column=2, value=row.contact_number or "")
        ws.cell(row=row_idx, column=3, value=_fmt_date(row.initiated_at))
        ws.cell(row=row_idx, column=4, value=_fmt_time(row.initiated_at))
        ws.cell(row=row_idx, column=5, value=row.ai_summary or "")

    ws.column_dimensions["A"].width = 28  # nombre
    ws.column_dimensions["B"].width = 16  # teléfono
    ws.column_dimensions["C"].width = 12  # fecha
    ws.column_dimensions["D"].width = 8  # hora
    ws.column_dimensions["E"].width = 70  # resumen

    # Wrap del resumen para que se vea entero en Excel
    for row_idx in range(2, ws.max_row + 1):
        ws.cell(row=row_idx, column=5).alignment = _WRAP

    # Freeze cabecera
    ws.freeze_panes = "A2"

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    logger.info("Exportadas %d llamadas (últimos %d días) a XLSX", len(rows), days)
    return buffer.read()
