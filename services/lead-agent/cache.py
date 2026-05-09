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


def _get(key: str) -> list | None:
    try:
        data = _get_client().get(key)
        return json.loads(data) if data else None
    except Exception as e:
        logger.warning("Redis get failed: %s", e)
        return None


def _set(key: str, value: list) -> None:
    try:
        _get_client().setex(key, TTL, json.dumps(value))
    except Exception as e:
        logger.warning("Redis set failed: %s", e)


def get_emails(days: int, label: str | None) -> list | None:
    return _get(f"lead:emails:days:{days}:label:{label}")


def set_emails(days: int, label: str | None, emails: list) -> None:
    _set(f"lead:emails:days:{days}:label:{label}", emails)
