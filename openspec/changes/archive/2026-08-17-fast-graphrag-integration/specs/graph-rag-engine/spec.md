## ADDED Requirements

### Requirement: Knowledge Graph Construction and Storage
The graph engine SHALL construct and maintain a persistent Knowledge Graph stored in `data/graph/` containing entities (protocols, headers, flags, mechanisms, RFC documents) and directed relations with evidence citations.

#### Scenario: Extract metadata and protocol entities
- **WHEN** graph indexing runs across RFC documents
- **THEN** document relations (`OBSOLETES`, `UPDATES`) and protocol concepts (`DEFINES`, `USES`, `EXTENDS`) are persisted into the graph store

### Requirement: Personalized PageRank Subgraph Retrieval
The graph engine SHALL identify query-relevant seed entities via embedding similarity and apply Personalized PageRank (PPR) traversal to extract the most relevant interconnected subgraph.

#### Scenario: User queries protocol interaction
- **WHEN** a user asks about multi-hop relations (e.g. "How does RFC 8200 update header processing and obsoletes RFC 2460?")
- **THEN** the graph engine traverses related nodes and returns structured entity-relation context with provenance

### Requirement: Dual-Mode and Hybrid RAG Execution
The backend RAG generator and API SHALL accept a `rag_mode` parameter (`"vector"`, `"graph"`, `"hybrid"`) and adapt retrieval and prompt construction accordingly.

#### Scenario: Execute Hybrid RAG query
- **WHEN** user selects `"hybrid"` mode and submits a question
- **THEN** the system merges Vector chunks and Graph relations into the final prompt and returns citation metadata for both

### Requirement: Frontend RAG Mode Switcher
The web interface SHALL provide a clean selector for choosing between Vector RAG, Graph RAG, and Hybrid RAG modes, displaying mode-specific citation and reasoning path indicators.

#### Scenario: User switches mode in UI
- **WHEN** user selects "圖譜檢索 (Graph RAG)" in the UI
- **THEN** subsequent queries pass `rag_mode: "graph"` to the backend and display graph relationship badges
