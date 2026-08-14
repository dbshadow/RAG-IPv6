## ADDED Requirements

### Requirement: Dynamic Ollama Connection Parameters
The backend RAG engine and API endpoints SHALL accept per-request Ollama connection parameters (Base URL, API Token, Chat Model, Embedding Model) and apply them dynamically during retrieval and generation.

#### Scenario: Request with custom Chat model
- **WHEN** a client sends a chat request with a custom model (e.g. `qwen3.6:27b`)
- **THEN** the backend uses the specified model for the generation request

#### Scenario: Proxy model tags query
- **WHEN** client queries the `/api/ollama/models` endpoint with custom base URL and token
- **THEN** the backend fetches and returns available models classified by capability (completion vs embedding)
