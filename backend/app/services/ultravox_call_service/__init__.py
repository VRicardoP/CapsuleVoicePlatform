"""Ultravox call processing service package.

Backward compat: from app.services.ultravox_call_service import UltravoxCallService
"""

from .functions import UltravoxFunctionsMixin
from .recording import UltravoxRecordingMixin
from .webhook import ULTRAVOX_API_KEY, WEBHOOK_FORWARD_URL, WEBHOOK_SECRET, UltravoxWebhookMixin
from .zadarma import (
    ZADARMA_API_KEY,
    ZADARMA_API_SECRET,
    ZADARMA_CACHE_TTL_SECONDS,
    ZADARMA_CALL_CACHE,
    UltravoxZadarmaMixin,
)


class UltravoxCallService(
    UltravoxWebhookMixin, UltravoxZadarmaMixin, UltravoxRecordingMixin, UltravoxFunctionsMixin
):
    """Ultravox call processing service — facade combining all domain mixins."""

    pass


__all__ = [
    "UltravoxCallService",
    "ZADARMA_CALL_CACHE",
    "ZADARMA_CACHE_TTL_SECONDS",
    "WEBHOOK_FORWARD_URL",
    "WEBHOOK_SECRET",
    "ULTRAVOX_API_KEY",
    "ZADARMA_API_KEY",
    "ZADARMA_API_SECRET",
]
