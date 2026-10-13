"""
Integration tests for Robinson List operations.

Tests verify compliance with:
- LOPDGDD Art. 34: Exclusion systems
- Orden ETD/1286/2022 Art. 4.1: Must check before commercial communications
- Orden ETD/1286/2022 Art. 4.2: Check valid for max 30 days
- Orden ETD/1286/2022 Art. 6: Must document all checks

These tests use real PostgreSQL to verify Robinson list workflow.
"""

import hashlib
from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class TestRobinsonCheckIntegration:
    """
    Integration tests for Robinson list checks.
    Orden ETD/1286/2022 compliance.
    """

    async def _create_test_user(self, db_session: AsyncSession) -> str:
        """Helper to create a test user for checked_by FK."""
        unique_id = uuid4().hex[:8]
        result = await db_session.execute(
            text("""
                INSERT INTO users (name, email, password_hash, role)
                VALUES (:name, :email, :password_hash, 'user')
                RETURNING id
            """),
            {
                "name": f"Robinson Test User {unique_id}",
                "email": f"robinson_{unique_id}@example.com",
                "password_hash": "$2b$12$test_hash",
            },
        )
        return result.scalar()

    @staticmethod
    def hash_phone_number(phone: str) -> str:
        """Hash phone number for lookup."""
        normalized = "".join(c for c in phone if c.isdigit())
        return hashlib.sha256(normalized.encode()).hexdigest()

    @pytest.mark.asyncio
    async def test_hash_phone_number_consistency(self):
        """Test phone number hashing is consistent."""
        phone = "+34600123456"

        hash1 = self.hash_phone_number(phone)
        hash2 = self.hash_phone_number(phone)

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex

    @pytest.mark.asyncio
    async def test_record_robinson_check(self, db_session: AsyncSession):
        """Test recording a Robinson list check."""
        user_id = await self._create_test_user(db_session)
        phone = "+34600000001"
        phone_hash = self.hash_phone_number(phone)

        result = await db_session.execute(
            text("""
                INSERT INTO robinson_checks (
                    phone_hash, is_registered, channel_checked, checked_by
                )
                VALUES (:phone_hash, :is_registered, :channel, :checked_by)
                RETURNING id, phone_hash, is_registered, valid_until
            """),
            {
                "phone_hash": phone_hash,
                "is_registered": False,
                "channel": "phone",
                "checked_by": user_id,
            },
        )
        row = result.fetchone()

        assert row is not None
        assert row.phone_hash == phone_hash
        assert row.is_registered is False
        # Trigger should set valid_until to 30 days from now
        assert row.valid_until is not None

    @pytest.mark.asyncio
    async def test_record_listed_phone(self, db_session: AsyncSession):
        """Test recording a phone that IS on the Robinson list."""
        user_id = await self._create_test_user(db_session)
        phone = "+34600000002"
        phone_hash = self.hash_phone_number(phone)

        result = await db_session.execute(
            text("""
                INSERT INTO robinson_checks (
                    phone_hash, is_registered, channel_checked, checked_by,
                    api_response_code
                )
                VALUES (:phone_hash, true, 'phone', :checked_by, 'LISTED')
                RETURNING is_registered, api_response_code
            """),
            {
                "phone_hash": phone_hash,
                "checked_by": user_id,
            },
        )
        row = result.fetchone()

        assert row.is_registered is True
        assert row.api_response_code == "LISTED"

    @pytest.mark.asyncio
    async def test_30_day_validity_orden_etd(self, db_session: AsyncSession):
        """
        Test Orden ETD/1286/2022 Art. 4.2 - Check valid for max 30 days.
        The trigger set_robinson_valid_until() should set valid_until.
        """
        user_id = await self._create_test_user(db_session)
        phone_hash = self.hash_phone_number("+34600000003")

        result = await db_session.execute(
            text("""
                INSERT INTO robinson_checks (
                    phone_hash, is_registered, channel_checked, checked_by
                )
                VALUES (:phone_hash, false, 'phone', :checked_by)
                RETURNING check_timestamp, valid_until
            """),
            {
                "phone_hash": phone_hash,
                "checked_by": user_id,
            },
        )
        row = result.fetchone()

        # Verify valid_until is approximately 30 days from check_timestamp
        if row.valid_until:
            expected_validity = row.check_timestamp + timedelta(days=30)
            validity_diff = abs((row.valid_until - expected_validity).total_seconds())
            assert validity_diff < 86400  # Within 1 day tolerance

    @pytest.mark.asyncio
    async def test_get_valid_check_for_phone(self, db_session: AsyncSession):
        """Test retrieving a valid (non-expired) check for a phone."""
        user_id = await self._create_test_user(db_session)
        phone_hash = self.hash_phone_number("+34600000004")

        # Record a check
        await db_session.execute(
            text("""
                INSERT INTO robinson_checks (
                    phone_hash, is_registered, channel_checked, checked_by
                )
                VALUES (:phone_hash, false, 'phone', :checked_by)
            """),
            {
                "phone_hash": phone_hash,
                "checked_by": user_id,
            },
        )

        # Retrieve valid check
        result = await db_session.execute(
            text("""
                SELECT id, is_registered, valid_until
                FROM robinson_checks
                WHERE phone_hash = :phone_hash
                AND (valid_until IS NULL OR valid_until > CURRENT_TIMESTAMP)
                ORDER BY check_timestamp DESC
                LIMIT 1
            """),
            {"phone_hash": phone_hash},
        )
        row = result.fetchone()

        assert row is not None
        assert row.is_registered is False

    @pytest.mark.asyncio
    async def test_can_contact_not_listed(self, db_session: AsyncSession):
        """Test determining if a phone can be contacted (not listed)."""
        user_id = await self._create_test_user(db_session)
        phone_hash = self.hash_phone_number("+34600000005")

        # Record check - not registered
        await db_session.execute(
            text("""
                INSERT INTO robinson_checks (
                    phone_hash, is_registered, channel_checked, checked_by
                )
                VALUES (:phone_hash, false, 'phone', :checked_by)
            """),
            {
                "phone_hash": phone_hash,
                "checked_by": user_id,
            },
        )

        # Check if can contact
        result = await db_session.execute(
            text("""
                SELECT
                    CASE
                        WHEN EXISTS (
                            SELECT 1 FROM robinson_checks
                            WHERE phone_hash = :phone_hash
                            AND is_registered = false
                            AND (valid_until IS NULL OR valid_until > CURRENT_TIMESTAMP)
                        )
                        THEN true
                        ELSE false
                    END as can_contact
            """),
            {"phone_hash": phone_hash},
        )
        can_contact = result.scalar()

        assert can_contact is True

    @pytest.mark.asyncio
    async def test_cannot_contact_if_listed(self, db_session: AsyncSession):
        """Test that listed phones cannot be contacted."""
        user_id = await self._create_test_user(db_session)
        phone_hash = self.hash_phone_number("+34600000006")

        # Record check - registered (listed)
        await db_session.execute(
            text("""
                INSERT INTO robinson_checks (
                    phone_hash, is_registered, channel_checked, checked_by
                )
                VALUES (:phone_hash, true, 'phone', :checked_by)
            """),
            {
                "phone_hash": phone_hash,
                "checked_by": user_id,
            },
        )

        # Check if can contact
        result = await db_session.execute(
            text("""
                SELECT
                    CASE
                        WHEN EXISTS (
                            SELECT 1 FROM robinson_checks
                            WHERE phone_hash = :phone_hash
                            AND is_registered = true
                            ORDER BY check_timestamp DESC
                            LIMIT 1
                        )
                        THEN false
                        ELSE true
                    END as can_contact
            """),
            {"phone_hash": phone_hash},
        )
        can_contact = result.scalar()

        assert can_contact is False

    @pytest.mark.asyncio
    async def test_record_check_for_campaign(self, db_session: AsyncSession):
        """Test recording check associated with a campaign."""
        user_id = await self._create_test_user(db_session)
        phone_hash = self.hash_phone_number("+34600000007")

        # Create campaign first (campaigns table doesn't have 'channel' column)
        result = await db_session.execute(
            text("""
                INSERT INTO campaigns (
                    name, description, status, user_id,
                    start_date, end_date
                )
                VALUES (
                    :name, 'Test campaign', 'draft', :user_id,
                    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP + interval '30 days'
                )
                RETURNING id
            """),
            {
                "name": f"Test Campaign {uuid4().hex[:8]}",
                "user_id": user_id,
            },
        )
        campaign_id = result.scalar()

        # Record check with campaign
        result = await db_session.execute(
            text("""
                INSERT INTO robinson_checks (
                    phone_hash, is_registered, channel_checked,
                    checked_by, campaign_id
                )
                VALUES (:phone_hash, false, 'phone', :checked_by, :campaign_id)
                RETURNING id, campaign_id
            """),
            {
                "phone_hash": phone_hash,
                "checked_by": user_id,
                "campaign_id": campaign_id,
            },
        )
        row = result.fetchone()

        assert row.campaign_id == campaign_id

    @pytest.mark.asyncio
    async def test_get_checks_for_campaign(self, db_session: AsyncSession):
        """Test retrieving all checks for a specific campaign."""
        user_id = await self._create_test_user(db_session)

        # Create campaign
        result = await db_session.execute(
            text("""
                INSERT INTO campaigns (
                    name, description, status, user_id,
                    start_date, end_date
                )
                VALUES (
                    :name, 'Multi-check campaign', 'draft', :user_id,
                    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP + interval '30 days'
                )
                RETURNING id
            """),
            {
                "name": f"Multi Check Campaign {uuid4().hex[:8]}",
                "user_id": user_id,
            },
        )
        campaign_id = result.scalar()

        # Record multiple checks
        for i in range(5):
            phone_hash = self.hash_phone_number(f"+3460010000{i}")
            await db_session.execute(
                text("""
                    INSERT INTO robinson_checks (
                        phone_hash, is_registered, channel_checked,
                        checked_by, campaign_id
                    )
                    VALUES (:phone_hash, :is_registered, 'phone', :checked_by, :campaign_id)
                """),
                {
                    "phone_hash": phone_hash,
                    "is_registered": (i % 2 == 0),  # Alternate
                    "checked_by": user_id,
                    "campaign_id": campaign_id,
                },
            )

        # Get checks for campaign
        result = await db_session.execute(
            text("""
                SELECT COUNT(*) FROM robinson_checks
                WHERE campaign_id = :campaign_id
            """),
            {"campaign_id": campaign_id},
        )
        count = result.scalar()

        assert count == 5

    @pytest.mark.asyncio
    async def test_get_compliance_stats(self, db_session: AsyncSession):
        """Test Robinson check compliance statistics."""
        user_id = await self._create_test_user(db_session)

        # Create some checks
        for i in range(10):
            phone_hash = self.hash_phone_number(f"+3460020000{i}")
            await db_session.execute(
                text("""
                    INSERT INTO robinson_checks (
                        phone_hash, is_registered, channel_checked, checked_by
                    )
                    VALUES (:phone_hash, :is_registered, 'phone', :checked_by)
                """),
                {
                    "phone_hash": phone_hash,
                    "is_registered": (i < 3),  # 3 registered, 7 not
                    "checked_by": user_id,
                },
            )

        # Get stats
        result = await db_session.execute(
            text("""
                SELECT
                    COUNT(*) as total_checks,
                    COUNT(*) FILTER (WHERE is_registered = true) as registered_count,
                    COUNT(*) FILTER (WHERE is_registered = false) as not_registered_count,
                    COUNT(DISTINCT phone_hash) as unique_phones
                FROM robinson_checks
            """)
        )
        row = result.fetchone()

        assert row.total_checks >= 10
        assert row.registered_count >= 3
        assert row.not_registered_count >= 7


