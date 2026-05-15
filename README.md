# Mailroom — AI Inbox Triage Assistant

A microservices-based AI assistant that classifies your Gmail inbox, generates
a morning briefing, drafts replies, and surfaces unsubscribe candidates —
all controlled from a React web UI. Nothing is ever auto-sent.

---

## What it does

- **Inbox sync** — fetches emails for the last 1–30 days and classifies each
  one: `urgent`, `action_needed`, `calendar`, `fyi`, `newsletter`, `promo`, `spam`
- **Morning briefing** — generates a concise summary grouped by priority,
  including today's calendar events
- **Draft reply** — Researcher enriches context, Drafter writes a reply,
  Critic reviews it; the result lands in Gmail Drafts, never auto-sent
- **Cleanup** — surfaces newsletter and promo senders you never open and
  extracts their unsubscribe links; one-click to act, never automatic
- **Calendar** — shows upcoming Google Calendar events inline

## Architecture

```
Browser (React/Vite :3000)
        │
        ▼
Lead Agent :8000          ← single orchestrator
        │
        ├──▶ Sorter      :8001   classify emails
        ├──▶ Researcher  :8002   enrich context
        ├──▶ Drafter     :8003   write reply drafts
        ├──▶ Critic      :8004   review drafts
        ├──▶ Briefer     :8005   morning summary
        └──▶ Unsubscribe :8007   newsletter cleanup
                │
                ▼
          MCP Server :8006       Gmail + Google Calendar gateway
                │
                ▼
        Gmail API / Google Calendar API

PostgreSQL :5432   — emails, drafts, briefing history
Redis      :6379   — Gmail API cache (TTL: 1h)
```

All inter-service communication is HTTP REST. Services never call each other
directly — only Lead Agent orchestrates.

## Tech stack

| Layer       | Technology                          |
|-------------|-------------------------------------|
| Services    | Python 3.13 + FastAPI               |
| AI          | Anthropic API `claude-sonnet-4-5` |
| Storage     | PostgreSQL 16                       |
| Cache       | Redis 7                             |
| Frontend    | React + Vite (nginx container)      |
| Infra       | Docker + docker-compose             |
| Gmail/Cal   | Google OAuth 2.0                    |

## Quickstart

### Prerequisites
- Docker Desktop
- Google Cloud project with Gmail API and Google Calendar API enabled
- OAuth 2.0 credentials (`credentials.json`) for your Gmail account
- Anthropic API key

### Setup

```bash
git clone <repo>
cd cp_mailroom

# Add credentials
cp .env.example config/.env
# Edit config/.env — set ANTHROPIC_API_KEY
# Place your OAuth credentials.json in config/

# First run: mint OAuth tokens
python scripts/oauth_setup.py   # opens browser, saves token files to config/

# Start everything
docker compose up --build
```

Open [http://localhost:3000](http://localhost:3000).

Click **Sync inbox** to classify emails, **Generate briefing** to run the
morning summary. To draft a reply, open an email card and click **Draft reply**
— the draft appears in your Gmail Drafts folder.

## Repo layout

```
services/
├── lead-agent/     FastAPI orchestrator (port 8000)
├── sorter/         email classifier (port 8001)
├── researcher/     context enrichment (port 8002)
├── drafter/        reply writer (port 8003)
├── critic/         draft reviewer (port 8004)
├── briefer/        morning briefing (port 8005)
├── mcp-server/     Gmail + Calendar gateway (port 8006)
├── unsubscribe/    newsletter cleanup (port 8007)
└── web-ui/         React frontend (port 3000)
config/             credentials.json, .env (gitignored)
docs/               SPEC, ARCHITECTURE, per-agent and per-API specs
```

Each service follows the same internal structure:
```
services/<name>/
├── Dockerfile
├── requirements.txt
├── main.py     FastAPI app + routes
├── agent.py    Claude API logic (where applicable)
├── db.py       PostgreSQL queries
├── cache.py    Redis logic
└── models.py   Pydantic models
```

## Rules

- **Never sends email** — only saves to Gmail Drafts
- **Never deletes or modifies emails**
- **Never unsubscribes automatically** — only surfaces candidates
- All secrets live in `config/.env`, never committed

## License

MIT — see `LICENSE`.
