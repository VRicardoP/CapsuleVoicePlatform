"""Shared httpx AsyncClient singletons for connection reuse.

Managed by the FastAPI lifespan in main.py.
"""

import httpx

# Ultravox API client (short timeouts, no redirects)
ultravox_client: httpx.AsyncClient | None = None

# WhatsApp/Meta API client
whatsapp_client: httpx.AsyncClient | None = None

# Recording download client (longer timeout, follows redirects)
recording_client: httpx.AsyncClient | None = None

# Apify REST API client (for captacion scrapers)
apify_client: httpx.AsyncClient | None = None

# OpenAI API client (for captacion call analysis)
openai_client: httpx.AsyncClient | None = None


async def startup() -> None:
    """Initialize shared HTTP clients. Called from main.py lifespan."""
    global ultravox_client, whatsapp_client, recording_client, apify_client, openai_client

    ultravox_client = httpx.AsyncClient(timeout=15.0)
    whatsapp_client = httpx.AsyncClient(timeout=30.0)
    recording_client = httpx.AsyncClient(follow_redirects=True, timeout=60.0)
    apify_client = httpx.AsyncClient(timeout=120.0)
    openai_client = httpx.AsyncClient(timeout=60.0)


async def shutdown() -> None:
    """Close shared HTTP clients. Called from main.py lifespan."""
    global ultravox_client, whatsapp_client, recording_client, apify_client, openai_client

    for client in (ultravox_client, whatsapp_client, recording_client, apify_client, openai_client):
        if client:
            await client.aclose()

    ultravox_client = None
    whatsapp_client = None
    recording_client = None
    apify_client = None
    openai_client = None
