from functools import lru_cache

from sentence_transformers import CrossEncoder

from app.config import settings


@lru_cache(maxsize=1)
def get_reranker() -> CrossEncoder:
    return CrossEncoder(settings.reranker_model)


def rerank(question: str, candidates: list, top_k: int) -> list[tuple]:
    if not candidates:
        return []

    model = get_reranker()
    pairs = [(question, c.text) for c in candidates]
    scores = model.predict(pairs)

    ranked = sorted(zip(candidates, scores), key=lambda pair: pair[1], reverse=True)
    return [(c, float(score)) for c, score in ranked[:top_k]]
