# Researcher API — Spec

Base URL: `http://localhost:8002`

## Endpoints

### POST /research
Fetch and summarize recent email history with a specific sender.

**Request**
```json
{
  "email_id": "gmail_message_id",
  "max_emails": 5
}
```
- `email_id` — required, the email we want to reply to
- `max_emails` — optional, default 5, max 10

**Response 200**
```json
{
  "sender": "sender@example.com",
  "history_count": 3,
  "summaries": [
    {
      "id": "gmail_message_id",
      "date": "2026-05-01T10:00:00Z",
      "subject": "Previous subject",
      "summary": "2-3 sentence summary of this email."
    }
  ]
}
```

**Response 200 — no history found**
```json
{
  "sender": "sender@example.com",
  "history_count": 0,
  "summaries": []
}
```

**Response 404**
```json
{
  "error": "Email not found."
}
```

---

### GET /health
Health check.

**Response 200**
```json
{
  "status": "ok",
  "service": "researcher"
}
```

## Notes
- Researcher is called synchronously by Lead Agent before Drafter
- Response time depends on number of emails fetched (typically 5-15s)
- If Researcher is unavailable, Lead Agent skips it and calls Drafter directly