import base64
import os
from datetime import datetime, timedelta, timezone

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
]

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TOKEN_FILE = os.path.join(_ROOT, "config", "token.json")


def _get_service():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            credentials_file = os.getenv(
                "GMAIL_CREDENTIALS_FILE",
                os.path.join(_ROOT, "config", "credentials.json"),
            )
            flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
    return build("gmail", "v1", credentials=creds)


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


def create_draft(to: str, subject: str, body: str, thread_id: str | None = None) -> str:
    from email.mime.text import MIMEText

    service = _get_service()
    message = MIMEText(body)
    message["to"] = to
    message["subject"] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

    draft_body: dict = {"message": {"raw": raw}}
    if thread_id:
        draft_body["message"]["threadId"] = thread_id

    draft = service.users().drafts().create(userId="me", body=draft_body).execute()
    return draft["id"]


def _parse_summary(msg: dict) -> dict:
    headers = {h["name"].lower(): h["value"] for h in msg["payload"]["headers"]}
    return {
        "id": msg["id"],
        "from": headers.get("from", ""),
        "subject": headers.get("subject", "(no subject)"),
        "date": _parse_date(msg.get("internalDate")),
        "snippet": msg.get("snippet", ""),
        "thread_id": msg["threadId"],
    }


def _parse_full(msg: dict) -> dict:
    summary = _parse_summary(msg)
    summary["body"] = _extract_body(msg["payload"])
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
