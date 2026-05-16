import asyncio
import os

from dotenv import load_dotenv

load_dotenv("config/.env")

from fastapi import FastAPI, HTTPException

import cache
import gcalendar as gcal
import gmail
from models import (
    CalendarEventsResponse,
    DraftRequest,
    DraftResponse,
    Email,
    EmailSummary,
    SentEmailSummary,
    ThreadMessage,
)

app = FastAPI(title="MCP Server", description="Gmail API gateway — read + drafts")


@app.get("/health")
def health():
    return {"status": "ok", "service": "mcp-server"}


@app.get("/emails", response_model=list[EmailSummary], response_model_by_alias=True)
async def list_emails(days: int = 1):
    if not 1 <= days <= 30:
        raise HTTPException(status_code=422, detail="Invalid days value. Must be between 1 and 30.")

    cached = cache.get_emails(days)
    if cached is not None:
        return cached

    emails = await asyncio.to_thread(gmail.fetch_emails, days)
    cache.set_emails(days, emails)
    return emails


@app.get("/emails/sent", response_model=list[SentEmailSummary], response_model_by_alias=True)
async def list_sent_emails(days: int = 30):
    if not 1 <= days <= 30:
        raise HTTPException(status_code=422, detail="Invalid days value. Must be between 1 and 30.")
    emails = await asyncio.to_thread(gmail.fetch_sent_emails, days)
    return emails


@app.get("/threads/{thread_id}", response_model=list[ThreadMessage], response_model_by_alias=True)
async def get_thread(thread_id: str):
    messages = await asyncio.to_thread(gmail.fetch_thread, thread_id)
    return messages


@app.get("/emails/{email_id}", response_model=Email, response_model_by_alias=True)
async def get_email(email_id: str):
    cached = cache.get_email(email_id)
    if cached is not None:
        return cached

    email = await asyncio.to_thread(gmail.fetch_email, email_id)
    if email is None:
        raise HTTPException(status_code=404, detail="Email not found.")

    cache.set_email(email_id, email)
    return email


@app.get("/calendar/events/today", response_model=CalendarEventsResponse)
async def calendar_events_today():
    try:
        return await asyncio.to_thread(gcal.get_events, 1)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))


@app.get("/calendar/events", response_model=CalendarEventsResponse)
async def calendar_events(days_ahead: int = 5):
    if not 1 <= days_ahead <= 30:
        raise HTTPException(status_code=422, detail="days_ahead must be between 1 and 30.")
    try:
        return await asyncio.to_thread(gcal.get_events, days_ahead)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))


@app.post("/drafts", response_model=DraftResponse, status_code=201)
async def create_draft(request: DraftRequest):
    draft_id = await asyncio.to_thread(
        gmail.create_draft,
        to=request.to,
        subject=request.subject,
        body=request.body,
        thread_id=request.thread_id,
    )
    return DraftResponse(draft_id=draft_id)
