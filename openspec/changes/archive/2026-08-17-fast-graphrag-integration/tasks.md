## 1. Graph Storage and Traversal Engine

- [x] 1.1 Implement `app/graph/store.py` for persistent Knowledge Graph storage, node/edge CRUD, and JSON persistence in `data/graph/`
- [x] 1.2 Implement `app/graph/extractor.py` for deterministic metadata extraction and LLM-based entity/relation extraction
- [x] 1.3 Implement `app/graph/traverser.py` using Personalized PageRank (PPR) and entity seed matching

## 2. Fast-GraphRAG Indexing Pipeline

- [x] 2.1 Implement `scripts/index_graph.py` to index all 153 RFCs with checkpointing (`data/graph/checkpoint.json`) and progress logging
- [x] 2.2 Seed the graph with metadata-level relations from `data/metadata.json` and start background extraction

## 3. Backend Dual-Mode & Hybrid Integration

- [x] 3.1 Update `app/rag/generator.py` and `app/rag/prompt.py` to support `rag_mode: "vector" | "graph" | "hybrid"`
- [x] 3.2 Update `ChatRequest` schema and `/api/chat`, `/api/chat/stream` endpoints in `app/main.py`
- [x] 3.3 Add `/api/graph/stats` endpoint to inspect graph node and edge counts

## 4. Frontend Mode Switcher & Graph Citation Display

- [x] 4.1 Add RAG Mode toggle buttons/selector in `app/static/index.html`
- [x] 4.2 Update `app/static/app.js` to pass `rag_mode` and render graph relation chips in citations
- [x] 4.3 Add CSS styles in `app/static/style.css` for mode selector and graph badges

## 5. Verification and Comparative Testing

- [x] 5.1 Test Graph RAG retrieval on a multi-hop query (e.g. RFC 8200 vs RFC 2460 obsolescence and header modifications)
- [x] 5.2 Verify that traditional Vector RAG remains 100% functional and compare results side-by-side
