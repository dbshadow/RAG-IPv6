## 1. Backend Dynamic Ollama and Model Proxy Support

- [x] 1.1 Add `/api/ollama/models` proxy endpoint in `app/main.py` to query `/api/tags` with custom credentials
- [x] 1.2 Update `ChatRequest` schema, `RAGGenerator`, and `RAGRetriever` to accept dynamic `ollama_base_url`, `ollama_api_token`, `chat_model`, and `embed_model`

## 2. Frontend Settings Modal and State Management

- [x] 2.1 Add Settings Modal markup in `app/static/index.html` with inputs for Base URL, API Token, Chat Model, Embedding Model, and trigger button in the sidebar
- [x] 2.2 Implement CSS styles in `app/static/style.css` for the Settings Modal, inputs, and feedback badges
- [x] 2.3 Implement connection testing, model fetching, and localStorage persistence in `app/static/app.js`

## 3. Integration Testing and Verification

- [x] 3.1 Test fetching model tags via backend proxy with custom credentials
- [x] 3.2 Test chat generation using user-configured settings (e.g. switching between `gemma4:26b` and other available models)
