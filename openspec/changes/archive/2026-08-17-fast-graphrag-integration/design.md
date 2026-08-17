## Context

The current IPv6 RAG system uses ChromaDB for dense cosine similarity search. While effective for localized text retrieval, it struggles with queries requiring multi-hop reasoning across RFC documents (e.g. tracking how RFC 8200 obsoleted RFC 2460, or resolving protocol interaction chains across SLAAC and DHCPv6). Fast-GraphRAG solves this by constructing an Entity-Relation Knowledge Graph and utilizing Personalized PageRank (PPR) for dynamic subgraph navigation without the high computation cost of hierarchical community summarization.

## Goals / Non-Goals

**Goals:**
- Create an independent Graph RAG engine alongside the existing Vector RAG engine.
- Build a structured Knowledge Graph from all 153 RFCs containing:
  - Document-level relations (`OBSOLETES`, `UPDATES`, `REFERENCES`) from `metadata.json` and text.
  - Protocol entity relations (`USES`, `DEFINES`, `CONTROLS`, `EXTENDS`, `CONFLICTS_WITH`).
- Implement Personalized PageRank (PPR) traversal starting from query-matched seed entities to extract the most relevant subgraph.
- Support `rag_mode` (`"vector"`, `"graph"`, `"hybrid"`) in API requests and UI.
- Provide a robust background batch indexing script `scripts/index_graph.py` with checkpointing and progress logging for all 153 RFCs.

**Non-Goals:**
- Replacing or modifying existing ChromaDB vector storage.
- Using heavyweight graph database servers (NetworkX/JSON-based persistent graph storage is sufficient, lightweight, and zero-dependency).

## Decisions

1. **Storage Structure (`data/graph/`)**:
   - `graph_data.json`: Persists all nodes (entities, RFC documents, protocol terms) and directed edges (relations with descriptions and source RFC tags).
   - `entity_embeddings.json`: Entity name/description embeddings for fast semantic seed matching.
   - *Rationale*: Clean separation from `data/chroma/`, easy incremental updates, and inspectable.

2. **Graph Extraction Strategy**:
   - **Deterministic Layer**: Extract explicit document-level relations from `data/metadata.json` (instantaneous, 100% accurate).
   - **Semantic Layer**: Batch-process RFC key sections with LLM (`gemma4:26b`) using structured JSON extraction schema for entities and relationships with concurrency throttling.

3. **Hybrid Retrieval Fusion**:
   - In `"hybrid"` mode: Retrieve Top-K chunks via Vector RAG + Top subgraph nodes/edges via Graph RAG. Merge and format them into the Prompt context with explicit source provenance.

## Risks / Trade-offs

- [Risk] LLM-based entity extraction for 153 RFCs takes significant time.
  → *Mitigation*: Script `scripts/index_graph.py` runs with resume/checkpointing support (`graph_checkpoint.json`), concurrency rate-limiting, and progress feedback so it can run smoothly in the background.
