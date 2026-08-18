## Context

In multi-turn technical conversations, users build on preceding context. A robust conversational RAG must balance **latency** (avoiding unneeded searches) and **precision** (ensuring pronoun-laden queries find the right RFCs). We implement a 3-tier routing architecture combining fast rule-based intent classification, context retention, and LLM-powered query condensation.

## Goals / Non-Goals

**Goals:**
- Implement `app/rag/router.py` with `ConversationRouter`:
  - **Tier 1 (Intent Classifier)**: Detect zero-retrieval intents (table formatting, translation, refinement, gratitude, generic clarifications).
  - **Tier 2 (Context Retention)**: Check if previous chunks/graph context already contain sufficient context for follow-up explanations.
  - **Tier 3 (LLM Query Rewriter)**: Use lightweight prompt to transform follow-up questions (e.g. "What did it replace?") into unambiguous search queries (e.g. "RFC 8200 obsoleted standards").
- Update `app/rag/generator.py` and `app/rag/prompt.py` to accept message history and routing directives.
- Update `app/main.py` request schemas and SSE streaming headers.
- Update frontend `app/static/app.js` and `app/static/style.css` to persist multi-turn history per session and display routing badges.

**Non-Goals:**
- Heavyweight server-side database session management (client-side history payload is standard, lightweight, and stateless).

## Decisions

1. **Routing Decision Pipeline**:
   - `DIRECT_GENERATE`: Skip RAG entirely. Send history directly to LLM.
   - `REUSE_CONTEXT`: Skip new vector/graph search. Reuse the previous turn's context chunks.
   - `REWRITE_AND_SEARCH`: Call Ollama `/api/generate` with a low-temperature condensation prompt, then execute Vector / Graph / Hybrid search with the standalone query.
   - *Rationale*: Eliminates 100% of retrieval overhead for formatting/summarization while ensuring zero retrieval misses for ambiguous follow-ups.

2. **History Truncation**:
   - Maintain sliding window of last 6 turns (3 User + 3 Assistant) to avoid prompt bloat and stay within context limits.

3. **Routing Visualization**:
   - Emits an SSE event `event: router` with `{"decision": "rewrite", "standalone_query": "...", "reason": "..."}` to give the user transparent visibility into AI reasoning.

## Risks / Trade-offs

- [Risk] LLM Query Rewriting adds ~200-400ms when triggered.
  → *Mitigation*: Tier 1 and Tier 2 bypass rewriting whenever possible. Rewriting only executes when there is an active multi-turn context needing resolution.
