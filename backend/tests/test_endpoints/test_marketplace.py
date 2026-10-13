"""Tests for marketplace endpoints (public, no auth required)."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from httpx import ASGITransport, AsyncClient


async def test_list_modules_no_auth_required():
    """GET /api/v1/marketplace/modules is public — no 401."""
    from app.main import app

    # Create a temp marketplace file
    modules = [
        {"slug": "whatsapp", "name": "WhatsApp", "available": True},
        {"slug": "crm", "name": "CRM", "available": False},
    ]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(modules, f)
        temp_path = f.name

    with patch("app.api.v1.endpoints.marketplace.get_settings") as mock_settings:
        mock_settings.return_value.marketplace_file_path = temp_path
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            response = await c.get("/api/v1/marketplace/modules")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2
    assert data[0]["slug"] == "whatsapp"

    # Cleanup
    Path(temp_path).unlink(missing_ok=True)


async def test_marketplace_missing_file():
    """GET /api/v1/marketplace/modules returns 503 when catalog file missing."""
    from app.main import app

    with patch("app.api.v1.endpoints.marketplace.get_settings") as mock_settings:
        mock_settings.return_value.marketplace_file_path = "/nonexistent/path.json"
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            response = await c.get("/api/v1/marketplace/modules")

    assert response.status_code == 503
