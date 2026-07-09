# Testing Skill — API Integration Tests

## Stack

- **pytest** with `pytest-asyncio` for async test functions
- **httpx** `AsyncClient` for HTTP calls
- Tests run against a live `docker-compose up` environment
- No mocking of services — test real HTTP round-trips

```
pip install pytest pytest-asyncio httpx
```

`pytest.ini` (or `pyproject.toml`):
```ini
[pytest]
asyncio_mode = auto
```

---

## How to Run

```bash
# Start all services
docker-compose up -d

# Run all tests
pytest tests/

# Run a specific service suite
pytest tests/test_lead_agent.py -v

# Run with output (useful for polling logs)
pytest tests/ -s
```

Tests assume services are reachable at their default ports.
Use `docker-compose ps` to confirm all containers are healthy before running.

---

## Base URLs and Fixtures

Put these in `tests/conftest.py`:

```python
import pytest
import httpx

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
    """Shorthand: pre-configured client + base URL."""
    return client, LEAD
```

---

## Pattern: Testing a Simple Endpoint

```python
async def test_health(client):
    r = await client.get(f"{LEAD}/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data["service"] == "lead-agent"


async def test_get_emails_default(client):
    r = await client.get(f"{LEAD}/emails")
    assert r.status_code == 200
    emails = r.json()
    assert isinstance(emails, list)
    for e in emails:
        assert "id" in e
        assert "label" in e
        assert e["label"] in {
            "urgent", "action_needed", "fyi",
            "calendar", "newsletter", "promo", "spam",
        }


async def test_get_emails_label_filter(client):
    r = await client.get(f"{LEAD}/emails", params={"label": "urgent", "days": 7})
    assert r.status_code == 200
    for e in r.json():
        assert e["label"] == "urgent"


async def test_get_emails_invalid_days(client):
    r = await client.get(f"{LEAD}/emails", params={"days": 99})
    assert r.status_code == 422
```

---

## Pattern: Testing Async Job Endpoints (POST → poll until done)

Use a helper so every polling test follows the same pattern:

```python
import asyncio

async def poll_until_done(client, url: str, interval: float = 2.0, timeout: float = 120.0) -> dict:
    """Poll GET url until status is 'done' or 'failed'. Raises on timeout."""
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
```

### Briefer job

```python
async def test_brief_job(client):
    # Start job
    r = await client.post(f"{LEAD}/brief", json={"days": 1})
    assert r.status_code == 202
    job_id = r.json()["job_id"]
    assert job_id

    # Poll until done
    result = await poll_until_done(client, f"{LEAD}/brief/{job_id}", timeout=120.0)
    assert result["status"] == "done"
    assert result["content"]
    assert result["summary"]["total"] >= 0
    assert "urgent" in result["summary"]


async def test_briefs_latest(client):
    r = await client.get(f"{LEAD}/briefs/latest")
    # 200 if a briefing exists, 404 if not — both are valid
    assert r.status_code in (200, 404)
    if r.status_code == 200:
        data = r.json()
        assert data["content"]
        assert data["summary"]
```

### Brief cache reuse (POST /brief within 1 hour returns existing job)

```python
async def test_brief_cache_reuse(client):
    # First call creates a job
    r1 = await client.post(f"{LEAD}/brief", json={"days": 1})
    assert r1.status_code == 202
    job_id_1 = r1.json()["job_id"]

    # Wait for it to finish
    await poll_until_done(client, f"{LEAD}/brief/{job_id_1}")

    # Second call within 1 hour should return the same job as done immediately
    r2 = await client.post(f"{LEAD}/brief", json={"days": 1})
    assert r2.status_code == 202
    data2 = r2.json()
    assert data2["status"] == "done"
    assert data2["job_id"] == job_id_1
```

### Draft job (full workflow through lead-agent)

Requires at least one classified email in the DB.

```python
async def test_draft_workflow(client):
    # Get an email to draft a reply for
    emails_r = await client.get(f"{LEAD}/emails", params={"days": 7})
    emails = emails_r.json()
    if not emails:
        pytest.skip("No emails in DB — run sync first")

    email_id = emails[0]["id"]

    # Start draft
    r = await client.post(f"{LEAD}/draft", json={"email_id": email_id, "instructions": "be brief"})
    assert r.status_code == 202
    job_id = r.json()["job_id"]

    # Poll
    result = await poll_until_done(client, f"{LEAD}/draft/{job_id}", timeout=120.0)
    assert result["status"] == "done"
    draft = result["draft"]
    assert draft["subject"]
    assert draft["body"]
    assert draft["language"]
    # draft_id is NOT set until Approve — do not assert it here


async def test_draft_pending_has_no_draft_field(client):
    emails_r = await client.get(f"{LEAD}/emails", params={"days": 7})
    emails = emails_r.json()
    if not emails:
        pytest.skip("No emails in DB")

    r = await client.post(f"{LEAD}/draft", json={"email_id": emails[0]["id"]})
    job_id = r.json()["job_id"]

    # Poll once immediately — should be pending or done, never crash
    poll_r = await client.get(f"{LEAD}/draft/{job_id}")
    assert poll_r.status_code == 200
    data = poll_r.json()
    assert data["status"] in ("pending", "done", "failed")
```

### Approve endpoint

