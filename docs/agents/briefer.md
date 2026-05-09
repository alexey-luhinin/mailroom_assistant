# Briefer Agent — Spec

## Role
Generate a morning briefing for the user.
Summarizes new emails from today and includes any unresolved
urgent or action_needed emails from previous days.

## Input
```json
{
  "days": 1
}
```
- `days` — how many days back to fetch new emails (default: 1)

## Process
1. Read today's classified emails from PostgreSQL
2. Read all unresolved `urgent` and `action_needed` from previous days
3. Generate a short summary per email (2-4 sentences)
4. Group by label, ordered by priority
5. Add counts per label at the top
6. Save briefing to PostgreSQL and return to Web UI

## Output format

```markdown
# Morning Briefing — May 9, 2026

## Summary
- Total: 12 emails
- Urgent: 2
- Action needed: 4
- FYI: 3
- Calendar: 1
- Newsletter: 1
- Promo: 1
- Spam: 0

## Unresolved from previous days
### Urgent
- **Re: Q2 report** from boss@company.com (May 7)
  Waiting for your confirmation on the Q2 report submission.

### Action needed
- **API question** from colleague@company.com (May 8)
  Colleague asked about pagination support in the new API endpoint.

## Today

### Urgent
- **Server down** from ops@company.com
  Production server is down, immediate action required.

### Action needed
- **Quick question** from partner@company.com
  Partner asking about contract renewal timeline.

### FYI
...
```

## Rules
- Unresolved = `urgent` or `action_needed` emails with no draft saved yet
- Summary per email is 2-4 sentences max
- Language of each summary matches the language of the email
- Always show counts at the top even if a category is 0

## Dependencies
- PostgreSQL (read classified emails, save briefing)
