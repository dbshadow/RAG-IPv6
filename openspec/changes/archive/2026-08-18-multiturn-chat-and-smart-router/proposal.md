## Why

The current IPv6 RAG system operates strictly in single-turn Q&A mode. In conversational scenarios, users frequently ask follow-up questions with pronouns or contextual references (e.g., "What older standards did it obsolete?", "Can you summarize the above in a markdown table?", "Translate that to English"). Without multi-turn memory and routing:
1. Search queries with pronouns fail to match the correct RFC sections or graph entities.
2. Follow-up commands (translation, formatting, summarization) unnecessarily trigger redundant vector/graph searches.
3. Users lose conversational continuity.

## What Changes

- Implement Multi-turn Context & Smart Retrieval Router (`app/rag/router.py`):
  - **Strategy 1 (Intent Routing)**: Fast deterministic check for meta-actions (summarization, translation, formatting, conversational pleasantries) that can be fulfilled entirely from conversation history without running RAG (0ms latency, zero extra search).
  - **Strategy 2 (Context Retention)**: Reuse previous Top-K chunks and subgraph when the query directly explores details of the already-retrieved context.
  - **LLM Query Rewriting**: When new retrieval is required, rewrite ambiguous conversational queries into standalone, self-contained search queries containing explicit RFC numbers and technical terminology before querying ChromaDB and Fast-GraphRAG.
- Extend Backend APIs & Prompt Handling (`app/main.py`, `app/rag/generator.py`, `app/rag/prompt.py`):
  - Add `history: List[ChatMessage]` to `ChatRequest`.
  - Pass router metadata (`routing_decision`, `standalone_query`) through SSE events.
- Update Frontend Chat State & UI (`app/static/app.js`, `app/static/index.html`, `app/static/style.css`):
  - Maintain client-side session conversation history across message turns.
  - Display routing badges on chat bubbles (e.g. `⚡ 沿用上下文`, `🔍 重寫檢索: RFC 8200...`, `💬 直接對話`).
  - Add a "Clear History / New Topic" action.

## Capabilities

### New Capabilities
- `conversational-rag-router`: Multi-turn conversational memory, intent classification, contextual chunk retention, and LLM-powered standalone query rewriting.

### Modified Capabilities
- `rag-qa-engine`: Extended to consume multi-turn dialogue history and execute smart routing before search.
- `qa-web-interface`: Extended to preserve session message history and visualize routing decisions in real time.

## Impact

- Zero disruption to single-turn queries (backward compatible).
- Dramatic latency savings for follow-up formatting/translation queries (bypasses RAG search).
- High retrieval precision for multi-turn pronoun follow-ups (prevents hallucination and retrieval misses).
