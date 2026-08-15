# Incident RAG Assistant

A RAG system for internal engineering knowledge (runbooks, postmortems, architecture docs),
built as a series of system-design upgrades on top of a basic RAG pipeline — not a
single-file chatbot, but a set of services that could plausibly run in production.

Why this exists instead of "just use ChatGPT": see the architecture rationale below.
Each phase adds one system design concept on purpose, so the build doubles as a
system design learning log.

## Phase 1 — service separation + persistent vector store

```
client -> ingestion-service -> [Qdrant (vectors)]
client -> query-service      -> [Qdrant (search), Groq (generation)]
```

- **ingestion-service** (`:8001`) — `POST /upload`: extracts text (PDF/DOCX/TXT/MD),
  chunks it, embeds locally with `sentence-transformers`, and upserts the vectors
  into Qdrant. Raw file bytes aren't kept past processing — nothing downstream needs
  to re-read the original file once it's chunked and embedded.
- **query-service** (`:8002`) — `POST /query`: embeds the question, retrieves top-k
  chunks from Qdrant, asks the LLM to answer using only that context, returns the
  answer plus which source chunks were used.

Why split into two services, why Qdrant over in-memory FAISS, why local embeddings
but a hosted LLM for generation — all covered in the architecture discussion this
project started from; short version: independent scaling, durability across
restarts, decoupled compute/storage, and cost control.

## Phase 2 — async ingestion

```
client -> ingestion-service -> Redis (raw file, short TTL) + Redis Stream (job)
                                      |
                                      v
                              ingestion-worker -> Qdrant (vectors)
```

`POST /upload` no longer blocks on extraction/chunking/embedding. It now only
validates the file type, stashes the raw file bytes in Redis (just long enough
for the worker to pick the job up — not durable storage), pushes a job onto a
Redis Stream (`ingestion_jobs`), and returns immediately with a `document_id` and
`status: "queued"`. A separate **ingestion-worker** process consumes that stream
via a consumer group, does the actual extract -> chunk -> embed -> upsert work,
and records progress in Redis so it can be polled:

```bash
curl -F "file=@/path/to/runbook.pdf" http://localhost:8001/upload
# {"document_id": "...", "filename": "runbook.pdf", "status": "queued"}

curl http://localhost:8001/status/<document_id>
# {"status": "processing", "filename": "runbook.pdf"}
# {"status": "done", "filename": "runbook.pdf", "chunks_indexed": "12"}
```

Using a consumer group (not plain pub/sub) means a job survives a worker crash —
it stays unacknowledged in the stream until it's explicitly processed, instead of
being silently dropped.

## Phase 3 (current) — caching + hybrid search

```
client -> query-service -> Redis (cache-aside) -> [Qdrant (vector) + BM25 (keyword)]
                                                          |
                                                     cross-encoder rerank -> Groq
```

`POST /query` now:

1. Checks Redis for a cached answer to the (normalized) question. Cache hit ->
   return immediately, `"cached": true`, no retrieval or LLM call at all.
2. On a miss, runs **hybrid retrieval**: a vector search against Qdrant (catches
   semantic similarity) unioned with a BM25 keyword search rebuilt from the
   indexed chunks (catches exact matches on jargon, error codes, ticket IDs that
   embeddings tend to blur together).
3. Merges and dedupes both candidate pools, then reranks them with a
   cross-encoder (`cross-encoder/ms-marco-MiniLM-L-6-v2`) to pick the final top-k
   most relevant chunks — vector/BM25 scores aren't directly comparable, so
   reranking is what actually decides the final order.
4. Writes the answer to Redis (`SETEX`, 1h TTL) before returning, so the next
   identical question skips retrieval and generation entirely.

The BM25 index is rebuilt from Qdrant on a short TTL (30s) rather than per
request — fine at this dataset size; a larger deployment would maintain a
persistent inverted index instead of scrolling the whole collection each time.

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

## Roadmap (each phase = one LinkedIn post)

- **Phase 4 — observability**: structured logs, Prometheus metrics, a Grafana
  dashboard (query latency, cache hit rate, queue depth).
- **Phase 5 — evaluation**: RAGAS-based eval harness with real precision/recall
  numbers on a test question set.
- **Phase 6 (optional) — cloud deploy**: auth, per-team access control,
  multi-tenancy, deploy to a real cluster.
