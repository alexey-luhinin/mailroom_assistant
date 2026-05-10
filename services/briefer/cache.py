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
    return _get(f"briefer:brief:{job_id}")


def set_job(job_id: str, job: dict) -> None:
    _set(f"briefer:brief:{job_id}", job)


def get_latest() -> dict | None:
    return _get("briefer:briefs:latest")


def set_latest(brief: dict) -> None:
    _set("briefer:briefs:latest", brief)


def invalidate_latest() -> None:
    try:
        _get_client().delete("briefer:briefs:latest")
    except Exception as e:
        logger.warning("Redis delete failed: %s", e)


def get_briefs(limit: int) -> list[dict] | None:
    return _get(f"briefer:briefs:limit:{limit}")


def set_briefs(limit: int, briefs: list[dict]) -> None:
    _set(f"briefer:briefs:limit:{limit}", briefs)
