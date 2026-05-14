import asyncio
import logging
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv("config/.env")

import asyncpg
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI, HTTPException

import agent
import cache
import db
from models import BriefJobResponse, BriefListItem, BriefRequest, BriefResponse

logger = logging.getLogger(__name__)

_pool: asyncpg.Pool | None = None
_scheduler: AsyncIOScheduler | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _pool, _scheduler
    _pool = await asyncpg.create_pool(os.getenv("POSTGRES_URL"))
    try:
        await db.ensure_table(_pool)

        _scheduler = AsyncIOScheduler()
        _scheduler.add_job(
            _run_scheduled_brief,
            CronTrigger.from_crontab(os.getenv("BRIEF_SCHEDULE", "0 8 * * *")),
        )
        _scheduler.start()

        yield
    finally:
        if _scheduler:
            _scheduler.shutdown(wait=False)
        await _pool.close()


app = FastAPI(title="Briefer", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok", "service": "briefer"}


@app.post("/brief", response_model=BriefJobResponse, status_code=202)
async def post_brief(request: BriefRequest):
    if not 1 <= request.days <= 30:
        raise HTTPException(status_code=422, detail="Invalid days value. Must be between 1 and 30.")

    job_id = str(uuid.uuid4())
    await db.create_job(_pool, job_id)
    asyncio.create_task(_run_brief(job_id, request.days, request.calendar_events, request.feedback))
    return BriefJobResponse(job_id=job_id, status="pending")


@app.get("/brief/{job_id}", response_model=BriefResponse)
async def get_brief(job_id: str):
    cached = cache.get_job(job_id)
    if cached and cached["status"] == "done":
        return cached

    job = await db.get_job(_pool, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")

    if job["status"] == "done":
        cache.set_job(job_id, job)
    return job


@app.get("/briefs/latest", response_model=BriefResponse)
async def get_latest():
    cached = cache.get_latest()
    if cached:
        return cached

    brief = await db.get_latest(_pool)
    if brief is None:
        raise HTTPException(status_code=404, detail="No briefings found.")

    cache.set_latest(brief)
    return brief


@app.get("/briefs", response_model=list[BriefListItem])
async def list_briefs(limit: int = 7):
    if not 1 <= limit <= 100:
        raise HTTPException(status_code=422, detail="Invalid limit. Must be between 1 and 100.")

    cached = cache.get_briefs(limit)
    if cached is not None:
        return cached

    briefs = await db.get_briefs(_pool, limit)
    cache.set_briefs(limit, briefs)
    return briefs


async def _run_brief(job_id: str, days: int, calendar_events: list[dict] | None = None, feedback: str = "") -> None:
    try:
        today_emails = await db.get_today_emails(_pool, days)
        previous_emails = await db.get_unresolved_emails(_pool, days)
        summary = _compute_summary(today_emails)
        now = datetime.now(timezone.utc)
        date_str = now.strftime(f"%B {now.day}, %Y")
        content = await agent.generate(date_str, today_emails, previous_emails, summary, calendar_events or [], feedback)
        cache.invalidate_latest()
        await db.update_job(_pool, job_id, "done", content=content, summary=summary)
    except Exception as e:
        logger.error("Brief job %s failed: %s", job_id, e)
        await db.update_job(_pool, job_id, "failed", error=str(e))


async def _run_scheduled_brief() -> None:
    job_id = str(uuid.uuid4())
    await db.create_job(_pool, job_id)
    await _run_brief(job_id, days=1)


def _compute_summary(emails: list[dict]) -> dict:
    counts: dict[str, int] = {
        k: 0 for k in ("urgent", "action_needed", "fyi", "calendar", "newsletter", "promo", "spam")
    }
    for e in emails:
        label = e.get("label", "")
        if label in counts:
            counts[label] += 1
    return {"total": len(emails), **counts}
