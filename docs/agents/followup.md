# Follow-up Agent — Spec

## Role
Track sent emails that are waiting for a reply.
No caching, no DB storage — always fetches live state from Gmail
to ensure accuracy (replies may have arrived since last check).

## How it works
1. Fetch sent emails from Gmail for the last N days (default: 30)
2. For each sent email — check if anyone replied in the same thread
3. If no reply exists in the thread → email is "waiting"
4. If a reply exists → email is resolved, not shown

## Input
```json
{
  "days": 30
}
```
- `days` — how far back to look at sent emails (default: 30, configurable)

## Output
```json
{
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
- Sorted by `days_waiting` descending (longest wait first)

## Rules
- Never cache results — always fetch live from Gmail
- Never store in DB — state changes when replies arrive
- Only track emails sent by the user (from Sent folder)
- A reply = any message in the same thread sent by someone else after our message
- Default window: 30 days, configurable per request
- Skip threads where we sent the last message but it was a reply ourselves

## Dependencies
- MCP Server (Gmail read — sent folder + thread fetch)