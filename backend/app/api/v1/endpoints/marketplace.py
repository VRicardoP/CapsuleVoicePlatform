"""
Marketplace catalog endpoint.
Public endpoint — no JWT required (catalog is not sensitive data).
Reads from a shared JSON file (mounted as volume), not from the database.
"""

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.config.settings import get_settings

router = APIRouter()


@router.get("/modules")
async def list_modules():
    """Return all marketplace modules from the shared JSON catalog."""
    path = Path(get_settings().marketplace_file_path)
    if not path.exists():
        raise HTTPException(503, "Marketplace catalog not available")
    return json.loads(path.read_text(encoding="utf-8"))
