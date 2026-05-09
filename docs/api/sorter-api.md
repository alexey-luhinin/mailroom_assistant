# Sorter API — Spec

Base URL: `http://localhost:8001`

## Endpoints

### POST /sort
Fetch and classify emails from Gmail.

**Request**
```json
{
  "days": 1
}
```
- `days` — how many days back to fetch (default: 1)

**Response 200**
```json
{
  "total": 12,
  "new": 8,
  "skipped": 4,
  "emails": [
    {
      "id": "gmail_message_id",
      "from": "sender@example.com",
      "subject": "Subject line",
      "date": "2026-05-09T10:00:00Z",
      "label": "action_needed",
      "reason": "One sentence: why this label was chosen",
      "priority": 1
    }
  ]
}
```
- `skipped` — emails already classified in DB
- `emails` — sorted by priority ascending

**Response 422**
```json
{
  "error": "Invalid days value. Must be between 1 and 30."
}
```

---

### GET /emails
Return all classified emails from DB.

**Query params**
- `label` — filter by label (optional), e.g. `?label=urgent`
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
Health check.

**Response 200**
```json
{
  "status": "ok",
  "service": "sorter"
}
```
