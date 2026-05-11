from dotenv import load_dotenv

load_dotenv("config/.env")

import asyncio
import logging
import os
import uuid
from contextlib import asynccontextmanager

import asyncpg
import httpx
from fastapi import FastAPI, HTTPException

import agent
import cache
import db
from models import DraftJobResponse, DraftListItem, DraftRequest, DraftResponse

logger = logging.getLogger(__name__)

MCP_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8006")

_T_SHORT = 30.0

_pool: asyncpg.Pool | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _pool
    _pool = await asyncpg.create_pool(os.getenv("POSTGRES_URL"))
    try:
        await db.ensure_table(_pool)
        yield
    finally:
        await _pool.close()


app = FastAPI(title="Drafter", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok", "service": "drafter"}


@app.post("/draft", response_model=DraftJobResponse, status_code=202)
async def post_draft(request: DraftRequest):
    job_id = str(uuid.uuid4())
    await db.create_job(_pool, job_id, request.email_id)
    asyncio.create_task(_run_draft(job_id, request.email_id, request.instructions))
    return DraftJobResponse(job_id=job_id, status="pending")


@app.get("/draft/{job_id}", response_model=DraftResponse)
async def get_draft_job(job_id: str):
    cached = cache.get_job(job_id)
    if cached and cached["status"] == "done":
        return cached

    job = await db.get_job(_pool, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")

    if job["status"] == "done":
        cache.set_job(job_id, job)
    return job


@app.get("/drafts", response_model=list[DraftListItem])
async def list_drafts(email_id: str | None = None):
    cached = cache.get_drafts(email_id)
    if cached is not None:
        return cached

    drafts = await db.get_drafts(_pool, email_id)
    cache.set_drafts(email_id, drafts)
    return drafts


async def _run_draft(job_id: str, email_id: str, instructions: str) -> None:
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{MCP_URL}/emails/{email_id}", timeout=_T_SHORT)
            resp.raise_for_status()
        email = resp.json()

        style_profile = _load_style_profile()
        result = await agent.generate(email, instructions, style_profile)

        await db.update_job(
            _pool,
            job_id,
            "done",
            subject=result["subject"],
            body=result["body"],
            language=result["language"],
        )
    except Exception as e:
        logger.error("Draft job %s failed: %s", job_id, e)
        await db.update_job(_pool, job_id, "failed", error=str(e))


def _load_style_profile() -> str:
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config", "style_profile.md")
    try:
        with open(path) as f:
            return f.read()
    except FileNotFoundError:
        return ""
