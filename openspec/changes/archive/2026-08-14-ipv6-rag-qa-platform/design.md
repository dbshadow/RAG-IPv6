## Context

The repository contains 153 official RFC documents from the IETF 6man and v6ops working groups, stored under `data/rfcs/` with metadata in `data/metadata.json`. The user requires an end-to-end interactive IPv6 Q&A web platform that leverages RAG. The system connects to a remote Ollama server with `embeddinggemma:latest` for dense embeddings and `gemma4:26b` for LLM completion with strict factual citations to RFC sections.

## Goals / Non-Goals

**Goals:**
- Provide an automated RFC chunking, embedding, and vector storage pipeline using remote `embeddinggemma:latest`.
- Implement a FastAPI backend providing RAG retrieval (dense + BM25 keyword hybrid search / semantic search with section metadata) and streaming response generation via remote `gemma4:26b`.
- Guarantee verifiable provenance: every answer includes RFC citation chips (RFC number, section heading, text excerpt, and datatracker link).
- Build a responsive, clean, and modern web UI (built with Vite/React or Vanilla modern frontend, served directly or via dev server) featuring a chat interface, streaming tokens, prompt suggestions, and collapsible citation inspectors.
- Provide clean CLI commands with `uv run` to build vector database and run services.

**Non-Goals:**
- Real-time crawling of draft RFCs (only the 153 published RFCs are indexed).
- Complex user authentication or multi-tenant database partitioning.

## Decisions

1. **Embedding & LLM Provider**:
   - *Choice*: Remote Ollama API at `https://llm.ainvc.i234.me` with Bearer token.
   - *Embedding*: `embeddinggemma:latest` (768-dim vectors).
   - *Generator*: `gemma4:26b` (with fallback support to other models on the instance if configured).
   - *Rationale*: Uses the user's pre-configured GPU cluster without requiring local GPU resources.

2. **Chunking Strategy**:
   - *Choice*: RFC-aware semantic chunker. RFCs have structured headers (e.g. `1. Introduction`, `3.2. Address Format`). Chunks will preserve Section Number, Section Title, RFC number, and title in metadata.
   - *Parameters*: ~500-800 tokens per chunk with 100-token overlap, respecting section boundaries.

3. **Vector Database / Index**:
   - *Choice*: Lightweight persistent vector storage using `ChromaDB` or `FAISS` / `sqlite-vec` in local `data/vectorstore/`.
   - *Rationale*: Zero external database server overhead, fast local persistence, easy to commit/rebuild via uv.

4. **Backend Framework**:
   - *Choice*: FastAPI with `httpx` async client and Server-Sent Events (SSE) streaming for real-time response generation.
   - *Rationale*: High performance, native async streaming, automatic OpenAPI docs.

5. **Frontend Architecture**:
   - *Choice*: Modern Single-Page Application (HTML5 / Vanilla JS or Vite React) with clean styling, typography, citation modals/drawers, and markdown rendering.

## Risks / Trade-offs

- [Risk] Remote Ollama embedding latency when indexing 153 RFCs.
  → *Mitigation*: Batch embedding requests with concurrency limit (asyncio Semaphore) and disk caching of embeddings so re-indexing is incremental and fast.
- [Risk] Context window limitations or hallucinated section numbers.
  → *Mitigation*: Strict system prompt enforcing citations only from provided context snippets, passing chunk section IDs explicitly.
- [Risk] Network fluctuations to the remote Ollama server.
  → *Mitigation*: Proper timeout handling, retry logic with exponential backoff in backend client.
