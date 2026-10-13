"""Integration tests for refactored services with real DB.

Verifies that mixin-based services execute SQL correctly against
real PostgreSQL. These tests catch:
- Missing imports in mixin files (e.g., DAYS_EN)
- Wrong column names in SQL queries (e.g., completed_at vs responded_at)
- Mixin inheritance issues with self.db
- Repository method execution against real schema

Requires: PostgreSQL on localhost:5433 with sferaai.sql schema loaded.
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import text

# =============================================================================
# DashboardQueryService — EVERY method must execute without NameError/SQL error
# =============================================================================


@pytest.mark.asyncio
async def test_dashboard_service_init(db_session):
    """DashboardQueryService initializes correctly."""
    from app.services.dashboard_query_service import DashboardQueryService

    service = DashboardQueryService(db_session)
    assert service.db is db_session


@pytest.mark.asyncio
async def test_dashboard_get_call_metrics(db_session):
    """get_call_metrics executes SQL without error."""
    from app.services.dashboard_query_service import DashboardQueryService

    service = DashboardQueryService(db_session)
    result = await service.get_call_metrics()
    assert isinstance(result, dict)


@pytest.mark.asyncio
async def test_dashboard_get_weekly_calls_data(db_session):
    """get_weekly_calls_data executes SQL without error."""
    from app.services.dashboard_query_service import DashboardQueryService

    service = DashboardQueryService(db_session)
    result = await service.get_weekly_calls_data()
    assert isinstance(result, list)


@pytest.mark.asyncio
async def test_dashboard_get_status_distribution(db_session):
    """get_status_distribution executes SQL without error."""
    from app.services.dashboard_query_service import DashboardQueryService

    service = DashboardQueryService(db_session)
    result = await service.get_status_distribution()
    assert isinstance(result, list)


@pytest.mark.asyncio
async def test_dashboard_get_recent_calls(db_session):
    """get_recent_calls executes SQL without error."""
    from app.services.dashboard_query_service import DashboardQueryService

    service = DashboardQueryService(db_session)
    result = await service.get_recent_calls(limit=5)
    assert isinstance(result, list)


@pytest.mark.asyncio
async def test_dashboard_get_performance_data(db_session):
    """get_performance_data executes SQL without error."""
    from app.services.dashboard_query_service import DashboardQueryService

    service = DashboardQueryService(db_session)
    result = await service.get_performance_data()
    assert isinstance(result, list)


@pytest.mark.asyncio
async def test_dashboard_get_heatmap_data(db_session):
    """get_heatmap_data executes SQL without error.

    THIS TEST would have caught the DAYS_EN NameError.
    """
    from app.services.dashboard_query_service import DashboardQueryService

    service = DashboardQueryService(db_session)
    result = await service.get_heatmap_data()
    assert isinstance(result, list)


@pytest.mark.asyncio
async def test_dashboard_get_conversion_data(db_session):
    """get_conversion_data executes SQL without error."""
    from app.services.dashboard_query_service import DashboardQueryService

    service = DashboardQueryService(db_session)
    result = await service.get_conversion_data()
    assert isinstance(result, list)


@pytest.mark.asyncio
async def test_dashboard_get_campaigns_data(db_session):
    """get_campaigns_data executes SQL without error."""
    from app.services.dashboard_query_service import DashboardQueryService

    service = DashboardQueryService(db_session)
    result = await service.get_campaigns_data()
    assert isinstance(result, list)


@pytest.mark.asyncio
async def test_dashboard_get_kpi_metrics(db_session):
    """get_kpi_metrics executes SQL without error."""
    from app.services.dashboard_query_service import DashboardQueryService

    service = DashboardQueryService(db_session)
    result = await service.get_kpi_metrics(days=30)
    assert result is not None


@pytest.mark.asyncio
async def test_dashboard_get_trends(db_session):
    """get_trends executes SQL without error."""
    from app.services.dashboard_query_service import DashboardQueryService

    service = DashboardQueryService(db_session)
    result = await service.get_trends(days=7)
    assert hasattr(result, "calls_trend")


@pytest.mark.asyncio
async def test_dashboard_get_call_stats_by_period(db_session):
    """get_call_stats_by_period executes SQL without error."""
    from app.services.dashboard_query_service import DashboardQueryService

    service = DashboardQueryService(db_session)
    result = await service.get_call_stats_by_period()
    assert hasattr(result, "currentYear")


@pytest.mark.asyncio
async def test_dashboard_get_gdpr_metrics(db_session):
    """get_gdpr_metrics executes SQL without error."""
    from app.services.dashboard_query_service import DashboardQueryService

    service = DashboardQueryService(db_session)
    result = await service.get_gdpr_metrics()
    assert result is not None


@pytest.mark.asyncio
async def test_dashboard_get_gdpr_summary(db_session):
    """get_gdpr_summary executes SQL without error.

    THIS TEST would have caught the completed_at/consent_type column errors.
    """
    from app.services.dashboard_query_service import DashboardQueryService

    service = DashboardQueryService(db_session)
    result = await service.get_gdpr_summary()
    assert result is not None


@pytest.mark.asyncio
async def test_dashboard_get_gdpr_trends(db_session):
    """get_gdpr_trends executes SQL without error."""
    from app.services.dashboard_query_service import DashboardQueryService

    service = DashboardQueryService(db_session)
    result = await service.get_gdpr_trends(days=7)
    assert result is not None


@pytest.mark.asyncio
async def test_dashboard_get_compliance_gaps(db_session):
    """get_compliance_gaps executes SQL without error."""
    from app.services.dashboard_query_service import DashboardQueryService

    service = DashboardQueryService(db_session)
    result = await service.get_compliance_gaps()
    assert isinstance(result, dict)


@pytest.mark.asyncio
async def test_dashboard_get_alerts(db_session):
    """get_alerts executes SQL without error."""
    from app.services.dashboard_query_service import DashboardQueryService

    service = DashboardQueryService(db_session)
    result = await service.get_alerts()
    assert isinstance(result, dict)


# =============================================================================
# Repositories (P1 refactoring)
# =============================================================================


@pytest.mark.asyncio
async def test_user_preferences_repository(db_session):
    """UserPreferencesRepository upsert + get cycle."""
    from app.repositories.user_repository import UserPreferencesRepository

    repo = UserPreferencesRepository(db_session)
    result = await db_session.execute(text("SELECT id FROM users LIMIT 1"))
    row = result.fetchone()
    if not row:
        pytest.skip("No users in test DB")

    await repo.upsert_preferences(row.id, ["calls", "whatsapp"], "dark")
    await db_session.flush()
    prefs = await repo.get_preferences(row.id)
    assert prefs is not None
    assert prefs["theme"] == "dark"


@pytest.mark.asyncio
async def test_organization_repository(db_session):
    """OrganizationRepository.get_tenant_features returns dict."""
    from app.repositories.user_repository import OrganizationRepository

    repo = OrganizationRepository(db_session)
    features = await repo.get_tenant_features()
    assert isinstance(features, dict)


@pytest.mark.asyncio
async def test_client_error_repository(db_session):
    """ClientErrorRepository create + list cycle."""
    from app.repositories.client_error_repository import ClientErrorRepository

    repo = ClientErrorRepository(db_session)

    error_id = await repo.create(
        api_key_id=None,
        client_version="1.0.0-test",
        error_type="test_error",
        error_message="Integration test",
        environment="test",
        error_timestamp=datetime.now(UTC),
    )
    await db_session.flush()
    assert error_id is not None

    items, total = await repo.list_errors(days=1, error_type="test_error")
    assert total >= 1


@pytest.mark.asyncio
async def test_api_key_repository_list(db_session):
    """ApiKeyRepository.list_api_keys returns list."""
    from app.repositories.api_key_repository import ApiKeyRepository

    repo = ApiKeyRepository(db_session)
    items = await repo.list_api_keys(include_revoked=True)
    assert isinstance(items, list)


@pytest.mark.asyncio
async def test_call_detail_service_not_found(db_session):
    """get_call_detail raises ValueError for non-existent call."""
    from app.services.call_detail_service import get_call_detail

    with pytest.raises(ValueError, match="Call not found"):
        await get_call_detail(uuid4(), db_session)


# =============================================================================
# Smoke test
# =============================================================================


@pytest.mark.asyncio
async def test_app_routes_registered():
    """FastAPI app has all expected route prefixes."""
    from app.main import app

    route_paths = [r.path for r in app.routes if hasattr(r, "path")]

    for prefix in [
        "/api/v1/auth/",
        "/api/v1/users/",
        "/api/v1/dashboard",
        "/api/v1/calls",
        "/api/v1/gdpr/",
        "/api/v1/ultravox/",
        "/api/v1/whatsapp/",
        "/api/v1/marketplace/",
    ]:
        assert any(prefix in p for p in route_paths), f"Missing routes for {prefix}"
