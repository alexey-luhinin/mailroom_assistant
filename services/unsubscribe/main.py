from dotenv import load_dotenv

load_dotenv("config/.env")

import asyncio
import logging
import os
import re
import uuid
from collections import defaultdict
from contextlib import asynccontextmanager
from email.utils import parseaddr

import asyncpg
import httpx
from fastapi import FastAPI, HTTPException

import db
from models import AnalyzeJobResponse, AnalyzeRequest, AnalyzeResponse, Candidate

logger = logging.getLogger(__name__)

MCP_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8006")

_T_FETCH  = 30.0
_T_LIST   = 60.0

_UNSUB_HEADER_RE = re.compile(r"<(https?://[^>]+)>")
_UNSUB_BODY_RE   = re.compile(r"https?://[^\s<>\"']*unsubscribe[^\s<>\"']*", re.IGNORECASE)

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


app = FastAPI(title="Unsubscribe", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok", "service": "unsubscribe"}


@app.post("/analyze", response_model=AnalyzeJobResponse, status_code=202)
async def post_analyze(request: AnalyzeRequest):
    job_id = str(uuid.uuid4())
    await db.create_job(_pool, job_id, request.days)
    asyncio.create_task(_run_analyze(_pool, job_id, request.days))
    return AnalyzeJobResponse(job_id=job_id, status="pending")


# /analyze/latest must be declared before /analyze/{job_id}
@app.get("/analyze/latest", response_model=AnalyzeResponse, response_model_exclude_none=True)
async def get_latest_analyze():
    job = await db.get_latest_job(_pool)
    if job is None:
        raise HTTPException(status_code=404, detail="No analysis found.")
    return job


@app.get("/analyze/{job_id}", response_model=AnalyzeResponse, response_model_exclude_none=True)
async def get_analyze(job_id: str):
    job = await db.get_job(_pool, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job


# ── Analysis background task ──────────────────────────────────────────────────

async def _run_analyze(pool: asyncpg.Pool, job_id: str, days: int) -> None:
    try:
        db_emails = await db.get_newsletter_promo_emails(pool, days)

        if not db_emails:
            await db.update_job(pool, job_id, status="done",
                                result={"total_senders": 0, "candidates": []})
            return

        # Fetch full email data from MCP in parallel (is_read, body, list_unsubscribe)
        async with httpx.AsyncClient() as client:
            fetched = await asyncio.gather(
                *[_fetch_email(client, e["id"]) for e in db_emails],
                return_exceptions=True,
            )

        mcp_by_id: dict[str, dict] = {}
        for email, result in zip(db_emails, fetched):
            if isinstance(result, dict):
                mcp_by_id[email["id"]] = result
            else:
                logger.warning("Failed to fetch email %s from MCP: %s", email["id"], result)

        # Group by sender address, accumulate read counts
        groups: dict[str, list[dict]] = defaultdict(list)
        for e in db_emails:
            name, addr = parseaddr(e["from"])
            addr = addr.lower() or e["from"].lower()
            mcp = mcp_by_id.get(e["id"], {})
            groups[addr].append({
                "id":               e["id"],
                "name":             name or addr,
                "date":             e.get("date", ""),
                "is_read":          mcp.get("is_read", False),
                "body":             mcp.get("body", ""),
                "list_unsubscribe": mcp.get("list_unsubscribe"),
            })

        candidates: list[dict] = []
        for sender, group in groups.items():
            total  = len(group)
            opened = sum(1 for e in group if e["is_read"])
            open_rate = opened / total

            if open_rate >= 0.20:
                continue

            recommendation = "unsubscribe" if open_rate == 0.0 else "consider"

            # Use the latest email for unsubscribe link extraction
            latest = max(group, key=lambda e: e["date"])
            unsubscribe_url = _extract_unsubscribe_url(
                latest["list_unsubscribe"], latest["body"]
            )

            candidates.append({
                "sender":          sender,
                "name":            latest["name"],
                "total":           total,
                "opened":          opened,
                "open_rate":       round(open_rate, 3),
                "recommendation":  recommendation,
                "unsubscribe_url": unsubscribe_url,
            })

        # Sort: "unsubscribe" before "consider", then most emails first
        candidates.sort(key=lambda c: (c["recommendation"] != "unsubscribe", -c["total"]))

        await db.update_job(pool, job_id, status="done", result={
            "total_senders": len(groups),
            "candidates":    candidates,
        })

    except Exception as e:
        logger.error("Analyze job %s failed: %s", job_id, e)
        await db.update_job(pool, job_id, status="failed", error=str(e))


async def _fetch_email(client: httpx.AsyncClient, email_id: str) -> dict:
    resp = await client.get(f"{MCP_URL}/emails/{email_id}", timeout=_T_FETCH)
    resp.raise_for_status()
    return resp.json()


def _extract_unsubscribe_url(list_unsubscribe: str | None, body: str) -> str | None:
    if list_unsubscribe:
        m = _UNSUB_HEADER_RE.search(list_unsubscribe)
        if m:
            return m.group(1)
    if body:
        m = _UNSUB_BODY_RE.search(body)
        if m:
            return m.group(0)
    return None
