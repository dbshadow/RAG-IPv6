## ADDED Requirements

### Requirement: Ollama Connection and Model Settings Interface
The web interface SHALL provide a dedicated settings interface for configuring Ollama connection details (Base URL, API Token, Chat LLM model, and Embedding model) with local storage persistence.

#### Scenario: Open settings and modify Ollama connection
- **WHEN** user clicks the "連線與模型設定" button
- **THEN** a settings dialog opens allowing modification of Base URL, API Token, Chat Model, and Embedding Model

#### Scenario: Fetch available models from Ollama instance
- **WHEN** user clicks "測試連線並獲取模型清單"
- **THEN** the system contacts the Ollama server and populates the Chat LLM and Embedding Model dropdowns with available models

#### Scenario: Reset settings to server defaults
- **WHEN** user clicks "恢復預設值"
- **THEN** all connection fields and model selectors revert to the platform default configuration
