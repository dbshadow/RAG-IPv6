## Context

Currently, the Ollama connection parameters (`ollama_base_url`, `ollama_api_token`, `ollama_chat_model`, `ollama_embed_model`) are statically configured in `app/config.py`. Users require the ability to configure these credentials and model choices on the fly in the Web UI.

## Goals / Non-Goals

**Goals:**
- Provide a clean, accessible Settings Modal via a gear icon / button in the sidebar.
- Allow users to enter custom Ollama Base URL and Bearer API Token.
- Implement a "Fetch Models / Test Connection" button that calls `/api/ollama/models` (which queries `/api/tags` on the target Ollama instance) and categorizes models into Chat Models and Embedding Models.
- Allow fallback manual text entry for models if desired.
- Persist custom settings in `localStorage` and send them with Q&A chat requests.
- Backend dynamically creates or uses requested Ollama credentials per request.

**Non-Goals:**
- Re-indexing the entire 7,030 RFC database with every newly selected embedding model on the fly (embeddings in ChromaDB are 768-dim from `embeddinggemma:latest`). When a user selects a compatible embedding model, it is used for query vectorization.

## Decisions

1. **Backend Proxy for Model Fetching (`/api/ollama/models`)**:
   - *Rationale*: Avoids CORS and mixed-content issues when querying remote Ollama instances from the client browser.
   - Accepts `base_url` and `api_token` in query/POST, calls the target `/api/tags`, and returns sorted completion and embedding models.

2. **Per-Request Override in RAG Pipeline**:
   - `ChatRequest` model extended with:
     ```python
     class ChatRequest(BaseModel):
         query: str
         top_k: int = 5
         wg_filter: Optional[str] = None
         ollama_base_url: Optional[str] = None
         ollama_api_token: Optional[str] = None
         chat_model: Optional[str] = None
         embed_model: Optional[str] = None
     ```
   - `RAGGenerator` and `RAGRetriever` accept these parameters and default to `settings.*` when `None`.

3. **Frontend UI/UX**:
   - Sidebar displays current active model badges with a "⚙️ 連線與模型設定" button.
   - Settings Modal with field validation, show/hide token toggle, fetch status feedback, and "儲存設定" / "恢復預設" buttons.

## Risks / Trade-offs

- [Risk] User selects an embedding model with dimension mismatch against ChromaDB index (e.g. 1024-dim vs 768-dim).
  → *Mitigation*: Clearly indicate default `embeddinggemma:latest` (768-dim) in the UI, and return clear error notification if dimension mismatch occurs.
