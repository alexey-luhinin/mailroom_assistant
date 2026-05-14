import asyncio
import logging
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv("config/.env")

logging.basicConfig(level=logging.INFO)

import asyncpg
import httpx
from fastapi import FastAPI, HTTPException

import cache
import db
from models import (
    ApproveRequest,
    BriefRequest,
    DraftJobResponse,
    DraftRequest,
    RunJobResponse,
    RunRequest,
)
from workflows import (
    BRIEFER_URL,
    MCP_URL,
    RESEARCHER_URL,
    SORTER_URL,
    DRAFTER_URL,
    CRITIC_URL,
    get_or_create_brief,
    run_draft,
    run_morning,
)

logger = logging.getLogger(__name__)

_T_HEALTH = 5.0
_T_SHORT  = 10.0
_T_MEDIUM = 30.0

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
    try:
        await db.ensure_tables(_pool)
        yield
    finally:
        await _pool.close()


app = FastAPI(title="Lead Agent", lifespan=lifespan)


@app.get("/health")
async def health():
    async def _check(client: httpx.AsyncClient, url: str) -> str:
        try:
            r = await client.get(f"{url}/health", timeout=_T_HEALTH)
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
    asyncio.create_task(run_morning(_pool, job_id, request.days))
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
    asyncio.create_task(run_draft(_pool, job_id, request.email_id, request.instructions))
    return DraftJobResponse(job_id=job_id, status="pending", step="researching")


@app.get("/draft/{job_id}", response_model=DraftJobResponse, response_model_exclude_none=True)
async def get_draft(job_id: str):
    job = await db.get_draft_job(_pool, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job


@app.post("/approve/{job_id}")
async def approve_draft(job_id: str, request: ApproveRequest):
    job = await db.get_draft_job(_pool, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Draft job not found.")
    if job["status"] != "done":
        raise HTTPException(status_code=422, detail="Draft is not ready.")

    draft = job.get("draft") or {}
    subject = request.subject if request.subject is not None else draft.get("subject", "")
    body    = request.body    if request.body    is not None else draft.get("body", "")

    async with httpx.AsyncClient() as client:
        email_resp = await client.get(f"{MCP_URL}/emails/{job['email_id']}", timeout=_T_SHORT)
        email_resp.raise_for_status()
        email = email_resp.json()

        draft_resp = await client.post(
            f"{MCP_URL}/drafts",
            json={
                "to":        email.get("from", ""),
                "subject":   subject,
                "body":      body,
                "thread_id": email.get("thread_id"),
            },
            timeout=_T_MEDIUM,
        )
        draft_resp.raise_for_status()

    return {"draft_id": draft_resp.json()["draft_id"]}


@app.post("/brief", status_code=202)
async def post_brief(request: BriefRequest):
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{BRIEFER_URL}/briefs/latest", timeout=_T_SHORT)
            if resp.status_code == 200:
                latest = resp.json()
                created_at = latest.get("created_at")
                if created_at:
                    age = datetime.now(timezone.utc) - datetime.fromisoformat(created_at)
                    logger.info("post_brief: latest brief created_at=%s age=%.0fs", created_at, age.total_seconds())
                    if age.total_seconds() < 3600:
                        logger.info("post_brief: reusing brief job_id=%s", latest["job_id"])
                        return {"job_id": latest["job_id"], "status": "done"}
        except Exception as e:
            logger.warning("post_brief: could not check latest brief: %s", e)

        resp = await client.post(f"{BRIEFER_URL}/brief", json=request.model_dump(), timeout=_T_MEDIUM)
        resp.raise_for_status()
    return resp.json()


@app.get("/brief/{job_id}")
async def get_brief(job_id: str):
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BRIEFER_URL}/brief/{job_id}", timeout=_T_SHORT)
    if 400 <= resp.status_code < 500:
        raise HTTPException(status_code=resp.status_code,
                            detail=resp.json().get("detail", resp.text))
    resp.raise_for_status()
    return resp.json()


@app.get("/briefs/latest")
async def get_latest_brief():
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BRIEFER_URL}/briefs/latest", timeout=_T_SHORT)
    if 400 <= resp.status_code < 500:
        raise HTTPException(status_code=resp.status_code,
                            detail=resp.json().get("detail", resp.text))
    resp.raise_for_status()
    return resp.json()


@app.get("/calendar/events/today")
async def get_calendar_events_today():
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{MCP_URL}/calendar/events/today", timeout=_T_SHORT)
    if 400 <= resp.status_code < 500:
        raise HTTPException(status_code=resp.status_code,
                            detail=resp.json().get("detail", resp.text))
    resp.raise_for_status()
    return resp.json()


@app.get("/calendar/events")
async def get_calendar_events(days_ahead: int = 5):
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{MCP_URL}/calendar/events",
                                params={"days_ahead": days_ahead}, timeout=_T_SHORT)
    if 400 <= resp.status_code < 500:
        raise HTTPException(status_code=resp.status_code,
                            detail=resp.json().get("detail", resp.text))
    resp.raise_for_status()
    return resp.json()


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
        resp = await client.get(f"{SORTER_URL}/emails", params=params, timeout=_T_MEDIUM)
        resp.raise_for_status()

    emails = resp.json()
    cache.set_emails(days, label, emails)
    return emails
