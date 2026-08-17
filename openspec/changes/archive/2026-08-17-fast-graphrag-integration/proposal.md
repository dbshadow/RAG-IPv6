## Why

While traditional Vector RAG retrieves relevant document chunks based on isolated cosine similarity, it lacks global multi-hop relation understanding across RFCs (e.g. RFC obsoletion/update chains, protocol entity interactions between SLAAC, NDP, RA flags, DHCPv6). Integrating Fast-GraphRAG alongside the existing Vector RAG enables knowledge graph traversal, multi-hop reasoning, and head-to-head comparison without breaking the existing vector retrieval pipeline.

## What Changes

- Implement a standalone Knowledge Graph extraction and indexing pipeline (`app/graph/`):
  - Entity & Relation extraction leveraging Ollama LLM and RFC metadata relationships (`OBSOLETES`, `UPDATES`, `REFERENCES`, protocol entities).
  - Graph storage and traversal module using PageRank / Personalized PageRank (PPR) for high-relevance subgraph expansion.
  - Full batch indexing script for all 153 RFCs (`scripts/index_graph.py`).
- Implement dual-mode RAG retrieval in the backend (`app/rag/generator.py` and `app/main.py`):
  - Support `rag_mode`: `"vector"`, `"graph"`, or `"hybrid"`.
  - Provide structured citation metadata from graph entities/relations as well as chunk citations.
- Update frontend UI (`app/static/index.html`, `app/static/app.js`, `app/static/style.css`):
  - Add RAG Mode selector in the sidebar/input area (`向量檢索 Vector`, `圖譜檢索 Graph`, `混合檢索 Hybrid`).
  - Render graph entity relationship badges alongside document chunk citations.

## Capabilities

### New Capabilities
- `graph-rag-engine`: Entity/Relation graph extraction, graph storage, Personalized PageRank subgraph retrieval, and hybrid fusion.

### Modified Capabilities
- `rag-qa-engine`: Extended to support dynamic selection between Vector, Graph, and Hybrid retrieval modes.
- `qa-web-interface`: Extended with UI controls for RAG retrieval mode selection and visualization of graph reasoning paths.

## Impact

- Independent storage at `data/graph/` (does not affect `data/chroma/`).
- Full backward compatibility for standard Vector RAG requests.
