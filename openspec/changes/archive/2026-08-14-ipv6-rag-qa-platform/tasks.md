## 1. Environment and Project Setup

- [x] 1.1 Initialize `pyproject.toml` with dependencies (`fastapi`, `uvicorn`, `httpx`, `chromadb`, `pydantic`, `pydantic-settings`, `rich`) using `uv`
- [x] 1.2 Create backend configuration module (`app/config.py`) to manage Ollama endpoint, API token, model names, and data paths

## 2. RFC Knowledge Base and Ingestion Pipeline

- [x] 2.1 Implement section-aware RFC text parser and chunker (`app/indexer/chunker.py`)
- [x] 2.2 Implement remote Ollama embedding client (`app/indexer/embedder.py`) with batching and retry logic
- [x] 2.3 Implement vector database manager (`app/indexer/vector_store.py`) to store and index chunk embeddings
- [x] 2.4 Create CLI indexer script (`scripts/index_rfcs.py`) and run indexing on the 153 downloaded RFCs

## 3. RAG Engine and Retrieval

- [x] 3.1 Implement RAG retriever (`app/rag/retriever.py`) for similarity search with metadata filtering
- [x] 3.2 Implement citation-enforcing prompt builder and parser (`app/rag/prompt.py`)
- [x] 3.3 Implement LLM generation engine (`app/rag/generator.py`) supporting streaming response and token yield

## 4. FastAPI Backend API

- [x] 4.1 Implement FastAPI application setup and CORS middleware (`app/main.py`)
- [x] 4.2 Implement streaming Q&A endpoint (`/api/chat/stream`) and standard Q&A endpoint (`/api/chat`)
- [x] 4.3 Implement RFC metadata and content inspection endpoint (`/api/rfcs`)

## 5. Web Frontend

- [x] 5.1 Create interactive chat web application with clean, modern layout and responsive design (`app/static/index.html`, `app/static/app.js`, `app/static/style.css`)
- [x] 5.2 Implement real-time SSE streaming answer display with Markdown rendering
- [x] 5.3 Implement interactive RFC citation chips with expandable drawer/modal showing exact source text and datatracker links

## 6. End-to-End Testing and Verification

- [x] 6.1 Run test questions against the backend (e.g., IPv6 header fields, SLAAC vs DHCPv6, Solicited-Node Multicast) and verify RFC citation accuracy
- [x] 6.2 Verify web UI streaming interaction and responsiveness
