"""Tests for dashboard endpoints."""

from unittest.mock import AsyncMock, MagicMock


async def test_dashboard_requires_auth(unauth_client):
    """GET /api/v1/dashboard without token returns 401."""
    response = await unauth_client.get("/api/v1/dashboard")
    assert response.status_code == 401


async def test_kpi_requires_auth(unauth_client):
    """GET /api/v1/dashboard/kpi without token returns 401."""
    response = await unauth_client.get("/api/v1/dashboard/kpi")
    assert response.status_code == 401


async def test_dashboard_returns_data(client, test_app):
    """GET /api/v1/dashboard with auth returns 200."""

    # Build a mock execute that returns proper Row-like objects
    def make_mock_result():
        mock_result = MagicMock()
        # fetchone returns a Row-like object with _mapping
        mock_row = MagicMock()
        mock_row._mapping = {
            "total_calls": 0,
            "avg_duration_seconds": 0,
            "total_minutes": 0,
            "success_rate": 0,
            "prev_total_calls": 0,
            "prev_avg_duration_seconds": 0,
            "prev_total_minutes": 0,
            "prev_success_rate": 0,
        }
        mock_result.fetchone.return_value = mock_row
        mock_result.fetchall.return_value = []
        mock_result.scalar.return_value = 0
        mock_result.scalars.return_value = MagicMock(all=MagicMock(return_value=[]))
        mock_result.mappings.return_value = MagicMock(all=MagicMock(return_value=[]))
        return mock_result

    # Override the mock session's execute to return proper results
    from app.core.dependencies import get_db_with_rls

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(side_effect=lambda *a, **kw: make_mock_result())

    async def override():
        return mock_session

    test_app.dependency_overrides[get_db_with_rls] = override

    response = await client.get("/api/v1/dashboard")
    assert response.status_code == 200


async def test_gdpr_metrics_requires_auth(unauth_client):
    """GET /api/v1/dashboard/gdpr-metrics without token returns 401."""
    response = await unauth_client.get("/api/v1/dashboard/gdpr-metrics")
    assert response.status_code == 401


async def test_trends_requires_auth(unauth_client):
    """GET /api/v1/dashboard/trends without token returns 401."""
    response = await unauth_client.get("/api/v1/dashboard/trends")
    assert response.status_code == 401
