## Why

Building an interactive IPv6 Q&A platform backed by Retrieval-Augmented Generation (RAG) enables network engineers, developers, and students to query and understand authoritative IPv6 standards (RFCs from 6man and v6ops working groups) with strict provenance, high accuracy, and verifiable citations.

## What Changes

- Implement an RFC ingestion, chunking, and embedding pipeline using the remote Ollama `embeddinggemma` service and a local vector store (such as ChromaDB/FAISS/SQLite-Vec).
- Build a FastAPI-based RAG Q&A backend engine that integrates with the remote Ollama `gemma4:26b` completion API, supporting streaming responses and mandatory RFC citations (RFC number, section, title, and excerpt).
- Build a modern, clean web frontend for conversational Q&A featuring streaming message rendering, RFC reference citations with expandable excerpt viewing, and conversation history.
- Provide unified start and ingestion management scripts with `uv` and Node.js.

## Capabilities

### New Capabilities
- `rfc-knowledge-base`: Ingestion, semantic chunking, vector embedding generation via remote `embeddinggemma`, and hybrid/dense vector search over the downloaded 153 IPv6 RFCs with rich metadata.
- `rag-qa-engine`: Retrieval-augmented prompt engineering, remote LLM inference (`gemma4:26b`), streaming completion support, and strict RFC citation and provenance extraction.
- `qa-web-interface`: Interactive web conversation interface with real-time streaming output, collapsible RFC source references, and responsive layout.

### Modified Capabilities
<!-- None -->

## Impact

- **New Backend Services**: FastAPI application with endpoints for health checks, question answering (streaming and non-streaming), and RFC source document inspection.
- **New Frontend Web App**: Single-page application (or lightweight Vite/React) with chat interface and citation display.
- **External Dependencies**: Connects to the remote Ollama endpoint `https://llm.ainvc.i234.me` with Bearer Token authentication.
- **Local Storage**: Vector database index and RFC metadata stored in `data/` directory.
