from fastapi import FastAPI
from pydantic import BaseModel

from app.llm import generate_answer
from app.retrieval import retrieve

app = FastAPI(title="Query Service")


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


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/query", response_model=QueryResponse)
def query(request: QueryRequest):
    chunks = retrieve(request.question)
    answer = generate_answer(request.question, chunks)
    return QueryResponse(
        answer=answer,
        sources=[
            Source(
                filename=c.filename,
                document_id=c.document_id,
                chunk_index=c.chunk_index,
                score=c.score,
            )
            for c in chunks
        ],
    )
