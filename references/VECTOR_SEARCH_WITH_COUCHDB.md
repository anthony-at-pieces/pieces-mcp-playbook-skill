# Vector search with CouchDB (practical reality check)

You mentioned PiecesOS is using **CouchDB** today and asked: *“how are they doing vector searches?”*

## Key distinction: CouchDB vs Couchbase
- **Apache CouchDB** is a document database with HTTP/JSON APIs.
- **Couchbase** (different product) added **vector search** capabilities in recent versions, but that does *not* mean CouchDB has native vector indexing.

If someone says “CouchDB has vector search”, double‑check whether they actually mean **Couchbase**.

## What CouchDB can do natively
CouchDB supports:
- primary document CRUD
- map/reduce views
- Mango queries (secondary-indexed queries)
- full-text search via separate components (historically “Clouseau” / Lucene-based search integrations)

But **vector similarity (kNN/ANN) search** is typically *not* a native CouchDB feature.

## Common architectures (what teams actually do)

### Option A — CouchDB as source of truth + external vector index (most common)
- Store canonical “memory documents” in CouchDB.
- Maintain a vector index elsewhere (examples: Qdrant, Milvus, Elasticsearch/OpenSearch vector fields, Postgres+pgvector, local FAISS).
- The vector index stores:
  - `{embedding, doc_id, metadata}`

Query flow:
1. Embed user query
2. kNN search in vector index → top K `doc_id`s
3. Fetch those documents from CouchDB by id
4. (optional) apply metadata filters via CouchDB queries or in the vector store

Sync options:
- Use CouchDB’s `_changes` feed to stream updates into your embedding/indexing pipeline.
- Run periodic re-index jobs to handle drift.

### Option B — Local-first vector index (cross-platform friendly)
If the product is local-first and wants minimal ops:
- Keep CouchDB for doc storage
- Use a local vector library/store:
  - FAISS (fast, native)
  - sqlite + vector extension (if you can ship it)
  - an embedded vector DB

This avoids running an external service but adds packaging complexity.

### Option C — “Hybrid” using CouchDB full-text search + reranking
If you only need “semantic-ish” behavior and can tolerate lower quality:
- Use CouchDB full-text search integration for lexical recall
- Rerank candidates using embeddings/LLM reranker in-process
This is not true vector search, but can be good enough for some UX.

## What to ask the PiecesOS team (to make the conversation concrete)
1. Where are embeddings computed (local model vs cloud)?
2. Where are embeddings stored (CouchDB docs vs separate store)?
3. What ANN index are they using (HNSW, IVF, PQ, etc.)?
4. How do they do metadata filters (“only terminal + IDE last 24h”)?
5. How do they keep index consistent with CouchDB updates?

If they can’t answer #2 and #3 clearly, they likely don’t have a real vector index yet (or it’s implicit in another component).

## Why this matters to “deep research” reliability
If retrieval is weak or unstable:
- downstream synthesis fails more often
- reports look random
- errors get masked as “LLM issues”

A robust agent workflow should **log retrieval diagnostics** (how many candidates, from where, any tool errors) before synthesis.
