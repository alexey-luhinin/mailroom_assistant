from datetime import datetime, timedelta, timezone

import asyncpg

_CREATE = """
CREATE TABLE IF NOT EXISTS emails (
    id            TEXT PRIMARY KEY,
    from_addr     TEXT NOT NULL,
    subject       TEXT NOT NULL,
    date          TEXT NOT NULL,
    label         TEXT NOT NULL,
    reason        TEXT NOT NULL,
    priority      INTEGER NOT NULL,
    classified_at TIMESTAMPTZ DEFAULT NOW()
)
"""


async def ensure_table(pool: asyncpg.Pool) -> None:
    async with pool.acquire() as conn:
        await conn.execute(_CREATE)


async def get_classified_ids(pool: asyncpg.Pool, ids: list[str]) -> set[str]:
    rows = await pool.fetch("SELECT id FROM emails WHERE id = ANY($1)", ids)
    return {r["id"] for r in rows}


async def save_emails(pool: asyncpg.Pool, emails: list[dict]) -> None:
    async with pool.acquire() as conn:
        await conn.executemany(
            """INSERT INTO emails (id, from_addr, subject, date, label, reason, priority)
               VALUES ($1, $2, $3, $4, $5, $6, $7)
               ON CONFLICT (id) DO NOTHING""",
            [
                (e["id"], e["from"], e["subject"], e["date"],
                 e["label"], e["reason"], e["priority"])
                for e in emails
            ],
        )


async def get_emails_by_ids(pool: asyncpg.Pool, ids: list[str]) -> list[dict]:
    rows = await pool.fetch(
        "SELECT * FROM emails WHERE id = ANY($1) ORDER BY priority ASC", ids
    )
    return [_to_dict(r) for r in rows]


async def get_emails(
    pool: asyncpg.Pool,
    days: int,
    label: str | None,
    until: datetime | None = None,
) -> list[dict]:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    conditions = ["classified_at >= $1"]
    params: list = [since]
    if until is not None:
        params.append(until)
        conditions.append(f"classified_at < ${len(params)}")
    if label:
        params.append(label)
        conditions.append(f"label = ${len(params)}")
    where = " AND ".join(conditions)
    rows = await pool.fetch(
        f"SELECT * FROM emails WHERE {where} ORDER BY priority ASC",
        *params,
    )
    return [_to_dict(r) for r in rows]


async def get_emails_from(
    pool: asyncpg.Pool, since: datetime, label: str | None
) -> list[dict]:
    if label:
        rows = await pool.fetch(
            "SELECT * FROM emails WHERE classified_at >= $1 AND label = $2 ORDER BY priority ASC",
            since, label,
        )
    else:
        rows = await pool.fetch(
            "SELECT * FROM emails WHERE classified_at >= $1 ORDER BY priority ASC",
            since,
        )
    return [_to_dict(r) for r in rows]


def _to_dict(row: asyncpg.Record) -> dict:
    return {
        "id":       row["id"],
        "from":     row["from_addr"],
        "subject":  row["subject"],
        "date":     row["date"],
        "label":    row["label"],
        "reason":   row["reason"],
        "priority": row["priority"],
    }
