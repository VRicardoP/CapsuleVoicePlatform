"""
Servicio de cuotas de voz por tenant.

Controla el consumo mensual de minutos (inbound/outbound) para evitar
costes descontrolados en Ultravox/Zadarma. Configuración por tenant en
organizations.settings:

  voice_inbound_monthly_limit_minutes:  int | None  (None = ilimitado)
  voice_outbound_monthly_limit_minutes: int | None
  voice_block_when_exceeded:            bool (default True)

Patrón reserve/commit:
  1. assert_can_start_call() → reserva segundos estimados antes de crear la llamada
  2. commit_call_ended()     → reconcilia con la duración real al terminar
  3. release_on_no_answer()  → libera la reserva si la llamada no conectó
"""

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Organization
from app.repositories.voice_quota_repository import VoiceQuotaRepository

logger = logging.getLogger(__name__)

# Segundos estimados por defecto para llamadas entrantes (buffer inicial)
_DEFAULT_INBOUND_ESTIMATE_SEC = 600   # 10 min
# Buffer adicional sobre join_timeout para llamadas salientes
_OUTBOUND_BUFFER_SEC = 300            # 5 min


class VoiceQuotaExceededError(Exception):
    """Se lanza cuando el tenant ha agotado su cuota de voz del mes."""

    def __init__(self, org_id: UUID, direction: str, used_min: int, limit_min: int):
        self.org_id = org_id
        self.direction = direction
        self.used_min = used_min
        self.limit_min = limit_min
        super().__init__(
            f"Cuota de voz agotada [{direction}] para org {org_id}: "
            f"{used_min}/{limit_min} min usados este mes"
        )


class VoiceQuotaService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = VoiceQuotaRepository(db)

    # ------------------------------------------------------------------
    # Configuración
    # ------------------------------------------------------------------

    async def _get_limit_seconds(self, org_id: UUID, direction: str) -> int | None:
        """Lee el límite en segundos desde organizations.settings. None = ilimitado."""
        org = await self.db.get(Organization, org_id)
        if not org:
            return None
        settings = org.settings or {}
        key = (
            "voice_inbound_monthly_limit_minutes"
            if direction == "inbound"
            else "voice_outbound_monthly_limit_minutes"
        )
        limit_minutes = settings.get(key)
        if limit_minutes is None:
            return None
        return int(limit_minutes) * 60

    async def _is_blocking(self, org_id: UUID) -> bool:
        org = await self.db.get(Organization, org_id)
        if not org:
            return True
        return (org.settings or {}).get("voice_block_when_exceeded", True)

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    async def assert_can_start_call(
        self,
        org_id: UUID,
        direction: str,
        estimated_seconds: int,
    ) -> int:
        """Verifica cuota y reserva segundos estimados antes de iniciar la llamada.

        Devuelve los segundos reservados (para pasarlos a commit/release luego).
        Lanza VoiceQuotaExceededError si la cuota está agotada y block=True.
        """
        limit_seconds = await self._get_limit_seconds(org_id, direction)
        if limit_seconds is None:
            return 0  # Sin límite configurado, sin reserva

        blocking = await self._is_blocking(org_id)
        if not blocking:
            return 0  # Modo monitorización: no bloquea ni reserva

        reserved = await self.repo.try_reserve(org_id, direction, estimated_seconds, limit_seconds)
        if not reserved:
            usage = await self.repo.get_usage(org_id)
            dir_usage = usage.get(direction, {"used_seconds": 0, "reserved_seconds": 0})
            used_min = (dir_usage["used_seconds"] + dir_usage["reserved_seconds"]) // 60
            limit_min = limit_seconds // 60
            logger.warning(
                "[voice_quota] Llamada bloqueada [%s] org=%s: %d/%d min",
                direction,
                org_id,
                used_min,
                limit_min,
            )
            raise VoiceQuotaExceededError(org_id, direction, used_min, limit_min)

        logger.info(
            "[voice_quota] Reserva OK [%s] org=%s: %ds estimados",
            direction,
            org_id,
            estimated_seconds,
        )
        return estimated_seconds

    async def commit_call_ended(
        self,
        org_id: UUID,
        direction: str,
        actual_seconds: int,
        was_reserved_seconds: int,
    ) -> None:
        """Registra la duración real de una llamada terminada."""
        if was_reserved_seconds == 0 and actual_seconds == 0:
            return
        await self.repo.commit_usage(org_id, direction, actual_seconds, was_reserved_seconds)
        logger.debug(
            "[voice_quota] Commit [%s] org=%s: real=%ds reservado=%ds",
            direction,
            org_id,
            actual_seconds,
            was_reserved_seconds,
        )

    async def release_on_no_answer(
        self,
        org_id: UUID,
        direction: str,
        was_reserved_seconds: int,
    ) -> None:
        """Libera reserva para llamadas que no llegaron a conectar."""
        if was_reserved_seconds == 0:
            return
        await self.repo.release_reservation(org_id, direction, was_reserved_seconds)
        logger.debug(
            "[voice_quota] Release [%s] org=%s: %ds liberados",
            direction,
            org_id,
            was_reserved_seconds,
        )

    async def get_remaining_seconds(self, org_id: UUID, direction: str) -> int | None:
        """Segundos disponibles este mes. None si no hay límite."""
        limit_seconds = await self._get_limit_seconds(org_id, direction)
        if limit_seconds is None:
            return None
        usage = await self.repo.get_usage(org_id)
        dir_usage = usage.get(direction, {"used_seconds": 0, "reserved_seconds": 0})
        consumed = dir_usage["used_seconds"] + dir_usage["reserved_seconds"]
        return max(0, limit_seconds - consumed)

    async def get_status(self, org_id: UUID) -> dict:
        """Estado completo de cuota para el endpoint de visibilidad."""
        month_key = self.repo.current_month_key()
        usage = await self.repo.get_usage(org_id)

        result = {"month_key": month_key, "inbound": None, "outbound": None}
        for direction in ("inbound", "outbound"):
            limit_sec = await self._get_limit_seconds(org_id, direction)
            dir_usage = usage.get(direction, {"used_seconds": 0, "reserved_seconds": 0})
            used_sec = dir_usage["used_seconds"]
            reserved_sec = dir_usage["reserved_seconds"]
            consumed_sec = used_sec + reserved_sec

            if limit_sec is not None:
                remaining_min = max(0, (limit_sec - consumed_sec)) // 60
                result[direction] = {
                    "limit_minutes": limit_sec // 60,
                    "used_minutes": used_sec // 60,
                    "reserved_minutes": reserved_sec // 60,
                    "remaining_minutes": remaining_min,
                    "is_exceeded": consumed_sec >= limit_sec,
                }
            else:
                result[direction] = {
                    "limit_minutes": None,
                    "used_minutes": used_sec // 60,
                    "reserved_minutes": reserved_sec // 60,
                    "remaining_minutes": None,
                    "is_exceeded": False,
                }
        return result

    # ------------------------------------------------------------------
    # Helpers para los puntos de enforcement
    # ------------------------------------------------------------------

    @staticmethod
    def estimate_outbound_seconds(join_timeout_sec: int) -> int:
        """Estimación conservadora para reserva outbound."""
        return join_timeout_sec + _OUTBOUND_BUFFER_SEC

    @staticmethod
    def estimate_inbound_seconds(remaining_seconds: int | None) -> int:
        """Estimación para reserva inbound basada en saldo disponible."""
        if remaining_seconds is None:
            return _DEFAULT_INBOUND_ESTIMATE_SEC
        return min(remaining_seconds, _DEFAULT_INBOUND_ESTIMATE_SEC)
