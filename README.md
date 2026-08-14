# Incident RAG Assistant

A RAG system for internal engineering knowledge (runbooks, postmortems, architecture docs),
built as a series of system-design upgrades on top of a basic RAG pipeline — not a
single-file chatbot, but a set of services that could plausibly run in production.

Why this exists instead of "just use ChatGPT": see the architecture rationale below.
Each phase adds one system design concept on purpose, so the build doubles as a
system design learning log.

## Phase 1 (current) — service separation + persistent vector store

```
client -> ingestion-service -> [MinIO (raw files), Qdrant (vectors)]
client -> query-service      -> [Qdrant (search), Groq (generation)]
```

- **ingestion-service** (`:8001`) — `POST /upload`: extracts text (PDF/DOCX/TXT/MD),
  chunks it, embeds locally with `sentence-transformers`, stores the raw file in MinIO
  and the vectors in Qdrant.
- **query-service** (`:8002`) — `POST /query`: embeds the question, retrieves top-k
  chunks from Qdrant, asks the LLM to answer using only that context, returns the
  answer plus which source chunks were used.

Why split into two services, why Qdrant over in-memory FAISS, why MinIO for raw
files, why local embeddings but a hosted LLM for generation — all covered in the
architecture discussion this project started from; short version: independent
scaling, durability across restarts, decoupled compute/storage, and cost control.

## Running it

```bash
cp .env.example .env   # add your GROQ_API_KEY (from console.groq.com)
docker compose up --build
```

Upload a document:

```bash
curl -F "file=@/path/to/runbook.pdf" http://localhost:8001/upload
```

Ask a question:

```bash
curl -X POST http://localhost:8002/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What do we do when the payments service returns 503s?"}'
```

Qdrant dashboard: http://localhost:6333/dashboard
MinIO console: http://localhost:9001 (minioadmin / minioadmin)

## Roadmap (each phase = one LinkedIn post)

- **Phase 2 — async ingestion**: add a queue (Redis Streams) + worker so upload
  doesn't block on embedding; ingestion-service just enqueues a job.
- **Phase 3 — caching + hybrid search**: Redis cache-aside for repeat queries,
  BM25 + vector hybrid retrieval with reranking for better accuracy on jargon/IDs.
- **Phase 4 — observability**: structured logs, Prometheus metrics, a Grafana
  dashboard (query latency, cache hit rate, queue depth).
- **Phase 5 — evaluation**: RAGAS-based eval harness with real precision/recall
  numbers on a test question set.
- **Phase 6 (optional) — cloud deploy**: auth, per-team access control,
  multi-tenancy, deploy to a real cluster.
