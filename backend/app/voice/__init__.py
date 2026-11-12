"""Voice provider abstraction layer.

This module provides a unified interface for different voice AI providers
(Ultravox, Retell, Internal) to integrate with CapsuleCorp.
"""

from app.voice.events import CallEvent, CallEventType
from app.voice.providers import VoiceProvider

__all__ = ["CallEvent", "CallEventType", "VoiceProvider"]
