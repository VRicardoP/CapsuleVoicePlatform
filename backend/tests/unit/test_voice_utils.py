"""Tests for app.voice.utils — direction detection and phone extraction."""


from app.voice.utils import (
    _extract_phone_from_sip_uri,
    detect_direction_and_numbers,
)

# ============================================================================
# _extract_phone_from_sip_uri
# ============================================================================


class TestExtractPhoneFromSipUri:
    def test_full_sip_uri(self):
        assert _extract_phone_from_sip_uri("sip:+34612345678@zadarma.com") == "+34612345678"

    def test_sip_uri_no_plus(self):
        assert _extract_phone_from_sip_uri("sip:34612345678@zadarma.com") == "34612345678"

    def test_tel_uri(self):
        assert _extract_phone_from_sip_uri("tel:+34612345678") == "+34612345678"

    def test_plain_phone(self):
        assert _extract_phone_from_sip_uri("+34612345678") == "+34612345678"

    def test_empty_string(self):
        assert _extract_phone_from_sip_uri("") is None

    def test_none(self):
        assert _extract_phone_from_sip_uri(None) is None

    def test_invalid_uri(self):
        assert _extract_phone_from_sip_uri("sip:agent@server.com") is None

    def test_short_number(self):
        assert _extract_phone_from_sip_uri("sip:123@x.com") is None

    def test_international_format(self):
        assert _extract_phone_from_sip_uri("sip:+442071234567@provider.co.uk") == "+442071234567"


# ============================================================================
# detect_direction_and_numbers — Inbound SIP
# ============================================================================


class TestDetectDirectionInbound:
    def test_sip_incoming_basic(self):
        medium = {
            "sip": {
                "incoming": {
                    "from": "+34612345678",
                    "to": "+34911234567",
                }
            }
        }
        direction, caller, called = detect_direction_and_numbers(medium)
        assert direction == "inbound"
        assert caller == "+34612345678"
        assert called == "+34911234567"

    def test_sip_incoming_caller_number_field(self):
        medium = {
            "sip": {
                "incoming": {
                    "callerNumber": "+34600111222",
                    "calledNumber": "+34900333444",
                }
            }
        }
        direction, caller, called = detect_direction_and_numbers(medium)
        assert direction == "inbound"
        assert caller == "+34600111222"
        assert called == "+34900333444"

    def test_sip_incoming_empty_incoming(self):
        """Empty incoming dict — should default to inbound with no numbers."""
        medium = {"sip": {"incoming": {}}}
        direction, caller, called = detect_direction_and_numbers(medium)
        assert direction == "inbound"
        assert caller is None
        assert called is None

    def test_sip_metadata_fallback(self):
        """If no numbers in medium, SIP metadata should provide caller."""
        medium = {"sip": {"incoming": {}}}
        metadata = {"ultravox.sip.caller_id": "+34666777888"}
        direction, caller, called = detect_direction_and_numbers(medium, metadata)
        assert direction == "inbound"
        assert caller == "+34666777888"
        assert called is None


# ============================================================================
# detect_direction_and_numbers — Outbound SIP
# ============================================================================


class TestDetectDirectionOutbound:
    def test_sip_outgoing_basic(self):
        medium = {
            "sip": {
                "outgoing": {
                    "to": "sip:+34612345678@zadarma.com",
                    "from": "sip:+34911234567@zadarma.com",
                }
            }
        }
        direction, caller, called = detect_direction_and_numbers(medium)
        assert direction == "outbound"
        assert caller == "+34911234567"  # our number
        assert called == "+34612345678"  # customer number

    def test_sip_outgoing_plain_numbers(self):
        medium = {
            "sip": {
                "outgoing": {
                    "to": "+34612345678",
                    "from": "+34911234567",
                }
            }
        }
        direction, caller, called = detect_direction_and_numbers(medium)
        assert direction == "outbound"
        assert caller == "+34911234567"
        assert called == "+34612345678"

    def test_sip_outgoing_tel_uri(self):
        medium = {
            "sip": {
                "outgoing": {
                    "to": "tel:+34612345678",
                    "from": "tel:+34911234567",
                }
            }
        }
        direction, caller, called = detect_direction_and_numbers(medium)
        assert direction == "outbound"
        assert caller == "+34911234567"
        assert called == "+34612345678"

    def test_outgoing_takes_priority_over_incoming(self):
        """If both outgoing and incoming exist, outgoing wins."""
        medium = {
            "sip": {
                "outgoing": {
                    "to": "sip:+34111111111@z.com",
                    "from": "sip:+34222222222@z.com",
                },
                "incoming": {
                    "from": "+34333333333",
                    "to": "+34444444444",
                },
            }
        }
        direction, caller, called = detect_direction_and_numbers(medium)
        assert direction == "outbound"
        assert caller == "+34222222222"
        assert called == "+34111111111"