```python
async def test_approve_saves_to_gmail(client):
    emails_r = await client.get(f"{LEAD}/emails", params={"days": 7})
    emails = emails_r.json()
    if not emails:
        pytest.skip("No emails in DB")

    r = await client.post(f"{LEAD}/draft", json={"email_id": emails[0]["id"]})
    job_id = r.json()["job_id"]
    result = await poll_until_done(client, f"{LEAD}/draft/{job_id}")
    assert result["status"] == "done"

    # Approve with edited subject
    approve_r = await client.post(
        f"{LEAD}/approve/{job_id}",
        json={"subject": "Re: test — edited", "body": result["draft"]["body"]},
    )
    assert approve_r.status_code == 200
    assert approve_r.json()["draft_id"]  # Gmail returned a draft ID


async def test_approve_rejects_pending_draft(client):
    emails_r = await client.get(f"{LEAD}/emails", params={"days": 7})
    emails = emails_r.json()
    if not emails:
        pytest.skip("No emails in DB")

    r = await client.post(f"{LEAD}/draft", json={"email_id": emails[0]["id"]})
    job_id = r.json()["job_id"]

    # Do NOT poll — approve immediately while still pending
    approve_r = await client.post(f"{LEAD}/approve/{job_id}", json={})
    # Must be 422 (not ready) or 200 if it finished instantly
    assert approve_r.status_code in (200, 422)
```

---

## Pattern: Testing Run (Sync) Endpoint

```python
async def test_run_workflow(client):
    r = await client.post(f"{LEAD}/run", json={"days": 1})
    assert r.status_code == 202
    job_id = r.json()["job_id"]
    assert r.json()["step"] == "sorting"

    result = await poll_until_done(client, f"{LEAD}/run/{job_id}", timeout=300.0)
    assert result["status"] == "done"
    assert result["step"] == "done"
    assert isinstance(result["emails_classified"], int)
    assert isinstance(result["emails_skipped"], int)


async def test_run_invalid_days(client):
    r = await client.post(f"{LEAD}/run", json={"days": 0})
    assert r.status_code == 422

    r = await client.post(f"{LEAD}/run", json={"days": 31})
    assert r.status_code == 422
```

---

## Pattern: Testing 404 and Error Cases

```python
async def test_draft_job_not_found(client):
    r = await client.get(f"{LEAD}/draft/nonexistent-job-id")
    assert r.status_code == 404


async def test_brief_job_not_found(client):
    r = await client.get(f"{LEAD}/brief/nonexistent-job-id")
    assert r.status_code == 404


async def test_approve_not_found(client):
    r = await client.post(f"{LEAD}/approve/nonexistent-job-id", json={})
    assert r.status_code == 404
```

---

## Pattern: Health Checks for All Services

```python
@pytest.mark.parametrize("url", [
    f"{LEAD}/health",
    f"{SORTER}/health",
    f"{DRAFTER}/health",
    f"{BRIEFER}/health",
    f"{MCP}/health",
])
async def test_service_health(client, url):
    r = await client.get(url)
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


async def test_lead_health_shows_dependencies(client):
    r = await client.get(f"{LEAD}/health")
    deps = r.json()["dependencies"]
    assert set(deps.keys()) == {"sorter", "researcher", "drafter", "critic", "briefer", "mcp-server"}
    # At minimum, core services must be reachable
    for svc in ("sorter", "drafter", "briefer", "mcp-server"):
        assert deps[svc] == "ok", f"{svc} is not healthy"
```

---

## What NOT to Test

| Area | Why |
|---|---|
| Gmail API calls directly | Requires real OAuth credentials and creates real drafts. Mock at the MCP boundary instead, or test `POST /drafts` on MCP only in a dedicated Gmail integration suite. |
| Redis internals | Test observable HTTP behavior (second request returns same data faster). Never assert Redis key existence or TTLs directly. |
| APScheduler cron jobs | Triggering time-based jobs in tests is flaky. Test `POST /brief` directly instead. |
| Anthropic API responses | Non-deterministic. Assert shape (`content` is a non-empty string, `label` is valid) not exact content. |
| Critic / Researcher when unavailable | These are optional. Lead-agent skips them on connection error. Tests should not fail if these services are down. |
| DB schema internals | Test via HTTP endpoints only. Never connect to Postgres directly in integration tests. |

---

## Directory Layout

```
tests/
├── conftest.py          ← fixtures, poll_until_done helper, base URLs
├── test_health.py       ← all /health endpoints
├── test_emails.py       ← GET /emails, filters, day ranges
├── test_run.py          ← POST /run workflow + polling
├── test_brief.py        ← POST /brief, GET /brief/{id}, /briefs/latest, cache reuse
├── test_draft.py        ← POST /draft, GET /draft/{id}, POST /approve/{id}
└── test_errors.py       ← 404s, 422 validation, edge cases
```

---

## Tips

- **Skipping tests when DB is empty**: use `pytest.skip("No emails — run sync first")` rather than failing. Tests that depend on prior state should be documented as needing a seeded DB.
- **Timeout tuning**: briefing generation can take 30-60s if Claude is slow. Set `timeout=120.0` in `poll_until_done` for brief tests.
- **Idempotency**: `POST /run` and `POST /brief` create new jobs each time. Running the full test suite multiple times will accumulate jobs in the DB — this is expected.
- **Parallel tests**: avoid `pytest-xdist` parallelism for polling tests — concurrent run jobs can interfere with each other.
