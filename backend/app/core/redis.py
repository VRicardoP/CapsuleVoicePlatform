"""Redis connection pool singleton.

Managed by the FastAPI lifespan in main.py.
Follows the same pattern as http_clients.py.
"""

import logging

import redis.asyncio as aioredis

from app.config.settings import settings

logger = logging.getLogger(__name__)

# Module-level singleton (same pattern as http_clients.py)
pool: aioredis.Redis | None = None


async def startup() -> None:
    """Initialize Redis connection pool. Called from main.py lifespan."""
    global pool
    pool = aioredis.from_url(
        settings.redis_url,
        decode_responses=True,
        max_connections=20,
    )
    # Verify connectivity
    await pool.ping()
    logger.info("Redis pool initialized: %s", settings.redis_url)


async def shutdown() -> None:
    """Close Redis connection pool. Called from main.py lifespan."""
    global pool
    if pool:
        await pool.aclose()
        pool = None
        logger.info("Redis pool closed")


def get_pool() -> aioredis.Redis:
    """Get the Redis pool. Raises if not initialized."""
    if pool is None:
        raise RuntimeError("Redis pool not initialized. Call startup() first.")
    return pool
