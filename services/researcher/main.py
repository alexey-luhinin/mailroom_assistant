from dotenv import load_dotenv

load_dotenv("config/.env")

import asyncio
import logging
import os

import httpx
from fastapi import FastAPI, HTTPException

import agent
from models import EmailSummaryItem, ResearchRequest, ResearchResponse

logger = logging.getLogger(__name__)

MCP_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8006")
_T_SHORT = 10.0
_T_MEDIUM = 30.0
_T_LONG = 60.0
_MAX_EMAILS_CAP = 10
_HISTORY_DAYS = 30

app = FastAPI(title="Researcher")


@app.get("/health")
def health():
    return {"status": "ok", "service": "researcher"}


@app.post("/research", response_model=ResearchResponse)
async def post_research(request: ResearchRequest):
    max_emails = min(request.max_emails, _MAX_EMAILS_CAP)

    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{MCP_URL}/emails/{request.email_id}", timeout=_T_LONG)
        if resp.status_code == 404:
            raise HTTPException(status_code=404, detail="Email not found.")
        resp.raise_for_status()
        target = resp.json()

    sender = target.get("from", "")

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{MCP_URL}/emails", params={"days": _HISTORY_DAYS}, timeout=_T_LONG
        )
        resp.raise_for_status()
        all_emails = resp.json()

    history = [
        e for e in all_emails
        if e.get("from") == sender and e["id"] != request.email_id
    ]
    history = sorted(history, key=lambda e: e.get("date", ""), reverse=True)[:max_emails]

    if not history:
        return ResearchResponse(sender=sender, history_count=0, summaries=[])

    async with httpx.AsyncClient() as client:
        full_emails = await asyncio.gather(
            *[_fetch_full_email(client, e["id"]) for e in history]
        )

    full_emails = [e for e in full_emails if e is not None]
    if not full_emails:
        return ResearchResponse(sender=sender, history_count=0, summaries=[])

    summaries_raw = await agent.summarize(full_emails)
    summary_by_id = {s["id"]: s["summary"] for s in summaries_raw}

    summaries = [
        EmailSummaryItem(
            id=e["id"],
            date=e.get("date", ""),
            subject=e.get("subject", ""),
            summary=summary_by_id.get(e["id"], ""),
        )
        for e in full_emails
        if e["id"] in summary_by_id
    ]

    return ResearchResponse(
        sender=sender,
        history_count=len(summaries),
        summaries=summaries,
    )


async def _fetch_full_email(client: httpx.AsyncClient, email_id: str) -> dict | None:
    try:
        resp = await client.get(f"{MCP_URL}/emails/{email_id}", timeout=_T_LONG)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.warning("Failed to fetch full email %s: %s", email_id, e)
        return None
