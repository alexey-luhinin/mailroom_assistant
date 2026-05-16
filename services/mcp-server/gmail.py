import base64
import os
from datetime import datetime, timedelta, timezone

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/calendar.readonly",
]

_ROOT = os.path.dirname(os.path.abspath(__file__))
TOKEN_FILE = os.path.join(_ROOT, "config", "token.json")

_service = None  # built lazily on first request, never at import time


def _get_service():
    global _service
    if _service is not None:
        return _service

    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            raise RuntimeError(
                f"Gmail token missing or expired. "
                f"Run  python services/mcp-server/auth.py  locally to authenticate, "
                f"then restart Docker. Expected token at: {TOKEN_FILE}"
            )
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())

    _service = build("gmail", "v1", credentials=creds)
    return _service


def fetch_emails(days: int) -> list[dict]:
    service = _get_service()
    after = int((datetime.now(timezone.utc) - timedelta(days=days)).timestamp())
    result = (
        service.users()
        .messages()
        .list(userId="me", q=f"in:inbox after:{after}", maxResults=200)
        .execute()
    )
    messages = result.get("messages", [])

    emails = []
    for msg in messages:
        try:
            raw = (
                service.users()
                .messages()
                .get(userId="me", id=msg["id"], format="metadata",
                     metadataHeaders=["From", "Subject", "Date"])
                .execute()
            )
            emails.append(_parse_summary(raw))
        except HttpError:
            continue
    return emails


def fetch_email(email_id: str) -> dict | None:
    service = _get_service()
    try:
        raw = service.users().messages().get(userId="me", id=email_id, format="full").execute()
    except HttpError:
        return None
    return _parse_full(raw)


def fetch_sent_emails(days: int) -> list[dict]:
    service = _get_service()
    after = int((datetime.now(timezone.utc) - timedelta(days=days)).timestamp())
    result = (
        service.users()
        .messages()
        .list(userId="me", q=f"in:sent after:{after}", maxResults=200)
        .execute()
    )
    messages = result.get("messages", [])
    emails = []
    for msg in messages:
        try:
            raw = (
                service.users()
                .messages()
                .get(
                    userId="me",
                    id=msg["id"],
                    format="metadata",
                    metadataHeaders=["From", "To", "Subject", "Date"],
                )
                .execute()
            )
            emails.append(_parse_sent_summary(raw))
        except HttpError:
            continue
    return emails


def fetch_thread(thread_id: str) -> list[dict]:
    service = _get_service()
    try:
        result = (
            service.users()
            .threads()
            .get(
                userId="me",
                id=thread_id,
                format="metadata",
                metadataHeaders=["From", "Date"],
            )
            .execute()
        )
    except HttpError:
        return []
    return [_parse_thread_message(msg) for msg in result.get("messages", [])]


def create_draft(to: str, subject: str, body: str, thread_id: str | None = None) -> str:
    from email.mime.text import MIMEText
    from email.utils import parseaddr

    _, addr = parseaddr(to)
    service = _get_service()
    message = MIMEText(body)
    message["to"] = addr or to
    message["subject"] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

    draft_body: dict = {"message": {"raw": raw}}
    if thread_id:
        draft_body["message"]["threadId"] = thread_id

    draft = service.users().drafts().create(userId="me", body=draft_body).execute()
    return draft["id"]


def _parse_sent_summary(msg: dict) -> dict:
    headers = {h["name"].lower(): h["value"] for h in msg["payload"]["headers"]}
    return {
        "id": msg["id"],
        "from": headers.get("from", ""),
        "to": headers.get("to", ""),
        "subject": headers.get("subject", "(no subject)"),
        "date": _parse_date(msg.get("internalDate")),
        "thread_id": msg["threadId"],
    }


def _parse_thread_message(msg: dict) -> dict:
    headers = {h["name"].lower(): h["value"] for h in msg["payload"]["headers"]}
    return {
        "id": msg["id"],
        "from": headers.get("from", ""),
        "date": _parse_date(msg.get("internalDate")),
    }


def _parse_summary(msg: dict) -> dict:
    headers = {h["name"].lower(): h["value"] for h in msg["payload"]["headers"]}
    return {
        "id": msg["id"],
        "from": headers.get("from", ""),
        "subject": headers.get("subject", "(no subject)"),
        "date": _parse_date(msg.get("internalDate")),
        "snippet": msg.get("snippet", ""),
        "thread_id": msg["threadId"],
        "is_read": "UNREAD" not in msg.get("labelIds", []),
    }


def _parse_full(msg: dict) -> dict:
    summary = _parse_summary(msg)
    headers = {h["name"].lower(): h["value"] for h in msg["payload"]["headers"]}
    summary["body"] = _extract_body(msg["payload"])
    summary["to"] = headers.get("to", "")
    summary["list_unsubscribe"] = headers.get("list-unsubscribe")
    return summary


def _extract_body(payload: dict) -> str:
    if payload.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")
    for mime in ("text/plain", "text/html"):
        for part in payload.get("parts", []):
            if part["mimeType"] == mime:
                data = part.get("body", {}).get("data", "")
                if data:
                    return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
    return ""


def _parse_date(internal_date_ms: str | None) -> str:
    if internal_date_ms:
        return datetime.fromtimestamp(int(internal_date_ms) / 1000, tz=timezone.utc).isoformat()
    return datetime.now(timezone.utc).isoformat()
