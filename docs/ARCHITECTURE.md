# E-Mail Assistant — Architecture

## Overview

```
Browser (Web UI)
      │
      ▼
Lead Agent :8000          ← orchestrates everything
      │
      ├──▶ Sorter     :8001
      ├──▶ Researcher :8002
      ├──▶ Drafter    :8003
      ├──▶ Critic     :8004
      └──▶ Briefer    :8005
                │
                ▼
          MCP Server :8006
                │
                ▼
           Gmail API
```

## Services

| Service    | Port | Tech             | Responsibility                |
|------------|------|------------------|-------------------------------|
| Web UI     | 3000 | React + Vite     | Browser interface             |
| Lead Agent | 8000 | FastAPI + Claude | Orchestrates all agents       |
| Sorter     | 8001 | FastAPI + Claude | Classifies inbox emails       |
| Researcher | 8002 | FastAPI + Claude | Enriches email context        |
| Drafter    | 8003 | FastAPI + Claude | Writes reply drafts           |
| Critic     | 8004 | FastAPI + Claude | Reviews drafts before saving  |
| Briefer    | 8005 | FastAPI + Claude | Generates morning briefing    |
| MCP Server | 8006 | Python MCP       | Gmail read + drafts gateway   |
| Database   | 5432 | PostgreSQL       | Emails, drafts, briefings     |
| Cache      | 6379 | Redis            | Gmail API response cache      |

## Data flows

### 1. Morning run
```
User clicks "Run"
  → Lead Agent
  → Sorter fetches + classifies emails via MCP Server
  → Sorter saves to PostgreSQL
  → Briefer reads from DB, generates summaries
  → Web UI displays briefing
```

### 2. Draft reply
```
User selects email in Web UI
  → Lead Agent
  → Researcher fetches context
  → Drafter writes draft
  → Critic reviews
  → MCP Server saves to Gmail Drafts
  → Web UI shows draft
```

## Rules
- Lead Agent is the only orchestrator
- Agents never call each other directly
- Nothing is sent without user action in Gmail

## Persistence
- PostgreSQL — emails, drafts, briefing history
- Redis — Gmail cache (TTL: 1h)

## Local setup
- All services via docker-compose
- One `.env` in root for all credentials

## Directory structure
```
mailroom/
├── docs/
│   ├── SPEC.md
│   ├── ARCHITECTURE.md
│   ├── agents/
│   └── api/
├── CLAUDE.md
├── docker-compose.yml
├── .env.example
└── services/
    ├── lead-agent/
    ├── sorter/
    ├── researcher/
    ├── drafter/
    ├── critic/
    ├── briefer/
    ├── mcp-server/
    └── web-ui/
```