"""Automatic RFC Vector Store Synchronization Service."""

import asyncio
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from app.config import settings
from app.indexer.chunker import DocumentChunk, RFCChunker
from app.indexer.embedder import OllamaEmbedder
from app.indexer.vector_store import VectorStore

logger = logging.getLogger(__name__)


class RFCSyncService:
    """Handles automatic cold-start vector initialization and incremental document sync."""

    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        embedder: Optional[OllamaEmbedder] = None,
        rfcs_dir: Optional[Path] = None,
        state_file: Optional[Path] = None,
    ) -> None:
        self.vector_store = vector_store or VectorStore()
        self.embedder = embedder or OllamaEmbedder()
        self.rfcs_dir = rfcs_dir or settings.rfcs_dir
        self.state_file = state_file or (settings.data_dir / "index_state.json")

        self.status = "idle"  # idle, indexing, ready, error
        self.current_action = "None"
        self.total_to_process = 0
        self.processed_count = 0
        self.last_sync_time: Optional[str] = None
        self.last_error: Optional[str] = None
        self._lock = asyncio.Lock()

    def _load_state(self) -> Dict[str, Any]:
        if self.state_file.exists():
            try:
                return json.loads(self.state_file.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning("Failed to load index state file: %s", e)
        return {}

    def _save_state(self, state: Dict[str, Any]) -> None:
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            self.state_file.write_text(json.dumps(state, indent=2), encoding="utf-8")
        except Exception as e:
            logger.error("Failed to save index state file: %s", e)

    def get_sync_status(self) -> Dict[str, Any]:
        """Return real-time sync status for health reporting."""
        return {
            "status": self.status,
            "current_action": self.current_action,
            "processed": self.processed_count,
            "total": self.total_to_process,
            "last_sync_time": self.last_sync_time,
            "last_error": self.last_error,
            "vector_count": self.vector_store.count(),
        }

    async def sync(self, force: bool = False) -> Dict[str, Any]:
        """Perform incremental synchronization between data/rfcs and ChromaDB."""
        if self._lock.locked():
            logger.info("RFC sync is already running, skipping trigger.")
            return self.get_sync_status()

        async with self._lock:
            self.status = "indexing"
            self.last_error = None
            start_time = time.time()

            try:
                if not self.rfcs_dir.exists():
                    logger.warning("RFCs directory not found at %s", self.rfcs_dir)
                    self.status = "ready"
                    return self.get_sync_status()

                current_files = {f.stem.lower(): f for f in self.rfcs_dir.glob("rfc*.txt")}
                state = {} if force else self._load_state()

                # If vector store is empty, treat all as new
                current_vec_count = self.vector_store.count()
                if current_vec_count == 0:
                    logger.info("Vector store is empty. Triggering full initial indexing.")
                    state = {}

                # 1. Detect deleted RFCs
                deleted_rfc_ids: Set[str] = set(state.keys()) - set(current_files.keys())
                for del_id in deleted_rfc_ids:
                    logger.info("Detected deleted RFC file: %s. Pruning vectors.", del_id)
                    self.vector_store.delete_rfc(del_id)
                    del state[del_id]

                # 2. Detect added or modified RFCs
                to_index_files: List[Path] = []
                for rfc_id, file_path in current_files.items():
                    stat = file_path.stat()
                    file_mtime = stat.st_mtime
                    file_size = stat.st_size

                    prev = state.get(rfc_id)
                    if not prev or prev.get("mtime") != file_mtime or prev.get("size") != file_size:
                        to_index_files.append(file_path)

                logger.info(
                    "RFC Sync check: %d total files, %d deleted, %d to index/update.",
                    len(current_files),
                    len(deleted_rfc_ids),
                    len(to_index_files),
                )

                if not to_index_files and not deleted_rfc_ids and current_vec_count > 0:
                    self.status = "ready"
                    self.current_action = "Up to date"
                    self.last_sync_time = datetime.now().isoformat()
                    return self.get_sync_status()

                # 3. Process new and updated files
                self.total_to_process = len(to_index_files)
                self.processed_count = 0
                chunker = RFCChunker(metadata_file=settings.metadata_file)

                for file_path in to_index_files:
                    rfc_id = file_path.stem.lower()
                    self.current_action = f"Indexing {rfc_id}"

                    # If updating an existing RFC, clean old vectors first
                    if rfc_id in state:
                        self.vector_store.delete_rfc(rfc_id)

                    chunks = chunker.chunk_file(file_path)
                    if chunks:
                        texts = [c.text for c in chunks]
                        embeddings = await self.embedder.get_embeddings(texts)
                        self.vector_store.add_chunks(chunks, embeddings)

                    stat = file_path.stat()
                    state[rfc_id] = {
                        "mtime": stat.st_mtime,
                        "size": stat.st_size,
                        "chunk_count": len(chunks),
                        "indexed_at": datetime.now().isoformat(),
                    }

                    self.processed_count += 1

                self._save_state(state)
                self.status = "ready"
                self.current_action = "Idle"
                self.last_sync_time = datetime.now().isoformat()
                elapsed = time.time() - start_time
                logger.info(
                    "RFC Sync completed in %.2fs. Total vectors now: %d",
                    elapsed,
                    self.vector_store.count(),
                )
                return self.get_sync_status()

            except Exception as exc:
                logger.error("RFC sync failed: %s", exc, exc_info=True)
                self.status = "error"
                self.last_error = str(exc)
                return self.get_sync_status()


# Global sync service instance
sync_service = RFCSyncService()
