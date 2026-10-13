"""
Pytest configuration and fixtures for integration tests.

This module provides async database fixtures for testing backend-database integration.
Tests use the actual PostgreSQL database to verify:
- Repository CRUD operations
- PII encryption/decryption
- GDPR rights (Art. 15-22)
- Audit log integrity
- Robinson list checks
- Session management

IMPORTANT: Tests require the sferaai.sql schema to be loaded in PostgreSQL.
"""

import os
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# =============================================================================
# CONFIGURATION
# =============================================================================

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5433/sfera"
)

# KMS keys for encryption tests (must match PostgreSQL SET commands)
# These must be exactly 32 characters for AES-256
TEST_KMS_MASTER_KEY = os.getenv("TEST_KMS_MASTER_KEY", "TEST_MASTER_KEY_FOR_TESTS_32CHAR")

TEST_AUDIT_HMAC_KEY = os.getenv("TEST_AUDIT_HMAC_KEY", "TEST_AUDIT_KEY_FOR_HMAC_CHAIN__")

TEST_HASH_PEPPER = os.getenv("TEST_HASH_PEPPER", "TEST_PEPPER_V1_FOR_HMAC_FUNCTIONS")


# =============================================================================
# DATABASE FIXTURES
# =============================================================================


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Create a new database session for each test.

    Sets up the PostgreSQL session context with:
    - KMS master key for encryption
    - HMAC key for audit integrity
    - Test user ID for audit trail (creates real user)

    Rolls back all changes after each test.
    """
    # Create engine per-test to avoid event loop issues
    engine = create_async_engine(
        TEST_DATABASE_URL,
        pool_size=1,
        max_overflow=0,
        pool_pre_ping=True,
        echo=False,
    )

    factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async with factory() as session:
        # Set up PostgreSQL session context for SferaAI functions
        # Note: SET commands don't accept parameters, use literal strings
        await session.execute(text(f"SET app.kms_master_key = '{TEST_KMS_MASTER_KEY}'"))
        await session.execute(text(f"SET app.audit_hmac_key = '{TEST_AUDIT_HMAC_KEY}'"))
        await session.execute(text(f"SET app.hash_pepper = '{TEST_HASH_PEPPER}'"))
        await session.execute(text("SET app.hash_pepper_version = '1'"))

        # Override secure_keys table so get_secure_key() uses test keys
        # (get_secure_key reads from secure_keys table FIRST, ignoring GUC)
        # The session rollback at the end restores the original values.
        await session.execute(
            text(
                f"UPDATE secure_keys SET key_value = '{TEST_KMS_MASTER_KEY}' WHERE key_name = 'kms_master_key'"
            )
        )
        await session.execute(
            text(
                f"UPDATE secure_keys SET key_value = '{TEST_AUDIT_HMAC_KEY}' WHERE key_name = 'audit_hmac_key'"
            )
        )
        await session.execute(
            text(
                f"UPDATE secure_keys SET key_value = '{TEST_HASH_PEPPER}' WHERE key_name = 'hash_pepper'"
            )
        )

        # Setup encryption key for tests (must be done before any encryption operations)
        await session.execute(
            text("""
                DO $$
                BEGIN
                    -- Desactivar todas las claves existentes
                    UPDATE encryption_keys SET is_active = false WHERE is_active = true;

                    -- Crear o actualizar clave de test única
                    INSERT INTO encryption_keys (key_id, encrypted_key, is_active, kms_provider, activated_at)
                    VALUES (
                        'test_key_python_integration',
                        pgp_sym_encrypt(encode(gen_random_bytes(32), 'hex'), current_setting('app.kms_master_key'), 'cipher-algo=aes256'),
                        true,
                        'hashicorp-vault',
                        CURRENT_TIMESTAMP
                    )
                    ON CONFLICT (key_id) DO UPDATE SET
                        encrypted_key = pgp_sym_encrypt(encode(gen_random_bytes(32), 'hex'), current_setting('app.kms_master_key'), 'cipher-algo=aes256'),
                        is_active = true,
                        activated_at = CURRENT_TIMESTAMP;
                EXCEPTION WHEN OTHERS THEN
                    RAISE NOTICE 'Note: Could not setup test key: %', SQLERRM;
                END $$;
            """)
        )

        # Create a real test user for audit log FK constraint
        test_user_id = str(uuid4())
        unique_suffix = uuid4().hex[:8]
        await session.execute(
            text("""
                INSERT INTO users (id, name, email, password_hash, role)
                VALUES (:id, :name, :email, '$2b$12$test_hash', 'user')
            """),
            {
                "id": test_user_id,
                "name": f"Test Context User {unique_suffix}",
                "email": f"test_context_{unique_suffix}@example.com",
            },
        )

        # Set user context for audit log
        await session.execute(text(f"SET app.current_user_id = '{test_user_id}'"))
        await session.execute(text("SET app.client_ip = '127.0.0.1'"))

        try:
            yield session
        finally:
            # Rollback to clean up test data
            await session.rollback()
            await session.close()

    # Dispose engine to clean up connections
    await engine.dispose()


@pytest_asyncio.fixture
async def committed_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Session that commits changes (for tests that need persistent data).
    Use with caution - creates real data that must be cleaned up.
    """
    engine = create_async_engine(
        TEST_DATABASE_URL,
        pool_size=1,
        max_overflow=0,
        pool_pre_ping=True,
        echo=False,
    )

    factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async with factory() as session:
        await session.execute(text(f"SET app.kms_master_key = '{TEST_KMS_MASTER_KEY}'"))
        await session.execute(text(f"SET app.audit_hmac_key = '{TEST_AUDIT_HMAC_KEY}'"))

        # Create a real test user for audit log FK constraint
        test_user_id = str(uuid4())
        unique_suffix = uuid4().hex[:8]
        await session.execute(
            text("""
                INSERT INTO users (id, name, email, password_hash, role)
                VALUES (:id, :name, :email, '$2b$12$test_hash', 'user')
            """),
            {
                "id": test_user_id,
                "name": f"Test Context User {unique_suffix}",
                "email": f"test_context_{unique_suffix}@example.com",
            },
        )

        await session.execute(text(f"SET app.current_user_id = '{test_user_id}'"))

        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    await engine.dispose()


