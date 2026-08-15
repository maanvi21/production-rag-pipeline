from dataclasses import dataclass

from app.bm25_index import IndexedChunk, bm25_search
from app.clients import get_qdrant_client
from app.config import settings
from app.embeddings import embed_query
from app.rerank import rerank

_client = get_qdrant_client()


@dataclass
class RetrievedChunk:
    text: str
    filename: str
    document_id: str
    chunk_index: int
    score: float


def _vector_search(question: str, limit: int) -> list[IndexedChunk]:
    if not _client.collection_exists(settings.qdrant_collection):
        return []

    vector = embed_query(question)
    results = _client.query_points(
        collection_name=settings.qdrant_collection, query=vector, limit=limit
    ).points

    return [
        IndexedChunk(
            text=r.payload["text"],
            filename=r.payload["filename"],
            document_id=r.payload["document_id"],
            chunk_index=r.payload["chunk_index"],
        )
        for r in results
    ]


def retrieve(question: str, top_k: int | None = None) -> list[RetrievedChunk]:
    k = top_k or settings.top_k
    n = settings.hybrid_candidates

    # Vector search catches semantic similarity; BM25 catches exact keyword/ID
    # matches vector search tends to miss. Union the two candidate pools, dedupe,
    # then let a cross-encoder rerank the merge into a final relevance order.
    vector_hits = _vector_search(question, n)
    keyword_hits = bm25_search(question, n)

    seen: set[tuple[str, int]] = set()
    candidates: list[IndexedChunk] = []
    for chunk in vector_hits + keyword_hits:
        key = (chunk.document_id, chunk.chunk_index)
        if key not in seen:
            seen.add(key)
            candidates.append(chunk)

    if not candidates:
        return []

    reranked = rerank(question, candidates, k)
    return [
        RetrievedChunk(
            text=chunk.text,
            filename=chunk.filename,
            document_id=chunk.document_id,
            chunk_index=chunk.chunk_index,
            score=score,
        )
        for chunk, score in reranked
    ]
