## Why

In the multi-turn conversational RAG pipeline, Strategy 2 (Context Retention / `REUSE_CONTEXT`) was implicitly bundled into the LLM rewriting flow without an explicit deterministic classifier or distinct UI representation. As a result, follow-up queries that merely ask to "deep-dive into a term mentioned in the previous answer" (e.g., "詳細解釋上面提到的 Hop Limit", "請進一步說明剛剛第 2 點的內容") were unconditionally sent to the LLM query rewriter and triggered full search cycles.

Making Strategy 2 explicit:
1. Drastically cuts latency (0ms rewriting + 0ms retrieval) for in-depth drill-down follow-up questions.
2. Provides explicit visibility and transparency in the UI with a dedicated badge (`🔄 沿用上下文 (Context Reuse)`).
3. Completes the 3-tier routing architecture with distinct decision paths for Strategy 1, Strategy 2, and Strategy 3.

## What Changes

- Update `app/rag/router.py`:
  - Add explicit intent & drill-down pattern recognizer for Strategy 2 (`classify_intent_reuse_context`):
    - Matches drill-downs referencing previous points ("詳細解釋第X點", "進一步說明剛剛第N項", "詳細說明上述提到的 [名詞]", "上面說的 [名詞] 是什麼意思").
  - Update `route()` to return `REUSE_CONTEXT` with a clear explanation when matched.
- Update `app/rag/generator.py`:
  - When `decision == "REUSE_CONTEXT"`, skip vector and graph search, and instruct prompt generator to synthesize answer directly from dialogue history and prior context.
- Update Frontend (`app/static/app.js` & `app/static/style.css`):
  - Render a dedicated Morandi green/teal badge: `🔄 沿用上下文 (零檢索)`.

## Capabilities

### New Capabilities
- `explicit-context-retention`: Deterministic pattern matching and execution for reusing prior turn context without triggering LLM rewrite or vector/graph search.

### Modified Capabilities
- `conversational-rag-router`: Expanded to support explicit 3-way routing: `DIRECT_GENERATE` (Strategy 1), `REUSE_CONTEXT` (Strategy 2), and `REWRITE_AND_SEARCH` / `STANDALONE_SEARCH` (Strategy 3).
- `qa-web-interface`: Added `🔄 沿用上下文` badge visualization.

## Impact

- Follow-up drill-downs to previous answers execute with zero rewrite overhead and zero search latency.
- Users can clearly see when Strategy 2 is triggered via visual UI badge.
