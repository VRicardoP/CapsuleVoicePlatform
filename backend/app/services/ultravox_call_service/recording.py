"""Ultravox recording and API mixin."""

import json
import logging
from typing import Any

import httpx
from sqlalchemy import text

from app.config.settings import settings as app_settings
from app.services.recording_service import RecordingService

logger = logging.getLogger(__name__)

ULTRAVOX_API_KEY = app_settings.ultravox_api_key or None


class UltravoxRecordingMixin:
    """Recording processing and Ultravox API methods."""

    @staticmethod
    async def fetch_call_details(call_id: str) -> dict[str, Any] | None:
        """Fetch call details from Ultravox API to get phone number and summary.

        Returns the call data including fromNumber/toNumber if available.
        """
        if not ULTRAVOX_API_KEY:
            logger.warning("ULTRAVOX_API_KEY not configured, cannot fetch call details")
            return None

        try:
            from app.core.http_clients import ultravox_client

            response = await ultravox_client.get(
                f"https://api.ultravox.ai/api/calls/{call_id}",
                headers={"X-API-Key": ULTRAVOX_API_KEY},
            )
            if response.status_code == 200:
                data = response.json()
                logger.debug("Ultravox API call details: %s", json.dumps(data, default=str)[:500])
                return data
            else:
                logger.warning(
                    "Failed to fetch Ultravox call %s: %d", call_id, response.status_code
                )
                return None
        except (httpx.HTTPError, json.JSONDecodeError, KeyError) as e:
            logger.error("Error fetching Ultravox call details: %s", e)
            return None

    @staticmethod
    async def fetch_messages(
        call_id: str, include_tool_calls: bool = False
    ) -> list[dict[str, Any]]:
        """Fetch call messages from Ultravox API.

        By default returns only AGENT and USER messages (for transcript).
        Set include_tool_calls=True to also return TOOL_CALL and TOOL_RESULT messages.
        """
        if not ULTRAVOX_API_KEY:
            logger.warning("ULTRAVOX_API_KEY not configured, cannot fetch messages")
            return []

        roles_filter = {"MESSAGE_ROLE_AGENT", "MESSAGE_ROLE_USER"}
        if include_tool_calls:
            roles_filter.add("MESSAGE_ROLE_TOOL_CALL")
            roles_filter.add("MESSAGE_ROLE_TOOL_RESULT")

        all_messages = []
        cursor = None

        try:
            from app.core.http_clients import ultravox_client

            while True:
                url = f"https://api.ultravox.ai/api/calls/{call_id}/messages"
                if cursor:
                    url += f"?cursor={cursor}"

                response = await ultravox_client.get(url, headers={"X-API-Key": ULTRAVOX_API_KEY})
                if response.status_code != 200:
                    logger.warning(
                        "Failed to fetch Ultravox messages %s: %d", call_id, response.status_code
                    )
                    break

                data = response.json()
                results = data.get("results", [])

                for msg in results:
                    role = msg.get("role", "")
                    if role in roles_filter:
                        all_messages.append(msg)

                # Check for pagination
                cursor = data.get("next")
                if not cursor:
                    break

            tool_count = sum(
                1 for m in all_messages if m.get("role", "").startswith("MESSAGE_ROLE_TOOL")
            )
            conv_count = len(all_messages) - tool_count
            logger.debug(
                "Ultravox API messages: fetched %d conversation + %d tool messages",
                conv_count,
                tool_count,
            )
            return all_messages
        except (httpx.HTTPError, json.JSONDecodeError, KeyError) as e:
            logger.error("Error fetching Ultravox messages: %s", e)
            return []

    # -----------------------------------------------------------------------
    # Zadarma integration
    # -----------------------------------------------------------------------

    @staticmethod
    async def process_recording_background(
        ultravox_call_id: str,
        db_call_id: str,
        api_key: str,
    ) -> None:
        """Background task: download, transcode, encrypt and save recording."""
        from app.config.database import async_session_maker

        try:
            recording_service = RecordingService(app_settings)
            file_path = await recording_service.download_and_process(
                ultravox_call_id=ultravox_call_id,
                db_call_id=db_call_id,
                ultravox_api_key=api_key,
            )
            if file_path:
                async with async_session_maker() as session:
                    await session.execute(
                        text(
                            "UPDATE calls SET recording_file_path = :path, is_recorded = true, updated_at = NOW() WHERE id = :call_id"
                        ),
                        {"call_id": db_call_id, "path": file_path},
                    )
                    await session.commit()
                logger.info("Ultravox: recording saved (background): %s", file_path)
        except (httpx.HTTPError, json.JSONDecodeError, KeyError) as e:
            logger.error("Ultravox: recording processing failed (background): %s", e)
