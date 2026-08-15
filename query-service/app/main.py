from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import APIError
from pydantic import BaseModel

from app.cache import get_cached, set_cached
from app.llm import generate_answer
from app.retrieval import retrieve

app = FastAPI(title="Query Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class QueryRequest(BaseModel):
    question: str


class Source(BaseModel):
    filename: str
    document_id: str
    chunk_index: int
    score: float


class QueryResponse(BaseModel):
    answer: str
    sources: list[Source]
    cached: bool = False


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/query", response_model=QueryResponse)
def query(request: QueryRequest):
    cached = get_cached(request.question)
    if cached is not None:
        return QueryResponse(**cached, cached=True)

    chunks = retrieve(request.question)
    try:
        answer = generate_answer(request.question, chunks)
    except APIError as e:
        raise HTTPException(status_code=502, detail=f"LLM request failed: {e.message}")

    sources = [
        Source(
            filename=c.filename,
            document_id=c.document_id,
            chunk_index=c.chunk_index,
            score=c.score,
        )
        for c in chunks
    ]

    set_cached(request.question, {"answer": answer, "sources": [s.model_dump() for s in sources]})
    return QueryResponse(answer=answer, sources=sources, cached=False)
