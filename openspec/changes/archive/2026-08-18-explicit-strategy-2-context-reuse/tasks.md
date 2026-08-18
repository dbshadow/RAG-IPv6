## 1. Router Logic & Pattern Matching

- [x] 1.1 Add `INTENT_REUSE_CONTEXT_PATTERNS` and `classify_intent_reuse_context` in `app/rag/router.py`
- [x] 1.2 Update `ConversationRouter.route()` to return `REUSE_CONTEXT` when pattern matches

## 2. Generator & Frontend Integration

- [x] 2.1 Ensure `RAGGenerator.answer` and `RAGGenerator.answer_stream` handle `REUSE_CONTEXT` by skipping retrieval and passing history context
- [x] 2.2 Update `app/static/app.js` to render `🔄 沿用上下文 (零檢索)` badge on `decision === 'REUSE_CONTEXT'`
- [x] 2.3 Update `app/static/style.css` to add styling for `.router-badge.reuse`

## 3. Verification & Sample Testing

- [x] 3.1 Test Sample query 1: "請詳細解釋第 2 點的內容" -> verifies `REUSE_CONTEXT`
- [x] 3.2 Test Sample query 2: "詳細說明上面提到的 Hop Limit" -> verifies `REUSE_CONTEXT`
- [x] 3.3 Verify Strategy 1 (`DIRECT_GENERATE`) and Strategy 3 (`REWRITE_AND_SEARCH`) continue functioning normally
