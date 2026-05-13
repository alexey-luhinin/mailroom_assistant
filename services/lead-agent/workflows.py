import asyncio
import logging
import os
from datetime import datetime, timezone

import asyncpg
import httpx

import db

logger = logging.getLogger(__name__)

SORTER_URL     = os.getenv("SORTER_URL",     "http://localhost:8001")
RESEARCHER_URL = os.getenv("RESEARCHER_URL", "http://localhost:8002")
DRAFTER_URL    = os.getenv("DRAFTER_URL",    "http://localhost:8003")
CRITIC_URL     = os.getenv("CRITIC_URL",     "http://localhost:8004")
BRIEFER_URL    = os.getenv("BRIEFER_URL",    "http://localhost:8005")
MCP_URL        = os.getenv("MCP_SERVER_URL", "http://localhost:8006")

_T_SHORT  = 10.0
_T_MEDIUM = 30.0
_T_DRAFT  = 60.0
_T_SORT   = 120.0


async def run_morning(pool: asyncpg.Pool, job_id: str, days: int) -> None:
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{SORTER_URL}/sort", json={"days": days}, timeout=_T_SORT
            )
            resp.raise_for_status()
        sort = resp.json()

        await db.update_run_job(
            pool, job_id,
            step="briefing",
            emails_classified=sort["new"],
            emails_skipped=sort["skipped"],
        )

        briefing = await get_or_create_brief(days)

        await db.update_run_job(
            pool, job_id,
            status="done",
            step="done",
            briefing={"summary": briefing["summary"], "content": briefing["content"]},
        )

    except Exception as e:
        logger.error("Run job %s failed: %s", job_id, e)
        await db.update_run_job(pool, job_id, status="failed", step="failed", error=str(e))


async def get_or_create_brief(days: int) -> dict:
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{BRIEFER_URL}/briefs/latest", timeout=_T_SHORT)
            logger.info("Latest brief status: %s", resp.status_code)
            if resp.status_code == 200:
                latest = resp.json()
                logger.info("Latest brief response: %s", latest)
                created_at = latest.get("created_at")
                if created_at:
                    age = datetime.now(timezone.utc) - datetime.fromisoformat(created_at)
                    logger.info("Latest briefing created_at=%s age=%.0fs", created_at, age.total_seconds())
                    if age.total_seconds() < 3600:
                        logger.info("Reusing briefing from %s (age %.0fs)", created_at, age.total_seconds())
                        return latest
        except Exception as e:
            logger.warning("Could not fetch latest brief, generating new one: %s", e)

        resp = await client.post(f"{BRIEFER_URL}/brief", json={"days": days}, timeout=_T_MEDIUM)
        resp.raise_for_status()

    briefing = await _poll_brief(resp.json()["job_id"])
    if briefing["status"] == "failed":
        raise RuntimeError(briefing.get("error", "Briefing failed."))
    return briefing


async def _poll_brief(brief_job_id: str, timeout: int = 300) -> dict:
    async with httpx.AsyncClient() as client:
        for _ in range(timeout // 2):
            resp = await client.get(
                f"{BRIEFER_URL}/brief/{brief_job_id}", timeout=_T_SHORT
            )
            resp.raise_for_status()
            data = resp.json()
            if data["status"] in ("done", "failed"):
                return data
            await asyncio.sleep(2)
    raise TimeoutError(f"Brief job {brief_job_id} timed out after {timeout}s.")


async def _poll_drafter(drafter_job_id: str, timeout: int = 120) -> dict:
    async with httpx.AsyncClient() as client:
        for _ in range(timeout // 2):
            resp = await client.get(
                f"{DRAFTER_URL}/draft/{drafter_job_id}", timeout=_T_SHORT
            )
            resp.raise_for_status()
            data = resp.json()
            if data["status"] in ("done", "failed"):
                return data
            await asyncio.sleep(2)
    raise TimeoutError(f"Drafter job {drafter_job_id} timed out after {timeout}s.")


async def run_draft(pool: asyncpg.Pool, job_id: str, email_id: str, instructions: str) -> None:
    try:
        context: dict = {}
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{RESEARCHER_URL}/research",
                    json={"email_id": email_id},
                    timeout=_T_DRAFT,
                )
                resp.raise_for_status()
            context = resp.json()
        except (httpx.ConnectError, httpx.ConnectTimeout):
            logger.warning("Researcher unavailable, skipping for draft job %s", job_id)

        best_draft: dict | None = None
        best_score: int = -1
        draft: dict = {}
        current_instructions = instructions
        _MAX_ITER = 3

        for iteration in range(1, _MAX_ITER + 1):
            await db.update_draft_job(pool, job_id, step="drafting")

            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{DRAFTER_URL}/draft",
                    json={"email_id": email_id, "instructions": current_instructions, "context": context},
                    timeout=_T_DRAFT,
                )
                resp.raise_for_status()
            drafter_job_id = resp.json()["job_id"]

            drafter_result = await _poll_drafter(drafter_job_id)
            if drafter_result["status"] == "failed":
                raise RuntimeError(drafter_result.get("error", "Drafting failed."))

            draft = {
                "draft_id": drafter_result.get("draft_id"),
                "subject":  drafter_result.get("subject"),
                "body":     drafter_result.get("body"),
                "language": drafter_result.get("language"),
            }

            await db.update_draft_job(pool, job_id, step="reviewing")

            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.post(
                        f"{CRITIC_URL}/review",
                        json={
                            "draft": {
                                "subject":  draft["subject"],
                                "body":     draft["body"],
                                "language": draft["language"],
                            },
                            "instructions": instructions,
                            "iteration": iteration,
                        },
                        timeout=_T_DRAFT,
                    )
                    resp.raise_for_status()
                review = resp.json()
            except (httpx.ConnectError, httpx.ConnectTimeout, httpx.HTTPStatusError) as e:
                logger.warning("Critic unavailable at iteration %d for job %s: %s", iteration, job_id, e)
                best_draft = draft
                break

            score = review.get("score", 0)
            approved = review.get("approved", False)
            feedback = review.get("feedback", "")

            logger.info("Draft job %s iteration %d: score=%d approved=%s", job_id, iteration, score, approved)

            if score > best_score:
                best_score = score
                best_draft = draft

            if approved:
                break

            if iteration < _MAX_ITER:
                current_instructions = (
                    f"{instructions}\n\nCritic feedback (iteration {iteration}): {feedback}"
                    if instructions
                    else f"Critic feedback (iteration {iteration}): {feedback}"
                )

        await db.update_draft_job(pool, job_id, status="done", step="done", draft=best_draft or draft)

    except Exception as e:
        logger.error("Draft job %s failed: %s", job_id, e)
        await db.update_draft_job(pool, job_id, status="failed", step="failed", error=str(e))
