"""Alembic environment configuration for SferaAI."""

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

import app.models  # noqa: F401 — registers all ORM models on Base.metadata
from alembic import context
from app.config.settings import settings
from app.models.base import Base

# Alembic Config object
config = context.config

# Set sqlalchemy.url from application settings
config.set_main_option("sqlalchemy.url", settings.database_url)

# Setup Python logging from ini file
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for autogenerate
target_metadata = Base.metadata

# Tables managed by raw SQL (not ORM) — exclude from autogenerate
EXCLUDED_TABLES = {
    "secure_keys",
    "secure_sessions",
    "encryption_keys",
    "user_preferences",
    "client_error_logs",
    "api_keys",
    "api_key_usage_log",
    "client_integrations",
}


def include_name(name: str, type_: str, parent_names: dict) -> bool:  # noqa: ARG001
    """Filter callback: exclude non-ORM tables from autogeneration."""
    if type_ == "table":
        return name not in EXCLUDED_TABLES
    return True


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (generates SQL without DB connection)."""
    url = config.get_main_option("sqlalchemy.url")
    # For offline mode, use sync URL if available
    offline_url = url
    if offline_url and offline_url.startswith("postgresql+asyncpg://"):
        offline_url = offline_url.replace("postgresql+asyncpg://", "postgresql://", 1)

    context.configure(
        url=offline_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_name=include_name,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_name=include_name,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode with async engine."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
