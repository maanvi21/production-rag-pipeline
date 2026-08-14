from dataclasses import dataclass

from qdrant_client import QdrantClient

from app.config import settings
from app.embeddings import embed_query

_client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)


@dataclass
class RetrievedChunk:
    text: str
    filename: str
    document_id: str
    chunk_index: int
    score: float


def retrieve(question: str, top_k: int | None = None) -> list[RetrievedChunk]:
    vector = embed_query(question)
    if not _client.collection_exists(settings.qdrant_collection):
        return []

    results = _client.query_points(
        collection_name=settings.qdrant_collection,
        query=vector,
        limit=top_k or settings.top_k,
    ).points

    return [
        RetrievedChunk(
            text=r.payload["text"],
            filename=r.payload["filename"],
            document_id=r.payload["document_id"],
            chunk_index=r.payload["chunk_index"],
            score=r.score,
        )
        for r in results
    ]
