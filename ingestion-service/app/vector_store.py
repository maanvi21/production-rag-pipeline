import uuid

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from app.config import settings

_client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)


def ensure_collection() -> None:
    if not _client.collection_exists(settings.qdrant_collection):
        _client.create_collection(
            collection_name=settings.qdrant_collection,
            vectors_config=VectorParams(
                size=settings.embedding_dim, distance=Distance.COSINE
            ),
        )


def upsert_chunks(
    document_id: str, filename: str, chunks: list[str], vectors: list[list[float]]
) -> None:
    ensure_collection()
    points = [
        PointStruct(
            id=str(uuid.uuid4()),
            vector=vector,
            payload={
                "document_id": document_id,
                "filename": filename,
                "chunk_index": i,
                "text": chunk,
            },
        )
        for i, (chunk, vector) in enumerate(zip(chunks, vectors))
    ]
    _client.upsert(collection_name=settings.qdrant_collection, points=points)
