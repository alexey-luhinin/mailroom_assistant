import json
import logging
import os

import redis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
TTL = 3600
logger = logging.getLogger(__name__)
_client: redis.Redis | None = None


def _get_client() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.from_url(REDIS_URL, decode_responses=True)
    return _client


def _get(key: str) -> dict | list | None:
    try:
        data = _get_client().get(key)
        return json.loads(data) if data else None
    except Exception as e:
        logger.warning("Redis get failed: %s", e)
        return None


def _set(key: str, value: dict | list) -> None:
    try:
        _get_client().setex(key, TTL, json.dumps(value))
    except Exception as e:
        logger.warning("Redis set failed: %s", e)


def get_job(job_id: str) -> dict | None:
    return _get(f"drafter:job:{job_id}")


def set_job(job_id: str, job: dict) -> None:
    _set(f"drafter:job:{job_id}", job)


def get_drafts(email_id: str | None) -> list | None:
    key = f"drafter:drafts:email:{email_id}" if email_id else "drafter:drafts:all"
    return _get(key)


def set_drafts(email_id: str | None, drafts: list) -> None:
    key = f"drafter:drafts:email:{email_id}" if email_id else "drafter:drafts:all"
    _set(key, drafts)
