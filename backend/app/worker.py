"""ARQ worker configuration.

This module defines the ARQ worker that runs as a separate process.
It initializes its own DB connection pool and HTTP clients.

Run with: python -m arq app.worker.WorkerSettings
"""

import logging

from arq import cron
from arq.connections import RedisSettings

from app.config.settings import settings
from app.tasks.legacy import (
    breach_detection,
    cleanup_expired_sessions,
    recording_cleanup,
    sla_check,
    whatsapp_campaign_scheduler,
)

logger = logging.getLogger(__name__)


async def startup(ctx: dict) -> None:
    """Worker startup: initialize DB engine and HTTP clients."""
    from app.config.database import async_session_maker, init_db
    from app.core import http_clients

    await init_db()
    await http_clients.startup()

    ctx["session_maker"] = async_session_maker
    logger.info("ARQ worker started")


async def shutdown(ctx: dict) -> None:
    """Worker shutdown: close DB and HTTP connections."""
    from app.config.database import close_db
    from app.core import http_clients

    await http_clients.shutdown()
    await close_db()
    logger.info("ARQ worker stopped")


class WorkerSettings:
    """ARQ worker settings."""

    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    on_startup = startup
    on_shutdown = shutdown
    max_jobs = 10
    job_timeout = 600  # 10 minutes default
    keep_result = 3600  # 1 hour
    health_check_interval = 30  # seconds

    functions = []

    cron_jobs = [
        # === Legacy tasks (migrated from main.py asyncio loops) ===
        cron(recording_cleanup, hour=4, minute=0),  # Daily 04:00 UTC
        cron(
            breach_detection, minute={0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55}
        ),  # Every 5 min
        cron(whatsapp_campaign_scheduler, minute=None),  # Every minute
        cron(sla_check, minute=None),  # Every minute

    # === Session / token housekeeping ===
        cron(cleanup_expired_sessions, hour={0, 6, 12, 18}, minute=30),  # Every 6h at :30
    ]
