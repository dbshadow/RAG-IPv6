## Why

Enabling users to dynamically configure their Ollama endpoint URL, Bearer API Token, Chat LLM model, and Embedding model directly from the web interface provides flexibility to switch servers, test different LLMs (e.g. `gemma4:26b`, `qwen3.6:27b`, `gpt-oss:20b`), and use personal Ollama instances without modifying server environment files.

## What Changes

- Add an **Ollama & Model Settings** modal/panel in the web UI allowing users to configure:
  - Ollama Base URL (with default prefilled)
  - API Token / Bearer Key (password masked with toggle)
  - Dynamic model fetch button that queries `/api/tags` on the target Ollama instance
  - Chat LLM model selector (populated with completion-capable models)
  - Embedding model selector (populated with embedding-capable models)
  - Save & Reset to defaults (persisted in browser `localStorage`)
- Add a proxy backend endpoint `/api/ollama/models` to safely query available models from the specified Ollama server and credentials.
- Update `/api/chat` and `/api/chat/stream` endpoints to accept optional user-specified `ollama_base_url`, `ollama_api_token`, `chat_model`, and `embed_model` per request, gracefully falling back to server defaults.

## Capabilities

### New Capabilities
<!-- None -->

### Modified Capabilities
- `qa-web-interface`: Added Ollama connection settings dialog, custom model selectors, model fetching trigger, and client-side configuration persistence.
- `rag-qa-engine`: Added per-request Ollama connection parameters (base URL, token, chat model, embedding model) and remote model listing proxy.

## Impact

- Frontend: Settings modal in `app/static/index.html`, UI state handling & model fetching in `app/static/app.js`, styles in `app/static/style.css`.
- Backend: Endpoint updates in `app/main.py`, dynamic client instantiation in `app/rag/generator.py` and `app/rag/retriever.py`.
