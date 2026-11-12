"""FastAPI application entry point.

CapsuleCorp Backend API - GDPR/LOPDGDD/AI Act Compliant

This API implements secure data handling with:
- PostgreSQL secure_sessions for authentication (immune to GUC manipulation)
- PostgreSQL secure_keys for encryption keys (immune to GUC manipulation)
- AES-256-CBC + HMAC-SHA256 encryption for PII (via PostgreSQL functions)
- Comprehensive audit logging (RGPD Art. 30)
- Row Level Security (RLS) with FORCE RLS
"""

import logging
from contextlib import asynccontextmanager
from typing import Any

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import OperationalError, ProgrammingError

from app.config.database import close_db, init_db
from app.config.settings import settings
from app.core.bff_middleware import BFFSessionMiddleware
from app.core.middleware import (
    AuditMiddleware,
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
)

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
        if settings.log_format == "json"
        else structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

# Install request_id filter BEFORE any logs are emitted, so %(request_id)s
# never raises KeyError. The filter defaults to "-" outside request context.
#
# IMPORTANT: filters attached to a Logger only run for records emitted on that
# logger directly — they do NOT run for records propagated from child loggers.
# So we attach the filter to the HANDLER created by basicConfig, which sees
# every record reaching the root logger regardless of where it originated.
from app.core.middleware import _RequestIdFilter

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] [%(request_id)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
    level=logging.INFO,
    force=True,
)

_root = logging.getLogger()
for _h in _root.handlers:
    if not any(isinstance(f, _RequestIdFilter) for f in _h.filters):
        _h.addFilter(_RequestIdFilter())

logger = structlog.get_logger(__name__)


async def verify_database_security() -> dict[str, Any]:
    """Verify database security configuration on startup.

    Checks:
    1. secure_keys table has encryption keys configured
    2. Active encryption key exists
    3. secure_sessions table is accessible

    Returns:
        Dictionary with verification results
    """
    from sqlalchemy import text

    from app.config.database import engine

    results = {
        "secure_keys_configured": False,
        "encryption_key_active": False,
        "secure_sessions_ready": False,
        "tables_exist": False,
    }

    try:
        async with engine.connect() as conn:
            # Check if basic tables exist (users table as indicator)
            try:
                result = await conn.execute(
                    text(
                        "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'users')"
                    )
                )
                results["tables_exist"] = result.scalar() or False
            except (ProgrammingError, OperationalError):
                results["tables_exist"] = False
                logger.warning("Database schema not initialized - tables don't exist")
                return results

            # Check secure_keys (optional - may not exist in dev)
            try:
                result = await conn.execute(
                    text("SELECT COUNT(*) FROM secure_keys WHERE key_value IS NOT NULL")
                )
                key_count = result.scalar()
                results["secure_keys_configured"] = key_count > 0
            except (ProgrammingError, OperationalError):
                await conn.rollback()
                logger.warning("secure_keys table not found - security features limited")

            # Check encryption key (optional)
            try:
                result = await conn.execute(
                    text("SELECT EXISTS(SELECT 1 FROM encryption_keys WHERE is_active = true)")
                )
                results["encryption_key_active"] = result.scalar() or False
            except (ProgrammingError, OperationalError):
                await conn.rollback()
                logger.warning("encryption_keys table not found - PII encryption disabled")

            # Check secure_sessions (optional)
            try:
                result = await conn.execute(
                    text(
                        "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'secure_sessions')"
                    )
                )
                results["secure_sessions_ready"] = result.scalar() or False
            except (ProgrammingError, OperationalError):
                await conn.rollback()
                logger.warning("secure_sessions table not found")

    except (ProgrammingError, OperationalError) as e:
        logger.error("Database connection failed", error=str(e))

    return results


