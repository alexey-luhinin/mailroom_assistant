# Follow-up API — Spec

Base URL: `http://localhost:8008`

## Endpoints

### POST /followup
Start a follow-up analysis job.

**Request**
```json
{
  "days": 30
}
```
- `days` — how far back to look (default: 30, configurable)

**Response 202**
```json
{
  "job_id": "abc123",
  "status": "pending"
}
```

---

### GET /followup/{job_id}
Check status of a follow-up job.

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
  "days": 30,
  "waiting_count": 3,
  "emails": [
    {
      "id": "gmail_message_id",
      "thread_id": "gmail_thread_id",
      "to": "colleague@company.com",
      "subject": "Re: API question",
      "sent_at": "2026-05-09T10:00:00Z",
      "days_waiting": 5
    }
  ]
}
```

**Response 200 — failed**
```json
{
  "job_id": "abc123",
  "status": "failed",
  "error": "Could not fetch sent emails."
}
```

**Response 404**
```json
{
  "error": "Job not found."
}
```

---

### GET /health

**Response 200**
```json
{
  "status": "ok",
  "service": "followup"
}
```

## Notes
- No caching, no DB for results — always fetches live from Gmail
- Job metadata stored in memory only (lost on restart)
- Results reflect real-time state — if reply arrived, email won't appear