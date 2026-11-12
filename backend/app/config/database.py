"""Database configuration with async SQLAlchemy."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config.settings import settings

# Create async engine
engine: AsyncEngine = create_async_engine(
    settings.database_url,
    pool_size=settings.postgres_pool_size,
    max_overflow=settings.postgres_max_overflow,
    pool_pre_ping=True,
    pool_recycle=1800,
    pool_timeout=30,
    echo=settings.debug,
    connect_args={"ssl": False},
)

# Create async session factory
async_session_maker = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting async database sessions."""
    async with async_session_maker() as session:
        try:
            yield session
        except (SQLAlchemyError, RuntimeError, ValueError):
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_session_context() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for async database sessions."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except (SQLAlchemyError, RuntimeError, ValueError):
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database connection and verify connectivity."""
    async with engine.begin() as conn:
        # Test connection
        await conn.execute(text("SELECT 1"))


async def close_db() -> None:
    """Close database connections."""
    await engine.dispose()


async def set_session_context(
    session: AsyncSession,
    kms_key: str | None = None,
    hmac_key: str | None = None,
    user_id: str | None = None,
) -> None:
    """Set PostgreSQL session variables for CapsuleCorp functions.

    This configures the session with the necessary keys and context
    for the database functions that require app.kms_master_key,
    app.audit_hmac_key, etc.
    """
    if kms_key or settings.kms_master_key:
        await session.execute(
            text("SET app.kms_master_key = :key"),
            {"key": kms_key or settings.kms_master_key},
        )

    if hmac_key or settings.audit_hmac_key:
        await session.execute(
            text("SET app.audit_hmac_key = :key"),
            {"key": hmac_key or settings.audit_hmac_key},
        )

    if user_id:
        await session.execute(
            text("SET app.current_user_id = :user_id"),
            {"user_id": user_id},
        )


async def call_db_function(
    session: AsyncSession,
    function_name: str,
    *args: Any,
) -> Any:
    """Call a PostgreSQL function and return the result.

    Args:
        session: AsyncSession instance
        function_name: Name of the PostgreSQL function
        *args: Arguments to pass to the function

    Returns:
        The result from the function call
    """
    # Build parameter placeholders
    placeholders = ", ".join(f":p{i}" for i in range(len(args)))
    params = {f"p{i}": arg for i, arg in enumerate(args)}

    query = text(f"SELECT {function_name}({placeholders})")
    result = await session.execute(query, params)
    return result.scalar()


async def call_db_function_json(
    session: AsyncSession,
    function_name: str,
    *args: Any,
) -> dict[str, Any] | list[Any] | None:
    """Call a PostgreSQL function that returns JSON/JSONB."""
    result = await call_db_function(session, function_name, *args)
    return result
