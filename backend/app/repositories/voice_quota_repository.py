"""Repositorio para el sistema de cuotas de voz por tenant."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class VoiceQuotaRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def current_month_key() -> str:
        return datetime.now(UTC).strftime("%Y-%m")

    async def try_reserve(
        self,
        org_id: UUID,
        direction: str,
        delta_seconds: int,
        limit_seconds: int,
    ) -> bool:
        """Reserva preventiva atómica para una llamada que va a iniciar.

        Usa INSERT ... ON CONFLICT DO UPDATE con WHERE condicional — la operación
        completa es atómica a nivel de fila. Si la condición del WHERE no se cumple
        (cuota agotada), el UPDATE no ocurre y RETURNING no devuelve filas.

        Devuelve True si la reserva se realizó, False si la cuota está agotada.
        """
        month_key = self.current_month_key()
        result = await self.db.execute(
            text("""
                INSERT INTO voice_monthly_usage
                    (organization_id, month_key, direction, used_seconds, reserved_seconds)
                VALUES
                    (:org_id, :month_key, :direction, 0, :delta)
                ON CONFLICT (organization_id, month_key, direction) DO UPDATE
                    SET reserved_seconds = voice_monthly_usage.reserved_seconds + EXCLUDED.reserved_seconds,
                        updated_at       = NOW()
                    WHERE (voice_monthly_usage.used_seconds
                           + voice_monthly_usage.reserved_seconds
                           + EXCLUDED.reserved_seconds) <= :limit
                RETURNING id
            """),
            {
                "org_id": str(org_id),
                "month_key": month_key,
                "direction": direction,
                "delta": delta_seconds,
                "limit": limit_seconds,
            },
        )
        return result.fetchone() is not None

    async def commit_usage(
        self,
        org_id: UUID,
        direction: str,
        actual_seconds: int,
        was_reserved_seconds: int,
    ) -> None:
        """Reconcilia al terminar una llamada: incrementa used, decrementa reserved."""
        month_key = self.current_month_key()
        await self.db.execute(
            text("""
                UPDATE voice_monthly_usage
                SET used_seconds     = used_seconds + :actual,
                    reserved_seconds = GREATEST(0, reserved_seconds - :was_reserved),
                    updated_at       = NOW()
                WHERE organization_id = :org_id
                  AND month_key       = :month_key
                  AND direction       = :direction
            """),
            {
                "org_id": str(org_id),
                "month_key": month_key,
                "direction": direction,
                "actual": actual_seconds,
                "was_reserved": was_reserved_seconds,
            },
        )

    async def release_reservation(
        self,
        org_id: UUID,
        direction: str,
        was_reserved_seconds: int,
    ) -> None:
        """Libera una reserva para llamadas que fallaron sin consumir tiempo real."""
        month_key = self.current_month_key()
        await self.db.execute(
            text("""
                UPDATE voice_monthly_usage
                SET reserved_seconds = GREATEST(0, reserved_seconds - :was_reserved),
                    updated_at       = NOW()
                WHERE organization_id = :org_id
                  AND month_key       = :month_key
                  AND direction       = :direction
            """),
            {
                "org_id": str(org_id),
                "month_key": month_key,
                "direction": direction,
                "was_reserved": was_reserved_seconds,
            },
        )

    async def get_usage(self, org_id: UUID) -> dict[str, dict]:
        """Devuelve el uso actual del mes para ambas direcciones."""
        month_key = self.current_month_key()
        result = await self.db.execute(
            text("""
                SELECT direction, used_seconds, reserved_seconds
                FROM voice_monthly_usage
                WHERE organization_id = :org_id
                  AND month_key = :month_key
            """),
            {"org_id": str(org_id), "month_key": month_key},
        )
        rows = result.fetchall()
        return {
            row.direction: {
                "used_seconds": row.used_seconds,
                "reserved_seconds": row.reserved_seconds,
            }
            for row in rows
        }
