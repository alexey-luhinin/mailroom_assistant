# Calendar MCP — Spec

## Overview
Google Calendar read-only access added to the existing MCP server.
Uses the same OAuth credentials as Gmail with an additional Calendar scope.

## New OAuth Scope
```
https://www.googleapis.com/auth/calendar.readonly
```

## New Endpoints

### GET /calendar/events
Fetch events for the current work week (Monday to Friday).

**Query params**
- `days_ahead` — how many days ahead to fetch (default: 5, current work week)

**Response 200**
```json
{
  "week": "May 12 – May 16, 2026",
  "events": [
    {
      "id": "google_event_id",
      "title": "Team standup",
      "start": "2026-05-13T09:00:00+03:00",
      "end": "2026-05-13T09:30:00+03:00",
      "all_day": false,
      "description": "Daily team sync",
      "location": null,
      "meet_link": "https://meet.google.com/abc-defg-hij",
      "attendees": [
        {
          "email": "colleague@company.com",
          "name": "John Doe",
          "status": "accepted"
        }
      ],
      "organizer": "me@gmail.com"
    }
  ]
}
```

**Response 200 — no events**
```json
{
  "week": "May 12 – May 16, 2026",
  "events": []
}
```

---

### GET /calendar/events/today
Fetch events for today only.

**Response 200** — same format as above but only today's events.

---

### GET /health
Already exists — no change needed.

## Notes
- Read-only — never creates, modifies, or deletes events
- Returns only events where the user is invited or organizer
- meet_link extracted from hangoutLink or conferenceData in Google API response
- attendees status: accepted / declined / tentative / needsAction