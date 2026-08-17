"""Knowledge Graph indexing script for all 153 RFCs with checkpointing and resume support."""

import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Set

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings
from app.graph.extractor import GraphExtractor
from app.graph.store import KnowledgeGraphStore
from app.indexer.chunker import RFCChunker
from app.indexer.embedder import OllamaEmbedder

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("index_graph")


class GraphIndexer:
    def __init__(self) -> None:
        self.store = KnowledgeGraphStore()
        self.extractor = GraphExtractor(store=self.store)
        self.embedder = OllamaEmbedder()
        self.chunker = RFCChunker(metadata_file=settings.metadata_file)
        self.checkpoint_file = settings.graph_dir / "checkpoint.json"

    def _load_checkpoint(self) -> Set[str]:
        if self.checkpoint_file.exists():
            try:
                data = json.loads(self.checkpoint_file.read_text(encoding="utf-8"))
                return set(data.get("processed_rfcs", []))
            except Exception as e:
                logger.warning("Failed to load checkpoint: %s", e)
        return set()

    def _save_checkpoint(self, processed: Set[str]) -> None:
        self.checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "processed_rfcs": list(processed),
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "stats": self.store.stats(),
        }
        self.checkpoint_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

    async def run(self, max_sections_per_rfc: int = 4) -> None:
        logger.info("=== Starting Fast-GraphRAG Knowledge Graph Indexing ===")

        # Step 1: Deterministic metadata relations extraction
        logger.info("Step 1: Extracting RFC Document nodes and Obsoletes/Updates relations...")
        meta_count = self.extractor.extract_metadata_relations()
        logger.info("Step 1 complete: %d RFC documents loaded.", meta_count)

        # Step 2: Semantic Entity & Triple extraction from key sections
        logger.info("Step 2: Processing RFC documents for semantic entity & relation triples...")
        processed_rfcs = self._load_checkpoint()
        logger.info("Resuming from checkpoint: %d RFCs already processed.", len(processed_rfcs))

        rfc_files = sorted(list(settings.rfcs_dir.glob("rfc*.txt")))
        total_files = len(rfc_files)

        for i, file_path in enumerate(rfc_files, 1):
            rfc_id = file_path.stem.lower()
            rfc_num = rfc_id.replace("rfc", "")

            if rfc_id in processed_rfcs:
                continue

            logger.info("[%d/%d] Processing %s for entity extraction...", i, total_files, rfc_id.upper())
            start_t = time.time()

            try:
                # Extract sections using chunker
                chunks = self.chunker.chunk_file(file_path)
                # Take key sections (e.g. Introduction, Protocol Overview, Header Format, Specifications)
                selected_chunks = chunks[:max_sections_per_rfc]

                for c in selected_chunks:
                    snippet = f"--- {c.section_title} ---\n{c.text[:1200]}"
                    await self.extractor.extract_semantic_triples_from_text(
                        rfc_num=rfc_num,
                        text_snippet=snippet,
                    )

                processed_rfcs.add(rfc_id)
                self._save_checkpoint(processed_rfcs)
                self.store.save()

                elapsed = time.time() - start_t
                logger.info(
                    "[%d/%d] %s completed in %.2fs. Graph now has %d nodes, %d edges.",
                    i,
                    total_files,
                    rfc_id.upper(),
                    elapsed,
                    len(self.store.nodes),
                    len(self.store.edges),
                )
            except Exception as exc:
                logger.error("Error processing %s: %s", rfc_id, exc)

        # Step 3: Embed entity names for semantic seed matching
        logger.info("Step 3: Generating dense embeddings for entity semantic search...")
        entity_nodes = [n for n in self.store.nodes.values() if n.type != "rfc"]
        texts_to_embed = [f"{n.name}: {n.description}" for n in entity_nodes]

        if texts_to_embed:
            logger.info("Embedding %d entity nodes...", len(texts_to_embed))
            embeddings = await self.embedder.get_embeddings(texts_to_embed)
            for n, emb in zip(entity_nodes, embeddings):
                self.store.entity_embeddings[n.id] = emb
            self.store.save()
            logger.info("Entity embeddings saved successfully.")

        stats = self.store.stats()
        logger.info("=== Fast-GraphRAG Indexing Finished Successfully! ===")
        logger.info("Final Graph Stats: %s", json.dumps(stats, indent=2))


if __name__ == "__main__":
    indexer = GraphIndexer()
    asyncio.run(indexer.run())
