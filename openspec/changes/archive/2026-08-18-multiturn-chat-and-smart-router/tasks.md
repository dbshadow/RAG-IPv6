## 1. Multi-turn Router & Query Rewriter Engine

- [x] 1.1 Implement `app/rag/router.py` with `ConversationRouter` (Intent Classification, Context Retention check, and LLM Query Rewriter)
- [x] 1.2 Update `app/rag/prompt.py` to support multi-turn message formatting and standalone query integration
- [x] 1.3 Update `app/rag/generator.py` to integrate router decisions, context reuse, and routing event generation

## 2. API & Data Contract Extensions

- [x] 2.1 Update `ChatMessage` and `ChatRequest` in `app/main.py` to accept `history: Optional[List[Dict[str, str]]]`
- [x] 2.2 Update `/api/chat` and `/api/chat/stream` endpoints to stream `event: router` and handle multi-turn context

## 3. Frontend Multi-turn State & Routing UI

- [x] 3.1 Update `app/static/app.js` to maintain `chatHistory` array across turns and send it in request payloads
- [x] 3.2 Add routing badge rendering (`⚡ 沿用上下文`, `🔍 重寫檢索`, `💬 直接生成`) on message cards in `app/static/app.js`
- [x] 3.3 Add CSS styles in `app/static/style.css` for routing badges and history status
- [x] 3.4 Wire up "新對話 (New Chat)" button to clear client-side conversation history cleanly

## 4. Verification and End-to-End Testing

- [x] 4.1 Test multi-turn pronoun follow-up (e.g. Q1: RFC 8200 -> Q2: "那它廢棄了什麼？") verifying query rewriting and citation accuracy
- [x] 4.2 Test zero-RAG follow-up (e.g. "請將上面的回答整理成表格") verifying instant response without search
- [x] 4.3 Verify backward compatibility with single-turn queries