# =============================================================================
# TEST DATA FIXTURES
# =============================================================================


@pytest.fixture
def test_user_data() -> dict:
    """Generate test user data."""
    unique_id = uuid4().hex[:8]
    return {
        "email": f"test_{unique_id}@example.com",
        "password_hash": "$2b$12$test_hash_for_testing_only",
        "name": f"Test User {unique_id}",
        "role": "user",
        "is_active": True,
    }


@pytest.fixture
def test_gdpr_request_data() -> dict:
    """Generate test GDPR request data."""
    return {
        "request_type": "access",
        "requester_type": "user",
        "request_details": "Test GDPR access request",
    }


@pytest.fixture
def test_security_breach_data() -> dict:
    """Generate test security breach data."""
    return {
        "breach_type": "unauthorized_access",
        "severity": "medium",
        "nature": "Test breach for integration testing",
        "detection_method": "automated_test",
        "approximate_records": 10,
        "approximate_subjects": 5,
    }


@pytest.fixture
def test_robinson_phone() -> str:
    """Generate test phone number for Robinson checks."""
    return "+34600000001"


@pytest.fixture
def test_campaign_data() -> dict:
    """Generate test campaign data."""
    unique_id = uuid4().hex[:8]
    return {
        "name": f"Test Campaign {unique_id}",
        "description": "Integration test campaign",
        "start_date": datetime.now(UTC),
        "end_date": datetime.now(UTC) + timedelta(days=30),
        "status": "draft",
        "robinson_check_required": True,
    }


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


async def create_test_user(
    session: AsyncSession,
    email: str | None = None,
    role: str = "user",
) -> dict:
    """
    Helper to create a test user.
    Returns the user data including the generated ID.
    """
    unique_id = uuid4().hex[:8]
    test_email = email or f"test_{unique_id}@example.com"

    result = await session.execute(
        text("""
            INSERT INTO users (
                name, email, password_hash, role, is_active
            )
            VALUES (:name, :email, :password_hash, :role, true)
            RETURNING id, created_at
        """),
        {
            "name": f"Test User {unique_id}",
            "email": test_email,
            "password_hash": "$2b$12$test_hash",
            "role": role,
        },
    )
    row = result.fetchone()

    return {
        "id": row.id,
        "email": test_email,
        "name": f"Test User {unique_id}",
        "role": role,
        "created_at": row.created_at,
    }


async def cleanup_test_data(
    session: AsyncSession, table: str, id_column: str, test_id: str
) -> None:
    """Helper to clean up test data."""
    await session.execute(text(f"DELETE FROM {table} WHERE {id_column} = :id"), {"id": test_id})
    await session.commit()
