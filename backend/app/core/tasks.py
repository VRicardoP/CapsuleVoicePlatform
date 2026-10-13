"""Helpers for background asyncio tasks with error handling."""

import asyncio
import logging
from collections.abc import Coroutine
from typing import Any

logger = logging.getLogger(__name__)


def create_logged_task(
    coro: Coroutine[Any, Any, Any],
    *,
    name: str | None = None,
) -> asyncio.Task:
    """Create an asyncio task that logs exceptions instead of silently dropping them.

    Use this instead of bare ``asyncio.create_task()`` for fire-and-forget work.
    """

    async def _wrapper() -> None:
        try:
            await coro
        except asyncio.CancelledError:
            pass
        except Exception:
            task_label = name or "background task"
            logger.error("Unhandled exception in %s", task_label, exc_info=True)

    return asyncio.create_task(_wrapper(), name=name)