# ============================================================================
# detect_direction_and_numbers — Telnyx / Twilio
# ============================================================================


class TestDetectDirectionTelnyxTwilio:
    def test_telnyx(self):
        medium = {"telnyx": {"from": "+14155551234", "to": "+14155555678"}}
        direction, caller, called = detect_direction_and_numbers(medium)
        assert direction == "inbound"  # no SIP info, defaults to inbound
        assert caller == "+14155551234"
        assert called == "+14155555678"

    def test_twilio(self):
        medium = {"twilio": {"from": "+14155551234", "to": "+14155555678"}}
        direction, caller, called = detect_direction_and_numbers(medium)
        assert direction == "inbound"
        assert caller == "+14155551234"
        assert called == "+14155555678"

    def test_telnyx_with_caller_number_field(self):
        medium = {"telnyx": {"callerNumber": "+14155551234", "calledNumber": "+14155555678"}}
        direction, caller, called = detect_direction_and_numbers(medium)
        assert caller == "+14155551234"
        assert called == "+14155555678"


# ============================================================================
# detect_direction_and_numbers — Edge Cases
# ============================================================================


class TestDetectDirectionEdgeCases:
    def test_none_medium(self):
        direction, caller, called = detect_direction_and_numbers(None)
        assert direction == "inbound"
        assert caller is None
        assert called is None

    def test_empty_dict(self):
        direction, caller, called = detect_direction_and_numbers({})
        assert direction == "inbound"
        assert caller is None
        assert called is None

    def test_string_medium(self):
        direction, caller, called = detect_direction_and_numbers("not_a_dict")
        assert direction == "inbound"
        assert caller is None
        assert called is None

    def test_sip_not_dict(self):
        medium = {"sip": "invalid"}
        direction, caller, called = detect_direction_and_numbers(medium)
        assert direction == "inbound"

    def test_metadata_only(self):
        """Metadata alone with no medium should work."""
        direction, caller, called = detect_direction_and_numbers(
            None, {"ultravox.sip.caller_id": "+34666999888"}
        )
        assert direction == "inbound"
        assert caller is None  # medium is None, so detect returns early


# ============================================================================
# Backward compatibility — typical Zadarma SIP payloads
# ============================================================================


class TestBackwardCompatibilitySipPayloads:
    """Ensure existing inbound SIP payloads still work identically."""

    def test_typical_inbound(self):
        """Typical inbound call via Zadarma SIP."""
        medium = {
            "sip": {
                "incoming": {
                    "from": "+34942123456",
                    "to": "+34942654321",
                }
            }
        }
        direction, caller, called = detect_direction_and_numbers(medium)
        assert direction == "inbound"
        assert caller == "+34942123456"
        assert called == "+34942654321"

    def test_sip_metadata_only(self):
        """Call where only SIP metadata has caller ID."""
        medium = {"sip": {"incoming": {}}}
        metadata = {"ultravox.sip.caller_id": "+34942123456"}
        direction, caller, called = detect_direction_and_numbers(medium, metadata)
        assert direction == "inbound"
        assert caller == "+34942123456"

    def test_no_medium(self):
        """Call where medium is absent — should default to inbound."""
        direction, caller, called = detect_direction_and_numbers(None)
        assert direction == "inbound"
        assert caller is None
        assert called is None
