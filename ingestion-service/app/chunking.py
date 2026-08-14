from app.config import settings


def chunk_text(text: str) -> list[str]:
    """Fixed-size sliding window chunking over whitespace-normalized text."""
    words = text.split()
    if not words:
        return []

    chunk_size = settings.chunk_size
    overlap = settings.chunk_overlap
    step = max(chunk_size - overlap, 1)

    chunks = []
    for start in range(0, len(words), step):
        window = words[start : start + chunk_size]
        if not window:
            break
        chunks.append(" ".join(window))
        if start + chunk_size >= len(words):
            break
    return chunks
