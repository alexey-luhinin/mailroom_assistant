import json
from datetime import datetime, timedelta, timezone

import asyncpg

_CREATE_JOBS = """
CREATE TABLE IF NOT EXISTS unsubscribe_jobs (
    job_id     TEXT PRIMARY KEY,
    status     TEXT NOT NULL DEFAULT 'pending',
    days       INTEGER NOT NULL,
    result     TEXT,
    error      TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
)
"""


async def ensure_table(pool: asyncpg.Pool) -> None:
    async with pool.acquire() as conn:
        await conn.execute(_CREATE_JOBS)


async def create_job(pool: asyncpg.Pool, job_id: str, days: int) -> None:
    await pool.execute(
        "INSERT INTO unsubscribe_jobs (job_id, days) VALUES ($1, $2)",
        job_id, days,
    )


async def update_job(
    pool: asyncpg.Pool,
    job_id: str,
    status: str | None = None,
    result: dict | None = None,
    error: str | None = None,
) -> None:
    fields, vals = [], [job_id]
    for col, val in (
        ("status", status),
        ("result", json.dumps(result) if result is not None else None),
        ("error", error),
    ):
        if val is not None:
            fields.append(f"{col}=${len(vals) + 1}")
            vals.append(val)
    if fields:
        await pool.execute(
            f"UPDATE unsubscribe_jobs SET {', '.join(fields)} WHERE job_id=$1", *vals
        )


async def get_job(pool: asyncpg.Pool, job_id: str) -> dict | None:
    row = await pool.fetchrow(
        "SELECT * FROM unsubscribe_jobs WHERE job_id=$1", job_id
    )
    return _to_dict(row) if row else None


async def get_latest_job(pool: asyncpg.Pool) -> dict | None:
    row = await pool.fetchrow(
        "SELECT * FROM unsubscribe_jobs WHERE status='done' ORDER BY created_at DESC LIMIT 1"
    )
    return _to_dict(row) if row else None


async def get_newsletter_promo_emails(pool: asyncpg.Pool, days: int) -> list[dict]:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    rows = await pool.fetch(
        """SELECT id, from_addr, subject, date
           FROM emails
           WHERE label IN ('newsletter', 'promo')
             AND date::timestamptz >= $1""",
        since,
    )
    return [
        {"id": r["id"], "from": r["from_addr"], "subject": r["subject"], "date": r["date"]}
        for r in rows
    ]


def _to_dict(row: asyncpg.Record) -> dict:
    result = row["result"]
    if isinstance(result, str):
        result = json.loads(result)
    d: dict = {
        "job_id": row["job_id"],
        "status": row["status"],
        "days":   row["days"],
        "error":  row["error"],
    }
    if result:
        d["total_senders"] = result.get("total_senders")
        d["candidates"]    = result.get("candidates")
    return d
