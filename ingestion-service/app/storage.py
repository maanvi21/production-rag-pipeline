from io import BytesIO

from minio import Minio

from app.config import settings

_client = Minio(
    settings.minio_endpoint,
    access_key=settings.minio_access_key,
    secret_key=settings.minio_secret_key,
    secure=False,
)


def ensure_bucket() -> None:
    if not _client.bucket_exists(settings.minio_bucket):
        _client.make_bucket(settings.minio_bucket)


def save_file(object_name: str, content: bytes, content_type: str) -> None:
    ensure_bucket()
    _client.put_object(
        settings.minio_bucket,
        object_name,
        data=BytesIO(content),
        length=len(content),
        content_type=content_type,
    )
