import os
from datetime import date, datetime, timedelta, timezone

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from gmail import SCOPES, TOKEN_FILE

_service = None


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
                f"Calendar token missing or expired. "
                f"Run  python services/mcp-server/auth.py  locally to re-authenticate, "
                f"then restart Docker. Expected token at: {TOKEN_FILE}"
            )
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())

    _service = build("calendar", "v3", credentials=creds)
    return _service


def get_events(days_ahead: int) -> dict:
    service = _get_service()
    today = date.today()
    time_min = _day_start_utc(today)
    time_max = _day_start_utc(today + timedelta(days=days_ahead))

    try:
        result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy="startTime",
                maxResults=100,
            )
            .execute()
        )
    except HttpError as e:
        raise RuntimeError(f"Calendar API error: {e}") from e

    events = [_parse_event(e) for e in result.get("items", [])]
    return {
        "week": _week_label(today, _week_end(today)),
        "events": events,
    }


def _parse_event(event: dict) -> dict:
    start = event.get("start", {})
    end = event.get("end", {})

    all_day = "date" in start and "dateTime" not in start
    start_str = start.get("dateTime") or start.get("date", "")
    end_str = end.get("dateTime") or end.get("date", "")

    meet_link = event.get("hangoutLink")
    if not meet_link:
        for ep in event.get("conferenceData", {}).get("entryPoints", []):
            if ep.get("entryPointType") == "video":
                meet_link = ep.get("uri")
                break

    attendees = [
        {
            "email": a.get("email", ""),
            "name": a.get("displayName", ""),
            "status": a.get("responseStatus", "needsAction"),
        }
        for a in event.get("attendees", [])
    ]

    return {
        "id": event["id"],
        "title": event.get("summary", "(no title)"),
        "start": start_str,
        "end": end_str,
        "all_day": all_day,
        "description": event.get("description"),
        "location": event.get("location"),
        "meet_link": meet_link,
        "attendees": attendees,
        "organizer": event.get("organizer", {}).get("email", ""),
    }


def _day_start_utc(d: date) -> str:
    return datetime(d.year, d.month, d.day, tzinfo=timezone.utc).isoformat()


def _week_end(d: date) -> date:
    days_to_friday = (4 - d.weekday()) % 7
    return d + timedelta(days=days_to_friday)


_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _week_label(start: date, end: date) -> str:
    s = f"{_MONTHS[start.month - 1]} {start.day}"
    if start == end:
        return f"{s}, {start.year}"
    e = f"{_MONTHS[end.month - 1]} {end.day}" if end.month != start.month else str(end.day)
    return f"{s} – {e}, {start.year}"
