"""
Unit tests for API Key schemas.

Tests verify Pydantic schema validation:
- Field constraints (min/max length, patterns)
- Client type validation
- Required vs optional fields
- Default values

No database required - pure schema validation.
"""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.schemas.auth import (
    APIKeyCreateRequest,
    APIKeyCreateResponse,
    APIKeyInfo,
    APIKeyProvisionRequest,
    APIKeyProvisionResponse,
    APIKeyRevokeRequest,
)


class TestAPIKeyCreateRequest:
    """Tests for APIKeyCreateRequest schema."""

    def test_valid_ai_agent_request(self):
        """Test valid request for ai_agent client type."""
        request = APIKeyCreateRequest(
            client_type="ai_agent",
            service_name="My AI Agent",
            description="Test AI agent service",
        )

        assert request.client_type == "ai_agent"
        assert request.service_name == "My AI Agent"
        assert request.service_id is None
        assert request.allowed_ips is None
        assert request.expires_days is None

    def test_valid_pbx_request(self):
        """Test valid request for pbx client type."""
        request = APIKeyCreateRequest(
            client_type="pbx",
            service_name="Asterisk PBX",
        )

        assert request.client_type == "pbx"

    def test_valid_external_request(self):
        """Test valid request for external client type."""
        request = APIKeyCreateRequest(
            client_type="external",
            service_name="Third Party Service",
        )

        assert request.client_type == "external"

    def test_valid_webhook_request(self):
        """Test valid request for webhook client type."""
        request = APIKeyCreateRequest(
            client_type="webhook",
            service_name="Webhook Handler",
        )

        assert request.client_type == "webhook"

    def test_invalid_client_type_rejected(self):
        """Test that invalid client_type raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            APIKeyCreateRequest(
                client_type="invalid_type",
                service_name="Test Service",
            )

        assert "client_type" in str(exc_info.value)

    def test_service_name_min_length(self):
        """Test service_name minimum length (3 characters)."""
        with pytest.raises(ValidationError) as exc_info:
            APIKeyCreateRequest(
                client_type="ai_agent",
                service_name="AB",  # Too short
            )

        assert "service_name" in str(exc_info.value)

    def test_service_name_max_length(self):
        """Test service_name maximum length (100 characters)."""
        with pytest.raises(ValidationError) as exc_info:
            APIKeyCreateRequest(
                client_type="ai_agent",
                service_name="A" * 101,  # Too long
            )

        assert "service_name" in str(exc_info.value)

    def test_service_id_max_length(self):
        """Test service_id maximum length (50 characters)."""
        with pytest.raises(ValidationError) as exc_info:
            APIKeyCreateRequest(
                client_type="ai_agent",
                service_name="Test Service",
                service_id="A" * 51,  # Too long
            )

        assert "service_id" in str(exc_info.value)

    def test_description_max_length(self):
        """Test description maximum length (500 characters)."""
        with pytest.raises(ValidationError) as exc_info:
            APIKeyCreateRequest(
                client_type="ai_agent",
                service_name="Test Service",
                description="A" * 501,  # Too long
            )

        assert "description" in str(exc_info.value)

    def test_expires_days_min_value(self):
        """Test expires_days minimum value (1 day)."""
        with pytest.raises(ValidationError) as exc_info:
            APIKeyCreateRequest(
                client_type="ai_agent",
                service_name="Test Service",
                expires_days=0,  # Too small
            )

        assert "expires_days" in str(exc_info.value)

    def test_expires_days_max_value(self):
        """Test expires_days maximum value (365 days)."""
        with pytest.raises(ValidationError) as exc_info:
            APIKeyCreateRequest(
                client_type="ai_agent",
                service_name="Test Service",
                expires_days=366,  # Too large
            )

        assert "expires_days" in str(exc_info.value)

    def test_valid_expires_days_range(self):
        """Test valid expires_days values."""
        # Min value
        req_min = APIKeyCreateRequest(
            client_type="ai_agent",
            service_name="Test Service",
            expires_days=1,
        )
        assert req_min.expires_days == 1

        # Max value
        req_max = APIKeyCreateRequest(
            client_type="ai_agent",
            service_name="Test Service",
            expires_days=365,
        )
        assert req_max.expires_days == 365

    def test_allowed_ips_list(self):
        """Test allowed_ips accepts list of strings."""
        request = APIKeyCreateRequest(
            client_type="pbx",
            service_name="IP Restricted PBX",
            allowed_ips=["192.168.1.100", "10.0.0.1"],
        )

        assert request.allowed_ips == ["192.168.1.100", "10.0.0.1"]


class TestAPIKeyCreateResponse:
    """Tests for APIKeyCreateResponse schema."""

    def test_valid_response(self):
        """Test valid response creation."""
        response = APIKeyCreateResponse(
            api_key="capsule_ai_agent_abc123def456",
            api_key_id="550e8400-e29b-41d4-a716-446655440000",
            key_prefix="capsule_ai_agent_abc",
            client_type="ai_agent",
            service_name="Test Agent",
            service_id="test-agent-001",
            expires_at=None,
        )

        assert response.api_key == "capsule_ai_agent_abc123def456"
        assert response.api_key_id == "550e8400-e29b-41d4-a716-446655440000"
        assert "will NOT be shown again" in response.message

    def test_response_with_expiration(self):
        """Test response with expiration date."""
        expires = datetime(2025, 12, 31, 23, 59, 59, tzinfo=UTC)

        response = APIKeyCreateResponse(
            api_key="capsule_external_xyz789",
            api_key_id="550e8400-e29b-41d4-a716-446655440001",
            key_prefix="capsule_external_xyz",
            client_type="external",
            service_name="Expiring Service",
            service_id="exp-service-001",
            expires_at=expires,
        )

        assert response.expires_at == expires


class TestAPIKeyInfo:
    """Tests for APIKeyInfo schema (listing existing keys)."""

    def test_valid_info(self):
        """Test valid APIKeyInfo creation."""
        now = datetime.now(UTC)

        info = APIKeyInfo(
            id="550e8400-e29b-41d4-a716-446655440000",
            key_prefix="capsule_ai_agent_abc",
            client_type="ai_agent",
            service_name="Test Agent",
            service_id="test-001",
            description="Test description",
            allowed_ips=["192.168.1.1"],
            is_active=True,
            created_at=now,
            expires_at=None,
            last_used_at=None,
            use_count=0,
        )

        assert info.id == "550e8400-e29b-41d4-a716-446655440000"
        assert info.is_active is True
        assert info.use_count == 0

    def test_info_with_usage_stats(self):
        """Test APIKeyInfo with usage statistics."""
        now = datetime.now(UTC)

        info = APIKeyInfo(
            id="550e8400-e29b-41d4-a716-446655440000",
            key_prefix="capsule_pbx_xyz",
            client_type="pbx",
            service_name="Active PBX",
            is_active=True,
            created_at=now,
            last_used_at=now,
            use_count=1500,
        )

        assert info.last_used_at == now
        assert info.use_count == 1500


class TestAPIKeyRevokeRequest:
    """Tests for APIKeyRevokeRequest schema."""

    def test_default_reason(self):
        """Test default revocation reason."""
        request = APIKeyRevokeRequest()

        assert request.reason == "Manual revocation"

    def test_custom_reason(self):
        """Test custom revocation reason."""
        request = APIKeyRevokeRequest(reason="Security breach detected")

        assert request.reason == "Security breach detected"

    def test_reason_max_length(self):
        """Test reason maximum length (255 characters)."""
        with pytest.raises(ValidationError) as exc_info:
            APIKeyRevokeRequest(reason="A" * 256)

        assert "reason" in str(exc_info.value)


class TestAPIKeyProvisionRequest:
    """Tests for APIKeyProvisionRequest schema."""

    def test_valid_provision_request(self):
        """Test valid provisioning request."""
        request = APIKeyProvisionRequest(
            provision_secret="a" * 64,  # 64 char hex secret
            client_type="ai_agent",
            service_name="Provisioned Agent",
            service_id="prov-agent-001",
            description="Auto-provisioned AI agent",
        )

        assert request.provision_secret == "a" * 64
        assert request.client_type == "ai_agent"
        assert request.service_name == "Provisioned Agent"

    def test_provision_secret_min_length(self):
        """Test provision_secret minimum length (32 characters)."""
        with pytest.raises(ValidationError) as exc_info:
            APIKeyProvisionRequest(
                provision_secret="short",  # Too short
                client_type="ai_agent",
                service_name="Test Service",
            )

        assert "provision_secret" in str(exc_info.value)

    def test_provision_secret_exact_min_length(self):
        """Test provision_secret at exactly minimum length."""
        request = APIKeyProvisionRequest(
            provision_secret="a" * 32,  # Exactly 32 characters
            client_type="ai_agent",
            service_name="Test Service",
        )

        assert len(request.provision_secret) == 32

    def test_provision_invalid_client_type(self):
        """Test that invalid client_type is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            APIKeyProvisionRequest(
                provision_secret="a" * 64,
                client_type="hacker",  # Invalid
                service_name="Test Service",
            )

        assert "client_type" in str(exc_info.value)

    def test_provision_service_name_validation(self):
        """Test service_name validation in provision request."""
        # Too short
        with pytest.raises(ValidationError):
            APIKeyProvisionRequest(
                provision_secret="a" * 64,
                client_type="ai_agent",
                service_name="AB",  # Too short
            )

        # Too long
        with pytest.raises(ValidationError):
            APIKeyProvisionRequest(
                provision_secret="a" * 64,
                client_type="ai_agent",
                service_name="A" * 101,  # Too long
            )

    def test_provision_optional_fields(self):
        """Test optional fields are truly optional."""
        request = APIKeyProvisionRequest(
            provision_secret="a" * 64,
            client_type="ai_agent",
            service_name="Minimal Request",
        )

        assert request.service_id is None
        assert request.description is None


class TestAPIKeyProvisionResponse:
    """Tests for APIKeyProvisionResponse schema."""

    def test_valid_provision_response(self):
        """Test valid provision response."""
        response = APIKeyProvisionResponse(
            api_key="capsule_ai_agent_provisionedkey123",
            api_key_id="550e8400-e29b-41d4-a716-446655440000",
            key_prefix="capsule_ai_agent_pro",
            client_type="ai_agent",
            service_name="Provisioned Service",
            service_id="prov-service-001",
            expires_at=None,
        )

        assert response.api_key == "capsule_ai_agent_provisionedkey123"
        assert "provisioned successfully" in response.message.lower()
        assert "NOT be shown again" in response.message

    def test_provision_response_message_warning(self):
        """Test that provision response has security warning."""
        response = APIKeyProvisionResponse(
            api_key="capsule_pbx_test123",
            api_key_id="550e8400-e29b-41d4-a716-446655440000",
            key_prefix="capsule_pbx_test1",
            client_type="pbx",
            service_name="Test PBX",
            service_id="pbx-001",
        )

        # Should contain warning about storing the key
        assert "securely" in response.message.lower() or "store" in response.message.lower()
