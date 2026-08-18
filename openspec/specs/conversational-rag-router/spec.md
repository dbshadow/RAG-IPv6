# conversational-rag-router Specification

## Purpose
Provides multi-turn conversational memory, fast intent-based retrieval routing, context retention, and LLM-powered standalone query condensation for the IPv6 RAG system.

## Requirements

### Requirement: 3-Tier Conversational Retrieval Routing
The RAG system SHALL evaluate multi-turn user queries through a 3-tier routing process:
1. **Strategy 1 (Intent Classification / Zero-RAG)**: Detects formatting, translation, refinement, and conversational pleasantries to answer directly from conversation history with 0ms retrieval overhead (`decision="DIRECT_GENERATE"`).
2. **Strategy 2 (Context Retention / Drill-down)**: Detects drill-downs into terms or points already present in the previous turn's output (e.g. "請詳細解釋第 2 點", "詳細說明上面提到的 Hop Limit") and reuses existing context (`decision="REUSE_CONTEXT"`).
3. **Strategy 3 (LLM Query Rewriting)**: When new retrieval is required, transforms follow-up questions containing pronouns or ambiguous references into standalone, unambiguous technical queries before issuing vector and graph searches (`decision="REWRITE_AND_SEARCH"`).

#### Scenario: User requests formatting of previous answer
- **WHEN** user sends "請把上面的內容整理成 Markdown 表格"
- **THEN** the router decides `DIRECT_GENERATE` without issuing vector or graph search

#### Scenario: User drills down on a specific point
- **WHEN** user sends "請詳細解釋第 2 點的內容" or "詳細說明上面提到的 Hop Limit"
- **THEN** the router decides `REUSE_CONTEXT` without rewriting or search

#### Scenario: User asks a pronoun follow-up needing new search
- **WHEN** user sends "那它廢棄了什麼舊標準？" after discussing RFC 8200
- **THEN** the router rewrites the query to "RFC 8200 廢棄了哪些舊標準？" and retrieves relevant RFC chunks and graph triples

### Requirement: Multi-turn Request and Event Streaming
The backend API SHALL accept an array of previous messages (`history: [{"role": "user" | "assistant", "content": "..."}]`) in `ChatRequest` and emit a `router` event in SSE stream containing the routing decision and standalone query.

### Requirement: Frontend Conversation History & Routing Badges
The frontend client SHALL preserve message history across turns, send history in API requests, allow resetting conversation history, and render routing state badges on answer cards (`⚡ 對話直連 (零檢索)`, `🔄 沿用上下文 (零檢索)`, `🔍 獨立檢索焦點: ...`, `📊 全域檢索`).
