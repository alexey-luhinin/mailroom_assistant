# Sorter Agent — Spec

## Role
Fetch emails from Gmail and classify each one by type.
Sorter only reads — it never replies, drafts, or modifies emails.

## Input
```json
{
  "days": 1
}
```
- `days` — how many days back to fetch (default: 1, user can override)

## Classification
Sorter looks at **subject and sender only** — it does not read the email body.

| Label          | Meaning                                      |
|----------------|----------------------------------------------|
| `urgent`       | Requires response within 24h                 |
| `action_needed`| Requires response, not time-critical         |
| `fyi`          | Informational, no reply needed               |
| `newsletter`   | Subscriptions and digests                    |
| `promo`        | Discounts, sales, offers                     |
| `spam`         | Suspicious or unwanted email                 |
| `calendar`     | Meeting invite or scheduling request         |

## Rules
- Skip emails that are already classified in the database
- Classify based on subject and sender only — do not fetch email body
- Default fetch window is 1 day, configurable per request

## Output
Saves results to PostgreSQL and returns:
```json
[
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
```
- Sorted by priority ascending (1 = highest)
- `reason` is one sentence explaining the label choice

## Dependencies
- MCP Server (Gmail read)
- PostgreSQL (check if already classified, save results)
- Redis (cache Gmail responses, TTL 1h)
