## Context

Currently, indexing requires manually running `python scripts/index_rfcs.py`. If a user starts the web server for the first time or updates the `data/rfcs/` directory (adding or deleting RFC files), the vector store may be empty or out of sync with the underlying text files.

## Goals / Non-Goals

**Goals:**
- Automatically build the vector database on application startup if it is empty.
- Detect added or modified RFC files and incrementally index only those files.
- Detect deleted RFC files and remove their corresponding chunks from ChromaDB.
- Run startup synchronization asynchronously without blocking the web server from serving requests.
- Track index state cleanly in `data/index_state.json`.

**Non-Goals:**
- Real-time inotify file watching while the server is running (synchronization occurs on server startup/restart or trigger).

## Decisions

1. **State Tracking Structure (`data/index_state.json`)**:
   - Stores mapping:
     ```json
     {
       "rfc_id": {
         "mtime": 1723620000.0,
         "size": 45120,
         "chunk_count": 48
       }
     }
     ```
   - *Rationale*: Comparing `mtime` and file existence is lightweight (< 5ms for 153 files) and avoids unnecessary re-embedding.

2. **ChromaDB Deletion API**:
   - Use `collection.delete(where={"rfc_id": rfc_id})` when an RFC file is removed from `data/rfcs/`.

3. **FastAPI Lifespan Integration**:
   - Use `asyncio.create_task(sync_rfcs_on_startup())` inside FastAPI's `@asynccontextmanager async def lifespan(app: FastAPI)` to ensure non-blocking server startup.

## Risks / Trade-offs

- [Risk] First-time cold start indexing takes ~1-2 minutes depending on network latency to Ollama.
  → *Mitigation*: Run in background task; queries during indexing use whatever chunks are already persisted; `/api/health` indicates `indexing` state.
