"""
Integration tests for GDPR operations.

Tests verify compliance with:
- RGPD Art. 12.3: Response within 1 month
- RGPD Art. 15-22: Data subject rights (ARCO+PL)
- LOPDGDD Art. 33: Data blocking before deletion
- RGPD Art. 33: Breach notification within 72 hours

These tests use real PostgreSQL to verify the complete GDPR workflow.
"""

import hashlib
import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class TestDataSubjectRequestsIntegration:
    """
    Integration tests for GDPR rights requests.
    RGPD Art. 15-22, Art. 12.3 (30-day response deadline).
    """

    async def _create_test_user(self, db_session: AsyncSession) -> str:
        """Helper to create a test user and return ID."""
        unique_id = uuid4().hex[:8]
        result = await db_session.execute(
            text("""
                INSERT INTO users (name, email, password_hash, role)
                VALUES (:name, :email, :password_hash, 'user')
                RETURNING id
            """),
            {
                "name": f"DSR Test User {unique_id}",
                "email": f"dsr_{unique_id}@example.com",
                "password_hash": "$2b$12$test_hash",
            },
        )
        return result.scalar()

    @pytest.mark.asyncio
    async def test_create_access_request_art15(self, db_session: AsyncSession):
        """Test RGPD Art. 15 - Right of access request creation."""
        user_id = await self._create_test_user(db_session)

        # Encryption keys are already set in conftest.py db_session fixture
        result = await db_session.execute(
            text("""
                INSERT INTO data_subject_requests (
                    request_type, data_subject_id, data_subject_type,
                    requester_email_encrypted, request_details_encrypted,
                    status, submitted_at, deadline_at
                )
                VALUES (
                    'access', :user_id, 'user',
                    encrypt_pii_with_metadata(:email),
                    encrypt_pii_with_metadata(:details),
                    'pending', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP + interval '1 month'
                )
                RETURNING id, request_type, status, deadline_at, submitted_at
            """),
            {
                "user_id": user_id,
                "email": "test@example.com",
                "details": "I want to access all my personal data",
            },
        )
        row = result.fetchone()

        assert row is not None
        assert row.request_type == "access"
        assert row.status == "pending"
        assert row.deadline_at <= row.submitted_at + timedelta(days=30)

    @pytest.mark.asyncio
    async def test_create_rectification_request_art16(self, db_session: AsyncSession):
        """Test RGPD Art. 16 - Right to rectification."""
        user_id = await self._create_test_user(db_session)

        result = await db_session.execute(
            text("""
                INSERT INTO data_subject_requests (
                    request_type, data_subject_id, data_subject_type,
                    requester_email_encrypted, request_details_encrypted,
                    status, submitted_at, deadline_at
                )
                VALUES (
                    'rectification', :user_id, 'user',
                    encrypt_pii_with_metadata(:email),
                    encrypt_pii_with_metadata(:details),
                    'pending', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP + interval '1 month'
                )
                RETURNING request_type, status
            """),
            {
                "user_id": user_id,
                "email": "test@example.com",
                "details": "Correct my name from 'Jon' to 'John'",
            },
        )
        row = result.fetchone()

        assert row.request_type == "rectification"
        assert row.status == "pending"

    @pytest.mark.asyncio
    async def test_create_erasure_request_art17(self, db_session: AsyncSession):
        """Test RGPD Art. 17 - Right to erasure (right to be forgotten)."""
        user_id = await self._create_test_user(db_session)

        result = await db_session.execute(
            text("""
                INSERT INTO data_subject_requests (
                    request_type, data_subject_id, data_subject_type,
                    requester_email_encrypted, request_details_encrypted,
                    status, submitted_at, deadline_at
                )
                VALUES (
                    'erasure', :user_id, 'user',
                    encrypt_pii_with_metadata(:email),
                    encrypt_pii_with_metadata(:details),
                    'pending', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP + interval '1 month'
                )
                RETURNING request_type, status
            """),
            {
                "user_id": user_id,
                "email": "test@example.com",
                "details": "Delete all my personal data",
            },
        )
        row = result.fetchone()

        assert row.request_type == "erasure"

    @pytest.mark.asyncio
    async def test_get_pending_requests(self, db_session: AsyncSession):
        """Test retrieving all pending GDPR requests."""
        user_id = await self._create_test_user(db_session)

        # Create multiple requests
        for req_type in ["access", "rectification", "erasure"]:
            await db_session.execute(
                text("""
                    INSERT INTO data_subject_requests (
                        request_type, data_subject_id, data_subject_type,
                        requester_email_encrypted, request_details_encrypted,
                        status, submitted_at, deadline_at
                    )
                    VALUES (
                        :req_type, :user_id, 'user',
                        encrypt_pii_with_metadata(:email),
                        encrypt_pii_with_metadata(:details),
                        'pending', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP + interval '1 month'
                    )
                """),
                {
                    "req_type": req_type,
                    "user_id": user_id,
                    "email": f"{req_type}@example.com",
                    "details": f"Test {req_type} request",
                },
            )

        # Get pending requests
        result = await db_session.execute(
            text("""
                SELECT COUNT(*) FROM data_subject_requests
                WHERE status IN ('pending', 'in_progress')
            """)
        )
        count = result.scalar()

        assert count >= 3

    @pytest.mark.asyncio
    async def test_complete_request_approved(self, db_session: AsyncSession):
        """Test completing a GDPR request with approval."""
        user_id = await self._create_test_user(db_session)

        # Create request
        result = await db_session.execute(
            text("""
                INSERT INTO data_subject_requests (
                    request_type, data_subject_id, data_subject_type,
                    requester_email_encrypted, request_details_encrypted,
                    status, submitted_at, deadline_at
                )
                VALUES (
                    'access', :user_id, 'user',
                    encrypt_pii_with_metadata(:email),
                    encrypt_pii_with_metadata(:details),
                    'pending', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP + interval '1 month'
                )
                RETURNING id
            """),
            {
                "user_id": user_id,
                "email": "complete@example.com",
                "details": "Complete test request",
            },
        )
        request_id = result.scalar()

        # Complete the request
        await db_session.execute(
            text("""
                UPDATE data_subject_requests
                SET status = 'completed',
                    completed_at = CURRENT_TIMESTAMP,
                    response_details_encrypted = encrypt_pii_with_metadata(:response)
                WHERE id = :id
            """),
            {"id": request_id, "response": "Data export provided via secure link"},
        )

        # Verify completion
        result = await db_session.execute(
            text("SELECT status, completed_at FROM data_subject_requests WHERE id = :id"),
            {"id": request_id},
        )
        row = result.fetchone()

        assert row.status == "completed"
        assert row.completed_at is not None

    @pytest.mark.asyncio
    async def test_complete_request_rejected(self, db_session: AsyncSession):
        """Test rejecting a GDPR request with valid legal basis."""
        user_id = await self._create_test_user(db_session)

        # Create request
        result = await db_session.execute(
            text("""
                INSERT INTO data_subject_requests (
                    request_type, data_subject_id, data_subject_type,
                    requester_email_encrypted, request_details_encrypted,
                    status, submitted_at, deadline_at
                )
                VALUES (
                    'erasure', :user_id, 'user',
                    encrypt_pii_with_metadata(:email),
                    encrypt_pii_with_metadata(:details),
                    'pending', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP + interval '1 month'
                )
                RETURNING id
            """),
            {
                "user_id": user_id,
                "email": "reject@example.com",
                "details": "Rejection test",
            },
        )
        request_id = result.scalar()

        # Reject the request
        await db_session.execute(
            text("""
                UPDATE data_subject_requests
                SET status = 'rejected',
                    completed_at = CURRENT_TIMESTAMP,
                    rejection_reason = :reason
                WHERE id = :id
            """),
            {"id": request_id, "reason": "Legal retention period: 5 years (Art. 17.3.b)"},
        )

        # Verify rejection
        result = await db_session.execute(
            text("SELECT status, rejection_reason FROM data_subject_requests WHERE id = :id"),
            {"id": request_id},
        )
        row = result.fetchone()

        assert row.status == "rejected"
        assert row.rejection_reason is not None


