import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv("config/.env")

import asyncpg
import httpx
from fastapi import FastAPI, HTTPException

import agent
import cache
import db
from models import ClassifiedEmail, SortRequest, SortResponse

MCP_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8006")

_T_SORT = 30.0

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


app = FastAPI(title="Sorter", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok", "service": "sorter"}


@app.post("/sort", response_model=SortResponse, response_model_by_alias=True)
async def sort(request: SortRequest):
    if not 1 <= request.days <= 30:
        raise HTTPException(status_code=422, detail="Invalid days value. Must be between 1 and 30.")

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{MCP_URL}/emails", params={"days": request.days}, timeout=_T_SORT
        )
        resp.raise_for_status()
    raw_emails: list[dict] = resp.json()

    if not raw_emails:
        return SortResponse(total=0, new=0, skipped=0, emails=[])

    all_ids = [e["id"] for e in raw_emails]
    known_ids = await db.get_classified_ids(_pool, all_ids)
    new_emails = [e for e in raw_emails if e["id"] not in known_ids]

    # Classify and persist new emails
    newly_classified: list[dict] = []
    if new_emails:
        classifications = await agent.classify(new_emails)
        cls_by_id = {c["id"]: c for c in classifications}
        for email in new_emails:
            cls = cls_by_id.get(email["id"])
            if cls:
                newly_classified.append({**email, **cls})
        await db.save_emails(_pool, newly_classified)

    # Fetch full rows for skipped emails so we can return their labels too
    skipped_rows = await db.get_emails_by_ids(_pool, list(known_ids)) if known_ids else []

    all_emails = sorted(newly_classified + skipped_rows, key=lambda e: e["priority"])

    return SortResponse(
        total=len(raw_emails),
        new=len(newly_classified),
        skipped=len(known_ids),
        emails=all_emails,
    )


@app.get("/emails", response_model=list[ClassifiedEmail], response_model_by_alias=True)
async def get_emails(label: str | None = None, days: int = 7):
    cached = cache.get_emails(days, label)
    if cached is not None:
        return cached

    emails = await db.get_emails(_pool, days, label)
    cache.set_emails(days, label, emails)
    return emails
