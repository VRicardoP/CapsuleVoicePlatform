"""CSV export and import utilities for WhatsApp contacts."""

import csv
import io
import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.whatsapp_repository import WAContactRepository, WASegmentRepository

logger = logging.getLogger(__name__)


async def generate_contacts_csv(db: AsyncSession, tenant_id: UUID) -> str:
    """Generate CSV content string with all contacts for a tenant.

    Returns the full CSV as a string ready to be streamed.
    """
    contact_repo = WAContactRepository(db)
    seg_repo = WASegmentRepository(db)

    items, _ = await contact_repo.list_by_tenant(tenant_id=tenant_id, skip=0, limit=10000)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        ["Teléfono", "Nombre", "Email", "Estado opt-in", "Origen", "Segmentos", "Fecha creación"]
    )

    for c in items:
        segments = await seg_repo.get_segments_for_contact(c.id)
        seg_names = ", ".join(s.name for s in segments)
        writer.writerow(
            [
                c.phone_e164,
                c.display_name or "",
                c.email or "",
                c.opt_in_status,
                c.source,
                seg_names,
                c.created_at.strftime("%Y-%m-%d %H:%M") if c.created_at else "",
            ]
        )

    return output.getvalue()
