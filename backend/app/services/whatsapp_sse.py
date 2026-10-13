"""SSE (Server-Sent Events) broadcaster for real-time updates.

Supports Redis pub/sub for cross-process communication (ARQ worker -> API server).
"""

import asyncio
import json
import logging
import uuid
from collections import defaultdict

logger = logging.getLogger(__name__)


class SSEBroadcaster:
    """
    Manages SSE subscriptions per tenant.

    Each subscriber gets an asyncio.Queue. Events are published
    to all queues for a given tenant_id. Slow clients (full queue)
    have events silently dropped.

    When Redis is connected, events are also published to Redis pub/sub
    so that ARQ workers (separate processes) can push SSE events.
    """

    def __init__(self) -> None:
        self._subscribers: dict[str, list[asyncio.Queue]] = defaultdict(list)
        self._instance_id: str = uuid.uuid4().hex[:8]
        self._pubsub = None
        self._listener_task: asyncio.Task | None = None

    def subscribe(self, tenant_id: str) -> asyncio.Queue:
        """Create a new subscription queue for a tenant."""
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._subscribers[tenant_id].append(queue)
        logger.info(
            "SSE subscriber added",
            extra={"tenant_id": tenant_id, "total": len(self._subscribers[tenant_id])},
        )
        return queue

    def unsubscribe(self, tenant_id: str, queue: asyncio.Queue) -> None:
        """Remove a subscription queue."""
        try:
            self._subscribers[tenant_id].remove(queue)
            if not self._subscribers[tenant_id]:
                del self._subscribers[tenant_id]
            logger.info("SSE subscriber removed", extra={"tenant_id": tenant_id})
        except (ValueError, KeyError):
            pass

    async def publish(self, tenant_id: str, event_type: str, data: dict) -> None:
        """
        Publish an event to all subscribers of a tenant.

        Delivers to local asyncio queues AND Redis pub/sub (if connected).
        Non-blocking: drops events for slow clients (full queue).
        """
        payload = {"event": event_type, "data": data}
        self._deliver_local(tenant_id, payload)
        await self._publish_redis(tenant_id, payload)

    def _deliver_local(self, tenant_id: str, payload: dict) -> None:
        """Deliver a payload to all local asyncio queues for a tenant."""
        queues = self._subscribers.get(tenant_id, [])
        for queue in queues:
            try:
                queue.put_nowait(payload)
            except asyncio.QueueFull:
                logger.warning(
                    "SSE queue full, dropping event",
                    extra={"tenant_id": tenant_id, "event_type": payload.get("event")},
                )

    async def _publish_redis(self, tenant_id: str, payload: dict) -> None:
        """Publish to Redis pub/sub channel. No-op if Redis not connected."""
        from app.core import redis as redis_mod

        if redis_mod.pool is None:
            return
        try:
            message = json.dumps(
                {
                    "origin": self._instance_id,
                    "payload": payload,
                }
            )
            await redis_mod.pool.publish(f"sse:{tenant_id}", message)
        except Exception:
            logger.warning("Failed to publish SSE event to Redis", exc_info=True)

    # --- Redis pub/sub listener (receives events from worker processes) ---

    async def start_redis_listener(self) -> None:
        """Subscribe to Redis pub/sub and forward events to local queues.

        Called from main.py lifespan after Redis is initialized.
        """
        from app.core import redis as redis_mod

        r = redis_mod.get_pool()
        self._pubsub = r.pubsub()
        await self._pubsub.psubscribe("sse:*")
        self._listener_task = asyncio.create_task(self._redis_listen_loop())
        logger.info("SSE Redis pub/sub listener started")

    async def _redis_listen_loop(self) -> None:
        """Background loop: read Redis pub/sub and forward to local queues."""
        try:
            async for message in self._pubsub.listen():
                if message["type"] != "pmessage":
                    continue
                try:
                    channel = message["channel"]
                    tenant_id = channel.split(":", 1)[1]
                    envelope = json.loads(message["data"])

                    # Skip messages we published ourselves (avoid double-delivery)
                    if envelope.get("origin") == self._instance_id:
                        continue

                    self._deliver_local(tenant_id, envelope["payload"])
                except (json.JSONDecodeError, KeyError, IndexError):
                    logger.warning("Malformed SSE Redis message", extra={"raw": message})
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.error("SSE Redis listener crashed", exc_info=True)

    async def stop_redis_listener(self) -> None:
        """Stop the Redis pub/sub listener. Called on shutdown."""
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
            self._listener_task = None
        if self._pubsub:
            await self._pubsub.punsubscribe("sse:*")
            await self._pubsub.aclose()
            self._pubsub = None
        logger.info("SSE Redis pub/sub listener stopped")

    def subscriber_count(self, tenant_id: str) -> int:
        """Get number of active subscribers for a tenant."""
        return len(self._subscribers.get(tenant_id, []))


# Singleton instance
sse_broadcaster = SSEBroadcaster()
