import base64

import redis

from app.config import settings

_client = (
    redis.from_url(settings.redis_url, decode_responses=True)
    if settings.redis_url
    else redis.Redis(host=settings.redis_host, port=settings.redis_port, decode_responses=True)
)

# Raw file bytes only need to survive the handoff from the upload request to
# whenever the worker picks the job up — not long-term storage. Reusing Redis
# (already required for the job queue) avoids a third piece of infra.
FILE_TTL_SECONDS = 3600


def save_file(object_name: str, content: bytes) -> None:
    _client.setex(f"file:{object_name}", FILE_TTL_SECONDS, base64.b64encode(content))


def get_file(object_name: str) -> bytes:
    raw = _client.get(f"file:{object_name}")
    if raw is None:
        raise FileNotFoundError(f"{object_name} not found (may have expired)")
    return base64.b64decode(raw)
