"""ChromaDB vector store wrapper for IPv6 RFC chunks."""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import settings
from app.indexer.chunker import DocumentChunk

logger = logging.getLogger(__name__)

COLLECTION_NAME = "ipv6_rfcs"


class VectorStore:
    """Manages ChromaDB vector collection and queries."""

    def __init__(self, persist_directory: Optional[Path] = None) -> None:
        self.persist_directory = str(persist_directory or settings.chroma_dir)
        self.client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

    def count(self) -> int:
        """Return total number of chunks in the collection."""
        try:
            return self.collection.count()
        except Exception:
            return 0

    def add_chunks(
        self,
        chunks: List[DocumentChunk],
        embeddings: List[List[float]],
    ) -> None:
        """Add chunks and corresponding embeddings in batches to the collection."""
        if not chunks:
            return

        batch_size = 500
        for i in range(0, len(chunks), batch_size):
            b_chunks = chunks[i : i + batch_size]
            b_embeds = embeddings[i : i + batch_size]

            ids = [c.id for c in b_chunks]
            documents = [c.text for c in b_chunks]
            metadatas = [
                {
                    "rfc_id": c.rfc_id,
                    "rfc_number": c.rfc_number,
                    "rfc_title": c.rfc_title,
                    "wg": c.wg,
                    "section_number": c.section_number,
                    "section_title": c.section_title,
                    "chunk_index": c.chunk_index,
                }
                for c in b_chunks
            ]

            self.collection.upsert(
                ids=ids,
                embeddings=b_embeds,
                documents=documents,
                metadatas=metadatas,
            )

    def delete_rfc(self, rfc_id: str) -> int:
        """Delete all chunk vectors belonging to a specific RFC ID."""
        clean_id = rfc_id.lower()
        try:
            # Delete where rfc_id matches
            self.collection.delete(where={"rfc_id": clean_id})
            logger.info("Deleted chunks from vector store for %s", clean_id)
            return 1
        except Exception as exc:
            logger.warning("Error deleting vectors for %s: %s", clean_id, exc)
            return 0

    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        where_filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Search top_k most similar chunks for a given query embedding."""
        kwargs: Dict[str, Any] = {
            "query_embeddings": [query_embedding],
            "n_results": top_k,
            "include": ["documents", "metadatas", "distances"],
        }
        if where_filter:
            kwargs["where"] = where_filter

        results = self.collection.query(**kwargs)

        matched: List[Dict[str, Any]] = []
        if results and results.get("ids") and results["ids"][0]:
            ids = results["ids"][0]
            docs = results["documents"][0] if results.get("documents") else []
            metas = results["metadatas"][0] if results.get("metadatas") else []
            distances = results["distances"][0] if results.get("distances") else []

            for cid, doc, meta, dist in zip(ids, docs, metas, distances):
                similarity = 1.0 - dist if dist is not None else 0.0
                matched.append(
                    {
                        "id": cid,
                        "text": doc,
                        "metadata": meta,
                        "distance": dist,
                        "similarity": similarity,
                    }
                )

        return matched
