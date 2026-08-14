import uuid

from fastapi import FastAPI, HTTPException, UploadFile

from app.chunking import chunk_text
from app.embeddings import embed_texts
from app.extract import extract_text
from app.storage import save_file
from app.vector_store import upsert_chunks

app = FastAPI(title="Ingestion Service")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/upload")
async def upload(file: UploadFile):
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")

    try:
        text = extract_text(file.filename, content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not text.strip():
        raise HTTPException(status_code=422, detail="No extractable text in file")

    document_id = str(uuid.uuid4())
    save_file(f"{document_id}/{file.filename}", content, file.content_type or "application/octet-stream")

    chunks = chunk_text(text)
    vectors = embed_texts(chunks)
    upsert_chunks(document_id, file.filename, chunks, vectors)

    return {
        "document_id": document_id,
        "filename": file.filename,
        "chunks_indexed": len(chunks),
    }
