## ADDED Requirements

### Requirement: Automatic Startup Vector Store Initialization
The system SHALL automatically detect on application startup whether the vector store is uninitialized or empty and trigger background parsing, chunking, and embedding generation for all local RFC files without manual CLI invocation.

#### Scenario: Server started with empty vector database
- **WHEN** the FastAPI server starts and `vector_store.count() == 0`
- **THEN** an asynchronous background task automatically indexes all RFC files in `data/rfcs/`

### Requirement: Incremental File Synchronization and Pruning
The synchronization service SHALL compare the current files in `data/rfcs/` against the tracked index state, embedding only newly added or modified RFC files and deleting vectors corresponding to removed RFC files.

#### Scenario: Added new RFC file
- **WHEN** a new file `rfc9999.txt` is placed in `data/rfcs/` and server restarts
- **THEN** only `rfc9999.txt` is chunked, embedded, and added to ChromaDB

#### Scenario: Deleted existing RFC file
- **WHEN** an existing RFC file is deleted from `data/rfcs/` and server restarts
- **THEN** all associated chunks for that RFC ID are removed from ChromaDB
