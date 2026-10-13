"""
Unit tests for WhatsApp SSE Broadcaster.

Tests verify pub/sub mechanics, queue behavior, and tenant isolation.
No database required.
"""

import asyncio

import pytest

from app.services.whatsapp_sse import SSEBroadcaster


@pytest.fixture
def broadcaster():
    return SSEBroadcaster()


class TestSSEBroadcaster:
    def test_initial_state(self, broadcaster: SSEBroadcaster):
        assert broadcaster.subscriber_count("tenant-1") == 0

    def test_subscribe_creates_queue(self, broadcaster: SSEBroadcaster):
        queue = broadcaster.subscribe("tenant-1")
        assert isinstance(queue, asyncio.Queue)
        assert broadcaster.subscriber_count("tenant-1") == 1

    def test_multiple_subscribers(self, broadcaster: SSEBroadcaster):
        broadcaster.subscribe("tenant-1")
        broadcaster.subscribe("tenant-1")
        broadcaster.subscribe("tenant-2")
        assert broadcaster.subscriber_count("tenant-1") == 2
        assert broadcaster.subscriber_count("tenant-2") == 1

    def test_unsubscribe_removes_queue(self, broadcaster: SSEBroadcaster):
        q1 = broadcaster.subscribe("tenant-1")
        q2 = broadcaster.subscribe("tenant-1")
        broadcaster.unsubscribe("tenant-1", q1)
        assert broadcaster.subscriber_count("tenant-1") == 1
        broadcaster.unsubscribe("tenant-1", q2)
        assert broadcaster.subscriber_count("tenant-1") == 0

    def test_unsubscribe_nonexistent_safe(self, broadcaster: SSEBroadcaster):
        """Unsubscribing a queue that doesn't exist should not raise."""
        q = asyncio.Queue()
        broadcaster.unsubscribe("nonexistent", q)

    @pytest.mark.asyncio
    async def test_publish_delivers_to_subscriber(self, broadcaster: SSEBroadcaster):
        queue = broadcaster.subscribe("tenant-1")
        await broadcaster.publish("tenant-1", "message.new", {"text": "hola"})

        payload = queue.get_nowait()
        assert payload["event"] == "message.new"
        assert payload["data"]["text"] == "hola"

    @pytest.mark.asyncio
    async def test_publish_delivers_to_all_subscribers(self, broadcaster: SSEBroadcaster):
        q1 = broadcaster.subscribe("tenant-1")
        q2 = broadcaster.subscribe("tenant-1")
        await broadcaster.publish("tenant-1", "test", {"x": 1})

        assert not q1.empty()
        assert not q2.empty()
        assert q1.get_nowait()["data"]["x"] == 1
        assert q2.get_nowait()["data"]["x"] == 1

    @pytest.mark.asyncio
    async def test_publish_tenant_isolation(self, broadcaster: SSEBroadcaster):
        q1 = broadcaster.subscribe("tenant-1")
        q2 = broadcaster.subscribe("tenant-2")
        await broadcaster.publish("tenant-1", "test", {"for": "t1"})

        assert not q1.empty()
        assert q2.empty()

    @pytest.mark.asyncio
    async def test_publish_no_subscribers_safe(self, broadcaster: SSEBroadcaster):
        """Publishing with no subscribers should not raise."""
        await broadcaster.publish("nobody", "test", {"data": 1})

    @pytest.mark.asyncio
    async def test_full_queue_drops_event(self, broadcaster: SSEBroadcaster):
        """When queue is full (100 items), new events are silently dropped."""
        queue = broadcaster.subscribe("tenant-1")

        # Fill the queue (maxsize=100)
        for i in range(100):
            await broadcaster.publish("tenant-1", "fill", {"i": i})

        assert queue.full()

        # This should not raise — just silently drop
        await broadcaster.publish("tenant-1", "overflow", {"dropped": True})

        # Queue should still have 100 items (not 101)
        assert queue.qsize() == 100

    @pytest.mark.asyncio
    async def test_event_payload_structure(self, broadcaster: SSEBroadcaster):
        """Verify the exact payload structure sent to subscribers."""
        queue = broadcaster.subscribe("t1")
        await broadcaster.publish(
            "t1",
            "message.status",
            {
                "conversationId": "abc-123",
                "messageId": "msg-456",
                "status": "delivered",
            },
        )

        payload = queue.get_nowait()
        assert "event" in payload
        assert "data" in payload
        assert payload["event"] == "message.status"
        assert payload["data"]["conversationId"] == "abc-123"
