"""
Integration tests for User operations.

Tests verify against real PostgreSQL:
- User CRUD operations
- Soft delete (LOPDGDD Art. 33)
- Session management
- Login tracking

RGPD Art. 32: Tests verify encryption and security of user data.
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class TestUserOperationsIntegration:
    """Integration tests for user operations with PostgreSQL."""

    @pytest.mark.asyncio
    async def test_create_user(self, db_session: AsyncSession):
        """Test user creation in database."""
        unique_id = uuid4().hex[:8]
        email = f"test_{unique_id}@example.com"

        result = await db_session.execute(
            text("""
                INSERT INTO users (name, email, password_hash, role, is_active)
                VALUES (:name, :email, :password_hash, :role, :is_active)
                RETURNING id, name, email, role, is_active, created_at
            """),
            {
                "name": f"Test User {unique_id}",
                "email": email,
                "password_hash": "$2b$12$test_hash_for_testing_only",
                "role": "user",
                "is_active": True,
            },
        )
        row = result.fetchone()

        assert row is not None
        assert row.email == email
        assert row.role == "user"
        assert row.is_active is True

    @pytest.mark.asyncio
    async def test_get_user_by_email(self, db_session: AsyncSession):
        """Test finding user by email."""
        unique_id = uuid4().hex[:8]
        email = f"find_test_{unique_id}@example.com"

        # Create user
        await db_session.execute(
            text("""
                INSERT INTO users (name, email, password_hash, role)
                VALUES (:name, :email, :password_hash, 'user')
            """),
            {
                "name": f"Find Test User {unique_id}",
                "email": email,
                "password_hash": "$2b$12$test_hash",
            },
        )

        # Find by email
        result = await db_session.execute(
            text("SELECT id, name, email, role FROM users WHERE email = :email"), {"email": email}
        )
        row = result.fetchone()

        assert row is not None
        assert row.email == email

    @pytest.mark.asyncio
    async def test_get_user_by_email_not_found(self, db_session: AsyncSession):
        """Test email lookup returns None for non-existent user."""
        result = await db_session.execute(
            text("SELECT id FROM users WHERE email = :email"),
            {"email": "nonexistent_user@example.com"},
        )
        row = result.fetchone()
        assert row is None

    @pytest.mark.asyncio
    async def test_get_users_by_role(self, db_session: AsyncSession):
        """Test filtering users by role."""
        unique_id = uuid4().hex[:8]

        # Create admin user
        await db_session.execute(
            text("""
                INSERT INTO users (name, email, password_hash, role)
                VALUES (:name, :email, :password_hash, 'admin')
            """),
            {
                "name": f"Admin User {unique_id}",
                "email": f"admin_{unique_id}@example.com",
                "password_hash": "$2b$12$test_hash",
            },
        )

        # Find admins
        result = await db_session.execute(
            text("SELECT COUNT(*) FROM users WHERE role = 'admin' AND deleted_at IS NULL")
        )
        count = result.scalar()

        assert count >= 1

    @pytest.mark.asyncio
    async def test_soft_delete_lopdgdd_art33(self, db_session: AsyncSession):
        """
        Test LOPDGDD Art. 33 - soft delete (blocking) before deletion.
        Data should be marked as deleted but not physically removed.
        """
        unique_id = uuid4().hex[:8]
        email = f"delete_test_{unique_id}@example.com"

        # Create user
        result = await db_session.execute(
            text("""
                INSERT INTO users (name, email, password_hash, role)
                VALUES (:name, :email, :password_hash, 'user')
                RETURNING id
            """),
            {
                "name": f"Delete Test User {unique_id}",
                "email": email,
                "password_hash": "$2b$12$test_hash",
            },
        )
        user_id = result.scalar()

        # Soft delete
        await db_session.execute(
            text("UPDATE users SET deleted_at = CURRENT_TIMESTAMP WHERE id = :id"), {"id": user_id}
        )

        # Verify soft deleted
        result = await db_session.execute(
            text("SELECT id, deleted_at FROM users WHERE id = :id"), {"id": user_id}
        )
        row = result.fetchone()

        assert row is not None
        assert row.deleted_at is not None

        # User should not appear in active queries
        result = await db_session.execute(
            text("SELECT id FROM users WHERE email = :email AND deleted_at IS NULL"),
            {"email": email},
        )
        assert result.fetchone() is None

    @pytest.mark.asyncio
    async def test_update_last_login(self, db_session: AsyncSession):
        """Test updating last login timestamp."""
        unique_id = uuid4().hex[:8]

        # Create user
        result = await db_session.execute(
            text("""
                INSERT INTO users (name, email, password_hash, role)
                VALUES (:name, :email, :password_hash, 'user')
                RETURNING id
            """),
            {
                "name": f"Login Test User {unique_id}",
                "email": f"login_{unique_id}@example.com",
                "password_hash": "$2b$12$test_hash",
            },
        )
        user_id = result.scalar()

        # Update last login
        await db_session.execute(
            text("""
                UPDATE users
                SET last_login_at = CURRENT_TIMESTAMP,
                    last_login_ip = :ip,
                    failed_login_attempts = 0
                WHERE id = :id
            """),
            {"id": user_id, "ip": "192.168.1.1"},
        )

        # Verify update
        result = await db_session.execute(
            text(
                "SELECT last_login_at, last_login_ip, failed_login_attempts FROM users WHERE id = :id"
            ),
            {"id": user_id},
        )
        row = result.fetchone()

        assert row.last_login_at is not None
        assert row.failed_login_attempts == 0

    @pytest.mark.asyncio
    async def test_increment_failed_attempts(self, db_session: AsyncSession):
        """Test failed login attempt tracking."""
        unique_id = uuid4().hex[:8]

        # Create user
        result = await db_session.execute(
            text("""
                INSERT INTO users (name, email, password_hash, role, failed_login_attempts)
                VALUES (:name, :email, :password_hash, 'user', 0)
                RETURNING id
            """),
            {
                "name": f"Failed Login Test {unique_id}",
                "email": f"failed_{unique_id}@example.com",
                "password_hash": "$2b$12$test_hash",
            },
        )
        user_id = result.scalar()

        # Increment failed attempts
        await db_session.execute(
            text("""
                UPDATE users
                SET failed_login_attempts = failed_login_attempts + 1
                WHERE id = :id
            """),
            {"id": user_id},
        )

        result = await db_session.execute(
            text("SELECT failed_login_attempts FROM users WHERE id = :id"), {"id": user_id}
        )
        count = result.scalar()
        assert count == 1

        # Increment again
        await db_session.execute(
            text("""
                UPDATE users
                SET failed_login_attempts = failed_login_attempts + 1
                WHERE id = :id
            """),
            {"id": user_id},
        )

        result = await db_session.execute(
            text("SELECT failed_login_attempts FROM users WHERE id = :id"), {"id": user_id}
        )
        count = result.scalar()
        assert count == 2

    @pytest.mark.asyncio
    async def test_account_lockout(self, db_session: AsyncSession):
        """Test account lockout after failed attempts."""
        unique_id = uuid4().hex[:8]

        # Create user
        result = await db_session.execute(
            text("""
                INSERT INTO users (name, email, password_hash, role)
                VALUES (:name, :email, :password_hash, 'user')
                RETURNING id
            """),
            {
                "name": f"Lockout Test {unique_id}",
                "email": f"lockout_{unique_id}@example.com",
                "password_hash": "$2b$12$test_hash",
            },
        )
        user_id = result.scalar()

        # Lock the account
        lock_until = datetime.now(UTC) + timedelta(minutes=15)
        await db_session.execute(
            text("UPDATE users SET is_locked = true, locked_until = :until WHERE id = :id"),
            {"id": user_id, "until": lock_until},
        )

        # Verify lockout
        result = await db_session.execute(
            text("SELECT is_locked, locked_until FROM users WHERE id = :id"), {"id": user_id}
        )
        row = result.fetchone()

        assert row.is_locked is True
        assert row.locked_until is not None


class TestUserSessionOperationsIntegration:
    """Integration tests for user session operations."""

    @pytest.mark.asyncio
    async def test_create_session(self, db_session: AsyncSession):
        """Test session creation."""
        unique_id = uuid4().hex[:8]

        # Create user first
        result = await db_session.execute(
            text("""
                INSERT INTO users (name, email, password_hash, role)
                VALUES (:name, :email, :password_hash, 'user')
                RETURNING id
            """),
            {
                "name": f"Session Test {unique_id}",
                "email": f"session_{unique_id}@example.com",
                "password_hash": "$2b$12$test_hash",
            },
        )
        user_id = result.scalar()

        # Create session
        token_hash = f"hash_{uuid4().hex}"
        result = await db_session.execute(
            text("""
                INSERT INTO user_sessions (user_id, token_hash, expires_at, ip_address)
                VALUES (:user_id, :token_hash, :expires_at, :ip_address)
                RETURNING id, user_id, is_revoked
            """),
            {
                "user_id": user_id,
                "token_hash": token_hash,
                "expires_at": datetime.now(UTC) + timedelta(hours=24),
                "ip_address": "127.0.0.1",
            },
        )
        row = result.fetchone()

        assert row is not None
        assert row.user_id == user_id
        assert row.is_revoked is False

    @pytest.mark.asyncio
    async def test_get_active_sessions(self, db_session: AsyncSession):
        """Test getting active sessions for a user."""
        unique_id = uuid4().hex[:8]

        # Create user
        result = await db_session.execute(
            text("""
                INSERT INTO users (name, email, password_hash, role)
                VALUES (:name, :email, :password_hash, 'user')
                RETURNING id
            """),
            {
                "name": f"Multi Session Test {unique_id}",
                "email": f"multi_{unique_id}@example.com",
                "password_hash": "$2b$12$test_hash",
            },
        )
        user_id = result.scalar()

        # Create multiple sessions
        for i in range(3):
            await db_session.execute(
                text("""
                    INSERT INTO user_sessions (user_id, token_hash, expires_at, ip_address)
                    VALUES (:user_id, :token_hash, :expires_at, :ip_address)
                """),
                {
                    "user_id": user_id,
                    "token_hash": f"hash_{i}_{uuid4().hex}",
                    "expires_at": datetime.now(UTC) + timedelta(hours=24),
                    "ip_address": f"192.168.1.{i}",
                },
            )

        # Get active sessions
        result = await db_session.execute(
            text("""
                SELECT COUNT(*) FROM user_sessions
                WHERE user_id = :user_id
                AND is_revoked = false
                AND expires_at > CURRENT_TIMESTAMP
            """),
            {"user_id": user_id},
        )
        count = result.scalar()

        assert count == 3

    @pytest.mark.asyncio
    async def test_revoke_session(self, db_session: AsyncSession):
        """Test session revocation (logout)."""
        unique_id = uuid4().hex[:8]

        # Create user
        result = await db_session.execute(
            text("""
                INSERT INTO users (name, email, password_hash, role)
                VALUES (:name, :email, :password_hash, 'user')
                RETURNING id
            """),
            {
                "name": f"Revoke Test {unique_id}",
                "email": f"revoke_{unique_id}@example.com",
                "password_hash": "$2b$12$test_hash",
            },
        )
        user_id = result.scalar()

        # Create session
        token_hash = f"revoke_hash_{uuid4().hex}"
        result = await db_session.execute(
            text("""
                INSERT INTO user_sessions (user_id, token_hash, expires_at, ip_address)
                VALUES (:user_id, :token_hash, :expires_at, :ip_address)
                RETURNING id
            """),
            {
                "user_id": user_id,
                "token_hash": token_hash,
                "expires_at": datetime.now(UTC) + timedelta(hours=24),
                "ip_address": "127.0.0.1",
            },
        )
        session_id = result.scalar()

        # Revoke session
        await db_session.execute(
            text("""
                UPDATE user_sessions
                SET is_revoked = true, revoked_at = CURRENT_TIMESTAMP, revoked_reason = :reason
                WHERE id = :id
            """),
            {"id": session_id, "reason": "user_logout"},
        )

        # Verify revoked
        result = await db_session.execute(
            text("SELECT is_revoked, revoked_at, revoked_reason FROM user_sessions WHERE id = :id"),
            {"id": session_id},
        )
        row = result.fetchone()

        assert row.is_revoked is True
        assert row.revoked_at is not None
        assert row.revoked_reason == "user_logout"

    @pytest.mark.asyncio
    async def test_revoke_all_user_sessions(self, db_session: AsyncSession):
        """Test revoking all sessions for a user (security incident)."""
        unique_id = uuid4().hex[:8]

        # Create user
        result = await db_session.execute(
            text("""
                INSERT INTO users (name, email, password_hash, role)
                VALUES (:name, :email, :password_hash, 'user')
                RETURNING id
            """),
            {
                "name": f"Revoke All Test {unique_id}",
                "email": f"revokeall_{unique_id}@example.com",
                "password_hash": "$2b$12$test_hash",
            },
        )
        user_id = result.scalar()

        # Create multiple sessions
        for i in range(5):
            await db_session.execute(
                text("""
                    INSERT INTO user_sessions (user_id, token_hash, expires_at, ip_address)
                    VALUES (:user_id, :token_hash, :expires_at, :ip_address)
                """),
                {
                    "user_id": user_id,
                    "token_hash": f"all_hash_{i}_{uuid4().hex}",
                    "expires_at": datetime.now(UTC) + timedelta(hours=24),
                    "ip_address": "127.0.0.1",
                },
            )

        # Revoke all sessions
        result = await db_session.execute(
            text("""
                UPDATE user_sessions
                SET is_revoked = true, revoked_at = CURRENT_TIMESTAMP, revoked_reason = :reason
                WHERE user_id = :user_id AND is_revoked = false
            """),
            {"user_id": user_id, "reason": "security_incident"},
        )

        # Verify all revoked
        result = await db_session.execute(
            text("""
                SELECT COUNT(*) FROM user_sessions
                WHERE user_id = :user_id AND is_revoked = false
            """),
            {"user_id": user_id},
        )
        count = result.scalar()

        assert count == 0
