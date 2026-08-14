## Why

Automatically initializing and incrementally synchronizing the vector database upon application startup ensures zero-configuration onboarding and guarantees that the knowledge base remains in sync with the file system whenever RFC documents are added, updated, or removed.

## What Changes

- Implement an incremental RFC synchronizer (`app/indexer/sync_service.py`) that tracks document state (file hashes, modification times, indexed chunk IDs).
- Integrate the synchronizer into FastAPI's `lifespan` event so that:
  1. On first startup (empty vector store), it automatically chunks and embeds all RFCs without manual CLI intervention.
  2. On subsequent startups, it detects added/modified RFC files (incremental embedding) and deleted RFC files (pruning orphaned vector chunks from ChromaDB).
- Add sync status and progress reporting to the `/api/health` endpoint.

## Capabilities

### New Capabilities
<!-- None -->

### Modified Capabilities
- `rfc-knowledge-base`: Added automatic startup initialization, file change detection, incremental vector embedding, and orphaned chunk deletion.

## Impact

- Backend: FastAPI lifecycle in `app/main.py`, new sync service `app/indexer/sync_service.py`, index tracking state file in `data/index_state.json`.
- Zero manual script execution required for initial setup or document updates.
