import pytest

from conftest import BRIEFER, DRAFTER, LEAD, MCP, SORTER


@pytest.mark.parametrize("url,service_name", [
    (f"{LEAD}/health",    "lead-agent"),
    (f"{SORTER}/health",  "sorter"),
    (f"{DRAFTER}/health", "drafter"),
    (f"{BRIEFER}/health", "briefer"),
    (f"{MCP}/health",     "mcp-server"),
])
async def test_service_health(client, url, service_name):
    r = await client.get(url)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data["service"] == service_name


async def test_lead_health_shows_all_dependency_keys(client):
    r = await client.get(f"{LEAD}/health")
    assert r.status_code == 200
    deps = r.json()["dependencies"]
    assert set(deps.keys()) == {
        "sorter", "researcher", "drafter", "critic", "briefer", "mcp-server"
    }


async def test_lead_health_core_services_ok(client):
    r = await client.get(f"{LEAD}/health")
    assert r.status_code == 200
    deps = r.json()["dependencies"]
    for svc in ("sorter", "drafter", "briefer", "mcp-server"):
        assert deps[svc] == "ok", f"Core service '{svc}' is not healthy: got '{deps[svc]}'"


async def test_lead_health_dependency_values_are_valid(client):
    r = await client.get(f"{LEAD}/health")
    deps = r.json()["dependencies"]
    for name, status in deps.items():
        assert status in ("ok", "error"), (
            f"Dependency '{name}' has unexpected status '{status}'"
        )
