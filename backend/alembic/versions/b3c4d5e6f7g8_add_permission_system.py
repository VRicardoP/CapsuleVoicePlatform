"""Add permission system: organization_id on users, permission tables, role migration.

Revision ID: b3c4d5e6f7g8
Revises: a1b2c3d4e5f6
Create Date: 2026-04-02
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "b3c4d5e6f7g8"
down_revision = "8e4c17fbcac1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add organization_id to users
    op.add_column("users", sa.Column("organization_id", UUID, nullable=True))
    op.create_foreign_key(
        "fk_users_organization_id",
        "users",
        "organizations",
        ["organization_id"],
        ["id"],
    )

    # Populate organization_id for existing users (single-tenant stacks)
    op.execute("""
        UPDATE users SET organization_id = (
            SELECT id FROM organizations WHERE is_active = true LIMIT 1
        ) WHERE organization_id IS NULL
    """)

    # 2. Create permission_catalog
    op.create_table(
        "permission_catalog",
        sa.Column("key", sa.String(100), primary_key=True),
        sa.Column("module", sa.String(50), nullable=False),
        sa.Column("label", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("parent", sa.String(100), sa.ForeignKey("permission_catalog.key"), nullable=True),
        sa.Column("scope", sa.String(10), nullable=False, server_default="module"),
        sa.Column("sort_order", sa.Integer, server_default="0"),
    )

    # 3. Create role_permission_templates
    op.create_table(
        "role_permission_templates",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("role", sa.String(50), nullable=False),
        sa.Column(
            "permission_key",
            sa.String(100),
            sa.ForeignKey("permission_catalog.key"),
            nullable=False,
        ),
        sa.UniqueConstraint("role", "permission_key", name="uq_role_permission"),
    )

    # 4. Create user_permissions
    op.create_table(
        "user_permissions",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "permission_key",
            sa.String(100),
            sa.ForeignKey("permission_catalog.key"),
            nullable=False,
        ),
        sa.Column(
            "granted_by", UUID, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.current_timestamp()
        ),
        sa.UniqueConstraint("user_id", "permission_key", name="uq_user_permission"),
    )
    op.create_index("idx_user_permissions_user", "user_permissions", ["user_id"])

    # 5. Add org+role index on users
    op.create_index(
        "idx_users_org_role",
        "users",
        ["organization_id", "role"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    # 6. Seed permission catalog (55 permissions)
    op.execute("""
        INSERT INTO permission_catalog (key, module, label, description, parent, scope, sort_order) VALUES
        -- Global / Sistema
        ('dashboard',                    'dashboard',  'Dashboard',                     'Dashboard principal',                           NULL,          'global', 0),
        ('dashboard.calls.view',         'dashboard',  'Ver llamadas',                  'Métricas y listado de llamadas',                'dashboard',   'module', 1),
        ('dashboard.gdpr.view',          'dashboard',  'Ver RGPD',                      'Métricas y gestión RGPD',                       'dashboard',   'module', 2),
        ('users',                        'system',     'Usuarios',                      'Gestión de usuarios',                           NULL,          'global', 0),
        ('users.view',                   'system',     'Ver usuarios',                  'Listar usuarios del tenant',                    'users',       'global', 1),
        ('users.manage',                 'system',     'Gestionar usuarios',            'Crear, editar y desactivar usuarios',           'users',       'global', 2),
        ('users.permissions.manage',     'system',     'Gestionar permisos',            'Asignar y revocar permisos a usuarios',         'users',       'global', 3),
        -- Outbound
        ('outbound',                     'outbound',   'Llamadas Salientes',            'Módulo completo',                               NULL,          'module', 0),
        ('outbound.dashboard.view',      'outbound',   'Vista general',                 'Dashboard y estadísticas',                      'outbound',    'module', 1),
        ('outbound.campaigns.view',      'outbound',   'Ver campañas',                  'Listar campañas y ver detalles',                'outbound',    'module', 2),
        ('outbound.campaigns.manage',    'outbound',   'Gestionar campañas',            'Crear, iniciar, pausar, cancelar campañas',     'outbound',    'module', 3),
        ('outbound.contacts.view',       'outbound',   'Ver contactos',                 'Pool de contactos',                             'outbound',    'module', 4),
        ('outbound.contacts.manage',     'outbound',   'Gestionar contactos',           'Subir CSV/Excel, eliminar contactos',           'outbound',    'module', 5),
        ('outbound.test_call',           'outbound',   'Emisión individual',            'Llamadas de prueba',                            'outbound',    'module', 6),
        ('outbound.analytics.view',      'outbound',   'Analíticas',                    'Métricas de rendimiento',                       'outbound',    'module', 7),
        ('outbound.settings.manage',     'outbound',   'Configuración',                 'SIP, webhooks, credenciales',                   'outbound',    'module', 8),
        -- Newsletter
        ('newsletter',                   'newsletter', 'Newsletter',                    'Módulo completo',                               NULL,          'module', 0),
        ('newsletter.dashboard.view',    'newsletter', 'Vista general',                 'Dashboard y métricas',                          'newsletter',  'module', 1),
        ('newsletter.campaigns.view',    'newsletter', 'Ver campañas',                  'Listar campañas y métricas',                    'newsletter',  'module', 2),
        ('newsletter.campaigns.manage',  'newsletter', 'Gestionar campañas',            'Crear y editar campañas',                       'newsletter',  'module', 3),
        ('newsletter.campaigns.send',    'newsletter', 'Enviar campañas',               'Programar y enviar campañas',                   'newsletter',  'module', 4),
        ('newsletter.contacts.view',     'newsletter', 'Ver contactos',                 'Listar suscriptores',                           'newsletter',  'module', 5),
        ('newsletter.contacts.manage',   'newsletter', 'Gestionar contactos',           'Importar, editar y eliminar contactos',         'newsletter',  'module', 6),
        ('newsletter.lists.view',        'newsletter', 'Ver listas',                    'Listar distribución',                           'newsletter',  'module', 7),
        ('newsletter.lists.manage',      'newsletter', 'Gestionar listas',              'Crear, editar y eliminar listas',               'newsletter',  'module', 8),
        ('newsletter.domains.manage',    'newsletter', 'Gestionar dominios',            'Dominios de envío',                             'newsletter',  'module', 9),
        ('newsletter.settings.manage',   'newsletter', 'Configuración',                 'Ajustes del módulo',                            'newsletter',  'module', 10),
        -- Captacion
        ('captacion',                    'captacion',  'Captación',                     'Módulo completo',                               NULL,          'module', 0),
        ('captacion.dashboard.view',     'captacion',  'Dashboard',                     'KPIs y embudo',                                 'captacion',   'module', 1),
        ('captacion.leads.view',         'captacion',  'Ver leads',                     'Listar y ver detalle de leads',                 'captacion',   'module', 2),
        ('captacion.leads.manage',       'captacion',  'Gestionar leads',               'Editar y eliminar leads',                       'captacion',   'module', 3),
        ('captacion.scrapers.manage',    'captacion',  'Scrapers',                      'Configurar y ejecutar scrapers',                'captacion',   'module', 4),
        ('captacion.runs.view',          'captacion',  'Historial',                     'Historial de ejecuciones',                      'captacion',   'module', 5),
        ('captacion.import.manage',      'captacion',  'Importar CSV',                  'Importación manual de leads',                   'captacion',   'module', 6),
        ('captacion.analytics.view',     'captacion',  'Analíticas',                    'Métricas y resúmenes',                          'captacion',   'module', 7),
        -- Calendar
        ('calendar',                     'calendar',   'Calendario',                    'Módulo completo',                               NULL,          'module', 0),
        ('calendar.dashboard.view',      'calendar',   'Vista general',                 'Dashboard y calendario',                        'calendar',    'module', 1),
        ('calendar.bookings.view',       'calendar',   'Ver reservas',                  'Listar reservas',                               'calendar',    'module', 2),
        ('calendar.bookings.manage',     'calendar',   'Gestionar reservas',            'Cancelar reservas',                             'calendar',    'module', 3),
        ('calendar.availability.view',   'calendar',   'Disponibilidad',               'Ver horarios',                                  'calendar',    'module', 4),
        ('calendar.event_types.manage',  'calendar',   'Tipos de evento',               'Gestionar tipos',                               'calendar',    'module', 5),
        ('calendar.team.view',           'calendar',   'Equipo',                        'Ver miembros',                                  'calendar',    'module', 6),
        ('calendar.settings.manage',     'calendar',   'Configuración',                 'Ajustes del calendario',                        'calendar',    'module', 7),
        -- WhatsApp
        ('whatsapp',                     'whatsapp',   'WhatsApp',                      'Módulo completo',                               NULL,          'module', 0),
        ('whatsapp.inbox.view',          'whatsapp',   'Inbox',                         'Ver y responder conversaciones',                'whatsapp',    'module', 1),
        ('whatsapp.templates.view',      'whatsapp',   'Ver plantillas',                'Listar plantillas',                             'whatsapp',    'module', 2),
        ('whatsapp.templates.manage',    'whatsapp',   'Gestionar plantillas',          'Crear, editar, sincronizar y enviar a Meta',    'whatsapp',    'module', 3),
        ('whatsapp.campaigns.view',      'whatsapp',   'Ver campañas',                  'Listar campañas y métricas',                    'whatsapp',    'module', 4),
        ('whatsapp.campaigns.manage',    'whatsapp',   'Gestionar campañas',            'Crear, iniciar, pausar, cancelar',              'whatsapp',    'module', 5),
        ('whatsapp.contacts.view',       'whatsapp',   'Ver contactos',                 'Contactos, segmentos, etiquetas',               'whatsapp',    'module', 6),
        ('whatsapp.contacts.manage',     'whatsapp',   'Gestionar contactos',           'Crear, importar, exportar, segmentar',          'whatsapp',    'module', 7),
        ('whatsapp.commerce.view',       'whatsapp',   'Ver comercio',                  'Pipeline, catálogo, pedidos',                   'whatsapp',    'module', 8),
        ('whatsapp.commerce.manage',     'whatsapp',   'Gestionar comercio',            'Crear deals, productos, pedidos',               'whatsapp',    'module', 9),
        ('whatsapp.automation.manage',   'whatsapp',   'Automatización',                'Macros, SLA, encuestas',                        'whatsapp',    'module', 10),
        ('whatsapp.analytics.view',      'whatsapp',   'Analíticas',                    'Dashboard y métricas',                          'whatsapp',    'module', 11),
        ('whatsapp.settings.manage',     'whatsapp',   'Configuración',                 'Webhooks, integraciones, auto-asignación',      'whatsapp',    'module', 12)
    """)

    # 7. Seed role templates: client_admin gets everything
    op.execute("""
        INSERT INTO role_permission_templates (role, permission_key)
        SELECT 'client_admin', key FROM permission_catalog
    """)

    # user gets dashboard base
    op.execute("""
        INSERT INTO role_permission_templates (role, permission_key) VALUES
        ('user', 'dashboard'),
        ('user', 'dashboard.calls.view')
    """)

    # 8. Migrate roles: admin → client_admin
    op.execute("UPDATE users SET role = 'client_admin' WHERE role = 'admin'")

    # 9. Migrate viewer → user + read-only permissions
    op.execute("""
        INSERT INTO user_permissions (user_id, permission_key)
        SELECT id, 'dashboard.calls.view' FROM users WHERE role = 'viewer'
        ON CONFLICT DO NOTHING
    """)
    op.execute("UPDATE users SET role = 'user' WHERE role = 'viewer'")

    # 10. Migrate auditor → user + GDPR permissions
    op.execute("""
        INSERT INTO user_permissions (user_id, permission_key)
        SELECT id, 'dashboard.gdpr.view' FROM users WHERE role = 'auditor'
        ON CONFLICT DO NOTHING
    """)
    op.execute("UPDATE users SET role = 'user' WHERE role = 'auditor'")

    # 11. Update role constraint
    op.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS users_role_check")
    op.execute("""
        ALTER TABLE users ADD CONSTRAINT users_role_check
        CHECK (role IN ('superadmin', 'client_admin', 'user'))
    """)


def downgrade() -> None:
    # Reverse role constraint
    op.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS users_role_check")
    op.execute("""
        ALTER TABLE users ADD CONSTRAINT users_role_check
        CHECK (role IN ('admin', 'user', 'viewer', 'auditor'))
    """)
    op.execute("UPDATE users SET role = 'admin' WHERE role IN ('superadmin', 'client_admin')")

    # Drop tables
    op.drop_table("user_permissions")
    op.drop_table("role_permission_templates")
    op.drop_table("permission_catalog")

    # Drop organization_id
    op.drop_index("idx_users_org_role", "users")
    op.drop_constraint("fk_users_organization_id", "users")
    op.drop_column("users", "organization_id")
