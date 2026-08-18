from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    qdrant_host: str = "qdrant"
    qdrant_port: int = 6333
    qdrant_url: str | None = None
    qdrant_api_key: str | None = None
    qdrant_collection: str = "documents"

    minio_endpoint: str = "minio:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "raw-documents"

    redis_host: str = "redis"
    redis_port: int = 6379
    redis_url: str | None = None
    stream_name: str = "ingestion_jobs"
    consumer_group: str = "ingestion_workers"

    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dim: int = 384

    chunk_size: int = 800
    chunk_overlap: int = 150

    # When true, ingestion-service runs the stream-consumer loop in a
    # background thread instead of relying on a separate ingestion-worker
    # process/service. Used on deploy targets where a second long-running
    # service isn't free (e.g. Render's Background Workers have no free tier).
    run_worker_inline: bool = False

    class Config:
        env_file = ".env"


settings = Settings()
