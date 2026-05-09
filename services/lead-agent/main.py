import asyncio
import logging
import os
import uuid
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv("config/.env")

import asyncpg
import httpx
from fastapi import FastAPI, HTTPException

import cache
import db
from models import (
    DraftJobResponse,
    DraftRequest,
    RunJobResponse,
    RunRequest,
)

logger = logging.getLogger(__name__)

SORTER_URL     = os.getenv("SORTER_URL",     "http://localhost:8001")
RESEARCHER_URL = os.getenv("RESEARCHER_URL", "http://localhost:8002")
DRAFTER_URL    = os.getenv("DRAFTER_URL",    "http://localhost:8003")
CRITIC_URL     = os.getenv("CRITIC_URL",     "http://localhost:8004")
BRIEFER_URL    = os.getenv("BRIEFER_URL",    "http://localhost:8005")
MCP_URL        = os.getenv("MCP_SERVER_URL", "http://localhost:8006")

_DEPS = {
    "sorter":     SORTER_URL,
    "researcher": RESEARCHER_URL,
    "drafter":    DRAFTER_URL,
    "critic":     CRITIC_URL,
    "briefer":    BRIEFER_URL,
    "mcp-server": MCP_URL,
}

_pool: asyncpg.Pool | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _pool
    _pool = await asyncpg.create_pool(os.getenv("POSTGRES_URL"))
    await db.ensure_tables(_pool)
    yield
    await _pool.close()


app = FastAPI(title="Lead Agent", lifespan=lifespan)


@app.get("/health")
async def health():
    async def _check(client: httpx.AsyncClient, url: str) -> str:
        try:
            r = await client.get(f"{url}/health", timeout=5.0)
            return "ok" if r.status_code == 200 else "error"
        except Exception:
            return "error"

    async with httpx.AsyncClient() as client:
        results = await asyncio.gather(*[_check(client, url) for url in _DEPS.values()])

    return {
        "status": "ok",
        "service": "lead-agent",
        "dependencies": dict(zip(_DEPS.keys(), results)),
    }


@app.post("/run", response_model=RunJobResponse, response_model_exclude_none=True, status_code=202)
async def post_run(request: RunRequest):
    if not 1 <= request.days <= 30:
        raise HTTPException(status_code=422, detail="Invalid days value. Must be between 1 and 30.")

    job_id = str(uuid.uuid4())
    await db.create_run_job(_pool, job_id, request.days)
    asyncio.create_task(_run_morning(job_id, request.days))
    return RunJobResponse(job_id=job_id, status="pending", step="sorting")


@app.get("/run/{job_id}", response_model=RunJobResponse, response_model_exclude_none=True)
async def get_run(job_id: str):
    job = await db.get_run_job(_pool, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job


@app.post("/draft", response_model=DraftJobResponse, response_model_exclude_none=True, status_code=202)
async def post_draft(request: DraftRequest):
    job_id = str(uuid.uuid4())
    await db.create_draft_job(_pool, job_id, request.email_id, request.instructions)
    asyncio.create_task(_run_draft(job_id, request.email_id, request.instructions))
    return DraftJobResponse(job_id=job_id, status="pending", step="researching")


@app.get("/draft/{job_id}", response_model=DraftJobResponse, response_model_exclude_none=True)
async def get_draft(job_id: str):
    job = await db.get_draft_job(_pool, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job


@app.get("/emails")
async def get_emails(label: str | None = None, days: int = 7):
    if not 1 <= days <= 30:
        raise HTTPException(status_code=422, detail="Invalid days value. Must be between 1 and 30.")

    cached = cache.get_emails(days, label)
    if cached is not None:
        return cached

    params: dict = {"days": days}
    if label:
        params["label"] = label

    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{SORTER_URL}/emails", params=params, timeout=30.0)
        resp.raise_for_status()

    emails = resp.json()
    cache.set_emails(days, label, emails)
    return emails


# ── Background workflows ───────────────────────────────────────────────────────

async def _run_morning(job_id: str, days: int) -> None:
    try:
        # Step 1: sort
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{SORTER_URL}/sort", json={"days": days}, timeout=120.0
            )
            resp.raise_for_status()
        sort = resp.json()

        await db.update_run_job(
            _pool, job_id,
            step="briefing",
            emails_classified=sort["new"],
            emails_skipped=sort["skipped"],
        )

        # Step 2: brief
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{BRIEFER_URL}/brief", json={"days": days}, timeout=30.0
            )
            resp.raise_for_status()
        brief_job_id = resp.json()["job_id"]

        briefing = await _poll_brief(brief_job_id)
        if briefing["status"] == "failed":
            raise RuntimeError(briefing.get("error", "Briefing failed."))

        await db.update_run_job(
            _pool, job_id,
            status="done",
            step="done",
            briefing={"summary": briefing["summary"], "content": briefing["content"]},
        )

    except Exception as e:
        logger.error("Run job %s failed: %s", job_id, e)
        await db.update_run_job(_pool, job_id, status="failed", step="failed", error=str(e))


async def _poll_brief(brief_job_id: str, timeout: int = 300) -> dict:
    async with httpx.AsyncClient() as client:
        for _ in range(timeout // 2):
            resp = await client.get(
                f"{BRIEFER_URL}/brief/{brief_job_id}", timeout=10.0
            )
            resp.raise_for_status()
            data = resp.json()
            if data["status"] in ("done", "failed"):
                return data
            await asyncio.sleep(2)
    raise TimeoutError(f"Brief job {brief_job_id} timed out after {timeout}s.")


async def _run_draft(job_id: str, email_id: str, instructions: str) -> None:
    try:
        # Step 1: research
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{RESEARCHER_URL}/research",
                json={"email_id": email_id},
                timeout=60.0,
            )
            resp.raise_for_status()
        context = resp.json()

        await db.update_draft_job(_pool, job_id, step="drafting")

        # Step 2: draft
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{DRAFTER_URL}/draft",
                json={"email_id": email_id, "instructions": instructions, "context": context},
                timeout=60.0,
            )
            resp.raise_for_status()
        draft = resp.json()

        await db.update_draft_job(_pool, job_id, step="reviewing")

        # Step 3: review
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{CRITIC_URL}/review",
                json={"draft": draft, "instructions": instructions},
                timeout=60.0,
            )
            resp.raise_for_status()
        reviewed = resp.json()

        final_draft = reviewed.get("draft", draft)
        await db.update_draft_job(
            _pool, job_id, status="done", step="done", draft=final_draft
        )

    except Exception as e:
        logger.error("Draft job %s failed: %s", job_id, e)
        await db.update_draft_job(_pool, job_id, status="failed", step="failed", error=str(e))
