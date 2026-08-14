from openai import OpenAI

from app.config import settings
from app.retrieval import RetrievedChunk

_client = OpenAI(api_key=settings.groq_api_key, base_url=settings.groq_base_url)

SYSTEM_PROMPT = (
    "You are an internal engineering knowledge assistant. Answer the question "
    "using ONLY the provided context chunks. If the context doesn't contain the "
    "answer, say you don't have enough information — do not make anything up. "
    "Cite which source file(s) you used."
)


def generate_answer(question: str, chunks: list[RetrievedChunk]) -> str:
    if not chunks:
        return "No relevant documents found in the knowledge base yet."

    context = "\n\n".join(
        f"[Source: {c.filename}, chunk {c.chunk_index}]\n{c.text}" for c in chunks
    )
    user_prompt = f"Context:\n{context}\n\nQuestion: {question}"

    response = _client.chat.completions.create(
        model=settings.groq_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
    )
    return response.choices[0].message.content
