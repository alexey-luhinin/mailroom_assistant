import asyncio

import httpx
import pytest

LEAD    = "http://localhost:8000"
SORTER  = "http://localhost:8001"
DRAFTER = "http://localhost:8003"
BRIEFER = "http://localhost:8005"
MCP     = "http://localhost:8006"


@pytest.fixture
def lead_url():
    return LEAD


@pytest.fixture
async def client():
    async with httpx.AsyncClient(timeout=30.0) as c:
        yield c


@pytest.fixture
async def lead(client):
    """Shorthand: pre-configured client + lead base URL."""
    return client, LEAD


async def poll_until_done(
    client: httpx.AsyncClient,
    url: str,
    interval: float = 2.0,
    timeout: float = 120.0,
) -> dict:
    """Poll GET url until status is 'done' or 'failed'. Raises TimeoutError on timeout."""
    deadline = asyncio.get_event_loop().time() + timeout
    while True:
        r = await client.get(url)
        r.raise_for_status()
        data = r.json()
        if data["status"] in ("done", "failed"):
            return data
        if asyncio.get_event_loop().time() > deadline:
            raise TimeoutError(f"Job at {url} did not complete within {timeout}s")
        await asyncio.sleep(interval)
