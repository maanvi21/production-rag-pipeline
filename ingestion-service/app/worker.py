import redis

from app.chunking import chunk_text
from app.config import settings
from app.embeddings import embed_texts
from app.extract import extract_text
from app.queue import GROUP, STREAM, ensure_group, set_status
from app.storage import get_file
from app.vector_store import upsert_chunks

_client = redis.Redis(host=settings.redis_host, port=settings.redis_port, decode_responses=True)

CONSUMER_NAME = "ingestion-worker"


def process_job(fields: dict) -> None:
    document_id = fields["document_id"]
    filename = fields["filename"]

    set_status(document_id, "processing", filename=filename)
    try:
        content = get_file(f"{document_id}/{filename}")
        text = extract_text(filename, content)
        if not text.strip():
            raise ValueError("No extractable text in file")

        chunks = chunk_text(text)
        vectors = embed_texts(chunks)
        upsert_chunks(document_id, filename, chunks, vectors)

        set_status(document_id, "done", filename=filename, chunks_indexed=len(chunks))
    except Exception as e:
        set_status(document_id, "failed", filename=filename, error=str(e))


def run() -> None:
    ensure_group()
    print(f"[worker] listening on stream '{STREAM}' as consumer '{CONSUMER_NAME}'", flush=True)

    while True:
        response = _client.xreadgroup(GROUP, CONSUMER_NAME, {STREAM: ">"}, count=1, block=5000)
        if not response:
            continue

        for _stream, messages in response:
            for message_id, fields in messages:
                process_job(fields)
                _client.xack(STREAM, GROUP, message_id)


if __name__ == "__main__":
    run()