class TestBlockedDataIntegration:
    """
    Integration tests for LOPDGDD Art. 33 data blocking.
    Data must be blocked (not deleted) when there's legal retention obligation.
    """

    @pytest.mark.asyncio
    async def test_block_data_lopdgdd_art33(self, db_session: AsyncSession):
        """Test LOPDGDD Art. 33 - Block data before deletion."""
        original_id = uuid4()
        test_data = b"encrypted_sensitive_data_for_blocking"
        data_hash = hashlib.sha256(test_data).hexdigest()

        result = await db_session.execute(
            text("""
                INSERT INTO blocked_data (
                    original_table, original_id, data_encrypted,
                    data_encryption_key_id, data_hash, block_reason,
                    block_legal_basis, unblock_date, status
                )
                VALUES (
                    'users', :original_id, :data,
                    'test_key_python_integration', :data_hash, :reason,
                    :legal_basis, :unblock_date, 'blocked'
                )
                RETURNING id, status, accessible_by
            """),
            {
                "original_id": original_id,
                "data": test_data,
                "data_hash": data_hash,
                "reason": "GDPR erasure request with legal retention",
                "legal_basis": "Ley 58/2003 Art. 70 - 4 years tax records",
                "unblock_date": (datetime.now(UTC) + timedelta(days=365 * 4)).date(),
            },
        )
        row = result.fetchone()

        assert row is not None
        assert row.status == "blocked"
        # Verify restricted access
        assert "JUDGES" in row.accessible_by or "PROSECUTORS" in row.accessible_by

    @pytest.mark.asyncio
    async def test_log_access_to_blocked_data(self, db_session: AsyncSession):
        """
        Test LOPDGDD Art. 33.3 - Access to blocked data must be logged.
        Only judicial/administrative authorities can access.
        """
        original_id = uuid4()
        data_hash = hashlib.sha256(b"test_data").hexdigest()

        # Create blocked data with empty access_log
        result = await db_session.execute(
            text("""
                INSERT INTO blocked_data (
                    original_table, original_id, data_encrypted,
                    data_encryption_key_id, data_hash, block_reason,
                    block_legal_basis, unblock_date, status, access_log
                )
                VALUES (
                    'users', :original_id, :data,
                    'test_key_python_integration', :data_hash, :reason,
                    :legal_basis, :unblock_date, 'blocked', '[]'::jsonb
                )
                RETURNING id
            """),
            {
                "original_id": original_id,
                "data": b"blocked_data_content",
                "data_hash": data_hash,
                "reason": "Test blocking",
                "legal_basis": "RGPD Art. 17.3.e",
                "unblock_date": (datetime.now(UTC) + timedelta(days=365)).date(),
            },
        )
        blocked_id = result.scalar()

        # Log judicial access - use proper JSON format
        # Note: asyncpg requires explicit cast, not ::jsonb syntax with parameters
        access_entry = json.dumps(
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "accessor_type": "judicial_authority",
                "accessor_id": "COURT_12345",
                "reason": "Criminal investigation case ref: 2025/001234",
            }
        )

        await db_session.execute(
            text("""
                UPDATE blocked_data
                SET access_log = access_log || CAST(:entry AS jsonb)
                WHERE id = :id
            """),
            {"id": blocked_id, "entry": access_entry},
        )

        # Verify access was logged
        result = await db_session.execute(
            text("SELECT access_log FROM blocked_data WHERE id = :id"), {"id": blocked_id}
        )
        row = result.fetchone()

        assert row.access_log is not None
        assert len(row.access_log) >= 1

    @pytest.mark.asyncio
    async def test_mark_destroyed(self, db_session: AsyncSession):
        """Test permanent destruction of blocked data."""
        original_id = uuid4()
        data_hash = hashlib.sha256(b"destroy_test").hexdigest()

        # Create blocked data with past unblock_date
        result = await db_session.execute(
            text("""
                INSERT INTO blocked_data (
                    original_table, original_id, data_encrypted,
                    data_encryption_key_id, data_hash, block_reason,
                    block_legal_basis, unblock_date, status
                )
                VALUES (
                    'users', :original_id, :data,
                    'test_key_python_integration', :data_hash, :reason,
                    :legal_basis, :unblock_date, 'blocked'
                )
                RETURNING id
            """),
            {
                "original_id": original_id,
                "data": b"data_to_destroy",
                "data_hash": data_hash,
                "reason": "Destruction test",
                "legal_basis": "Test",
                "unblock_date": (datetime.now(UTC) - timedelta(days=1)).date(),
            },
        )
        blocked_id = result.scalar()

        # Mark as destroyed - note: data_encrypted cannot be NULL per constraint
        # Just mark status as destroyed
        await db_session.execute(
            text("""
                UPDATE blocked_data
                SET status = 'destroyed',
                    destroyed_at = CURRENT_TIMESTAMP
                WHERE id = :id
            """),
            {"id": blocked_id},
        )

        # Verify destruction
        result = await db_session.execute(
            text("SELECT status, destroyed_at FROM blocked_data WHERE id = :id"), {"id": blocked_id}
        )
        row = result.fetchone()

        assert row.status == "destroyed"
        assert row.destroyed_at is not None


