## Context

The conversational RAG router needs a deterministic, ultra-fast mechanism to identify when a user is asking for further elaboration on concepts already provided in the previous turn, rather than asking for new RFC lookups.

## Goals / Non-Goals

**Goals:**
- Add `INTENT_REUSE_CONTEXT_PATTERNS` to `app/rag/router.py` covering:
  - Ordinal / item references ("第 [1-9一二三四五] [點項條]", "上一點", "下一點")
  - Elaboration requests referring to previous output ("上面提到的 [X]", "剛才說的 [X]", "上述 [X] 是什麼意思", "詳細說明這部分")
- When `classify_intent_reuse_context()` returns True:
  - Set `decision = "REUSE_CONTEXT"`
  - Set `standalone_query = query`
  - Set `reason = "追問上一輪已列出之細節/名詞，直接沿用上下文生成 (零檢索延遲)"`
- Ensure `RAGGenerator.answer` and `RAGGenerator.answer_stream` skip new ChromaDB / Graph queries and pass history into prompt generation.
- Style `router-badge.reuse` in `app/static/style.css` and handle `REUSE_CONTEXT` in `app/static/app.js`.

**Non-Goals:**
- Completely disabling Strategy 3 (LLM rewrite remains active for queries that need new external RFC search).

## Decisions

1. **Routing Hierarchy**:
   - `Tier 1`: `DIRECT_GENERATE` (Format / Translate / Acknowledgments)
   - `Tier 2`: `REUSE_CONTEXT` (Drill-down into previous points / terms already answered)
   - `Tier 3`: `REWRITE_AND_SEARCH` / `STANDALONE_SEARCH` (New technical search requiring query resolution)
   - *Rationale*: Guarantees lowest latency first. Tiers 1 and 2 take < 0.1ms without touching LLM or vector search.

2. **Frontend Badge Style**:
   - `REUSE_CONTEXT`: `🔄 沿用上下文 (零檢索)` with an emerald/sage Morandi badge.
