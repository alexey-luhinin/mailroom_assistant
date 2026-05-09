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


def get_emails(days: int) -> list[dict] | None:
    return _get(f"mcp:emails:days:{days}")


def set_emails(days: int, emails: list[dict]) -> None:
    _set(f"mcp:emails:days:{days}", emails)


def get_email(email_id: str) -> dict | None:
    return _get(f"mcp:email:{email_id}")


def set_email(email_id: str, email: dict) -> None:
    _set(f"mcp:email:{email_id}", email)
