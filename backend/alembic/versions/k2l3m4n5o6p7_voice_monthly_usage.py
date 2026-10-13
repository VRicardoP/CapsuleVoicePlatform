"""voice_monthly_usage: cuotas de voz por tenant

Revision ID: k2l3m4n5o6p7
Revises: j1k2l3m4n5o6
Create Date: 2026-04-22

Crea la tabla voice_monthly_usage para el sistema de cuotas de voz.
Almacena uso mensual (inbound/outbound) con soporte para reservas preventivas
que evitan el sobreconsumo en llamadas concurrentes.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "k2l3m4n5o6p7"
down_revision: str | Sequence[str] | None = "h9i0j1k2l3m4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "voice_monthly_usage",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("month_key", sa.String(7), nullable=False, comment="YYYY-MM"),
        sa.Column(
            "direction",
            sa.String(16),
            nullable=False,
            comment="inbound | outbound",
        ),
        sa.Column("used_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reserved_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "direction IN ('inbound', 'outbound')",
            name="voice_usage_direction_check",
        ),
        sa.CheckConstraint("used_seconds >= 0", name="voice_usage_used_non_negative"),
        sa.CheckConstraint("reserved_seconds >= 0", name="voice_usage_reserved_non_negative"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_voice_usage",
        "voice_monthly_usage",
        ["organization_id", "month_key", "direction"],
        unique=True,
    )
    op.create_index(
        "ix_voice_usage_org_month",
        "voice_monthly_usage",
        ["organization_id", "month_key"],
    )


def downgrade() -> None:
    op.drop_index("ix_voice_usage_org_month", table_name="voice_monthly_usage")
    op.drop_index("uq_voice_usage", table_name="voice_monthly_usage")
    op.drop_table("voice_monthly_usage")
