import hashlib
import json

import redis

from app.config import settings

_client = redis.Redis(host=settings.redis_host, port=settings.redis_port, decode_responses=True)


def _cache_key(question: str) -> str:
    normalized = " ".join(question.strip().lower().split())
    digest = hashlib.sha256(normalized.encode()).hexdigest()
    return f"query_cache:{digest}"


def get_cached(question: str) -> dict | None:
    raw = _client.get(_cache_key(question))
    return json.loads(raw) if raw else None


def set_cached(question: str, payload: dict) -> None:
    _client.setex(_cache_key(question), settings.cache_ttl_seconds, json.dumps(payload))
