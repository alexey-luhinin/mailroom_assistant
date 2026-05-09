# Briefer API — Spec

Base URL: `http://localhost:8005`

## Endpoints

### POST /brief
Generate a morning briefing. Can be triggered by scheduler or user manually.

**Request**
```json
{
  "days": 1
}
```
- `days` — how many days back to include new emails (default: 1)

**Response 202**
```json
{
  "job_id": "abc123",
  "status": "pending"
}
```

---

### GET /brief/{job_id}
Check status of a briefing job.

**Response 200 — pending**
```json
{
  "job_id": "abc123",
  "status": "pending"
}
```

**Response 200 — done**
```json
{
  "job_id": "abc123",
  "status": "done",
  "created_at": "2026-05-09T08:00:00Z",
  "summary": {
    "total": 12,
    "urgent": 2,
    "action_needed": 4,
    "fyi": 3,
    "calendar": 1,
    "newsletter": 1,
    "promo": 1,
    "spam": 0
  },
  "content": "# Morning Briefing — May 9, 2026\n..."
}
```

**Response 200 — failed**
```json
{
  "job_id": "abc123",
  "status": "failed",
  "error": "Could not fetch classified emails."
}
```

---

### GET /briefs
Return all saved briefings from DB.

**Query params**
- `limit` — max number of briefings to return (default: 7)

**Response 200**
```json
[
  {
    "job_id": "abc123",
    "created_at": "2026-05-09T08:00:00Z",
    "summary": {
      "total": 12,
      "urgent": 2,
      "action_needed": 4,
      "fyi": 3,
      "calendar": 1,
      "newsletter": 1,
      "promo": 1,
      "spam": 0
    }
  }
]
```

---

### GET /briefs/latest
Return the most recent briefing.

**Response 200**
```json
{
  "job_id": "abc123",
  "status": "done",
  "created_at": "2026-05-09T08:00:00Z",
  "summary": { ... },
  "content": "# Morning Briefing — May 9, 2026\n..."
}
```

**Response 404**
```json
{
  "error": "No briefings found."
}
```

---

### GET /health
Health check.

**Response 200**
```json
{
  "status": "ok",
  "service": "briefer"
}
```

## Scheduler
Briefer is triggered automatically every day at 08:00 local time.
Scheduler calls `POST /brief` with default params.
Schedule is configured via environment variable:

```
BRIEF_SCHEDULE=0 8 * * *
```