async def _check_alembic_version() -> None:
    """Compare alembic_version in DB against the head revision in code. Logs WARNING on drift."""
    try:
        import pathlib

        from alembic.config import Config as AlembicConfig
        from alembic.script import ScriptDirectory
        from sqlalchemy import text

        from app.config.database import engine

        ini_path = pathlib.Path(__file__).parent.parent / "alembic.ini"
        alembic_cfg = AlembicConfig(str(ini_path))
        script_dir = ScriptDirectory.from_config(alembic_cfg)
        head_revisions = set(script_dir.get_heads())

        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT version_num FROM alembic_version"))
            db_revisions = {row[0] for row in result.fetchall()}

        if db_revisions == head_revisions:
            logger.info("Alembic schema OK", revision=", ".join(head_revisions))
        else:
            missing = head_revisions - db_revisions
            extra = db_revisions - head_revisions
            logger.warning(
                "Schema drift — pending migrations. Run: alembic upgrade head",
                missing=list(missing),
                extra=list(extra),
            )
    except Exception as e:
        logger.warning("Alembic version check failed", error=str(e))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting CapsuleCorp API", version=settings.app_version)
    await init_db()
    logger.info("Database connection established")
    await _check_alembic_version()

    # create_all for dev/staging only — production should use: alembic upgrade head
    if settings.environment != "production":
        from app.config.database import engine
        from app.models import Base as ModelBase

        async with engine.begin() as conn:
            await conn.run_sync(ModelBase.metadata.create_all)
        logger.info("Database tables verified (non-production auto-create)")
    else:
        logger.info("Production mode — skipping metadata.create_all (use Alembic)")

    # Verify security configuration
    security_status = await verify_database_security()
    logger.info("Security verification", **security_status)

    if not security_status["secure_keys_configured"]:
        logger.error(
            "CRITICAL: secure_keys not configured. "
            "Run: SET app.kms_master_key='...'; SELECT initialize_secure_keys();"
        )

    if not security_status["encryption_key_active"]:
        logger.error("CRITICAL: No active encryption key. Insert a key into encryption_keys table.")

    # Initialize shared HTTP clients
    from app.core import http_clients

    await http_clients.startup()
    logger.info("HTTP clients initialized")

    # Initialize Redis pool + SSE pub/sub listener
    from app.core import redis as redis_mod

    try:
        await redis_mod.startup()
        from app.services.whatsapp_sse import sse_broadcaster as _sse

        await _sse.start_redis_listener()
        logger.info("Redis connected, SSE pub/sub active")
    except Exception as e:
        logger.warning("Redis not available — SSE pub/sub disabled, worker jobs won't run: %s", e)

    # Background tasks (recording cleanup, breach detection, campaign schedulers,
    # SLA check) run as ARQ cron jobs in the worker process.
    # See: app/tasks/legacy.py and app/worker.py
    logger.info("Background tasks delegated to ARQ worker")


    yield

    # Shutdown Redis + SSE listener
    logger.info("Shutting down CapsuleCorp API")
    try:
        from app.services.whatsapp_sse import sse_broadcaster as _sse

        await _sse.stop_redis_listener()
    except Exception:
        pass
    await redis_mod.shutdown()
    await http_clients.shutdown()
    await close_db()
    logger.info("Database connections closed")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="""
## CapsuleCorp Backend API

API para el sistema de Call Center con IA y compliance legal completo.

### Características
- Autenticación JWT con sesiones seguras
- Cumplimiento RGPD, LOPDGDD, AI Act, NIS2
- Cifrado AES-256-GCM para datos sensibles
- Auditoría inmutable con cadena HMAC
- Gestión de consentimientos granular
- Exportación de datos GDPR-compliant

### Seguridad
- Row Level Security (RLS) en todas las tablas
- Rate limiting por usuario
- Validación de entrada con Pydantic
- Logs de auditoría completos
    """,
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url="/redoc" if settings.environment != "production" else None,
    openapi_url="/openapi.json" if settings.environment != "production" else None,
    lifespan=lifespan,
)

# Middleware stack (order matters - first added = last executed)
# Security headers (outermost)
app.add_middleware(SecurityHeadersMiddleware)

# Rate limiting
app.add_middleware(RateLimitMiddleware, requests_per_minute=settings.rate_limit_requests)

# Audit logging (RGPD Art. 30)
app.add_middleware(AuditMiddleware)

# BFF session resolution + CSRF (after AuditMiddleware so request_id is bound,
# before route dependencies so request.state is populated)
app.add_middleware(BFFSessionMiddleware)

# CORS (innermost, closest to route handlers)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)


@app.get("/", tags=["Health"])
async def root() -> dict[str, Any]:
    """Root endpoint with API information."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "operational",
        "environment": settings.environment,
    }


@app.get("/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    """Health check endpoint for container orchestration."""
    return {"status": "healthy"}


@app.get("/health/ready", tags=["Health"])
async def readiness_check() -> dict[str, str]:
    """Readiness check - verifies database connectivity."""
    from sqlalchemy import text

    from app.config.database import engine

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception as e:
        logger.error("Database not ready", error=str(e))
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "error": "Database unavailable"},
        )


@app.get("/health/security", tags=["Health"])
async def security_check() -> dict[str, Any]:
    """Security configuration check.

    Verifies that security components are properly configured:
    - secure_keys table populated
    - Active encryption key exists
    - secure_sessions table ready

    Returns 503 if critical security components are missing.
    """
    status = await verify_database_security()

    if not status["secure_keys_configured"] or not status["encryption_key_active"]:
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "security": status,
                "message": "Security configuration incomplete",
            },
        )

    return {
        "status": "secure",
        "security": status,
    }


# Import and include routers
from app.api.v1.router import api_router

app.include_router(api_router, prefix="/api/v1")

# Serve template media files (publicly accessible — Meta needs to fetch these)
import os

if os.path.isdir(settings.media_dir):
    app.mount("/media", StaticFiles(directory=settings.media_dir), name="media")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        workers=settings.workers,
    )
