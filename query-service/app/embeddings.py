from functools import lru_cache

from sentence_transformers import SentenceTransformer

from app.config import settings


@lru_cache(maxsize=1)
def get_model() -> SentenceTransformer:
    return SentenceTransformer(settings.embedding_model)


def embed_query(text: str) -> list[float]:
    model = get_model()
    return model.encode([text], normalize_embeddings=True).tolist()[0]
