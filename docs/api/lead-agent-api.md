# Lead Agent API — Spec

Base URL: `http://localhost:8000`

## Role
Lead Agent is the single entry point for the Web UI.
It orchestrates all specialist agents and manages the workflow.
Web UI never calls specialist agents directly.

## Workflows

### Morning run
```
POST /run
  → Sorter: fetch + classify emails
  → Briefer: generate briefing
  → return briefing to Web UI
```

### Draft reply
```
POST /draft
  → Researcher: fetch thread context
  → Drafter: write draft
  → Critic: review draft
  → return draft to Web UI
```

---

## Endpoints

### POST /run
Trigger the morning run: classify emails and generate briefing.

**Request**
```json
{
  "days": 1
}
```

**Response 202**
```json
{
  "job_id": "abc123",
  "status": "pending"
}
```

---

### GET /run/{job_id}
Check status of a morning run job.

**Response 200 — pending**
```json
{
  "job_id": "abc123",
  "status": "pending",
  "step": "sorting"
}
```
- `step` — current step: `sorting`, `briefing`, `done`, `failed`

**Response 200 — done**
```json
{
  "job_id": "abc123",
  "status": "done",
  "step": "done",
  "emails_classified": 12,
  "emails_skipped": 4,
  "briefing": {
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
}
```

---

### POST /draft
Start a draft reply workflow.

**Request**
```json
{
  "email_id": "gmail_message_id",
  "instructions": "Keep it short and friendly"
}
```

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
  "status": "pending",
  "step": "researching"
}
```
- `step` — current step: `researching`, `drafting`, `reviewing`, `done`, `failed`

**Response 200 — done**
```json
{
  "job_id": "abc123",
  "status": "done",
  "step": "done",
  "draft": {
    "draft_id": "gmail_draft_id",
    "subject": "Re: Original subject",
    "body": "Draft text...",
    "language": "en"
  }
}
```

**Response 200 — failed**
```json
{
  "job_id": "abc123",
  "status": "failed",
  "step": "drafting",
  "error": "Could not fetch email thread."
}
```

---

### GET /emails
Return all classified emails from DB.

**Query params**
- `label` — filter by label (optional)
- `days` — how many days back (optional, default: 7)

**Response 200**
```json
[
  {
    "id": "gmail_message_id",
    "from": "sender@example.com",
    "subject": "Subject line",
    "date": "2026-05-09T10:00:00Z",
    "label": "urgent",
    "reason": "Time-sensitive request from manager.",
    "priority": 1
  }
]
```

---

### GET /health
Health check for Lead Agent and all downstream services.

**Response 200**
```json
{
  "status": "ok",
  "service": "lead-agent",
  "dependencies": {
    "sorter": "ok",
    "researcher": "ok",
    "drafter": "ok",
    "critic": "ok",
    "briefer": "ok",
    "mcp-server": "ok"
  }
}
```
