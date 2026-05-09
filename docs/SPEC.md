# E-Mail Assistant — Spec

## What it is
A microservices-based AI assistant that helps a single user process 
their Gmail inbox: classify emails, generate a morning briefing, 
and draft replies on demand. Accessible via a web UI in the browser.

## Architecture style
- Each agent is a standalone service with its own REST API
- Services communicate via HTTP REST
- Lead Agent orchestrates all specialist agents

## Services
| Service    | Responsibility                          |
|------------|-----------------------------------------|
| Lead Agent | Orchestrates all agents, main entry point |
| Sorter     | Classifies emails from Gmail            |
| Researcher | Enriches context from KB and web        |
| Drafter    | Writes reply drafts                     |
| Critic     | Reviews drafts before saving            |
| Briefer    | Generates morning summary               |
| MCP Server | Gmail API gateway (read + drafts)       |
| Web UI     | Browser interface for the user          |

## What it does

### 1. Classify emails
- Fetches inbox emails from the last X days (user-defined)
- Assigns one label per email:
  - `urgent` — requires response within 24h
  - `action_needed` — requires response, not time-critical
  - `fyi` — informational, no reply needed
  - `newsletter` — automated/marketing, skip
  - `calendar` — meeting invite or scheduling request
- Saves results to DB (cache layer)

### 2. Morning briefing
- Generates a short summary (2-4 sentences) per email
- Groups by label, ordered by priority
- Displayed in web UI and saved to DB

### 3. Draft replies
- User selects which email to reply to via web UI
- System generates a draft and saves it to Gmail Drafts folder
- User reviews and sends manually in Gmail

## What it does NOT do
- Does not send emails
- Does not delete or modify emails
- Does not process attachments

## Data storage
- Database: TBD (likely stores classified emails, drafts, briefings)
- Cache: TBD (to avoid re-fetching Gmail on every run)

## Tech stack
- Python, FastAPI (one instance per service)
- Anthropic API (claude-sonnet-4-20250514)
- Gmail API via MCP server (read-only + drafts)
- REST for inter-service communication
- Web UI in the browser
- DB + cache (TBD)

## Success looks like
User opens the browser, sees classified emails grouped by priority,
reads the morning briefing, clicks "Draft reply" on any email,
reviews the draft and sends it manually in Gmail.