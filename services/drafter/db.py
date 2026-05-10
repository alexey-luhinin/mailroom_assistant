import asyncpg

_CREATE = """
CREATE TABLE IF NOT EXISTS drafts (
    job_id     TEXT PRIMARY KEY,
    email_id   TEXT NOT NULL,
    draft_id   TEXT,
    subject    TEXT,
    body       TEXT,
    language   TEXT,
    status     TEXT NOT NULL DEFAULT 'pending',
    error      TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
)
"""


async def ensure_table(pool: asyncpg.Pool) -> None:
    async with pool.acquire() as conn:
        await conn.execute(_CREATE)


async def create_job(pool: asyncpg.Pool, job_id: str, email_id: str) -> None:
    await pool.execute(
        "INSERT INTO drafts (job_id, email_id, status) VALUES ($1, $2, 'pending')",
        job_id,
        email_id,
    )


async def update_job(
    pool: asyncpg.Pool,
    job_id: str,
    status: str,
    draft_id: str | None = None,
    subject: str | None = None,
    body: str | None = None,
    language: str | None = None,
    error: str | None = None,
) -> None:
    await pool.execute(
        """UPDATE drafts
           SET status=$2, draft_id=$3, subject=$4, body=$5, language=$6, error=$7
           WHERE job_id=$1""",
        job_id,
        status,
        draft_id,
        subject,
        body,
        language,
        error,
    )


async def get_job(pool: asyncpg.Pool, job_id: str) -> dict | None:
    row = await pool.fetchrow("SELECT * FROM drafts WHERE job_id=$1", job_id)
    return _to_dict(row) if row else None


async def get_drafts(pool: asyncpg.Pool, email_id: str | None = None) -> list[dict]:
    if email_id:
        rows = await pool.fetch(
            "SELECT * FROM drafts WHERE status='done' AND email_id=$1 ORDER BY created_at DESC",
            email_id,
        )
    else:
        rows = await pool.fetch(
            "SELECT * FROM drafts WHERE status='done' ORDER BY created_at DESC"
        )
    return [_to_dict(r) for r in rows]


def _to_dict(row: asyncpg.Record) -> dict:
    return {
        "job_id":     row["job_id"],
        "email_id":   row["email_id"],
        "draft_id":   row["draft_id"],
        "subject":    row["subject"],
        "body":       row["body"],
        "language":   row["language"],
        "status":     row["status"],
        "error":      row["error"],
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
    }
