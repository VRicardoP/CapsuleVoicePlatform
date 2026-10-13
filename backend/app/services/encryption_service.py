"""Encryption service for PII data handling.

This service delegates encryption to PostgreSQL functions to maintain
consistency with the database's encryption scheme (AES-256-CBC + HMAC-SHA256).

IMPORTANT: All PII encryption/decryption happens in PostgreSQL, NOT in Python.
This ensures:
1. Single source of truth for encryption keys (secure_keys table)
2. Consistent encryption format across all data
3. Keys never leave the database server
4. Compliance with RGPD Art. 32 (encryption at rest)

The backend sends plaintext to PostgreSQL functions which handle encryption.
The backend receives JSONB with encrypted data structure.
"""

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class EncryptionService:
    """Service for handling encrypted PII data via PostgreSQL functions.

    All encryption operations are delegated to PostgreSQL to ensure:
    - Keys remain in secure_keys table (never exposed to application)
    - Consistent AES-256-CBC + HMAC-SHA256 encryption
    - Proper authentication tags for data integrity
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def encrypt_pii(self, plaintext: str) -> dict[str, Any] | None:
        """Encrypt PII data using PostgreSQL's encrypt_pii_with_metadata.

        Args:
            plaintext: The sensitive data to encrypt

        Returns:
            JSONB structure with encrypted data:
            {
                "c": "<base64 ciphertext>",
                "iv": "<base64 IV>",
                "tag": "<base64 HMAC tag>",
                "alg": "AES-256-CBC+HMAC-SHA256",
                "kid": "<key_id>",
                "v": <key_version>
            }
        """
        if not plaintext:
            return None

        result = await self.session.execute(
            text("SELECT encrypt_pii_with_metadata(:data)"),
            {"data": plaintext},
        )
        return result.scalar()

    async def decrypt_pii(self, encrypted_data: dict[str, Any]) -> str | None:
        """Decrypt PII data using PostgreSQL's decrypt_pii_with_metadata.

        Args:
            encrypted_data: JSONB structure from encrypt_pii

        Returns:
            Decrypted plaintext or None if decryption fails
        """
        if not encrypted_data:
            return None

        result = await self.session.execute(
            text("SELECT decrypt_pii_with_metadata(:data::jsonb)"),
            {"data": encrypted_data},
        )
        return result.scalar()

    async def encrypt_field(self, table: str, field: str, value: str) -> dict[str, Any]:
        """Encrypt a specific field value for database storage.

        This is a convenience method that wraps encrypt_pii for clarity.

        Args:
            table: Table name (for logging/audit)
            field: Field name (for logging/audit)
            value: Value to encrypt

        Returns:
            Encrypted JSONB structure
        """
        return await self.encrypt_pii(value)

    async def verify_encryption_key_active(self) -> bool:
        """Verify that an active encryption key exists.

        This should be called during application startup to ensure
        the database is properly configured.

        Returns:
            True if active key exists, False otherwise
        """
        result = await self.session.execute(
            text("""
                SELECT EXISTS (
                    SELECT 1 FROM encryption_keys
                    WHERE is_active = true
                )
            """)
        )
        return result.scalar() or False

    async def get_encryption_key_info(self) -> dict[str, Any] | None:
        """Get metadata about the active encryption key (not the key itself).

        Returns:
            Key metadata without sensitive data
        """
        result = await self.session.execute(
            text("""
                SELECT
                    key_id,
                    algorithm,
                    key_version,
                    created_at,
                    activated_at,
                    expires_at
                FROM encryption_keys
                WHERE is_active = true
            """)
        )
        row = result.fetchone()
        if not row:
            return None

        return {
            "key_id": row.key_id,
            "algorithm": row.algorithm,
            "key_version": row.key_version,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "activated_at": row.activated_at.isoformat() if row.activated_at else None,
            "expires_at": row.expires_at.isoformat() if row.expires_at else None,
        }


class PIIFieldHandler:
    """Handler for PII fields in API requests/responses.

    This class provides methods to handle PII fields transparently:
    - On input: Pass through to PostgreSQL for encryption
    - On output: Decrypt via PostgreSQL before returning to client

    Usage in schemas:
        class UserCreate(BaseModel):
            email: str  # Will be encrypted by PostgreSQL
            phone: str  # Will be encrypted by PostgreSQL

        # In endpoint:
        handler = PIIFieldHandler(db)
        # Data is sent to PostgreSQL which handles encryption
    """

    # Fields that contain PII and must be encrypted
    PII_FIELDS = {
        "email",
        "phone",
        "phone_number",
        "first_name",
        "last_name",
        "full_name",
        "address",
        "dni",
        "national_id",
        "credit_card",
        "iban",
        "ip_address",
    }

    def __init__(self, session: AsyncSession):
        self.encryption = EncryptionService(session)

    def is_pii_field(self, field_name: str) -> bool:
        """Check if a field contains PII that needs encryption."""
        return field_name.lower() in self.PII_FIELDS

    async def prepare_for_storage(
        self,
        data: dict[str, Any],
        encrypt_fields: list[str] | None = None,
    ) -> dict[str, Any]:
        """Prepare data for database storage, encrypting PII fields.

        Note: In practice, PostgreSQL handles encryption via triggers or
        explicit function calls. This method is for cases where the
        application needs to pre-encrypt data.

        Args:
            data: Dictionary of field values
            encrypt_fields: Explicit list of fields to encrypt (optional)

        Returns:
            Dictionary with PII fields encrypted
        """
        result = data.copy()
        fields_to_encrypt = encrypt_fields or [k for k in data if self.is_pii_field(k)]

        for field in fields_to_encrypt:
            if field in result and result[field]:
                result[field] = await self.encryption.encrypt_pii(str(result[field]))

        return result

    async def prepare_for_response(
        self,
        data: dict[str, Any],
        decrypt_fields: list[str] | None = None,
    ) -> dict[str, Any]:
        """Prepare data for API response, decrypting PII fields.

        Args:
            data: Dictionary with potentially encrypted fields
            decrypt_fields: Explicit list of fields to decrypt (optional)

        Returns:
            Dictionary with PII fields decrypted
        """
        result = data.copy()
        fields_to_decrypt = decrypt_fields or [k for k in data if self.is_pii_field(k)]

        for field in fields_to_decrypt:
            if field in result and isinstance(result[field], dict):
                # Field is encrypted (JSONB structure)
                result[field] = await self.encryption.decrypt_pii(result[field])

        return result
