# Drafter Agent — Spec

## Role
Write a reply draft for a selected email.
Drafter reads conversation history and follows the user's style profile.
It never sends — only creates a draft in Gmail Drafts.

## Input
```json
{
  "email_id": "gmail_message_id",
  "instructions": "Optional user instructions, e.g. keep it short"
}
```
- `email_id` — the email to reply to (from sorted.json)
- `instructions` — optional, user can guide the tone or content

## Process
1. Fetch email thread history from MCP Server
2. Load user style profile from `config/style_profile.md`
3. Generate draft reply
4. Save draft to Gmail Drafts via MCP Server
5. Return draft text to Web UI for user review

## Style profile
Stored in `config/style_profile.md`. Example:
```
- Write concisely, no filler words
- Use plain language, no corporate jargon
- Sign off with first name only
- Bullet points for lists, not long paragraphs
```

## Language
Reply in the same language as the incoming email.

## Rules
- Never send — only save to Gmail Drafts
- Always read thread history before drafting
- Follow style profile strictly
- If `instructions` are provided, they override style profile

## Output
```json
{
  "email_id": "gmail_message_id",
  "draft_id": "gmail_draft_id",
  "subject": "Re: Original subject",
  "body": "Draft text...",
  "language": "en"
}
```

## Dependencies
- MCP Server (read thread history, save draft to Gmail)
- PostgreSQL (read classified email metadata)
- Style profile (`config/style_profile.md`)
