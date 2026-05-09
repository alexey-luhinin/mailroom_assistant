# Drafter API — Spec

Base URL: `http://localhost:8003`

## Endpoints

### POST /draft
Start a draft generation job.

**Request**
```json
{
  "email_id": "gmail_message_id",
  "instructions": "Keep it short and friendly"
}
```
- `email_id` — required, email to reply to
- `instructions` — optional, user guidance for tone or content

**Response 202**
```json
{
  "job_id": "abc123",
  "status": "pending"
}
```

---

### GET /draft/{job_id}
Check status of a draft job.

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
  "email_id": "gmail_message_id",
  "draft_id": "gmail_draft_id",
  "subject": "Re: Original subject",
  "body": "Draft text...",
  "language": "en"
}
```

**Response 200 — failed**
```json
{
  "job_id": "abc123",
  "status": "failed",
  "error": "Could not fetch email thread."
}
```

---

### GET /drafts
Return all saved drafts from DB.

**Query params**
- `email_id` — filter by email (optional)

**Response 200**
```json
[
  {
    "job_id": "abc123",
    "email_id": "gmail_message_id",
    "draft_id": "gmail_draft_id",
    "subject": "Re: Original subject",
    "body": "Draft text...",
    "language": "en",
    "created_at": "2026-05-09T10:00:00Z"
  }
]
```

---

### GET /health
Health check.

**Response 200**
```json
{
  "status": "ok",
  "service": "drafter"
}
```
