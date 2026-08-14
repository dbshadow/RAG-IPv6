## 1. Incremental Sync Service Implementation

- [x] 1.1 Implement `app/indexer/sync_service.py` with state tracking (`data/index_state.json`), incremental addition, and deletion pruning
- [x] 1.2 Add `delete_rfc(rfc_id: str)` method in `app/indexer/vector_store.py` to prune vectors for removed RFCs

## 2. FastAPI Lifecycle Integration

- [x] 2.1 Integrate `lifespan` handler in `app/main.py` to trigger background sync on application startup
- [x] 2.2 Expose synchronization progress and status in `/api/health`

## 3. Verification and Testing

- [x] 3.1 Verify incremental sync on startup (no duplicate embedding of unchanged RFC files)
- [x] 3.2 Test automatic deletion pruning when an RFC file is removed
