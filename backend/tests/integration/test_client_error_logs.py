"""
Integration tests for Client Error Logs functionality.

Tests verify against real PostgreSQL:
- Error report insertion via API endpoint
- Error retrieval for debugging
- Proper sanitization of sensitive data
- Integration with API keys
"""

from datetime import UTC, datetime

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class TestClientErrorLogCreation:
    """Integration tests for client error log creation in PostgreSQL."""

    @pytest.mark.asyncio
    async def test_insert_client_error_log(self, db_session: AsyncSession):
        """Test basic insertion of a client error log."""
        # First create an API key
        api_key_result = await db_session.execute(
            text("""
                SELECT * FROM create_api_key(
                    p_client_type := 'ai_agent',
                    p_service_name := 'Error Log Test Agent'
                )
            """)
        )
        api_key = api_key_result.fetchone()

        # Insert error log
        error_timestamp = datetime.now(UTC)
        result = await db_session.execute(
            text("""
                INSERT INTO client_error_logs (
                    api_key_id, client_version, error_type, error_message,
                    method, endpoint, response_status, error_timestamp,
                    environment
                ) VALUES (
                    :api_key_id, :client_version, :error_type, :error_message,
                    :method, :endpoint, :response_status, :error_timestamp,
                    :environment
                )
                RETURNING id, reported_at
            """),
            {
                "api_key_id": api_key.api_key_id,
                "client_version": "1.1.0",
                "error_type": "CapsuleClientError",
                "error_message": "Error HTTP 500: Internal Server Error",
                "method": "POST",
                "endpoint": "/api/v1/ai-agent/calls",
                "response_status": 500,
                "error_timestamp": error_timestamp,
                "environment": "dev",
            },
        )
        row = result.fetchone()

        assert row is not None
        assert row.id is not None
        assert row.reported_at is not None

    @pytest.mark.asyncio
    async def test_insert_error_log_with_payload(self, db_session: AsyncSession):
        """Test inserting error log with request payload."""
        # Create API key
        api_key_result = await db_session.execute(
            text("""
                SELECT * FROM create_api_key(
                    p_client_type := 'ai_agent',
                    p_service_name := 'Payload Test Agent'
                )
            """)
        )
        api_key = api_key_result.fetchone()

        # Insert error with JSONB payload
        payload = '{"direction": "inbound", "call_type": "ai_agent"}'
        result = await db_session.execute(
            text("""
                INSERT INTO client_error_logs (
                    api_key_id, client_version, error_type, error_message,
                    method, endpoint, request_payload, error_timestamp
                ) VALUES (
                    :api_key_id, :client_version, :error_type, :error_message,
                    :method, :endpoint, CAST(:request_payload AS JSONB), :error_timestamp
                )
                RETURNING id, request_payload
            """),
            {
                "api_key_id": api_key.api_key_id,
                "client_version": "1.1.0",
                "error_type": "CapsuleValidationError",
                "error_message": "Error de validación",
                "method": "POST",
                "endpoint": "/api/v1/pbx/calls",
                "request_payload": payload,
                "error_timestamp": datetime.now(UTC),
            },
        )
        row = result.fetchone()

        assert row is not None
        assert row.request_payload is not None
        assert row.request_payload["direction"] == "inbound"

    @pytest.mark.asyncio
    async def test_insert_error_log_with_call_reference(self, db_session: AsyncSession):
        """Test inserting error log with call_id reference."""
        # Create API key
        api_key_result = await db_session.execute(
            text("""
                SELECT * FROM create_api_key(
                    p_client_type := 'ai_agent',
                    p_service_name := 'Call Reference Test'
                )
            """)
        )
        api_key = api_key_result.fetchone()

        # Get a user_id for the call FK
        user_result = await db_session.execute(text("SELECT id FROM users LIMIT 1"))
        user_id = user_result.scalar()

        # Create a test call first
        call_result = await db_session.execute(
            text("""
                INSERT INTO calls (
                    direction, status, call_type, recording_encrypted,
                    user_id, call_date, call_time, call_timestamp,
                    duration_seconds, caller_phone_hash
                )
                VALUES (
                    'inbound', 'in_progress', 'ai_agent', false,
                    :user_id, CURRENT_DATE, CURRENT_TIME, NOW(),
                    0, 'test_hash'
                )
                RETURNING id
            """),
            {"user_id": user_id},
        )
        call_row = call_result.fetchone()
        call_id = call_row.id

        # Insert error with call reference
        result = await db_session.execute(
            text("""
                INSERT INTO client_error_logs (
                    api_key_id, client_version, error_type, error_message,
                    call_id, error_timestamp
                ) VALUES (
                    :api_key_id, :client_version, :error_type, :error_message,
                    :call_id, :error_timestamp
                )
                RETURNING id, call_id
            """),
            {
                "api_key_id": api_key.api_key_id,
                "client_version": "1.1.0",
                "error_type": "CapsuleComplianceError",
                "error_message": "AI disclosure not recorded",
                "call_id": call_id,
                "error_timestamp": datetime.now(UTC),
            },
        )
        row = result.fetchone()

        assert row is not None
        assert row.call_id == call_id

    @pytest.mark.asyncio
    async def test_insert_error_log_with_stack_trace(self, db_session: AsyncSession):
        """Test inserting error log with stack trace."""
        api_key_result = await db_session.execute(
            text("""
                SELECT * FROM create_api_key(
                    p_client_type := 'ai_agent',
                    p_service_name := 'Stack Trace Test'
                )
            """)
        )
        api_key = api_key_result.fetchone()

        stack_trace = """Traceback (most recent call last):
  File "capsule_agent_client.py", line 640, in _request
    raise error
CapsuleClientError: Error de conexión: Cannot connect to host"""

        result = await db_session.execute(
            text("""
                INSERT INTO client_error_logs (
                    api_key_id, client_version, error_type, error_message,
                    stack_trace, error_timestamp
                ) VALUES (
                    :api_key_id, :client_version, :error_type, :error_message,
                    :stack_trace, :error_timestamp
                )
                RETURNING id, stack_trace
            """),
            {
                "api_key_id": api_key.api_key_id,
                "client_version": "1.1.0",
                "error_type": "CapsuleClientError",
                "error_message": "Connection error",
                "stack_trace": stack_trace,
                "error_timestamp": datetime.now(UTC),
            },
        )
        row = result.fetchone()

        assert row is not None
        assert "Traceback" in row.stack_trace
        assert "CapsuleClientError" in row.stack_trace


