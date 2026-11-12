"""
Integration tests for API Keys operations.

Tests verify against real PostgreSQL:
- API Key creation via create_api_key() function
- API Key validation via validate_api_key() function
- API Key revocation via revoke_api_key() function
- Client types and rate limiting
- IP whitelist functionality
- Expiration handling

RGPD Art. 32: Tests verify secure handling of API keys.
AI Act Art. 12: Tests verify logging and traceability.
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class TestAPIKeyCreationIntegration:
    """Integration tests for API key creation with PostgreSQL."""

    @pytest.mark.asyncio
    async def test_create_api_key_ai_agent(self, db_session: AsyncSession):
        """Test creating an API key for AI agent client type."""
        result = await db_session.execute(
            text("""
                SELECT * FROM create_api_key(
                    p_client_type := 'ai_agent',
                    p_service_name := 'Test AI Agent',
                    p_description := 'Integration test AI agent key'
                )
            """)
        )
        row = result.fetchone()

        assert row is not None
        assert row.api_key is not None
        assert row.api_key.startswith("capsule_ai_agent_")
        assert row.api_key_id is not None
        assert row.key_prefix is not None
        assert len(row.key_prefix) == 20

    @pytest.mark.asyncio
    async def test_create_api_key_pbx(self, db_session: AsyncSession):
        """Test creating an API key for PBX client type."""
        result = await db_session.execute(
            text("""
                SELECT * FROM create_api_key(
                    p_client_type := 'pbx',
                    p_service_name := 'Test PBX System',
                    p_description := 'Integration test PBX key'
                )
            """)
        )
        row = result.fetchone()

        assert row is not None
        assert row.api_key.startswith("capsule_pbx_")
        assert row.api_key_id is not None

    @pytest.mark.asyncio
    async def test_create_api_key_external(self, db_session: AsyncSession):
        """Test creating an API key for external client type."""
        result = await db_session.execute(
            text("""
                SELECT * FROM create_api_key(
                    p_client_type := 'external',
                    p_service_name := 'Test External Service',
                    p_description := 'Integration test external key'
                )
            """)
        )
        row = result.fetchone()

        assert row is not None
        assert row.api_key.startswith("capsule_external_")

    @pytest.mark.asyncio
    async def test_create_api_key_webhook(self, db_session: AsyncSession):
        """Test creating an API key for webhook client type."""
        result = await db_session.execute(
            text("""
                SELECT * FROM create_api_key(
                    p_client_type := 'webhook',
                    p_service_name := 'Test Webhook Handler',
                    p_description := 'Integration test webhook key'
                )
            """)
        )
        row = result.fetchone()

        assert row is not None
        assert row.api_key.startswith("capsule_webhook_")

    @pytest.mark.asyncio
    async def test_create_api_key_with_custom_service_id(self, db_session: AsyncSession):
        """Test creating an API key with custom service ID."""
        unique_id = uuid4().hex[:8]
        service_id = f"custom-service-{unique_id}"

        result = await db_session.execute(
            text("""
                SELECT * FROM create_api_key(
                    p_client_type := 'ai_agent',
                    p_service_name := 'Custom Service Agent',
                    p_service_id := :service_id,
                    p_description := 'Test with custom service ID'
                )
            """),
            {"service_id": service_id},
        )
        row = result.fetchone()

        assert row is not None

        # Verify service_id was stored
        verify = await db_session.execute(
            text("SELECT service_id FROM api_keys WHERE id = :id"), {"id": row.api_key_id}
        )
        stored = verify.fetchone()
        assert stored.service_id == service_id

    @pytest.mark.asyncio
    async def test_create_api_key_with_expiration(self, db_session: AsyncSession):
        """Test creating an API key with expiration date."""
        result = await db_session.execute(
            text("""
                SELECT * FROM create_api_key(
                    p_client_type := 'external',
                    p_service_name := 'Expiring Service',
                    p_expires_days := 30
                )
            """)
        )
        row = result.fetchone()

        assert row is not None

        # Verify expiration was set
        verify = await db_session.execute(
            text("SELECT expires_at FROM api_keys WHERE id = :id"), {"id": row.api_key_id}
        )
        stored = verify.fetchone()
        assert stored.expires_at is not None

        # Should expire approximately 30 days from now
        expected_expiry = datetime.now(UTC) + timedelta(days=30)
        actual_expiry = (
            stored.expires_at.replace(tzinfo=UTC)
            if stored.expires_at.tzinfo is None
            else stored.expires_at
        )
        assert abs((actual_expiry - expected_expiry).total_seconds()) < 60

    @pytest.mark.asyncio
    async def test_create_api_key_with_ip_whitelist(self, db_session: AsyncSession):
        """Test creating an API key with IP whitelist."""
        result = await db_session.execute(
            text("""
                SELECT * FROM create_api_key(
                    p_client_type := 'pbx',
                    p_service_name := 'IP Restricted PBX',
                    p_allowed_ips := ARRAY['192.168.1.100'::INET, '10.0.0.50'::INET]
                )
            """)
        )
        row = result.fetchone()

        assert row is not None

        # Verify IPs were stored
        verify = await db_session.execute(
            text("SELECT allowed_ips FROM api_keys WHERE id = :id"), {"id": row.api_key_id}
        )
        stored = verify.fetchone()
        assert stored.allowed_ips is not None
        assert len(stored.allowed_ips) == 2

    @pytest.mark.asyncio
    async def test_create_api_key_unique_service_id_constraint(self, db_session: AsyncSession):
        """Test that duplicate service_id is rejected."""
        unique_id = uuid4().hex[:8]
        service_id = f"unique-service-{unique_id}"

        # Create first key
        await db_session.execute(
            text("""
                SELECT * FROM create_api_key(
                    p_client_type := 'ai_agent',
                    p_service_name := 'First Service',
                    p_service_id := :service_id
                )
            """),
            {"service_id": service_id},
        )

        # Try to create second key with same service_id
        with pytest.raises(Exception) as exc_info:
            await db_session.execute(
                text("""
                    SELECT * FROM create_api_key(
                        p_client_type := 'ai_agent',
                        p_service_name := 'Second Service',
                        p_service_id := :service_id
                    )
                """),
                {"service_id": service_id},
            )

        assert "unique" in str(exc_info.value).lower() or "duplicate" in str(exc_info.value).lower()


class TestAPIKeyValidationIntegration:
    """Integration tests for API key validation with PostgreSQL."""

    @pytest.mark.asyncio
    async def test_validate_valid_api_key(self, db_session: AsyncSession):
        """Test validating a valid API key."""
        # Create a key first
        create_result = await db_session.execute(
            text("""
                SELECT * FROM create_api_key(
                    p_client_type := 'ai_agent',
                    p_service_name := 'Validation Test Agent'
                )
            """)
        )
        created = create_result.fetchone()

        # Validate the key
        validate_result = await db_session.execute(
            text("SELECT * FROM validate_api_key(:api_key)"), {"api_key": created.api_key}
        )
        validated = validate_result.fetchone()

        assert validated.is_valid is True
        assert validated.api_key_id == created.api_key_id
        assert validated.client_type == "ai_agent"
        assert validated.error_message is None

    @pytest.mark.asyncio
    async def test_validate_invalid_api_key(self, db_session: AsyncSession):
        """Test validating an invalid API key."""
        result = await db_session.execute(
            text("SELECT * FROM validate_api_key(:api_key)"),
            {"api_key": "capsule_ai_agent_invalidkey12345"},
        )
        row = result.fetchone()

        assert row.is_valid is False
        assert row.error_message == "Invalid API key"

    @pytest.mark.asyncio
    async def test_validate_api_key_rate_limit_ai_agent(self, db_session: AsyncSession):
        """Test that AI agent gets correct default rate limit (1000)."""
        # Create key
        create_result = await db_session.execute(
            text("""
                SELECT * FROM create_api_key(
                    p_client_type := 'ai_agent',
                    p_service_name := 'Rate Limit Test AI'
                )
            """)
        )
        created = create_result.fetchone()

        # Validate and check rate limit
        validate_result = await db_session.execute(
            text("SELECT * FROM validate_api_key(:api_key)"), {"api_key": created.api_key}
        )
        validated = validate_result.fetchone()

        assert validated.is_valid is True
        assert validated.rate_limit == 1000

    @pytest.mark.asyncio
    async def test_validate_api_key_rate_limit_pbx(self, db_session: AsyncSession):
        """Test that PBX gets correct default rate limit (500)."""
        create_result = await db_session.execute(
            text("""
                SELECT * FROM create_api_key(
                    p_client_type := 'pbx',
                    p_service_name := 'Rate Limit Test PBX'
                )
            """)
        )
        created = create_result.fetchone()

        validate_result = await db_session.execute(
            text("SELECT * FROM validate_api_key(:api_key)"), {"api_key": created.api_key}
        )
        validated = validate_result.fetchone()

        assert validated.is_valid is True
        assert validated.rate_limit == 500

    @pytest.mark.asyncio
    async def test_validate_api_key_rate_limit_external(self, db_session: AsyncSession):
        """Test that external client gets correct default rate limit (100)."""
        create_result = await db_session.execute(
            text("""
                SELECT * FROM create_api_key(
                    p_client_type := 'external',
                    p_service_name := 'Rate Limit Test External'
                )
            """)
        )
        created = create_result.fetchone()

        validate_result = await db_session.execute(
            text("SELECT * FROM validate_api_key(:api_key)"), {"api_key": created.api_key}
        )
        validated = validate_result.fetchone()

        assert validated.is_valid is True
        assert validated.rate_limit == 100

    @pytest.mark.asyncio
    async def test_validate_api_key_rate_limit_webhook(self, db_session: AsyncSession):
        """Test that webhook gets correct default rate limit (200)."""
        create_result = await db_session.execute(
            text("""
                SELECT * FROM create_api_key(
                    p_client_type := 'webhook',
                    p_service_name := 'Rate Limit Test Webhook'
                )
            """)
        )
        created = create_result.fetchone()

        validate_result = await db_session.execute(
            text("SELECT * FROM validate_api_key(:api_key)"), {"api_key": created.api_key}
        )
        validated = validate_result.fetchone()

        assert validated.is_valid is True
        assert validated.rate_limit == 200

    @pytest.mark.asyncio
    async def test_validate_api_key_updates_usage_stats(self, db_session: AsyncSession):
        """Test that validation updates last_used_at and use_count."""
        # Create key
        create_result = await db_session.execute(
            text("""
                SELECT * FROM create_api_key(
                    p_client_type := 'ai_agent',
                    p_service_name := 'Usage Stats Test'
                )
            """)
        )
        created = create_result.fetchone()

        # Check initial state
        initial = await db_session.execute(
            text("SELECT last_used_at, use_count FROM api_keys WHERE id = :id"),
            {"id": created.api_key_id},
        )
        initial_row = initial.fetchone()
        assert initial_row.use_count == 0
        assert initial_row.last_used_at is None

        # Validate the key
        await db_session.execute(
            text("SELECT * FROM validate_api_key(:api_key)"), {"api_key": created.api_key}
        )

        # Check updated state
        updated = await db_session.execute(
            text("SELECT last_used_at, use_count FROM api_keys WHERE id = :id"),
            {"id": created.api_key_id},
        )
        updated_row = updated.fetchone()
        assert updated_row.use_count == 1
        assert updated_row.last_used_at is not None

        # Validate again
        await db_session.execute(
            text("SELECT * FROM validate_api_key(:api_key)"), {"api_key": created.api_key}
        )

        # Check count incremented
        final = await db_session.execute(
            text("SELECT use_count FROM api_keys WHERE id = :id"), {"id": created.api_key_id}
        )
        final_row = final.fetchone()
        assert final_row.use_count == 2

    @pytest.mark.asyncio
    async def test_validate_api_key_with_valid_ip(self, db_session: AsyncSession):
        """Test validating key from whitelisted IP."""
        create_result = await db_session.execute(
            text("""
                SELECT * FROM create_api_key(
                    p_client_type := 'pbx',
                    p_service_name := 'IP Whitelist Test',
                    p_allowed_ips := ARRAY['192.168.1.100'::INET]
                )
            """)
        )
        created = create_result.fetchone()

        # Validate from allowed IP
        validate_result = await db_session.execute(
            text("SELECT * FROM validate_api_key(:api_key, '192.168.1.100'::INET)"),
            {"api_key": created.api_key},
        )
        validated = validate_result.fetchone()

        assert validated.is_valid is True

    @pytest.mark.asyncio
    async def test_validate_api_key_with_invalid_ip(self, db_session: AsyncSession):
        """Test validating key from non-whitelisted IP."""
        create_result = await db_session.execute(
            text("""
                SELECT * FROM create_api_key(
                    p_client_type := 'pbx',
                    p_service_name := 'IP Blocked Test',
                    p_allowed_ips := ARRAY['192.168.1.100'::INET]
                )
            """)
        )
        created = create_result.fetchone()

        # Validate from different IP
        validate_result = await db_session.execute(
            text("SELECT * FROM validate_api_key(:api_key, '10.0.0.1'::INET)"),
            {"api_key": created.api_key},
        )
        validated = validate_result.fetchone()

        assert validated.is_valid is False
        assert validated.error_message == "IP not in whitelist"


class TestAPIKeyRevocationIntegration:
    """Integration tests for API key revocation with PostgreSQL."""

    @pytest.mark.asyncio
    async def test_revoke_api_key(self, db_session: AsyncSession):
        """Test revoking an API key."""
        # Create key
        create_result = await db_session.execute(
            text("""
                SELECT * FROM create_api_key(
                    p_client_type := 'ai_agent',
                    p_service_name := 'Revoke Test Agent'
                )
            """)
        )
        created = create_result.fetchone()

        # Revoke the key
        revoke_result = await db_session.execute(
            text("SELECT revoke_api_key(:id, 'Security breach')"), {"id": created.api_key_id}
        )
        revoked = revoke_result.scalar()

        assert revoked is True

        # Verify key is inactive
        verify = await db_session.execute(
            text("SELECT is_active, revoked_at, revoke_reason FROM api_keys WHERE id = :id"),
            {"id": created.api_key_id},
        )
        row = verify.fetchone()

        assert row.is_active is False
        assert row.revoked_at is not None
        assert row.revoke_reason == "Security breach"

    @pytest.mark.asyncio
    async def test_revoke_api_key_invalidates_validation(self, db_session: AsyncSession):
        """Test that revoked key fails validation."""
        # Create key
        create_result = await db_session.execute(
            text("""
                SELECT * FROM create_api_key(
                    p_client_type := 'ai_agent',
                    p_service_name := 'Revoke Validation Test'
                )
            """)
        )
        created = create_result.fetchone()
        api_key = created.api_key

        # Verify key works before revocation
        validate_before = await db_session.execute(
            text("SELECT * FROM validate_api_key(:api_key)"), {"api_key": api_key}
        )
        before = validate_before.fetchone()
        assert before.is_valid is True

        # Revoke
        await db_session.execute(text("SELECT revoke_api_key(:id)"), {"id": created.api_key_id})

        # Verify key fails after revocation
        validate_after = await db_session.execute(
            text("SELECT * FROM validate_api_key(:api_key)"), {"api_key": api_key}
        )
        after = validate_after.fetchone()
        assert after.is_valid is False

    @pytest.mark.asyncio
    async def test_revoke_nonexistent_key(self, db_session: AsyncSession):
        """Test revoking a non-existent key returns false."""
        fake_id = str(uuid4())

        result = await db_session.execute(text("SELECT revoke_api_key(:id)"), {"id": fake_id})
        revoked = result.scalar()

        assert revoked is False

    @pytest.mark.asyncio
    async def test_revoke_already_revoked_key(self, db_session: AsyncSession):
        """Test revoking an already revoked key returns false."""
        # Create and revoke a key
        create_result = await db_session.execute(
            text("""
                SELECT * FROM create_api_key(
                    p_client_type := 'webhook',
                    p_service_name := 'Double Revoke Test'
                )
            """)
        )
        created = create_result.fetchone()

        # First revocation
        await db_session.execute(text("SELECT revoke_api_key(:id)"), {"id": created.api_key_id})

        # Second revocation should return false
        result = await db_session.execute(
            text("SELECT revoke_api_key(:id)"), {"id": created.api_key_id}
        )
        revoked = result.scalar()

        assert revoked is False


class TestAPIKeyExpirationIntegration:
    """Integration tests for API key expiration handling."""

    @pytest.mark.asyncio
    async def test_expired_key_validation_fails(self, db_session: AsyncSession):
        """Test that expired keys fail validation."""
        # Create a key with 1 day expiration
        create_result = await db_session.execute(
            text("""
                SELECT * FROM create_api_key(
                    p_client_type := 'external',
                    p_service_name := 'Expiration Test',
                    p_expires_days := 1
                )
            """)
        )
        created = create_result.fetchone()

        # Manually set expiration to past
        await db_session.execute(
            text("""
                UPDATE api_keys
                SET expires_at = CURRENT_TIMESTAMP - INTERVAL '1 hour'
                WHERE id = :id
            """),
            {"id": created.api_key_id},
        )

        # Validate should fail
        validate_result = await db_session.execute(
            text("SELECT * FROM validate_api_key(:api_key)"), {"api_key": created.api_key}
        )
        validated = validate_result.fetchone()

        assert validated.is_valid is False
        assert validated.error_message == "API key expired"

    @pytest.mark.asyncio
    async def test_key_without_expiration_never_expires(self, db_session: AsyncSession):
        """Test that keys without expiration date don't expire."""
        # Create key without expiration
        create_result = await db_session.execute(
            text("""
                SELECT * FROM create_api_key(
                    p_client_type := 'ai_agent',
                    p_service_name := 'No Expiration Test'
                )
            """)
        )
        created = create_result.fetchone()

        # Verify expires_at is null
        verify = await db_session.execute(
            text("SELECT expires_at FROM api_keys WHERE id = :id"), {"id": created.api_key_id}
        )
        row = verify.fetchone()
        assert row.expires_at is None

        # Key should still validate
        validate_result = await db_session.execute(
            text("SELECT * FROM validate_api_key(:api_key)"), {"api_key": created.api_key}
        )
        validated = validate_result.fetchone()

        assert validated.is_valid is True