class TestRobinsonComplianceWorkflow:
    """
    End-to-end workflow tests for Robinson list compliance.
    """

    async def _create_test_user(self, db_session: AsyncSession) -> str:
        """Helper to create a test user."""
        unique_id = uuid4().hex[:8]
        result = await db_session.execute(
            text("""
                INSERT INTO users (name, email, password_hash, role)
                VALUES (:name, :email, :password_hash, 'user')
                RETURNING id
            """),
            {
                "name": f"Workflow Test User {unique_id}",
                "email": f"workflow_{unique_id}@example.com",
                "password_hash": "$2b$12$test_hash",
            },
        )
        return result.scalar()

    @staticmethod
    def hash_phone(phone: str) -> str:
        """Hash phone for Robinson lookup."""
        normalized = "".join(c for c in phone if c.isdigit())
        return hashlib.sha256(normalized.encode()).hexdigest()

    @pytest.mark.asyncio
    async def test_full_robinson_workflow(self, db_session: AsyncSession):
        """
        Test complete workflow:
        1. Create campaign
        2. Check numbers against Robinson
        3. Count excluded numbers
        4. Verify compliance
        """
        user_id = await self._create_test_user(db_session)

        # 1. Create campaign
        result = await db_session.execute(
            text("""
                INSERT INTO campaigns (
                    name, description, status, user_id,
                    start_date, end_date
                )
                VALUES (
                    :name, 'Workflow test campaign', 'draft', :user_id,
                    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP + interval '30 days'
                )
                RETURNING id
            """),
            {
                "name": f"Workflow Campaign {uuid4().hex[:8]}",
                "user_id": user_id,
            },
        )
        campaign_id = result.scalar()

        # 2. Simulate checking multiple numbers
        test_numbers = [
            ("+34600400001", False),  # Not listed
            ("+34600400002", True),  # Listed - BLOCKED
            ("+34600400003", False),  # Not listed
            ("+34600400004", True),  # Listed - BLOCKED
            ("+34600400005", False),  # Not listed
        ]

        for phone, is_registered in test_numbers:
            phone_hash = self.hash_phone(phone)
            await db_session.execute(
                text("""
                    INSERT INTO robinson_checks (
                        phone_hash, is_registered, channel_checked,
                        checked_by, campaign_id
                    )
                    VALUES (:phone_hash, :is_registered, 'phone', :checked_by, :campaign_id)
                """),
                {
                    "phone_hash": phone_hash,
                    "is_registered": is_registered,
                    "checked_by": user_id,
                    "campaign_id": campaign_id,
                },
            )

        # 3. Count excluded numbers (registered in Robinson)
        result = await db_session.execute(
            text("""
                SELECT
                    COUNT(*) FILTER (WHERE is_registered = true) as excluded,
                    COUNT(*) FILTER (WHERE is_registered = false) as contactable
                FROM robinson_checks
                WHERE campaign_id = :campaign_id
            """),
            {"campaign_id": campaign_id},
        )
        row = result.fetchone()

        assert row.excluded == 2  # 2 were listed
        assert row.contactable == 3  # 3 can be contacted

        # 4. Verify individual checks
        for phone, expected_registered in test_numbers:
            phone_hash = self.hash_phone(phone)
            result = await db_session.execute(
                text("""
                    SELECT is_registered FROM robinson_checks
                    WHERE phone_hash = :phone_hash
                    AND campaign_id = :campaign_id
                """),
                {"phone_hash": phone_hash, "campaign_id": campaign_id},
            )
            is_registered = result.scalar()
            assert is_registered == expected_registered

    @pytest.mark.asyncio
    async def test_expired_check_requires_refresh(self, db_session: AsyncSession):
        """
        Test that expired checks are not considered valid.
        Orden ETD/1286/2022 requires fresh checks.
        """
        user_id = await self._create_test_user(db_session)
        unique_suffix = uuid4().hex[:8]
        phone_hash_unique = hashlib.sha256(f"+34600500001_{unique_suffix}".encode()).hexdigest()

        # Create a check - valid_until is set by trigger (30 days from now)
        # Then update to make it expired
        result = await db_session.execute(
            text("""
                INSERT INTO robinson_checks (
                    phone_hash, is_registered, channel_checked, checked_by
                )
                VALUES (
                    :phone_hash, false, 'phone', :checked_by
                )
                RETURNING id
            """),
            {
                "phone_hash": phone_hash_unique,
                "checked_by": user_id,
            },
        )
        check_id = result.scalar()

        # Update to set expired date (bypass trigger by direct update)
        await db_session.execute(
            text("""
                UPDATE robinson_checks
                SET valid_until = CURRENT_TIMESTAMP - interval '1 day'
                WHERE id = :id
            """),
            {"id": check_id},
        )

        # Try to find valid check - should not find expired one
        result = await db_session.execute(
            text("""
                SELECT id FROM robinson_checks
                WHERE phone_hash = :phone_hash
                AND valid_until > CURRENT_TIMESTAMP
            """),
            {"phone_hash": phone_hash_unique},
        )
        row = result.fetchone()

        # No valid check should be found
        assert row is None
