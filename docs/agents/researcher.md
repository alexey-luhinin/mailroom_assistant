# Researcher Agent — Spec

## Role
Fetch recent email history with a specific sender from Gmail
and summarize it to provide context for the Drafter.

## Input
```json
{
  "email_id": "gmail_message_id",
  "max_emails": 5
}
```
- `email_id` — the email we want to reply to
- `max_emails` — how many recent emails from this sender to fetch
  (default: 5, max: 10)

## Process
1. Fetch the original email from MCP Server to get sender address
2. Search Gmail for recent emails from this sender via MCP Server
3. Fetch full content of each email
4. Generate a 2-3 sentence summary per email
5. Return summaries as context for Drafter

## Output
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

## Rules
- Return summaries only — never full email body
- Skip the current email from history (we already have it)
- If no history found — return empty summaries list
- Language of each summary matches the language of that email

## Dependencies
- MCP Server (fetch emails by sender)