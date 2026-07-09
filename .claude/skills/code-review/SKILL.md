# Code Review Skill — Python FastAPI Microservices

## Context

This project has 5 FastAPI microservices: `lead-agent`, `sorter`, `drafter`, `briefer`, `mcp-server`.
Each follows the same internal layout: `main.py` + `agent.py` + `db.py` + `cache.py` + `models.py`.
Use this document when reviewing or refactoring any service.

---

## What to Look For

### Code Smells

**Duplication across services**
- Cache boilerplate (`_get_client`, `_get`, `_set`) is nearly identical in every service's `cache.py`. This is intentional (services are separate Docker containers — no shared lib). Flag duplication within a single service, not across services.
- `_to_dict()` / `_email_to_dict()` manual row mapping: check for copy-pasted serialization between `db.py` files.
- `Status = Literal["pending", "done", "failed"]` is redefined per service. Accept this — do not create a shared package.

**Untyped or loosely typed endpoints**
- `request: dict` in endpoint signatures. Every POST endpoint should accept a Pydantic model for validation. Example violation: `lead-agent/main.py` `post_brief(request: dict)`.

**Hardcoded values**
- Timeout floats inline in httpx calls (`timeout=30.0`). Extract to module-level constants at the top of `main.py`.
- Redis TTL hardcoded as `3600` in `cache.py`. Accept as-is unless the service needs per-key TTLs.

**Oversized files**
- If `main.py` exceeds ~200 lines and mixes endpoint handlers with background workflow functions, the workflows belong in a separate `workflows.py`. Current threshold in this project: `lead-agent/main.py` at 360+ lines is the known case.

### Error Handling Gaps

| Pattern | Location | Risk |
|---|---|---|
| Agent tool not called → silent `return []` or fallback string | `sorter/agent.py`, `briefer/agent.py` | Data loss: emails silently unclassified |
| `raise_for_status()` on upstream 4xx in proxy endpoints | Any `main.py` that proxies to another service | 500 instead of 404 |
| `RuntimeError` from missing auth token not caught by caller | `mcp-server/gmail.py` | 500 on every request until token is present |
| Lifespan without `try/finally` around `ensure_table()` | All services | Pool leak if startup fails |

**Correct proxy error forwarding pattern** (already applied in `lead-agent/main.py`):
```python
if 400 <= resp.status_code < 500:
    raise HTTPException(status_code=resp.status_code,
                        detail=resp.json().get("detail", resp.text))
resp.raise_for_status()   # surface unexpected 5xx
return resp.json()
```

**Correct background task error boundary** (already applied everywhere):
```python
async def _run_X(job_id: str, ...) -> None:
    try:
        ...
    except Exception as e:
        logger.error("Job %s failed: %s", job_id, e)
        await db.update_job(_pool, job_id, "failed", error=str(e))
```
Never let a background task raise unhandled — it would silently terminate with no job status update.

### Async/Sync Issues

- `mcp-server/main.py` uses `def` (sync) endpoints backed by blocking Google API calls. This blocks the event loop under concurrent load. Safe to flag; fix by wrapping in `asyncio.to_thread()` and making the endpoint `async def`.
- `drafter/main.py` `_load_style_profile()` does a synchronous file read inside an async task. Low risk (fast local read), but flag in high-load contexts.

### SQL Safety

- All queries must use positional parameters (`$1`, `$2`). Never interpolate user input into SQL strings.
- Dynamic UPDATE builders (like `lead-agent/db.py`) are acceptable **only when column names are hardcoded** in the builder, never derived from user input.

---

## Patterns to Enforce

These are already in use across services — preserve them.

**Lazy Redis singleton**
```python
_client: redis.Redis | None = None

def _get_client() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.from_url(REDIS_URL, decode_responses=True)
    return _client
```
Never instantiate at module level — breaks tests that start without Redis.

**Silent cache failure**
```python
def _get(key: str) -> dict | list | None:
    try:
        data = _get_client().get(key)
        return json.loads(data) if data else None
    except Exception as e:
        logger.warning("Redis get failed: %s", e)
        return None
```
Cache errors must never crash an endpoint. Return `None` and let the caller fall back to DB.

