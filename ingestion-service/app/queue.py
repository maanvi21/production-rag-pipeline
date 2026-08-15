import redis

from app.config import settings

_client = (
    redis.from_url(settings.redis_url, decode_responses=True)
    if settings.redis_url
    else redis.Redis(host=settings.redis_host, port=settings.redis_port, decode_responses=True)
)

STREAM = settings.stream_name
GROUP = settings.consumer_group


def ensure_group() -> None:
    """Create the consumer group (and stream, if missing) starting from the beginning."""
    try:
        _client.xgroup_create(STREAM, GROUP, id="0", mkstream=True)
    except redis.exceptions.ResponseError as e:
        if "BUSYGROUP" not in str(e):
            raise


def enqueue_job(document_id: str, filename: str, content_type: str) -> None:
    _client.xadd(
        STREAM,
        {"document_id": document_id, "filename": filename, "content_type": content_type},
    )


def set_status(document_id: str, status: str, **fields) -> None:
    mapping = {"status": status, **{k: str(v) for k, v in fields.items()}}
    _client.hset(f"status:{document_id}", mapping=mapping)


def get_status(document_id: str) -> dict | None:
    data = _client.hgetall(f"status:{document_id}")
    return data or None
