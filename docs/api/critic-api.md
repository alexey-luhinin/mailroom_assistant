# Critic API — Spec

Base URL: `http://localhost:8004`

## Endpoints

### POST /review
Review a draft and return a score with feedback.

**Request**
```json
{
  "draft": {
    "subject": "Re: Original subject",
    "body": "Draft text...",
    "language": "en"
  },
  "instructions": "Optional user instructions",
  "iteration": 1
}
```

**Response 200**
```json
{
  "score": 8,
  "approved": true,
  "feedback": "Draft is concise and follows the style profile.",
  "improved_draft": null
}
```

**Response 200 — not approved**
```json
{
  "score": 5,
  "approved": false,
  "feedback": "Too long and contains filler phrases. Remove the second paragraph and get to the point faster.",
  "improved_draft": null
}
```

---

### GET /health
Health check.

**Response 200**
```json
{
  "status": "ok",
  "service": "critic"
}
```