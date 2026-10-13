"""
Permission repository - Data access for capability-based authorization.

Handles permission catalog, role templates, and per-user permission overrides.
"""

import logging
from uuid import UUID

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.permission import (
    PermissionCatalog,
    RolePermissionTemplate,
    UserPermission,
)

logger = logging.getLogger(__name__)


class PermissionRepository:
    """Repository for permission queries and mutations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_user_permissions(self, user_id: UUID) -> list[str]:
        """Get permission keys additively GRANTED to a user (excluding denies).

        Kept for backward compatibility with callers that only care about
        additive overrides. Use `get_user_grants_and_denies()` when you also
        need the deny set.
        """
        result = await self.session.execute(
            select(UserPermission.permission_key).where(
                UserPermission.user_id == user_id,
                UserPermission.granted.is_(True),
            )
        )
        return list(result.scalars().all())

    async def get_user_grants_and_denies(self, user_id: UUID) -> tuple[set[str], set[str]]:
        """Return (grants, denies) for a user.

        - grants: permissions added on top of the role template.
        - denies: role-template permissions explicitly revoked for this user.
        """
        result = await self.session.execute(
            select(UserPermission.permission_key, UserPermission.granted).where(
                UserPermission.user_id == user_id
            )
        )
        grants: set[str] = set()
        denies: set[str] = set()
        for row in result.all():
            if row.granted:
                grants.add(row.permission_key)
            else:
                denies.add(row.permission_key)
        return grants, denies

    async def get_role_template_permissions(self, role: str) -> list[str]:
        """Get default permission keys for a role from role_permission_templates.

        Args:
            role: Role name (e.g. 'client_admin', 'user').

        Returns:
            List of permission key strings.
        """
        result = await self.session.execute(
            select(RolePermissionTemplate.permission_key).where(RolePermissionTemplate.role == role)
        )
        return list(result.scalars().all())

    async def set_user_permissions(
        self,
        user_id: UUID,
        permissions: list[str],
        granted_by: UUID | None = None,
        denies: list[str] | None = None,
    ) -> tuple[int, int]:
        """Replace all per-user overrides with the given grants + denies.

        Deletes existing overrides and inserts the new ones atomically. A
        permission can appear in `permissions` (additive grant) or in
        `denies` (revoke a role-template permission for this user), but
        never in both — the same key in both is treated as a grant.

        Returns (granted_count, revoked_count) comparing the new effective
        override set against the previous one.
        """
        denies = denies or []
        # Exclude from denies anything that's being granted to avoid conflicts
        grant_set = set(permissions)
        deny_set = set(denies) - grant_set

        prev_grants, prev_denies = await self.get_user_grants_and_denies(user_id)
        granted = grant_set - prev_grants
        revoked = prev_grants - grant_set
        new_denies = deny_set - prev_denies
        removed_denies = prev_denies - deny_set

        # Delete all existing overrides
        await self.session.execute(delete(UserPermission).where(UserPermission.user_id == user_id))

        # Insert grants (granted=True)
        for perm_key in grant_set:
            self.session.add(
                UserPermission(
                    user_id=user_id,
                    permission_key=perm_key,
                    granted_by=granted_by,
                    granted=True,
                )
            )

        # Insert denies (granted=False)
        for perm_key in deny_set:
            self.session.add(
                UserPermission(
                    user_id=user_id,
                    permission_key=perm_key,
                    granted_by=granted_by,
                    granted=False,
                )
            )

        await self.session.flush()

        logger.info(
            "Updated permissions for user %s: grants +%d -%d / denies +%d -%d",
            user_id,
            len(granted),
            len(revoked),
            len(new_denies),
            len(removed_denies),
        )
        # Return totals treating denies as revocations of role perms.
        return len(granted), len(revoked) + len(new_denies)

    async def get_user_permissions_detailed(self, user_id: UUID) -> list[dict]:
        """Get detailed per-user permission entries (grants AND denies).

        Returns dicts with key, granted_by, created_at and granted flag for
        each UserPermission row, used by the GET /users/{id}/permissions
        endpoint.
        """
        result = await self.session.execute(
            select(
                UserPermission.permission_key,
                UserPermission.granted_by,
                UserPermission.created_at,
                UserPermission.granted,
            ).where(UserPermission.user_id == user_id)
        )
        return [
            {
                "key": row.permission_key,
                "granted_by": row.granted_by,
                "created_at": row.created_at,
                "granted": row.granted,
            }
            for row in result.all()
        ]

    async def get_catalog(self, module: str | None = None) -> list[PermissionCatalog]:
        """Get permission catalog entries, optionally filtered by module.

        Args:
            module: If provided, filter by this module name.

        Returns:
            List of PermissionCatalog ORM objects.
        """
        query = select(PermissionCatalog).order_by(
            PermissionCatalog.module, PermissionCatalog.sort_order
        )
        if module:
            query = query.where(PermissionCatalog.module == module)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_tenant_features(self, organization_id: UUID) -> dict[str, bool]:
        """Get feature flags for a specific organization.

        Queries organizations.settings JSONB and extracts *_enabled keys.

        Args:
            organization_id: The organization UUID.

        Returns:
            Dict mapping feature keys (e.g. 'whatsapp_enabled') to booleans.
        """
        result = await self.session.execute(
            text("SELECT settings FROM organizations WHERE id = CAST(:org_id AS UUID)"),
            {"org_id": str(organization_id)},
        )
        row = result.fetchone()
        if not row or not row.settings:
            return {}

        settings = row.settings
        return {key: bool(value) for key, value in settings.items() if key.endswith("_enabled")}
