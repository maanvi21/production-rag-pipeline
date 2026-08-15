import uuid

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.extract import is_supported
from app.queue import enqueue_job, get_status, set_status
from app.storage import save_file

app = FastAPI(title="Ingestion Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/upload")
async def upload(file: UploadFile):
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")

    if not is_supported(file.filename):
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {file.filename}")

    document_id = str(uuid.uuid4())
    save_file(f"{document_id}/{file.filename}", content)

    set_status(document_id, "queued", filename=file.filename)
    enqueue_job(document_id, file.filename, file.content_type or "application/octet-stream")

    return {
        "document_id": document_id,
        "filename": file.filename,
        "status": "queued",
    }


@app.get("/status/{document_id}")
def status(document_id: str):
    data = get_status(document_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Unknown document_id")
    return data
