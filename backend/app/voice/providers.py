"""Voice provider configuration and routing."""

from enum import Enum


class VoiceProvider(str, Enum):
    """Supported voice AI providers."""

    ULTRAVOX = "ultravox"
    RETELL = "retell"
    INTERNAL = "internal"  # Future: CapsuleCorp's own voice agent
