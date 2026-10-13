"""Unit tests for refactored services (no DB required).

Verifies that mixin-based services have correct structure,
static methods work, and imports don't circular-reference.
"""

import pytest


@pytest.mark.asyncio
async def test_dashboard_service_has_all_methods():
    """DashboardQueryService inherits all mixin methods."""
    from app.services.dashboard_query_service import DashboardQueryService

    expected_methods = [
        "get_call_metrics",
        "get_weekly_calls_data",
        "get_status_distribution",
        "get_recent_calls",
        "get_performance_data",
        "get_heatmap_data",
        "get_conversion_data",
        "get_campaigns_data",
        "get_kpi_metrics",
        "get_gdpr_metrics",
        "get_gdpr_summary",
        "get_gdpr_trends",
        "get_compliance_gaps",
        "get_alerts",
        "get_trends",
        "get_call_stats_by_period",
        "get_dashboard_metrics_complete",
    ]

    for method in expected_methods:
        assert hasattr(DashboardQueryService, method), f"Missing method: {method}"
        assert callable(getattr(DashboardQueryService, method))


@pytest.mark.asyncio
async def test_ultravox_service_has_all_methods():
    """UltravoxCallService inherits all mixin methods."""
    from app.services.ultravox_call_service import UltravoxCallService

    expected_methods = [
        "validate_signature",
        "map_disconnection_to_status",
        "map_sentiment",
        "extract_phone_from_medium",
        "resolve_ultravox_call_id",
        "get_function_arg",
        "get_most_recent_active_call",
        "get_or_create_call",
        "save_transcript_segments",
        "save_tool_call_actions",
        "forward_to_n8n",
        "handle_call_ended",
        "generate_zadarma_signature",
        "fetch_zadarma_caller_number",
        "cleanup_zadarma_cache",
        "store_zadarma_caller",
        "lookup_zadarma_caller",
        "fetch_call_details",
        "fetch_messages",
        "process_recording_background",
    ]

    for method in expected_methods:
        assert hasattr(UltravoxCallService, method), f"Missing method: {method}"


@pytest.mark.asyncio
async def test_ultravox_map_disconnection():
    """map_disconnection_to_status maps correctly."""
    from app.services.ultravox_call_service import UltravoxCallService

    assert UltravoxCallService.map_disconnection_to_status("hangup") == "completed"
    assert UltravoxCallService.map_disconnection_to_status("unjoined") == "abandoned"
    assert UltravoxCallService.map_disconnection_to_status(None) == "completed"


@pytest.mark.asyncio
async def test_ultravox_zadarma_cache():
    """Zadarma cache store/lookup cycle works via composed class."""
    from app.services.ultravox_call_service import ZADARMA_CALL_CACHE, UltravoxCallService

    # Clear cache first
    ZADARMA_CALL_CACHE.clear()

    UltravoxCallService.store_zadarma_caller("34911234567", "+34612345678", "test-pbx")
    result = UltravoxCallService.lookup_zadarma_caller(called_number="34911234567")
    assert result == "+34612345678"

    # Cleanup
    ZADARMA_CALL_CACHE.clear()


@pytest.mark.asyncio
async def test_ultravox_module_constants():
    """Module-level constants are accessible from the package."""
    from app.services.ultravox_call_service import (
        ZADARMA_CACHE_TTL_SECONDS,
        ZADARMA_CALL_CACHE,
    )

    assert isinstance(ZADARMA_CALL_CACHE, dict)
    assert ZADARMA_CACHE_TTL_SECONDS == 600


@pytest.mark.asyncio
async def test_app_routes_registered():
    """FastAPI app has all expected route prefixes."""
    from app.main import app

    route_paths = [r.path for r in app.routes if hasattr(r, "path")]

    expected_prefixes = [
        "/api/v1/auth/",
        "/api/v1/users/",
        "/api/v1/dashboard",
        "/api/v1/calls",
        "/api/v1/gdpr/",
        "/api/v1/ultravox/",
        "/api/v1/whatsapp/",
        "/api/v1/marketplace/",
    ]

    for prefix in expected_prefixes:
        assert any(prefix in p for p in route_paths), f"Missing routes for {prefix}"


@pytest.mark.asyncio
async def test_no_circular_imports():
    """All critical imports resolve without circular dependency."""
    from app.api.v1.router import api_router
    from app.services.dashboard_query_service import DashboardQueryService
    from app.services.ultravox_call_service import UltravoxCallService

    assert DashboardQueryService is not None
    assert UltravoxCallService is not None
    assert api_router is not None


@pytest.mark.asyncio
async def test_call_detail_service_maps():
    """call_detail_service internal maps are correct."""
    from app.services.call_detail_service import _ACTION_TYPE_MAP, _STATUS_MAP

    assert _STATUS_MAP["completed"] == "completed"
    assert _STATUS_MAP["abandoned"] == "rejected"
    assert _STATUS_MAP["initiated"] == "in_progress"
    assert _ACTION_TYPE_MAP["email"] == "email"
    assert _ACTION_TYPE_MAP["calendar"] == "calendar"


@pytest.mark.asyncio
async def test_tool_actions_tool_map():
    """tool_actions TOOL_MAP has expected tools."""
    from app.services.ultravox_call_service.tool_actions import TOOL_MAP

    assert "identificar_cliente" in TOOL_MAP
    assert "agendar_cita" in TOOL_MAP
    assert "cancelar_cita" in TOOL_MAP
    # All entries use 'other' as decision_type to satisfy the
    # ai_decisions_type_check constraint. UI action type is resolved
    # from tool_name at read-time via _TOOL_ACTION_MAP.
    assert TOOL_MAP["identificar_cliente"][0] == "other"
    assert TOOL_MAP["cancelar_cita"][0] == "other"