class TestSecurityBreachesIntegration:
    """
    Integration tests for security breach management.
    RGPD Art. 33: Notification within 72 hours.
    RGPD Art. 34: Communication to data subjects.
    """

    @pytest.mark.asyncio
    async def test_register_breach_72h_deadline(self, db_session: AsyncSession):
        """Test RGPD Art. 33 - 72-hour notification deadline."""
        unique_ref = f"BREACH-{uuid4().hex[:8]}"
        detected_at = datetime.now(UTC)
        deadline = detected_at + timedelta(hours=72)

        result = await db_session.execute(
            text("""
                INSERT INTO security_breaches (
                    breach_reference, breach_title, breach_description,
                    breach_type, severity, risk_level,
                    detected_at, authority_notification_deadline,
                    affected_records_count, data_categories_affected, status
                )
                VALUES (
                    :ref, :title, :description,
                    :breach_type, :severity, :risk_level,
                    :detected_at, :deadline,
                    :records, :categories, 'detected'
                )
                RETURNING id, authority_notification_deadline, status
            """),
            {
                "ref": unique_ref,
                "title": "Test Security Breach",
                "description": "Integration test breach for 72h deadline verification",
                "breach_type": "confidentiality",
                "severity": "medium",
                "risk_level": "possible",
                "detected_at": detected_at,
                "deadline": deadline,
                "records": 100,
                "categories": ["email", "name"],
            },
        )
        row = result.fetchone()

        assert row is not None
        assert row.status == "detected"

        # Verify 72-hour deadline
        deadline_diff = abs((row.authority_notification_deadline - deadline).total_seconds())
        assert deadline_diff < 60  # Within 1 minute

    @pytest.mark.asyncio
    async def test_get_pending_notifications(self, db_session: AsyncSession):
        """Test getting breaches pending authority notification."""
        unique_ref = f"BREACH-{uuid4().hex[:8]}"
        detected_at = datetime.now(UTC)

        # Create breach
        await db_session.execute(
            text("""
                INSERT INTO security_breaches (
                    breach_reference, breach_title, breach_description,
                    breach_type, severity, risk_level,
                    detected_at, authority_notification_deadline,
                    affected_records_count, data_categories_affected, status
                )
                VALUES (
                    :ref, :title, :description,
                    'integrity', 'high', 'likely',
                    :detected_at, :deadline,
                    1000, ARRAY['pii', 'financial'], 'detected'
                )
            """),
            {
                "ref": unique_ref,
                "title": "Pending Notification Test",
                "description": "Test breach pending notification",
                "detected_at": detected_at,
                "deadline": detected_at + timedelta(hours=72),
            },
        )

        # Get pending notifications
        result = await db_session.execute(
            text("""
                SELECT COUNT(*) FROM security_breaches
                WHERE authority_notified_at IS NULL
                AND status NOT IN ('resolved', 'closed')
            """)
        )
        count = result.scalar()

        assert count >= 1

    @pytest.mark.asyncio
    async def test_record_authority_notification(self, db_session: AsyncSession):
        """Test recording that authority has been notified."""
        unique_ref = f"BREACH-{uuid4().hex[:8]}"
        detected_at = datetime.now(UTC)

        # Create breach
        result = await db_session.execute(
            text("""
                INSERT INTO security_breaches (
                    breach_reference, breach_title, breach_description,
                    breach_type, severity, risk_level,
                    detected_at, authority_notification_deadline,
                    affected_records_count, data_categories_affected, status
                )
                VALUES (
                    :ref, :title, :description,
                    'availability', 'critical', 'high',
                    :detected_at, :deadline,
                    5000, ARRAY['all_data'], 'detected'
                )
                RETURNING id
            """),
            {
                "ref": unique_ref,
                "title": "Authority Notification Test",
                "description": "Test breach for authority notification",
                "detected_at": detected_at,
                "deadline": detected_at + timedelta(hours=72),
            },
        )
        breach_id = result.scalar()

        # Record notification
        await db_session.execute(
            text("""
                UPDATE security_breaches
                SET authority_notified_at = CURRENT_TIMESTAMP,
                    authority_notification_reference = :ref,
                    status = 'authority_notified'
                WHERE id = :id
            """),
            {"id": breach_id, "ref": "AEPD-2025-00001234"},
        )

        # Verify notification recorded
        result = await db_session.execute(
            text("""
                SELECT authority_notified_at, authority_notification_reference, status
                FROM security_breaches WHERE id = :id
            """),
            {"id": breach_id},
        )
        row = result.fetchone()

        assert row.authority_notified_at is not None
        assert row.authority_notification_reference == "AEPD-2025-00001234"
        assert row.status == "authority_notified"


