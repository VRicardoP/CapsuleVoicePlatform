"""WhatsApp admin, dashboard, widget, analytics, and audit routes."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.core.dependencies import (
    get_current_user_id,
    get_db,
    require_feature,
    require_permission,
    require_wa_admin,
)
from app.repositories.whatsapp_admin_repository import WhatsAppAdminRepository
from app.repositories.whatsapp_repository import (
    WATenantSettingsRepository,
    WAWidgetConfigRepository,
)
from app.schemas.whatsapp import (
    WAAutoAssignSettingsRequest,
    WAWidgetConfigResponse,
    WAWidgetConfigUpdateRequest,
)

from . import _helpers
from ._helpers import _get_tenant_id, _get_tenant_settings

router = APIRouter()
logger = logging.getLogger(__name__)

_wa_analytics = [
    Depends(require_feature("whatsapp")),
    Depends(require_permission("whatsapp.analytics.view")),
]
_wa_settings = [
    Depends(require_feature("whatsapp")),
    Depends(require_permission("whatsapp.settings.manage")),
]


# =============================================================================
# Agent Auto-Assignment (Round-Robin)
# =============================================================================


@router.get("/auto-assign/settings", dependencies=_wa_settings)
async def get_auto_assign_settings(
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Get auto-assignment settings (persisted in DB)."""
    tenant_id = await _get_tenant_id(db, user_id=current_user_id)
    ts = await _get_tenant_settings(db, tenant_id)
    config = ts.auto_assign_config or {}
    return {
        "enabled": config.get("enabled", False),
        "agent_ids": config.get("agent_ids", []),
    }


