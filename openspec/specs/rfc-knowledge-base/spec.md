## ADDED Requirements

### Requirement: RFC Document Chunking with Section Awareness
The knowledge base pipeline SHALL parse RFC text files from `data/rfcs/` and split them into semantic chunks while preserving RFC metadata and section hierarchy (RFC ID, RFC Title, Section Number, Section Title).

#### Scenario: Parse and chunk RFC files
- **WHEN** the ingestion script processes an RFC file like `rfc8200.txt`
- **THEN** it splits the content into chunks with section headers preserved in chunk metadata

### Requirement: Vector Embedding Generation via Remote Ollama
The system SHALL generate dense vector embeddings for all document chunks using the remote Ollama `embeddinggemma:latest` endpoint with batching, concurrency throttling, and embedding caching.

#### Scenario: Generate embeddings for chunks
- **WHEN** ingestion runs on new or modified chunks
- **THEN** the system calls the remote `/api/embed` endpoint and stores the 768-dimensional embeddings in the local vector store

### Requirement: Similarity Search Retrieval
The vector store SHALL support Top-K cosine/semantic similarity search for user queries, returning the most relevant chunks along with their RFC number, section, and text excerpt.

#### Scenario: Query relevant chunks
- **WHEN** a user asks a question about "IPv6 header format"
- **THEN** the retrieval engine returns the top matching chunks from relevant RFCs (such as RFC 8200) with similarity scores

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
