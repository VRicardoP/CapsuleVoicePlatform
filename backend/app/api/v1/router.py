"""
Main API v1 router.
Aggregates all endpoint routers.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    ai_agent,
    api_keys,
    auth,
    calls,
    calls_export,
    calls_recordings,
    contact,
    dashboard,
    gdpr,
    marketplace,
    pbx,
    permissions,
    ultravox,
    users,
    voice_quota,
    whatsapp,
)

api_router = APIRouter()

# Authentication endpoints (public + JWT)
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Authentication"],
)

# API Keys management (Admin only, same prefix for backward compat)
api_router.include_router(
    api_keys.router,
    prefix="/auth",
    tags=["API Keys"],
)

# User management (JWT required)
api_router.include_router(
    users.router,
    prefix="/users",
    tags=["Users"],
)

# Dashboard endpoints (JWT required)
api_router.include_router(
    dashboard.router,
    prefix="/dashboard",
    tags=["Dashboard"],
)

# Call export (XLSX) — registrar ANTES que calls.router para que la ruta
# /export.xlsx no la atrape el `/{call_id:UUID}` de calls.router (HTTP 422
# uuid_parsing al intentar parsear "export.xlsx" como UUID).
api_router.include_router(
    calls_export.router,
    prefix="/calls",
    tags=["Calls"],
)

# Call management (JWT required)
api_router.include_router(
    calls.router,
    prefix="/calls",
    tags=["Calls"],
)

# Call recordings, transcripts, human review, lookups
api_router.include_router(
    calls_recordings.router,
    prefix="/calls",
    tags=["Calls"],
)

# GDPR rights endpoints (JWT required)
api_router.include_router(
    gdpr.router,
    prefix="/gdpr",
    tags=["GDPR Rights"],
)

# AI Agent endpoints (API Key required - sfera_ai_agent)
api_router.include_router(
    ai_agent.router,
    prefix="/ai",
    tags=["AI Agent"],
)

# PBX/CTI endpoints (API Key required - sfera_pbx)
api_router.include_router(
    pbx.router,
    prefix="/pbx",
    tags=["PBX/CTI"],
)

# Contact form endpoints (JWT required)
api_router.include_router(
    contact.router,
    prefix="/contact",
    tags=["Contact"],
)

# Ultravox AI integration endpoints (API Key required - ultravox_agent)
api_router.include_router(
    ultravox.router,
    prefix="/ultravox",
    tags=["Ultravox AI"],
)

# WhatsApp Business (Webhook: public + HMAC, REST: JWT required)
api_router.include_router(
    whatsapp.router,
    prefix="/whatsapp",
    tags=["WhatsApp"],
)





# Permission management (JWT required)
api_router.include_router(
    permissions.router,
    prefix="/permissions",
    tags=["Permissions"],
)

# User permission sub-routes (mounted under /users for REST conventions)
api_router.include_router(
    permissions.user_permissions_router,
    prefix="/users",
    tags=["Permissions"],
)

# Marketplace catalog (public - no auth required)
api_router.include_router(
    marketplace.router,
    prefix="/marketplace",
    tags=["Marketplace"],
)



# Voice quota — visibilidad de cuota de voz por tenant (JWT required)
api_router.include_router(
    voice_quota.router,
    prefix="/organizations",
    tags=["Voice Quota"],
)
