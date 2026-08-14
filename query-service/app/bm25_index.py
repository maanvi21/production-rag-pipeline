import time
from dataclasses import dataclass

from qdrant_client import QdrantClient
from rank_bm25 import BM25Okapi

from app.config import settings

_client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)

_cache: dict = {"chunks": None, "bm25": None, "loaded_at": 0.0}


@dataclass
class IndexedChunk:
    text: str
    filename: str
    document_id: str
    chunk_index: int


def _load_all_chunks() -> list[IndexedChunk]:
    if not _client.collection_exists(settings.qdrant_collection):
        return []

    chunks: list[IndexedChunk] = []
    offset = None
    while True:
        points, offset = _client.scroll(
            collection_name=settings.qdrant_collection,
            limit=256,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )
        for p in points:
            chunks.append(
                IndexedChunk(
                    text=p.payload["text"],
                    filename=p.payload["filename"],
                    document_id=p.payload["document_id"],
                    chunk_index=p.payload["chunk_index"],
                )
            )
        if offset is None:
            break
    return chunks


def _get_index() -> tuple[list[IndexedChunk], BM25Okapi | None]:
    """Rebuild the BM25 index from Qdrant on a short TTL instead of per-request —
    fine at this dataset size; a larger deployment would maintain a persistent
    inverted index instead of scrolling the whole collection."""
    now = time.monotonic()
    if _cache["bm25"] is not None and now - _cache["loaded_at"] < settings.bm25_refresh_seconds:
        return _cache["chunks"], _cache["bm25"]

    chunks = _load_all_chunks()
    bm25 = BM25Okapi([c.text.lower().split() for c in chunks]) if chunks else None

    _cache["chunks"] = chunks
    _cache["bm25"] = bm25
    _cache["loaded_at"] = now
    return chunks, bm25


def bm25_search(question: str, top_k: int) -> list[IndexedChunk]:
    chunks, bm25 = _get_index()
    if not bm25:
        return []

    scores = bm25.get_scores(question.lower().split())
    ranked = sorted(zip(chunks, scores), key=lambda pair: pair[1], reverse=True)
    return [chunk for chunk, score in ranked[:top_k] if score > 0]
