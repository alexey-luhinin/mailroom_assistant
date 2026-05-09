# E-Mail Assistant

## Read these docs first
Before writing any code, read the following documents in order:

1. `docs/SPEC.md` — what the system does and what it does NOT do
2. `docs/ARCHITECTURE.md` — services, ports, data flows, directory structure
3. `docs/agents/sorter.md` — Sorter agent role and output format
4. `docs/agents/drafter.md` — Drafter agent role and output format
5. `docs/agents/briefer.md` — Briefer agent role and output format
6. `docs/api/lead-agent-api.md` — Lead Agent REST API spec
7. `docs/api/sorter-api.md` — Sorter REST API spec
8. `docs/api/drafter-api.md` — Drafter REST API spec
9. `docs/api/briefer-api.md` — Briefer REST API spec

## Tech stack
- Python + FastAPI for all services
- Anthropic API, model: `claude-sonnet-4-20250514`
- PostgreSQL for persistence
- Redis for caching (TTL: 1h)
- Docker + docker-compose for local setup
- React + Vite for Web UI

## Environment variables
All secrets are in `config/.env`. Load with:
```python
from dotenv import load_dotenv
load_dotenv("config/.env")
```

Required variables:
```
ANTHROPIC_API_KEY=
GMAIL_CREDENTIALS_FILE=config/credentials.json
POSTGRES_URL=postgresql://user:pass@localhost:5432/mailroom
REDIS_URL=redis://localhost:6379
BRIEF_SCHEDULE=0 8 * * *
```

## Directory structure
Follow this exactly:
```
mailroom/
├── docs/
│   ├── SPEC.md
│   ├── ARCHITECTURE.md
│   ├── agents/
│   │   ├── sorter.md
│   │   ├── drafter.md
│   │   └── briefer.md
│   └── api/
│       ├── lead-agent-api.md
│       ├── sorter-api.md
│       ├── drafter-api.md
│       └── briefer-api.md
├── CLAUDE.md
├── docker-compose.yml
├── .env.example
├── .gitignore
└── services/
    ├── lead-agent/
    ├── sorter/
    ├── drafter/
    ├── critic/
    ├── briefer/
    ├── mcp-server/
    └── web-ui/
```

Each service follows this internal structure:
```
services/sorter/
├── Dockerfile
├── requirements.txt
├── main.py        ← FastAPI app entry point
├── agent.py       ← Claude API logic
├── db.py          ← PostgreSQL queries
├── cache.py       ← Redis logic
└── models.py      ← Pydantic models
```

## Rules
- Never send emails — only save to Gmail Drafts
- Never delete or modify emails
- Always load `config/.env` before accessing env vars
- Every service must have a `GET /health` endpoint
- Lead Agent is the only orchestrator — services never call each other directly
- All inter-service communication is HTTP REST
- Follow API specs exactly — do not add or remove fields

## How to start
Implement services in this order:
1. `services/mcp-server/` — Gmail gateway first, everything depends on it
2. `services/sorter/` — first agent, simplest workflow
3. `services/lead-agent/` — orchestrator
4. `services/briefer/` — morning briefing
5. `services/drafter/` — draft replies
6. `services/web-ui/` — browser interface last
