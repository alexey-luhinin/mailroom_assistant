from dotenv import load_dotenv

load_dotenv("config/.env")

import asyncio
import logging
import os
import traceback
import uuid
from datetime import datetime, timezone
from email.utils import parseaddr

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from models import FollowupRequest

logger = logging.getLogger(__name__)

MCP_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8006")
_T = 30.0

_jobs: dict[str, dict] = {}

app = FastAPI(title="Followup")


@app.get("/health")
def health():
    return {"status": "ok", "service": "followup"}


@app.post("/followup", status_code=202)
async def post_followup(request: FollowupRequest):
    if not 1 <= request.days <= 30:
        raise HTTPException(status_code=422, detail="Invalid days value. Must be between 1 and 30.")
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {"job_id": job_id, "status": "pending"}
    asyncio.create_task(_run_followup(job_id, request.days))
    return {"job_id": job_id, "status": "pending"}


@app.get("/followup/{job_id}")
async def get_followup(job_id: str):
    job = _jobs.get(job_id)
    if job is None:
        return JSONResponse(status_code=404, content={"error": "Job not found."})
    return job


async def _run_followup(job_id: str, days: int) -> None:
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{MCP_URL}/emails/sent", params={"days": days}, timeout=_T
            )
            resp.raise_for_status()
            sent_emails = resp.json()

        if not sent_emails:
            _jobs[job_id].update({"status": "done", "days": days, "waiting_count": 0, "emails": []})
            return

        # Deduplicate by thread_id: keep only the latest sent email per thread
        latest_by_thread: dict[str, dict] = {}
        for email in sent_emails:
            tid = email["thread_id"]
            if tid not in latest_by_thread or email["date"] > latest_by_thread[tid]["date"]:
                latest_by_thread[tid] = email

        unique_sent = list(latest_by_thread.values())

        thread_results = []
        async with httpx.AsyncClient() as client:
            for i, e in enumerate(unique_sent):
                if i > 0:
                    await asyncio.sleep(0.5)
                try:
                    thread_results.append(await _fetch_thread(client, e["thread_id"]))
                except Exception as exc:
                    thread_results.append(exc)

        now = datetime.now(timezone.utc)
        waiting: list[dict] = []

        for email, thread_msgs in zip(unique_sent, thread_results):
            if isinstance(thread_msgs, Exception):
                logger.warning("Failed to fetch thread %s: %s", email["thread_id"], thread_msgs)
                continue

            if not thread_msgs:
                continue

            user_email = _extract_addr(email["from"])

            # Skip threads started by someone else (we replied to their email, not our outreach)
            if _extract_addr(thread_msgs[0]["from"]) != user_email:
                continue

            our_date = email["date"]

            # Check if anyone else replied after our last sent message
            has_reply = any(
                _extract_addr(msg["from"]) != user_email and msg["date"] > our_date
                for msg in thread_msgs
            )

            if not has_reply:
                try:
                    sent_dt = datetime.fromisoformat(our_date)
                except ValueError:
                    continue
                days_waiting = max(0, (now - sent_dt).days)
                waiting.append({
                    "id": email["id"],
                    "thread_id": email["thread_id"],
                    "to": email["to"],
                    "subject": email["subject"],
                    "sent_at": our_date,
                    "days_waiting": days_waiting,
                })

        waiting.sort(key=lambda e: e["days_waiting"], reverse=True)
        _jobs[job_id].update({
            "status": "done",
            "days": days,
            "waiting_count": len(waiting),
            "emails": waiting,
        })

    except Exception as e:
        logger.error("Followup job %s failed: %s\n%s", job_id, e, traceback.format_exc())
        _jobs[job_id].update({"status": "failed", "error": str(e)})


async def _fetch_thread(client: httpx.AsyncClient, thread_id: str) -> list[dict]:
    resp = await client.get(f"{MCP_URL}/threads/{thread_id}", timeout=_T)
    resp.raise_for_status()
    return resp.json()


def _extract_addr(addr_str: str) -> str:
    _, addr = parseaddr(addr_str)
    return (addr or addr_str).lower()
