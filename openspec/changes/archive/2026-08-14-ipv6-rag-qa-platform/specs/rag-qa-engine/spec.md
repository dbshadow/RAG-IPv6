## ADDED Requirements

### Requirement: Context-Augmented Prompt Construction
The RAG engine SHALL construct structured prompts combining retrieved RFC chunks, system guidelines, and user query, strictly instructing the model to rely solely on the retrieved RFC evidence.

#### Scenario: Prompt formatting with context snippets
- **WHEN** chunks are retrieved for a user query
- **THEN** the prompt formats each chunk with explicit citation identifiers `[RFC <number> Section <sec>]`

### Requirement: Remote LLM Generation with Streaming
The backend SHALL interface with the remote Ollama server using model `gemma4:26b` to stream generated answers in real time over Server-Sent Events (SSE).

#### Scenario: Stream answer generation
- **WHEN** a client initiates a streaming question request
- **THEN** the backend yields tokens incrementally via SSE until generation completes

### Requirement: Mandatory Provenance and Citation Output
The backend SHALL parse and guarantee structured citation metadata in the API response, linking every claim to its source RFC ID, RFC title, section number, and datatracker URL.

#### Scenario: Citation structure returned
- **WHEN** an answer is completed
- **THEN** the response includes a `citations` array with RFC numbers, titles, sections, and source URLs