**Optional service skip**
```python
try:
    resp = await client.post(f"{RESEARCHER_URL}/research", ...)
    resp.raise_for_status()
    context = resp.json()
except (httpx.ConnectError, httpx.ConnectTimeout):
    logger.warning("Researcher unavailable, skipping")
```
Catch only connection errors for optional services. Do not catch `Exception` — that hides real bugs.

**Lifespan pool management**
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    global _pool
    _pool = await asyncpg.create_pool(os.getenv("POSTGRES_URL"))
    try:
        await db.ensure_table(_pool)
        yield
    finally:
        await _pool.close()
```
`try/finally` ensures the pool is released even if `ensure_table` raises.

**Module logger**
```python
logger = logging.getLogger(__name__)
```
One per file. Never use the root logger directly.

---

## What NOT to Change

| Area | Reason |
|---|---|
| Database schema (no `ALTER TABLE`) | Live data depends on column names and types |
| Redis key namespaces (`briefer:brief:{id}`, etc.) | Changing silently invalidates cached data in production |
| `sorter/models.py` and `mcp-server/models.py` Pydantic alias pattern (`Field(alias="from")`) | Other services parse the `"from"` key in JSON responses |
| `briefer/main.py` APScheduler setup | Scheduled brief generation depends on this |
| `lead-agent/main.py` `_get_or_create_brief` + `post_brief` cache-reuse logic | Covered by `tests/test_brief.py::test_brief_cache_reuse` |
| `mcp-server/auth.py` | Manual one-time OAuth flow, not part of service runtime |
| Any endpoint that all integration tests currently pass against | Run `pytest tests/ -v` before and after to confirm no regression |

---

## Refactoring Order (Safest First)

**1. Cosmetic / zero-risk** — change one file, run tests, commit.
- Add `try/finally` to lifespan managers that are missing it.
- Replace `request: dict` with a proper Pydantic model in any endpoint that accepts one.
- Extract hardcoded timeout floats to module-level constants.

**2. Error handling** — change agent behavior, test manually.
- Fix `sorter/agent.py`: when `classify_emails` tool not called, raise `RuntimeError` instead of returning `[]`.
- Fix `briefer/agent.py`: same — raise instead of returning fallback content.
- These change job failure semantics: a "failed" job is now explicit rather than silently empty.

**3. Structural refactors** — change file layout, no logic change.
- Extract `_run_morning`, `_run_draft`, `_get_or_create_brief`, `_poll_brief`, `_poll_drafter` from `lead-agent/main.py` into `lead-agent/workflows.py`. Import them in `main.py`. No behavior change.

**4. Async fixes** — higher risk, requires manual testing of MCP server.
- Make `mcp-server/main.py` endpoints `async def` and wrap `gmail.*` calls in `asyncio.to_thread()`.
- Verify with `curl http://localhost:8006/emails?days=1`.

**Do not do:**
- Do not create a shared library package across services (coupling Docker build contexts).
- Do not refactor cache.py boilerplate away — duplication is the correct trade-off here.
- Do not change working DB query logic unless there is a proven bug.

---

## Verification

**After every change:**
```bash
pytest tests/ -v
```

**Key tests that catch regressions:**

| Test | What it protects |
|---|---|
| `test_brief_cache_reuse` | `_get_or_create_brief` and `post_brief` caching logic |
| `test_brief_job_not_found`, `test_errors.py::test_brief_job_not_found` | 4xx forwarding in proxy endpoints |
| `test_run_workflow_completes` | Full `_run_morning` background workflow |
| `test_draft_workflow_completes` | Full `_run_draft` + drafter + critic path |
| `test_approve_saves_to_gmail` | Approve endpoint + MCP POST /drafts |
| `test_service_health` (parametrized) | All five service `/health` endpoints |

**For mcp-server changes only** (no integration test covers it fully):
```bash
curl http://localhost:8006/health
curl "http://localhost:8006/emails?days=1"
```

**Before marking a refactor done:** confirm the test count did not decrease (no tests were accidentally deleted or skipped).