class TestAPIKeyUsageLogIntegration:
    """Integration tests for API key usage logging."""

    @pytest.mark.asyncio
    async def test_log_api_key_usage(self, db_session: AsyncSession):
        """Test logging API key usage."""
        # Create a key
        create_result = await db_session.execute(
            text("""
                SELECT * FROM create_api_key(
                    p_client_type := 'ai_agent',
                    p_service_name := 'Usage Log Test'
                )
            """)
        )
        created = create_result.fetchone()

        # Insert usage log
        await db_session.execute(
            text("""
                INSERT INTO api_key_usage_log (
                    api_key_id, endpoint, method, client_ip, response_status, response_time_ms
                ) VALUES (
                    :api_key_id, '/api/v1/calls', 'POST', '192.168.1.1'::INET, 201, 150
                )
            """),
            {"api_key_id": created.api_key_id},
        )

        # Verify log entry
        result = await db_session.execute(
            text("""
                SELECT endpoint, method, response_status, response_time_ms
                FROM api_key_usage_log
                WHERE api_key_id = :api_key_id
            """),
            {"api_key_id": created.api_key_id},
        )
        row = result.fetchone()

        assert row is not None
        assert row.endpoint == "/api/v1/calls"
        assert row.method == "POST"
        assert row.response_status == 201
        assert row.response_time_ms == 150

    @pytest.mark.asyncio
    async def test_multiple_usage_logs(self, db_session: AsyncSession):
        """Test multiple usage log entries for same key."""
        create_result = await db_session.execute(
            text("""
                SELECT * FROM create_api_key(
                    p_client_type := 'ai_agent',
                    p_service_name := 'Multi Log Test'
                )
            """)
        )
        created = create_result.fetchone()

        # Insert multiple log entries
        for i in range(5):
            await db_session.execute(
                text("""
                    INSERT INTO api_key_usage_log (
                        api_key_id, endpoint, method, response_status
                    ) VALUES (
                        :api_key_id, :endpoint, 'GET', 200
                    )
                """),
                {
                    "api_key_id": created.api_key_id,
                    "endpoint": f"/api/v1/calls/{i}",
                },
            )

        # Count entries
        result = await db_session.execute(
            text("SELECT COUNT(*) FROM api_key_usage_log WHERE api_key_id = :id"),
            {"id": created.api_key_id},
        )
        count = result.scalar()

        assert count == 5
