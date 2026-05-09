# FastAPI Service Patterns

Conventions derived from `services/mcp-server` and `services/sorter`.
Follow these exactly when adding a new service.

---

## File structure

```
services/<name>/
├── Dockerfile
├── requirements.txt
├── main.py      ← FastAPI app, routes, lifespan
├── agent.py     ← Claude API logic (omit if no AI)
├── db.py        ← asyncpg queries (omit if stateless)
├── cache.py     ← Redis logic
└── models.py    ← Pydantic models
```

---

## main.py

### Env loading

`load_dotenv` must be the **first** executable line, before any other imports,
because modules read env vars at import time.

```python
from dotenv import load_dotenv
load_dotenv("config/.env")

from fastapi import FastAPI, HTTPException
import cache, db, agent
from models import ...
```

### Health endpoint

Every service exposes `GET /health`. No auth, no logic.

```python
@app.get("/health")
def health():
    return {"status": "ok", "service": "<name>"}
```

### Lifespan (services with PostgreSQL)

Use `asynccontextmanager` lifespan to manage the connection pool.
Pass the pool explicitly to every db function — never store it in `db.py`.

```python
from contextlib import asynccontextmanager
import asyncpg

_pool: asyncpg.Pool | None = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _pool
    _pool = await asyncpg.create_pool(os.getenv("POSTGRES_URL"))
    await db.ensure_table(_pool)
    yield
    await _pool.close()

app = FastAPI(title="<Name>", lifespan=lifespan)
```

Stateless services (no DB) omit lifespan entirely:

```python
app = FastAPI(title="<Name>", description="...")
```

### Error handling

| Situation | Code |
|---|---|
| Invalid input range | `422` |
| Resource not found | `404` |
| Upstream HTTP error | let `resp.raise_for_status()` propagate |
| Redis failure | log warning, return `None` (cache is optional) |
| DB failure | let exception propagate (DB is critical) |

```python
if not 1 <= request.days <= 30:
    raise HTTPException(status_code=422, detail="Invalid days value. Must be between 1 and 30.")
```

### Inter-service calls

Read the upstream URL from env with a localhost default.
Use `httpx.AsyncClient` as a context manager, always set a timeout.

```python
MCP_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8006")

async with httpx.AsyncClient() as client:
    resp = await client.get(f"{MCP_URL}/emails", params={"days": days}, timeout=30.0)
    resp.raise_for_status()
```

---

## models.py

- Use `Literal` for fixed-value string enums, not Python `Enum`.
- Add `model_config = ConfigDict(populate_by_name=True)` on any model with aliases.
- Use `Field(alias="from")` for fields that clash with Python keywords.
- Add `response_model_by_alias=True` on every route that returns an aliased model.

```python
from pydantic import BaseModel, Field, ConfigDict
from typing import Literal

Label = Literal["urgent", "action_needed", "fyi"]

class MyModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    from_: str = Field(alias="from")
    label: Label
```

```python
@app.get("/emails", response_model=list[MyModel], response_model_by_alias=True)
```

---

## cache.py

- Lazy singleton client via a private `_get_client()`.
- `TTL = 3600` (1 h) as a module-level constant.
- Private `_get`/`_set` helpers that catch all exceptions and log a warning.
- Public `get_*`/`set_*` per entity — never expose the client directly.
- Key format: `<service>:<entity>:<param>:<value>` (e.g. `sorter:emails:days:7:label:urgent`).

```python
import json, logging, os, redis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
TTL = 3600
logger = logging.getLogger(__name__)
_client: redis.Redis | None = None

def _get_client() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.from_url(REDIS_URL, decode_responses=True)
    return _client

def _get(key: str) -> dict | list | None:
    try:
        data = _get_client().get(key)
        return json.loads(data) if data else None
    except Exception as e:
        logger.warning("Redis get failed: %s", e)
        return None

def _set(key: str, value: dict | list) -> None:
    try:
        _get_client().setex(key, TTL, json.dumps(value))
    except Exception as e:
        logger.warning("Redis set failed: %s", e)
```

---

## db.py

- `ensure_table(pool)` runs `CREATE TABLE IF NOT EXISTS` — called in lifespan.
- Pool is always passed as a parameter, never imported as a global.
- Use `ON CONFLICT (id) DO NOTHING` for idempotent inserts.
- `_to_dict(row)` converts `asyncpg.Record` to a plain `dict` (map `from_addr` → `"from"` here).
- All functions are `async`.

```python
async def ensure_table(pool: asyncpg.Pool) -> None:
    async with pool.acquire() as conn:
        await conn.execute(_CREATE)

async def save_emails(pool: asyncpg.Pool, emails: list[dict]) -> None:
    async with pool.acquire() as conn:
        await conn.executemany(
            "INSERT INTO emails (...) VALUES (...) ON CONFLICT (id) DO NOTHING",
            [(e["id"], ...) for e in emails],
        )

def _to_dict(row: asyncpg.Record) -> dict:
    return {"id": row["id"], "from": row["from_addr"], ...}
```

---

## agent.py

- Module-level `_client = anthropic.AsyncAnthropic()` — one instance per process.
- System prompt in a module-level string `_SYSTEM`.
- Tool schema in a module-level dict `_TOOL`.
- Use `tool_choice={"type": "any"}` to force tool use.
- Batch large lists (chunk size 50) and run batches with `asyncio.gather`.
- If the model doesn't call the expected tool, log a warning and return `[]` — never raise.

```python
import asyncio, logging, anthropic

logger = logging.getLogger(__name__)
_client = anthropic.AsyncAnthropic()

_SYSTEM = "..."
_TOOL = {"name": "...", "description": "...", "input_schema": {...}}

async def run(items: list[dict]) -> list[dict]:
    results = []
    tasks = [_process_batch(chunk) for chunk in _chunks(items, 50)]
    for batch in await asyncio.gather(*tasks):
        results.extend(batch)
    return results

async def _process_batch(items: list[dict]) -> list[dict]:
    response = await _client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        system=_SYSTEM,
        tools=[_TOOL],
        tool_choice={"type": "any"},
        messages=[{"role": "user", "content": "..."}],
    )
    for block in response.content:
        if block.type == "tool_use" and block.name == _TOOL["name"]:
            return [...]
    logger.warning("%s tool not called; %d item(s) lost", _TOOL["name"], len(items))
    return []

def _chunks(lst: list, n: int):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]
```

---

## Dockerfile

All services share the same Dockerfile shape. Only the port differs.

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE <port>

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "<port>"]
```

The `config/` directory is bind-mounted at runtime (`/app/config/`).
Never `COPY config/` into the image — it contains secrets.

Config file paths inside a service must resolve relative to `__file__`:

```python
_ROOT = os.path.dirname(os.path.abspath(__file__))
TOKEN_FILE = os.path.join(_ROOT, "config", "token.json")
```

---

## requirements.txt

Core packages every service needs:

```
fastapi>=0.115.0
uvicorn[standard]>=0.31.1
pydantic>=2.11.0,<3.0.0
python-dotenv>=1.0.1
redis>=5.0.0
```

Add per-service:

| Need | Package |
|---|---|
| PostgreSQL | `asyncpg>=0.29.0` |
| HTTP client | `httpx>=0.27.0` |
| Claude API | `anthropic>=0.40.0` |
| Gmail | `google-auth`, `google-auth-oauthlib`, `google-auth-httplib2`, `google-api-python-client` |
