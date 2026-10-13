"""ai_decision_logs.decision_value: VARCHAR(255) -> TEXT

Revision ID: m4n5o6p7q8r9
Revises: l3m4n5o6p7q8
Create Date: 2026-05-21

El campo `decision_value` guarda la descripción legible de cada acción
del agente IA (resultado de tool calls). Las respuestas de tools como
`cancelar_cita` pueden devolver listas de citas + instrucciones para el
LLM que superan fácilmente los 255 caracteres y causaban
StringDataRightTruncationError → la acción no se grababa y la llamada
aparecía sin actividad en el panel del dashboard.

Cambio: VARCHAR(255) -> TEXT. Idempotente: si ya es text (porque algún
cliente lo aplicó como hotfix con ALTER directo), la migración es no-op.
"""

from alembic import op
import sqlalchemy as sa

revision = "m4n5o6p7q8r9"
down_revision = "k2l3m4n5o6p7"
branch_labels = None
depends_on = None


def _current_type() -> str | None:
    bind = op.get_bind()
    result = bind.execute(
        sa.text(
            "SELECT data_type FROM information_schema.columns"
            " WHERE table_schema = current_schema()"
            " AND table_name = 'ai_decision_logs'"
            " AND column_name = 'decision_value'"
        )
    )
    row = result.fetchone()
    return row[0] if row else None


def upgrade() -> None:
    t = _current_type()
    if t is None or t == "text":
        return
    op.alter_column(
        "ai_decision_logs",
        "decision_value",
        existing_type=sa.String(255),
        type_=sa.Text(),
        existing_nullable=True,
    )


def downgrade() -> None:
    # No degradamos a VARCHAR(255) porque los datos existentes podrían
    # truncarse. Si se quiere revertir, hacerlo manualmente tras revisar
    # los datos: `ALTER TABLE ai_decision_logs ALTER COLUMN decision_value
    # TYPE VARCHAR(255) USING LEFT(decision_value, 255);`.
    pass
