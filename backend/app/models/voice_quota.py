"""
Modelo SQLAlchemy para el sistema de cuotas de voz por tenant.

Almacena el uso mensual de minutos de voz (inbound/outbound) por organización,
con soporte para reservas preventivas que evitan el sobreconsumo concurrente.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, Index, Integer, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class VoiceMonthlyUsage(Base):
    """
    Contador mensual de segundos de voz por organización y dirección.

    Patrón reserve/commit para evitar sobreconsumo en llamadas concurrentes:
    1. Al iniciar llamada: UPSERT atómico sobre reserved_seconds (try_reserve)
    2. Al terminar llamada: committed a used_seconds, reserved_seconds decrementado
    3. Si falla antes de conectar: reserved_seconds decrementado (release)

    Enforcement: used_seconds + reserved_seconds <= límite configurado en
    organizations.settings["voice_inbound_monthly_limit_minutes"] / _outbound_
    """

    __tablename__ = "voice_monthly_usage"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    organization_id: Mapped[UUID] = mapped_column(
        nullable=False,
        comment="FK lógica a organizations.id (sin FK física para evitar cascade complejo)",
    )

    # "YYYY-MM" — una fila por mes, sin reset explícito necesario
    month_key: Mapped[str] = mapped_column(String(7), nullable=False)

    direction: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        comment="inbound | outbound",
    )

    used_seconds: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Segundos realmente consumidos (duración real de llamadas terminadas)",
    )

    reserved_seconds: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Segundos pre-reservados por llamadas en curso, pendientes de commit",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )

    __table_args__ = (
        CheckConstraint(
            "direction IN ('inbound', 'outbound')",
            name="voice_usage_direction_check",
        ),
        CheckConstraint("used_seconds >= 0", name="voice_usage_used_non_negative"),
        CheckConstraint("reserved_seconds >= 0", name="voice_usage_reserved_non_negative"),
        Index("uq_voice_usage", "organization_id", "month_key", "direction", unique=True),
        Index("ix_voice_usage_org_month", "organization_id", "month_key"),
    )

    def __repr__(self) -> str:
        return (
            f"<VoiceMonthlyUsage("
            f"org={self.organization_id}, "
            f"month={self.month_key}, "
            f"dir={self.direction}, "
            f"used={self.used_seconds}s, "
            f"reserved={self.reserved_seconds}s)>"
        )
