import json
from datetime import datetime, timedelta, timezone

import asyncpg

_CREATE_BRIEFINGS = """
CREATE TABLE IF NOT EXISTS briefings (
    job_id     TEXT PRIMARY KEY,
    status     TEXT NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    summary    TEXT,
    content    TEXT,
    error      TEXT
)
"""


async def ensure_table(pool: asyncpg.Pool) -> None:
    async with pool.acquire() as conn:
        await conn.execute(_CREATE_BRIEFINGS)


async def create_job(pool: asyncpg.Pool, job_id: str) -> None:
    await pool.execute(
        "INSERT INTO briefings (job_id, status) VALUES ($1, 'pending')",
        job_id,
    )


async def update_job(
    pool: asyncpg.Pool,
    job_id: str,
    status: str,
    content: str | None = None,
    summary: dict | None = None,
    error: str | None = None,
) -> None:
    await pool.execute(
        """UPDATE briefings
           SET status=$2, content=$3, summary=$4, error=$5
           WHERE job_id=$1""",
        job_id,
        status,
        content,
        json.dumps(summary) if summary else None,
        error,
    )


async def get_job(pool: asyncpg.Pool, job_id: str) -> dict | None:
    row = await pool.fetchrow("SELECT * FROM briefings WHERE job_id=$1", job_id)
    return _to_dict(row) if row else None


async def get_briefs(pool: asyncpg.Pool, limit: int) -> list[dict]:
    rows = await pool.fetch(
        "SELECT * FROM briefings WHERE status='done' ORDER BY created_at DESC LIMIT $1",
        limit,
    )
    return [_to_dict(r) for r in rows]


async def get_latest(pool: asyncpg.Pool) -> dict | None:
    row = await pool.fetchrow(
        "SELECT * FROM briefings WHERE status='done' ORDER BY created_at DESC LIMIT 1"
    )
    return _to_dict(row) if row else None


async def get_today_emails(pool: asyncpg.Pool, days: int) -> list[dict]:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    rows = await pool.fetch(
        "SELECT * FROM emails WHERE classified_at >= $1 ORDER BY priority ASC",
        since,
    )
    return [_email_to_dict(r) for r in rows]


async def get_unresolved_emails(pool: asyncpg.Pool, days: int) -> list[dict]:
    """Return urgent/action_needed emails from before the `days` window with no draft saved."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    try:
        rows = await pool.fetch(
            """SELECT e.* FROM emails e
               LEFT JOIN drafts d ON d.email_id = e.id
               WHERE e.classified_at < $1
                 AND e.label IN ('urgent', 'action_needed')
                 AND d.email_id IS NULL
               ORDER BY e.priority ASC""",
            cutoff,
        )
    except asyncpg.exceptions.UndefinedTableError:
        # drafts table not yet created (drafter not deployed)
        rows = await pool.fetch(
            """SELECT * FROM emails
               WHERE classified_at < $1 AND label IN ('urgent', 'action_needed')
               ORDER BY priority ASC""",
            cutoff,
        )
    return [_email_to_dict(r) for r in rows]


def _email_to_dict(row: asyncpg.Record) -> dict:
    return {
        "id":       row["id"],
        "from":     row["from_addr"],
        "subject":  row["subject"],
        "date":     row["date"],
        "label":    row["label"],
        "reason":   row["reason"],
        "priority": row["priority"],
    }


def _to_dict(row: asyncpg.Record) -> dict:
    summary = row["summary"]
    if isinstance(summary, str):
        summary = json.loads(summary)
    return {
        "job_id":     row["job_id"],
        "status":     row["status"],
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        "summary":    summary,
        "content":    row["content"],
        "error":      row["error"],
    }