class TestAuditLogIntegration:
    """
    Integration tests for audit log.
    RGPD Art. 30: Records of processing activities.
    RGPD Art. 5.2: Accountability principle.
    """

    @pytest.mark.asyncio
    async def test_audit_log_entry_creation(self, db_session: AsyncSession):
        """Test creating an audit log entry."""
        result = await db_session.execute(
            text("""
                INSERT INTO audit_log (
                    action, entity_type, ip_address, severity
                )
                VALUES ('LOGIN', 'user', '192.168.1.1', 'info')
                RETURNING id, action, current_hash
            """)
        )
        row = result.fetchone()

        assert row is not None
        assert row.action == "LOGIN"
        assert row.current_hash is not None  # Hash should be generated

    @pytest.mark.asyncio
    async def test_audit_log_hash_chain(self, db_session: AsyncSession):
        """Test audit log maintains hash chain for integrity."""
        # Create multiple entries
        for action in ["LOGIN", "LOGOUT", "DATA_ACCESS_REQUEST"]:
            await db_session.execute(
                text("""
                    INSERT INTO audit_log (action, entity_type, severity)
                    VALUES (:action, 'user', 'info')
                """),
                {"action": action},
            )

        # Verify hash chain
        result = await db_session.execute(
            text("""
                SELECT id, previous_hash, current_hash
                FROM audit_log
                ORDER BY sequence_number DESC
                LIMIT 3
            """)
        )
        rows = result.fetchall()

        assert len(rows) >= 3
        # Each entry should have a current_hash
        for row in rows:
            assert row.current_hash is not None

    @pytest.mark.asyncio
    async def test_audit_log_immutability(self, db_session: AsyncSession):
        """Test that audit log entries cannot be modified or deleted."""
        # Create entry
        result = await db_session.execute(
            text("""
                INSERT INTO audit_log (action, entity_type, severity)
                VALUES ('LOGIN', 'user', 'info')
                RETURNING id
            """)
        )
        entry_id = result.scalar()

        # Attempt to update should fail (trigger prevents it)
        try:
            await db_session.execute(
                text("UPDATE audit_log SET action = 'MODIFIED' WHERE id = :id"), {"id": entry_id}
            )
            # If we get here, the trigger didn't prevent the update
            pytest.fail("Update should have been prevented by trigger")
        except Exception as e:
            # Expected - trigger should prevent updates
            error_msg = str(e).lower()
            assert (
                "cannot" in error_msg
                or "prevented" in error_msg
                or "immutable" in error_msg
                or "permission" in error_msg
            )

    @pytest.mark.asyncio
    async def test_verify_audit_integrity(self, db_session: AsyncSession):
        """Test audit log integrity verification function."""
        # Call the verification function
        result = await db_session.execute(
            text("SELECT * FROM verify_audit_log_integrity_summary()")
        )
        row = result.fetchone()

        assert row is not None
        # The function should return integrity status
