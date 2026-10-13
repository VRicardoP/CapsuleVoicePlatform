"""Add marketplace permission to catalog.

Introduces `marketplace` (global) + `marketplace.view` so the sidebar
can gate the "Tienda" button by permission. Seeded for superadmin
(implicit, wildcard) and client_admin (explicit, via role_permission_templates).
Regular `user` role does NOT receive it — admins must grant it
explicitly when needed.

Revision ID: g8h9i0j1k2l4
Revises: g8h9i0j1k2l3
Create Date: 2026-04-13

NOTE: This migration originally shared revision id g8h9i0j1k2l3 with the
oc_campaign_contacts_outcome migration, so alembic silently skipped it on
every deployment. Renamed to g8h9i0j1k2l4 and rechained after the
oc_campaign migration so it actually runs on next upgrade.
"""

from typing import Sequence, Union

from alembic import op


revision: str = "g8h9i0j1k2l4"
down_revision: Union[str, Sequence[str], None] = "f7g8h9i0j1k2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add marketplace permissions to the catalog. ON CONFLICT DO NOTHING
    # keeps the migration idempotent against databases that already ran
    # partial hot-patches.
    op.execute("""
        INSERT INTO permission_catalog (key, module, label, description, parent, scope, sort_order) VALUES
        ('marketplace',      'marketplace', 'Tienda',          'Marketplace de m\u00f3dulos contratables', NULL,          'global', 0),
        ('marketplace.view', 'marketplace', 'Ver tienda',      'Ver el cat\u00e1logo del marketplace',     'marketplace', 'global', 1)
        ON CONFLICT (key) DO NOTHING;
    """)

    # Grant the new permission to client_admin. Avoid duplicates on reruns.
    op.execute("""
        INSERT INTO role_permission_templates (role, permission_key)
        SELECT 'client_admin', key
        FROM permission_catalog
        WHERE key IN ('marketplace', 'marketplace.view')
          AND NOT EXISTS (
            SELECT 1 FROM role_permission_templates rpt
            WHERE rpt.role = 'client_admin'
              AND rpt.permission_key = permission_catalog.key
          );
    """)


def downgrade() -> None:
    op.execute("""
        DELETE FROM role_permission_templates
        WHERE permission_key IN ('marketplace', 'marketplace.view');
    """)
    op.execute("""
        DELETE FROM user_permissions
        WHERE permission_key IN ('marketplace', 'marketplace.view');
    """)
    op.execute("""
        DELETE FROM permission_catalog
        WHERE key IN ('marketplace', 'marketplace.view');
    """)
