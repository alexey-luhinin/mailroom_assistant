import json

import asyncpg

_CREATE_RUN_JOBS = """
CREATE TABLE IF NOT EXISTS run_jobs (
    job_id            TEXT PRIMARY KEY,
    status            TEXT NOT NULL DEFAULT 'pending',
    step              TEXT NOT NULL DEFAULT 'sorting',
    days              INTEGER NOT NULL,
    emails_classified INTEGER,
    emails_skipped    INTEGER,
    briefing          TEXT,
    error             TEXT,
    created_at        TIMESTAMPTZ DEFAULT NOW()
)
"""

_CREATE_DRAFT_JOBS = """
CREATE TABLE IF NOT EXISTS draft_jobs (
    job_id       TEXT PRIMARY KEY,
    status       TEXT NOT NULL DEFAULT 'pending',
    step         TEXT NOT NULL DEFAULT 'researching',
    email_id     TEXT NOT NULL,
    instructions TEXT,
    draft        TEXT,
    error        TEXT,
    created_at   TIMESTAMPTZ DEFAULT NOW()
)
"""


async def ensure_tables(pool: asyncpg.Pool) -> None:
    async with pool.acquire() as conn:
        await conn.execute(_CREATE_RUN_JOBS)
        await conn.execute(_CREATE_DRAFT_JOBS)


async def create_run_job(pool: asyncpg.Pool, job_id: str, days: int) -> None:
    await pool.execute(
        "INSERT INTO run_jobs (job_id, days) VALUES ($1, $2)",
        job_id, days,
    )


async def update_run_job(
    pool: asyncpg.Pool,
    job_id: str,
    status: str | None = None,
    step: str | None = None,
    emails_classified: int | None = None,
    emails_skipped: int | None = None,
    briefing: dict | None = None,
    error: str | None = None,
) -> None:
    fields, vals = [], [job_id]
    for col, val in (
        ("status", status),
        ("step", step),
        ("emails_classified", emails_classified),
        ("emails_skipped", emails_skipped),
        ("briefing", json.dumps(briefing) if briefing is not None else None),
        ("error", error),
    ):
        if val is not None:
            fields.append(f"{col}=${len(vals) + 1}")
            vals.append(val)
    if fields:
        await pool.execute(
            f"UPDATE run_jobs SET {', '.join(fields)} WHERE job_id=$1", *vals
        )


async def get_run_job(pool: asyncpg.Pool, job_id: str) -> dict | None:
    row = await pool.fetchrow("SELECT * FROM run_jobs WHERE job_id=$1", job_id)
    return _run_to_dict(row) if row else None


async def create_draft_job(
    pool: asyncpg.Pool, job_id: str, email_id: str, instructions: str
) -> None:
    await pool.execute(
        "INSERT INTO draft_jobs (job_id, email_id, instructions) VALUES ($1, $2, $3)",
        job_id, email_id, instructions,
    )


async def update_draft_job(
    pool: asyncpg.Pool,
    job_id: str,
    status: str | None = None,
    step: str | None = None,
    draft: dict | None = None,
    error: str | None = None,
) -> None:
    fields, vals = [], [job_id]
    for col, val in (
        ("status", status),
        ("step", step),
        ("draft", json.dumps(draft) if draft is not None else None),
        ("error", error),
    ):
        if val is not None:
            fields.append(f"{col}=${len(vals) + 1}")
            vals.append(val)
    if fields:
        await pool.execute(
            f"UPDATE draft_jobs SET {', '.join(fields)} WHERE job_id=$1", *vals
        )


async def get_draft_job(pool: asyncpg.Pool, job_id: str) -> dict | None:
    row = await pool.fetchrow("SELECT * FROM draft_jobs WHERE job_id=$1", job_id)
    return _draft_to_dict(row) if row else None


def _run_to_dict(row: asyncpg.Record) -> dict:
    briefing = row["briefing"]
    if isinstance(briefing, str):
        briefing = json.loads(briefing)
    return {
        "job_id":            row["job_id"],
        "status":            row["status"],
        "step":              row["step"],
        "emails_classified": row["emails_classified"],
        "emails_skipped":    row["emails_skipped"],
        "briefing":          briefing,
        "error":             row["error"],
    }


def _draft_to_dict(row: asyncpg.Record) -> dict:
    draft = row["draft"]
    if isinstance(draft, str):
        draft = json.loads(draft)
    return {
        "job_id": row["job_id"],
        "status": row["status"],
        "step":   row["step"],
        "draft":  draft,
        "error":  row["error"],
    }
