# Unsubscribe Agent — Spec

## Role
Analyze newsletter and promo emails to identify subscriptions 
the user never or rarely reads, and surface unsubscribe links.
Never unsubscribes automatically — only suggests.

## Input
```json
{
  "days": 30
}
```
- `days` — analysis window (default: 30, configurable)

## Process
1. Fetch all emails with label `newsletter` or `promo` from DB
   for the last N days
2. Group by sender
3. For each sender calculate:
   - `total` — total emails received
   - `opened` — emails marked as read in Gmail
   - `open_rate` — opened / total (0.0 to 1.0)
4. Classify each sender:
   - `unsubscribe` — open_rate == 0.0 (never opened)
   - `consider` — open_rate > 0.0 and < 0.20 (rarely opened)
   - Skip senders with open_rate >= 0.20
5. For each candidate — fetch latest email and extract 
   unsubscribe link:
   - First check `List-Unsubscribe` email header
   - If not found — search for "unsubscribe" link in email body

## Output
```json
{
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
      "unsubscribe_url": "https://..."
    }
  ]
}
```

## Rules
- Never unsubscribe automatically
- Never delete or modify emails
- If unsubscribe link not found — return `unsubscribe_url: null`
- Only analyze `newsletter` and `promo` labels
- Skip senders with open_rate >= 0.20

## Dependencies
- PostgreSQL (classified emails with read status)
- MCP Server (fetch email body and headers for unsubscribe link)