## ADDED Requirements

### Requirement: Conversational Retrieval Routing
The RAG system SHALL evaluate multi-turn user queries through a 3-tier routing process:
1. Intent Classification (Zero-RAG for format/translation/chitchat)
2. Context Retention (Reusing prior chunks for local drill-down)
3. LLM Query Rewriting (Condensing conversational history into a standalone search query)

#### Scenario: User requests formatting of previous answer
- **WHEN** user sends "請把上面的內容整理成 Markdown 表格" following an existing answer
- **THEN** the router decides `DIRECT_GENERATE` without issuing vector or graph search

#### Scenario: User asks a pronoun follow-up
- **WHEN** user sends "那它廢棄了什麼舊標準？" after discussing RFC 8200
- **THEN** the router rewrites the query to "RFC 8200 廢棄了哪些舊標準與規範？" and retrieves relevant RFC chunks/graph triples

### Requirement: Multi-turn Request and Event Streaming
The backend API SHALL accept an array of previous messages (`history: [{"role": "user" | "assistant", "content": "..."}]`) in `ChatRequest` and emit a `router` event in SSE stream containing the routing decision and standalone query.

#### Scenario: Streaming multi-turn response with routing metadata
- **WHEN** a client sends a multi-turn chat request
- **THEN** the server emits `event: router` before streaming tokens

### Requirement: Frontend Conversation History & Routing Badges
The frontend client SHALL preserve message history across turns, send history in API requests, allow resetting conversation history, and render routing state badges on answer cards.

#### Scenario: Render routing state on message card
- **WHEN** an answer is received
- **THEN** a routing badge (e.g. `⚡ 沿用上下文` or `🔍 重寫檢索: RFC 8200...`) is displayed above the citations