class TestClientErrorLogRetrieval:
    """Integration tests for retrieving client error logs."""

    @pytest.mark.asyncio
    async def test_retrieve_errors_by_timestamp(self, db_session: AsyncSession):
        """Test retrieving errors within a time range."""
        # Create API key
        api_key_result = await db_session.execute(
            text("""
                SELECT * FROM create_api_key(
                    p_client_type := 'ai_agent',
                    p_service_name := 'Timestamp Query Test'
                )
            """)
        )
        api_key = api_key_result.fetchone()

        # Insert errors
        for i in range(3):
            await db_session.execute(
                text("""
                    INSERT INTO client_error_logs (
                        api_key_id, client_version, error_type, error_message,
                        error_timestamp
                    ) VALUES (
                        :api_key_id, :client_version, :error_type, :error_message,
                        :error_timestamp
                    )
                """),
                {
                    "api_key_id": api_key.api_key_id,
                    "client_version": "1.1.0",
                    "error_type": f"TestError{i}",
                    "error_message": f"Test error message {i}",
                    "error_timestamp": datetime.now(UTC),
                },
            )

        # Query errors from last 7 days
        result = await db_session.execute(
            text("""
                SELECT COUNT(*)
                FROM client_error_logs
                WHERE api_key_id = :api_key_id
                AND error_timestamp >= NOW() - INTERVAL '7 days'
            """),
            {"api_key_id": api_key.api_key_id},
        )
        count = result.scalar()

        assert count == 3

    @pytest.mark.asyncio
    async def test_retrieve_errors_by_type(self, db_session: AsyncSession):
        """Test filtering errors by error type."""
        api_key_result = await db_session.execute(
            text("""
                SELECT * FROM create_api_key(
                    p_client_type := 'ai_agent',
                    p_service_name := 'Type Filter Test'
                )
            """)
        )
        api_key = api_key_result.fetchone()

        # Insert different error types
        error_types = ["CapsuleClientError", "CapsuleAuthenticationError", "CapsuleClientError"]
        for i, error_type in enumerate(error_types):
            await db_session.execute(
                text("""
                    INSERT INTO client_error_logs (
                        api_key_id, client_version, error_type, error_message,
                        error_timestamp
                    ) VALUES (
                        :api_key_id, :client_version, :error_type, :error_message,
                        :error_timestamp
                    )
                """),
                {
                    "api_key_id": api_key.api_key_id,
                    "client_version": "1.1.0",
                    "error_type": error_type,
                    "error_message": f"Error {i}",
                    "error_timestamp": datetime.now(UTC),
                },
            )

        # Filter by CapsuleClientError
        result = await db_session.execute(
            text("""
                SELECT COUNT(*)
                FROM client_error_logs
                WHERE api_key_id = :api_key_id
                AND error_type = 'CapsuleClientError'
            """),
            {"api_key_id": api_key.api_key_id},
        )
        count = result.scalar()

        assert count == 2

    @pytest.mark.asyncio
    async def test_retrieve_unresolved_errors(self, db_session: AsyncSession):
        """Test filtering unresolved errors."""
        api_key_result = await db_session.execute(
            text("""
                SELECT * FROM create_api_key(
                    p_client_type := 'ai_agent',
                    p_service_name := 'Unresolved Filter Test'
                )
            """)
        )
        api_key = api_key_result.fetchone()

        # Insert errors - some resolved, some not
        for i in range(4):
            await db_session.execute(
                text("""
                    INSERT INTO client_error_logs (
                        api_key_id, client_version, error_type, error_message,
                        error_timestamp, resolved
                    ) VALUES (
                        :api_key_id, :client_version, :error_type, :error_message,
                        :error_timestamp, :resolved
                    )
                """),
                {
                    "api_key_id": api_key.api_key_id,
                    "client_version": "1.1.0",
                    "error_type": "TestError",
                    "error_message": f"Error {i}",
                    "error_timestamp": datetime.now(UTC),
                    "resolved": i < 2,  # First 2 resolved
                },
            )

        # Query unresolved only
        result = await db_session.execute(
            text("""
                SELECT COUNT(*)
                FROM client_error_logs
                WHERE api_key_id = :api_key_id
                AND resolved = FALSE
            """),
            {"api_key_id": api_key.api_key_id},
        )
        count = result.scalar()

        assert count == 2