@router.post("/auto-assign/settings", status_code=204, dependencies=_wa_settings)
async def set_auto_assign_settings(
    body: WAAutoAssignSettingsRequest,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    _role: Annotated[str, Depends(require_wa_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Configure auto-assignment (round-robin, persisted in DB)."""
    tenant_id = await _get_tenant_id(db, user_id=current_user_id)
    ts = await _get_tenant_settings(db, tenant_id)
    ts.auto_assign_config = {
        "enabled": body.enabled,
        "agent_ids": [str(a) for a in body.agent_ids],
    }
    _helpers._auto_assign_index = 0
    await db.commit()


# =============================================================================
# Enhanced Analytics
# =============================================================================


@router.get("/analytics/messaging", dependencies=_wa_analytics)
async def get_messaging_analytics(
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
    days: int = Query(30, ge=1, le=365),
) -> dict:
    """Get messaging analytics for the tenant."""
    tenant_id = await _get_tenant_id(db, user_id=current_user_id)
    repo = WhatsAppAdminRepository(db)

    messages = await repo.get_messaging_summary(tenant_id, days)
    daily = await repo.get_daily_message_counts(tenant_id, days)
    campaigns = await repo.get_campaign_performance(tenant_id, days)

    return {
        "period_days": days,
        "messages": messages,
        "daily": daily,
        "campaigns": campaigns,
    }


# =============================================================================
# Widget Web
# =============================================================================


@router.get("/widget/config", response_model=WAWidgetConfigResponse, dependencies=_wa_settings)
async def get_widget_config(
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WAWidgetConfigResponse:
    """Get web widget configuration."""
    tenant_id = await _get_tenant_id(db, user_id=current_user_id)
    repo = WAWidgetConfigRepository(db)
    config = await repo.get_by_tenant(tenant_id)
    if not config:
        config = await repo.create({"tenant_id": tenant_id})
        await db.commit()
    return WAWidgetConfigResponse.model_validate(config)


@router.put("/widget/config", response_model=WAWidgetConfigResponse, dependencies=_wa_settings)
async def update_widget_config(
    body: WAWidgetConfigUpdateRequest,
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    _role: Annotated[str, Depends(require_wa_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WAWidgetConfigResponse:
    """Update web widget configuration."""
    tenant_id = await _get_tenant_id(db, user_id=current_user_id)
    repo = WAWidgetConfigRepository(db)
    updates = body.model_dump(exclude_unset=True)
    config = await repo.upsert(tenant_id, updates)
    await db.commit()
    return WAWidgetConfigResponse.model_validate(config)


@router.get("/widget/embed", dependencies=_wa_settings)
async def get_widget_embed_code(
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Generate embed code snippet for the web widget."""
    tenant_id = await _get_tenant_id(db, user_id=current_user_id)
    repo = WAWidgetConfigRepository(db)
    config = await repo.get_by_tenant(tenant_id)
    if not config:
        raise HTTPException(status_code=404, detail="Widget not configured")

    # Widget JS is served from the dashboard's public directory
    base_url = settings.cors_origins[0] if settings.cors_origins else "https://yourdomain.com"
    phone_attr = ""
    if hasattr(config, "display_phone") and config.display_phone:
        phone_attr = f' data-phone="{config.display_phone}"'
    snippet = (
        f'<script src="{base_url}/widget.js" '
        f'data-tenant="{tenant_id}" '
        f'data-color="{config.primary_color}" '
        f'data-position="{config.position}" '
        f'data-welcome="{config.welcome_message}" '
        f'data-name="{config.business_name or ""}"'
        f"{phone_attr}></script>"
    )
    return {"embed_code": snippet, "tenant_id": str(tenant_id)}


# =============================================================================
# Dashboard Overview (WA-specific)
# =============================================================================


@router.get("/dashboard/overview", dependencies=_wa_analytics)
async def get_wa_dashboard_overview(
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Get WhatsApp-specific dashboard overview."""
    tenant_id = await _get_tenant_id(db, user_id=current_user_id)
    repo = WhatsAppAdminRepository(db)

    conversations = await repo.get_conversations_summary(tenant_id)
    messages_today = await repo.get_messages_today(tenant_id)
    contacts_total = await repo.get_contacts_total(tenant_id)
    active_campaigns = await repo.get_active_campaigns_count(tenant_id)
    sla_breaches = await repo.get_unresolved_sla_breaches(tenant_id)
    avg_resp = await repo.get_avg_response_minutes(tenant_id)

    return {
        "conversations": conversations,
        "messages_today": messages_today,
        "contacts_total": contacts_total,
        "active_campaigns": active_campaigns,
        "sla_breaches_unresolved": sla_breaches,
        "avg_response_minutes": round(avg_resp, 1) if avg_resp else None,
    }


# =============================================================================
# Audit Log (WA-specific events)
# =============================================================================


@router.get("/audit/logs", dependencies=_wa_analytics)
async def list_wa_audit_logs(
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
    event_type: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    """List WhatsApp event audit trail."""
    tenant_id = await _get_tenant_id(db, user_id=current_user_id)

    base_where = "WHERE tenant_id = CAST(:tid AS UUID)"
    params: dict = {"tid": str(tenant_id), "skip": skip, "limit": limit}

    if event_type:
        base_where += " AND event_type = :etype"
        params["etype"] = event_type

    count_result = await db.execute(
        text(f"SELECT COUNT(*) FROM wa_events {base_where}"),
        params,
    )
    total = count_result.scalar_one()

    result = await db.execute(
        text(f"""
        SELECT id, event_type, payload_raw, created_at, provider_event_id
        FROM wa_events
        {base_where}
        ORDER BY created_at DESC
        OFFSET :skip LIMIT :limit
    """),
        params,
    )

    items = [
        {
            "id": str(r.id),
            "event_type": r.event_type,
            "payload": r.payload_raw,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "provider_event_id": r.provider_event_id,
        }
        for r in result.fetchall()
    ]

    return {"items": items, "total": total}


# =============================================================================
# Admin BSP (Business Service Provider overview)
# =============================================================================


@router.get("/admin/overview", dependencies=_wa_settings)
async def get_admin_bsp_overview(
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    _role: Annotated[str, Depends(require_wa_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Get BSP admin overview — tenant settings + usage stats."""
    tenant_id = await _get_tenant_id(db, user_id=current_user_id)

    # Tenant settings
    ts_repo = WATenantSettingsRepository(db)
    ts = await ts_repo.get_by_tenant(tenant_id)

    # Table counts for overview
    tables = [
        ("wa_contacts", "contacts"),
        ("wa_conversations", "conversations"),
        ("wa_messages", "messages"),
        ("wa_templates", "templates"),
        ("wa_campaigns", "campaigns"),
        ("wa_flows", "flows"),
        ("wa_macros", "macros"),
        ("wa_surveys", "surveys"),
        ("wa_integrations", "integrations"),
    ]
    counts = {}
    for table, key in tables:
        r = await db.execute(
            text(f"SELECT COUNT(*) FROM {table} WHERE tenant_id = CAST(:tid AS UUID)"),
            {"tid": str(tenant_id)},
        )
        counts[key] = r.scalar_one()

    return {
        "tenant_id": str(tenant_id),
        "settings": {
            "phone_number_id": ts.phone_number_id if ts else None,
            "business_account_id": ts.business_account_id if ts else None,
            "display_phone": ts.display_phone if ts else None,
            "webhook_verify_token": ts.webhook_verify_token if ts else None,
            "is_configured": ts is not None and ts.phone_number_id is not None,
        },
        "usage": counts,
    }
