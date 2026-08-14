## ADDED Requirements

### Requirement: Interactive Chat Interface
The web interface SHALL provide a clean, modern conversational UI allowing users to ask questions regarding IPv6 specifications and receive answers.

#### Scenario: User submits question
- **WHEN** user types an IPv6 question and clicks send or presses Enter
- **THEN** the message is appended to the chat stream and an answering indicator appears

### Requirement: Real-Time Streaming and Markdown Rendering
The web interface SHALL render incoming tokens in real-time as markdown formatted text (including code blocks, bullet points, and headings).

#### Scenario: Real-time token display
- **WHEN** streaming chunks are received from the backend
- **THEN** the chat bubble updates dynamically with formatted markdown

### Requirement: Interactive Citation Inspector
The web interface SHALL display citation tags/chips for each RFC referenced in the answer, allowing users to click or hover to view the referenced RFC section, text snippet, and link to IETF datatracker.

#### Scenario: Inspect RFC reference
- **WHEN** user clicks on an RFC citation badge (e.g. `RFC 8200 Section 3`)
- **THEN** a detail card/drawer expands showing the exact excerpt and a direct link to the RFC document

### Requirement: Dark and Light Theme Switching
The web interface SHALL provide a theme toggle mechanism enabling users to switch between a Dark theme (dark gray background) and a Light theme (pure white background).

#### Scenario: Switch from Dark to Light theme
- **WHEN** user clicks the "Light" mode button
- **THEN** the interface background immediately updates to white with light theme styling and the preference is saved to localStorage

#### Scenario: Switch from Light to Dark theme
- **WHEN** user clicks the "Dark" mode button
- **THEN** the interface background immediately updates to dark gray with dark theme styling and the preference is saved to localStorage

#### Scenario: Theme persistence across page reloads
- **WHEN** user reloads or revisits the web application
- **THEN** the application initializes with the previously saved theme from localStorage

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
