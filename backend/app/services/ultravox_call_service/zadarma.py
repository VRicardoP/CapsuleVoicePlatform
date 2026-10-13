"""Ultravox Zadarma integration mixin."""

import base64
import hashlib
import hmac
import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode

import httpx

from app.config.settings import settings as app_settings

logger = logging.getLogger(__name__)

ZADARMA_API_KEY = app_settings.zadarma_api_key or None
ZADARMA_API_SECRET = app_settings.zadarma_api_secret or None

# In-memory cache for Zadarma call -> caller_id mapping
# This is populated by Zadarma NOTIFY_START webhook and consumed by Ultravox webhook
# Key: timestamp_called_number (e.g., "1704067200_34911234567")
# Value: {"caller_id": "+34612345678", "pbx_call_id": "xxx", "timestamp": datetime}
# Entries expire after 10 minutes
ZADARMA_CALL_CACHE: dict[str, dict[str, Any]] = {}
ZADARMA_CACHE_TTL_SECONDS = 600  # 10 minutes


class UltravoxZadarmaMixin:
    """Zadarma integration methods."""

    @staticmethod
    def generate_zadarma_signature(
        api_key: str, api_secret: str, method: str, params: dict[str, str]
    ) -> str:
        """Generate Zadarma API signature.

        Zadarma uses HMAC-SHA1 with a specific signature format:
        1. Sort params alphabetically
        2. Create params string
        3. Sign: base64(hmac_sha1_hex(method + params_string + md5(params_string), api_secret))

        The hex digest must be base64 encoded (PHP-style signature).
        """
        # Sort parameters alphabetically and encode
        sorted_params = sorted(params.items())
        params_string = urlencode(sorted_params)

        # Create the string to sign
        sign_string = method + params_string + hashlib.md5(params_string.encode()).hexdigest()

        # Generate HMAC-SHA1 signature (hex string then base64 encode)
        hex_signature = hmac.new(
            api_secret.encode(), sign_string.encode(), hashlib.sha1
        ).hexdigest()

        # Base64 encode the hex string (Zadarma's PHP-style signature)
        signature = base64.b64encode(hex_signature.encode()).decode()

        return signature

    @staticmethod
    async def fetch_zadarma_caller_number(
        call_end_time: datetime,
        duration_seconds: int,
        called_number: str | None = None,
        call_type: str = "in",
    ) -> str | None:
        """Fetch caller phone number from Zadarma statistics API.

        Correlates Ultravox call with Zadarma call by:
        - Time window (call ended around the same time)
        - Duration (similar duration within 5 seconds tolerance)
        - Called number (DID) if provided

        Returns the caller's phone number if found.
        """
        if not ZADARMA_API_KEY or not ZADARMA_API_SECRET:
            logger.warning("ZADARMA_API_KEY/SECRET not configured, cannot fetch caller number")
            return None

        try:
            # Query calls from last 5 minutes to now
            start_time = call_end_time - timedelta(minutes=5)
            end_time = call_end_time + timedelta(minutes=1)

            params = {
                "start": start_time.strftime("%Y-%m-%d %H:%M:%S"),
                "end": end_time.strftime("%Y-%m-%d %H:%M:%S"),
                "type": call_type,  # "in" for inbound, "out" for outbound
            }

            method = "/v1/statistics/"
            signature = UltravoxZadarmaMixin.generate_zadarma_signature(
                ZADARMA_API_KEY, ZADARMA_API_SECRET, method, params
            )

            from app.core.http_clients import ultravox_client

            response = await ultravox_client.get(
                f"https://api.zadarma.com{method}",
                params=params,
                headers={"Authorization": f"{ZADARMA_API_KEY}:{signature}"},
            )

            logger.debug(
                "Zadarma API response: status=%d, body=%s",
                response.status_code,
                response.text[:500],
            )

            if response.status_code != 200:
                logger.warning("Zadarma API error: %d", response.status_code)
                return None

            data = response.json()
            if data.get("status") != "success":
                logger.warning("Zadarma API error: %s", data.get("message"))
                return None

            stats = data.get("stats", [])
            if not stats:
                logger.debug("Zadarma: no calls found in time window")
                return None

                # Find matching call by duration (within 5 seconds tolerance)
                best_match = None
                best_diff = float("inf")

                for call in stats:
                    call_duration = int(call.get("seconds", 0))
                    duration_diff = abs(call_duration - duration_seconds)

                    # If we have a called_number (DID), filter by it
                    if called_number:
                        call_destination = call.get("destination", "")
                        if (
                            called_number not in call_destination
                            and call_destination not in called_number
                        ):
                            continue

                    # Find the call with closest duration match
                    if (
                        duration_diff < best_diff and duration_diff <= 10
                    ):  # Max 10 seconds tolerance
                        best_diff = duration_diff
                        best_match = call

                if best_match:
                    caller = best_match.get("caller_id") or best_match.get("from")
                    logger.debug(
                        "Zadarma: found matching call, caller=%s, duration_diff=%ds",
                        caller,
                        best_diff,
                    )
                    return caller
                else:
                    logger.debug("Zadarma: no matching call found (duration=%ds)", duration_seconds)
                    return None

        except (httpx.HTTPError, ValueError, KeyError) as e:
            logger.error(f"Error fetching Zadarma statistics: {e}")
            return None

    @staticmethod
    def cleanup_zadarma_cache() -> None:
        """Remove expired entries from Zadarma call cache."""
        now = datetime.now(UTC)
        expired_keys = [
            key
            for key, value in ZADARMA_CALL_CACHE.items()
            if (now - value.get("timestamp", now)).total_seconds() > ZADARMA_CACHE_TTL_SECONDS
        ]
        for key in expired_keys:
            del ZADARMA_CALL_CACHE[key]

    @staticmethod
    def store_zadarma_caller(
        called_number: str, caller_id: str, pbx_call_id: str | None = None
    ) -> None:
        """Store caller ID from Zadarma NOTIFY_START for later correlation."""
        UltravoxZadarmaMixin.cleanup_zadarma_cache()

        # Normalize called number (remove +, spaces, etc.)
        called_normalized = called_number.replace("+", "").replace(" ", "").replace("-", "")

        # Use timestamp + called number as key for correlation
        now = datetime.now(UTC)
        # Round timestamp to nearest 30 seconds for fuzzy matching
        timestamp_key = int(now.timestamp()) // 30 * 30
        cache_key = f"{timestamp_key}_{called_normalized}"

        ZADARMA_CALL_CACHE[cache_key] = {
            "caller_id": caller_id,
            "pbx_call_id": pbx_call_id,
            "called_number": called_number,
            "timestamp": now,
        }

        # Also store with just the called number for simpler lookup
        ZADARMA_CALL_CACHE[f"latest_{called_normalized}"] = {
            "caller_id": caller_id,
            "pbx_call_id": pbx_call_id,
            "called_number": called_number,
            "timestamp": now,
        }

        logger.debug(
            "Zadarma cache: stored caller_id=%s*** for called=%s", caller_id[:6], called_number
        )

    @staticmethod
    def lookup_zadarma_caller(
        called_number: str | None = None, approximate_start_time: datetime | None = None
    ) -> str | None:
        """Lookup caller ID from Zadarma cache.

        Tries multiple strategies:
        1. If called_number is provided, look for latest call to that number
        2. If approximate_start_time is provided, look for calls around that time
        3. Return the most recent cached caller if nothing else matches
        """
        UltravoxZadarmaMixin.cleanup_zadarma_cache()

        if not ZADARMA_CALL_CACHE:
            return None

        # Strategy 1: Look up by called number (DID)
        if called_number:
            called_normalized = called_number.replace("+", "").replace(" ", "").replace("-", "")
            latest_key = f"latest_{called_normalized}"
            if latest_key in ZADARMA_CALL_CACHE:
                entry = ZADARMA_CALL_CACHE[latest_key]
                # Only use if fresh (last 2 minutes)
                age = (datetime.now(UTC) - entry["timestamp"]).total_seconds()
                if age < 120:
                    logger.debug("Zadarma cache hit: found caller by DID, age=%.0fs", age)
                    return entry["caller_id"]

        # Strategy 2: Look for calls around approximate start time
        if approximate_start_time:
            timestamp_key = int(approximate_start_time.timestamp()) // 30 * 30
            for offset in [0, -30, 30, -60, 60]:  # Check nearby time windows
                check_key = f"{timestamp_key + offset}_"
                for key, entry in ZADARMA_CALL_CACHE.items():
                    if key.startswith(check_key):
                        logger.debug("Zadarma cache hit: found caller by timestamp")
                        return entry["caller_id"]

        # Strategy 3: Return most recent entry if very fresh (last 30 seconds)
        most_recent = None
        most_recent_time = None
        for key, entry in ZADARMA_CALL_CACHE.items():
            if key.startswith("latest_"):
                continue
            if most_recent_time is None or entry["timestamp"] > most_recent_time:
                most_recent = entry
                most_recent_time = entry["timestamp"]

        if most_recent:
            age = (datetime.now(UTC) - most_recent["timestamp"]).total_seconds()
            if age < 30:
                logger.debug("Zadarma cache hit: using most recent caller, age=%.0fs", age)
                return most_recent["caller_id"]

        logger.debug("Zadarma cache miss: no matching caller found")
        return None