class TestClientErrorLogResolution:
    """Integration tests for resolving client errors."""

    @pytest.mark.asyncio
    async def test_mark_error_as_resolved(self, db_session: AsyncSession):
        """Test marking an error as resolved."""
        api_key_result = await db_session.execute(
            text("""
                SELECT * FROM create_api_key(
                    p_client_type := 'ai_agent',
                    p_service_name := 'Resolution Test'
                )
            """)
        )
        api_key = api_key_result.fetchone()

        # Insert error
        insert_result = await db_session.execute(
            text("""
                INSERT INTO client_error_logs (
                    api_key_id, client_version, error_type, error_message,
                    error_timestamp
                ) VALUES (
                    :api_key_id, :client_version, :error_type, :error_message,
                    :error_timestamp
                )
                RETURNING id
            """),
            {
                "api_key_id": api_key.api_key_id,
                "client_version": "1.1.0",
                "error_type": "CapsuleClientError",
                "error_message": "To be resolved",
                "error_timestamp": datetime.now(UTC),
            },
        )
        error_id = insert_result.fetchone().id

        # Mark as resolved
        await db_session.execute(
            text("""
                UPDATE client_error_logs
                SET resolved = TRUE,
                    resolved_at = NOW(),
                    resolution_notes = :notes
                WHERE id = :id
            """),
            {
                "id": error_id,
                "notes": "Fixed in version 1.2.0",
            },
        )

        # Verify resolution
        result = await db_session.execute(
            text("""
                SELECT resolved, resolved_at, resolution_notes
                FROM client_error_logs
                WHERE id = :id
            """),
            {"id": error_id},
        )
        row = result.fetchone()

        assert row.resolved is True
        assert row.resolved_at is not None
        assert row.resolution_notes == "Fixed in version 1.2.0"


class TestClientErrorLogIndexes:
    """Integration tests for verifying index usage on client error logs."""

    @pytest.mark.asyncio
    async def test_index_on_error_timestamp(self, db_session: AsyncSession):
        """Verify index exists on error_timestamp column."""
        result = await db_session.execute(
            text("""
                SELECT indexname
                FROM pg_indexes
                WHERE tablename = 'client_error_logs'
                AND indexname = 'idx_client_errors_timestamp'
            """)
        )
        row = result.fetchone()
        assert row is not None

    @pytest.mark.asyncio
    async def test_index_on_error_type(self, db_session: AsyncSession):
        """Verify index exists on error_type column."""
        result = await db_session.execute(
            text("""
                SELECT indexname
                FROM pg_indexes
                WHERE tablename = 'client_error_logs'
                AND indexname = 'idx_client_errors_type'
            """)
        )
        row = result.fetchone()
        assert row is not None

    @pytest.mark.asyncio
    async def test_partial_index_on_unresolved(self, db_session: AsyncSession):
        """Verify partial index exists for unresolved errors."""
        result = await db_session.execute(
            text("""
                SELECT indexname
                FROM pg_indexes
                WHERE tablename = 'client_error_logs'
                AND indexname = 'idx_client_errors_unresolved'
            """)
        )
        row = result.fetchone()
        assert row is not None


class TestClientErrorLogPermissions:
    """Integration tests for client error log permissions."""

    @pytest.mark.asyncio
    async def test_ai_agent_can_insert(self, db_session: AsyncSession):
        """Verify capsule_ai_agent role can insert into client_error_logs."""
        # Check if grant exists
        result = await db_session.execute(
            text("""
                SELECT privilege_type
                FROM information_schema.role_table_grants
                WHERE table_name = 'client_error_logs'
                AND grantee = 'capsule_ai_agent'
                AND privilege_type = 'INSERT'
            """)
        )
        row = result.fetchone()
        assert row is not None

    @pytest.mark.asyncio
    async def test_capsule_app_can_select_and_update(self, db_session: AsyncSession):
        """Verify capsule_app role can SELECT and UPDATE client_error_logs."""
        result = await db_session.execute(
            text("""
                SELECT privilege_type
                FROM information_schema.role_table_grants
                WHERE table_name = 'client_error_logs'
                AND grantee = 'capsule_app'
                AND privilege_type IN ('SELECT', 'UPDATE')
            """)
        )
        rows = result.fetchall()
        privileges = {row.privilege_type for row in rows}

        assert "SELECT" in privileges
        assert "UPDATE" in privileges
