# Critic Agent — Spec

## Role
Review a draft reply and score it against the user's style profile.
If the score is below 7, return specific feedback for Drafter to improve.
Critic does not rewrite the draft — only evaluates and explains.

## Input
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
- `iteration` — current iteration number (1-3)

## Evaluation criteria
Critic scores the draft against `config/style_profile.md`:
- Conciseness — no filler words
- Tone — matches style profile
- Language — matches incoming email language
- Relevance — addresses the email content
- Instructions — follows user instructions if provided

## Output
```json
{
  "score": 8,
  "approved": true,
  "feedback": "Draft is concise and on-point.",
  "improved_draft": null
}
```
- `score` — 1-10
- `approved` — true if score >= 7
- `feedback` — one paragraph explaining the score
- `improved_draft` — null (Critic does not rewrite)

## Iteration rules
- If `approved: false` — Lead Agent sends feedback back to Drafter
- Drafter rewrites using feedback as additional instructions
- Maximum 3 iterations total
- If score < 7 after 3 iterations — Lead Agent returns best draft

## Dependencies
- Style profile (`config/style_profile.md`)
- No tools, no DB, no external calls