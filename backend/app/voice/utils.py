"""Utility functions for voice call processing.

Shared between ultravox.py webhook handler and voice/handlers.py.
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# Regex: digits (optionally prefixed with +), at least 7 chars
_PHONE_RE = re.compile(r"^\+?\d{7,15}$")


def _extract_phone_from_sip_uri(uri: str) -> str | None:
    """Extract phone number from SIP URI like 'sip:+34612345678@zadarma.com'.

    Also handles plain phone numbers and tel: URIs.
    """
    if not uri:
        return None

    # Strip sip: or tel: prefix
    cleaned = uri
    for prefix in ("sip:", "tel:"):
        if cleaned.lower().startswith(prefix):
            cleaned = cleaned[len(prefix) :]
            break

    # Take everything before @ (SIP user part)
    if "@" in cleaned:
        cleaned = cleaned.split("@")[0]

    # Strip whitespace and dashes for validation
    stripped = cleaned.replace("-", "").replace(" ", "").replace("(", "").replace(")", "")
    if _PHONE_RE.match(stripped):
        return cleaned

    return None


def detect_direction_and_numbers(
    medium: Any,
    metadata: dict | None = None,
) -> tuple[str, str | None, str | None]:
    """Detect call direction and extract phone numbers from Ultravox medium.

    Returns:
        (direction, caller_number, called_number)

    Ultravox medium structures:
    - Inbound:  {"sip": {"incoming": {"from": "+34612...", "to": "+34911..."}}}
    - Outbound: {"sip": {"outgoing": {"to": "sip:+34612...@zadarma.com", "from": "sip:+34911...@zadarma.com"}}}
    - Telnyx:   {"telnyx": {"from": "+34612...", "to": "+34911..."}}
    - Twilio:   {"twilio": {"from": "+34612...", "to": "+34911..."}}

    Falls back to "inbound" if direction cannot be determined (backward-compatible).
    """
    direction = "inbound"
    caller_number: str | None = None
    called_number: str | None = None

    if not medium or not isinstance(medium, dict):
        return direction, caller_number, called_number

    # --- SIP metadata (primera opción — CLI real del llamante vía Zadarma) ---
    if isinstance(metadata, dict):
        sip_caller = metadata.get("ultravox.sip.caller_id")
        if sip_caller:
            caller_number = sip_caller
            logger.debug("Got caller from SIP metadata: %s", caller_number)

    # --- SIP ---
    if "sip" in medium:
        sip = medium["sip"]
        if isinstance(sip, dict):
            # Check outgoing first (outbound calls)
            outgoing = sip.get("outgoing")
            if isinstance(outgoing, dict) and outgoing:
                direction = "outbound"
                # For outbound: "to" = the person we're calling, "from" = our SIP URI
                called_number = _extract_phone_from_sip_uri(outgoing.get("to", ""))
                caller_number = _extract_phone_from_sip_uri(outgoing.get("from", ""))
                logger.debug(
                    "SIP outgoing detected: caller=%s, called=%s",
                    caller_number,
                    called_number,
                )
            else:
                # Check incoming (inbound calls)
                incoming = sip.get("incoming")
                if isinstance(incoming, dict) and incoming:
                    direction = "inbound"
                    if not caller_number:
                        caller_number = incoming.get("from") or incoming.get("callerNumber")
                    called_number = incoming.get("to") or incoming.get("calledNumber")

    # --- Telnyx / Twilio ---
    for provider in ("telnyx", "twilio"):
        if provider in medium:
            prov_data = medium[provider]
            if isinstance(prov_data, dict):
                if not caller_number:
                    caller_number = prov_data.get("from") or prov_data.get("callerNumber")
                if not called_number:
                    called_number = prov_data.get("to") or prov_data.get("calledNumber")

    return direction, caller_number, called_number
