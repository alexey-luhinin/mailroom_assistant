# Unsubscribe API — Spec

Base URL: `http://localhost:8007`

## Endpoints

### POST /analyze
Start an unsubscribe analysis job.

**Request**
```json
{
  "days": 30
}
```
- `days` — analysis window (default: 30, configurable)

**Response 202**
```json
{
  "job_id": "abc123",
  "status": "pending"
}
```

---

### GET /analyze/{job_id}
Check status of an analysis job.

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
  "total_senders": 15,
  "candidates": [
    {
      "sender": "newsletter@deeplearning.ai",
      "name": "The Batch @ DeepLearning.AI",
      "total": 21,
      "opened": 0,
      "open_rate": 0.0,
      "recommendation": "unsubscribe",
      "unsubscribe_url": "https://..."
    },
    {
      "sender": "events@pokerstars.com",
      "name": "PokerStars",
      "total": 8,
      "opened": 1,
      "open_rate": 0.125,
      "recommendation": "consider",
      "unsubscribe_url": null
    }
  ]
}
```

**Response 200 — failed**
```json
{
  "job_id": "abc123",
  "status": "failed",
  "error": "Could not fetch emails from DB."
}
```

---

### GET /analyze/latest
Return the most recent analysis result.

**Response 200** — same as done response above

**Response 404**
```json
{
  "error": "No analysis found."
}
```

---

### GET /health
Health check.

**Response 200**
```json
{
  "status": "ok",
  "service": "unsubscribe"
}
```