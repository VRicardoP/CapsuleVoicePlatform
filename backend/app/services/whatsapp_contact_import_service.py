"""WhatsApp contact CSV import/export service."""

import csv
import io
import logging
import re
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.whatsapp_repository import WAContactRepository

logger = logging.getLogger(__name__)

# Column name normalization map
_PHONE_ALIASES = {"phone", "telefono", "teléfono", "phone_e164", "número", "numero"}
_NAME_ALIASES = {"name", "nombre", "display_name"}
_EMAIL_ALIASES = {"email", "correo", "e-mail"}


def _normalize_phone(raw: str) -> str:
    """Normalize phone number to E.164 format."""
    phone = re.sub(r"[^\d+]", "", raw)
    if not phone.startswith("+"):
        if phone.startswith("34") and len(phone) >= 11:
            phone = "+" + phone
        elif len(phone) == 9:
            phone = "+34" + phone
        else:
            phone = "+" + phone
    return phone


def _build_column_map(fieldnames: list[str]) -> dict[str, str]:
    """Map CSV column names to canonical names (case-insensitive)."""
    col_map: dict[str, str] = {}
    for f in fieldnames:
        fl = f.strip().lower()
        if fl in _PHONE_ALIASES:
            col_map["phone"] = f
        elif fl in _NAME_ALIASES:
            col_map["name"] = f
        elif fl in _EMAIL_ALIASES:
            col_map["email"] = f
    return col_map


async def import_contacts_from_csv(
    db: AsyncSession,
    tenant_id: UUID,
    file_content: bytes,
) -> dict[str, int]:
    """Import contacts from CSV bytes. Returns {created, skipped, errors, total_rows}."""
    try:
        text_content = file_content.decode("utf-8-sig")
    except UnicodeDecodeError:
        text_content = file_content.decode("latin-1")

    reader = csv.DictReader(io.StringIO(text_content))
    if not reader.fieldnames:
        raise ValueError("CSV has no headers")

    col_map = _build_column_map(list(reader.fieldnames))
    if "phone" not in col_map:
        raise ValueError("CSV must have a 'phone' or 'telefono' column")

    contact_repo = WAContactRepository(db)
    created = skipped = errors = 0

    for row in reader:
        raw_phone = (row.get(col_map["phone"]) or "").strip()
        if not raw_phone:
            errors += 1
            continue

        phone = _normalize_phone(raw_phone)

        # Check duplicate
        existing = await db.execute(
            text("""
            SELECT 1 FROM wa_contacts
            WHERE tenant_id = CAST(:tid AS UUID) AND phone_e164 = :phone
            LIMIT 1
        """),
            {"tid": str(tenant_id), "phone": phone},
        )
        if existing.fetchone():
            skipped += 1
            continue

        name = (row.get(col_map.get("name", ""), "") or "").strip() or None
        email = (row.get(col_map.get("email", ""), "") or "").strip() or None

        await contact_repo.create(
            {
                "tenant_id": tenant_id,
                "phone_e164": phone,
                "display_name": name,
                "email": email,
                "source": "csv_import",
                "opt_in_status": "unknown",
            }
        )
        created += 1

    await db.commit()
    return {
        "created": created,
        "skipped": skipped,
        "errors": errors,
        "total_rows": created + skipped + errors,
    }


async def export_contacts_csv(
    db: AsyncSession,
    tenant_id: UUID,
) -> str:
    """Export contacts as CSV string."""
    contact_repo = WAContactRepository(db)
    contacts = await contact_repo.list(filters=[])

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        ["phone_e164", "display_name", "email", "source", "opt_in_status", "created_at"]
    )
    for c in contacts:
        if hasattr(c, "tenant_id") and str(c.tenant_id) != str(tenant_id):
            continue
        writer.writerow(
            [
                c.phone_e164,
                c.display_name or "",
                c.email or "",
                c.source or "",
                c.opt_in_status or "",
                str(c.created_at) if c.created_at else "",
            ]
        )
    return output.getvalue()
