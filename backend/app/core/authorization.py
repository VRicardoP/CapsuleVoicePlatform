"""
Core authorization module for capability-based access control.

Provides the Principal dataclass that carries the resolved permissions
for the current request, and the FEATURE_KEYS mapping that ties
module names to organization settings keys.
"""

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class Principal:
    """Immutable authorization context for a request.

    Attributes:
        user_id: Authenticated user UUID.
        role: User role (superadmin, client_admin, user).
        organization_id: Tenant UUID (None for superadmin).
        permissions: Resolved set of permission keys.
    """

    user_id: UUID
    role: str
    organization_id: UUID | None
    permissions: frozenset[str]

    def has_permission(self, key: str) -> bool:
        """Check if this principal has the given permission.

        Supports hierarchical matching: having 'whatsapp' grants
        'whatsapp.inbox.view', 'whatsapp.contacts.edit', etc.
        The wildcard '*' grants everything.
        """
        if "*" in self.permissions:
            return True
        parts = key.split(".")
        for i in range(len(parts)):
            if ".".join(parts[: i + 1]) in self.permissions:
                return True
        return False


# Feature key mapping: module name → organization settings key
FEATURE_KEYS: dict[str, str] = {
    "outbound": "outbound_enabled",
    "newsletter": "newsletter_enabled",
    "captacion": "captacion_enabled",
    "calendar": "calendar_enabled",
    "whatsapp": "whatsapp_enabled",
    "avisos": "avisos_enabled",
    "trips": "trips_enabled",
}
