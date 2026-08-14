"""RAG Retriever module for IPv6 knowledge base."""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx

from app.config import settings
from app.indexer.embedder import OllamaEmbedder
from app.indexer.vector_store import VectorStore

logger = logging.getLogger(__name__)


@dataclass
class RetrievedChunk:
    """Represents a retrieved chunk with similarity score and metadata."""

    id: str
    rfc_id: str
    rfc_number: str
    rfc_title: str
    wg: str
    section_number: str
    section_title: str
    text: str
    similarity: float
    citation_label: str
    datatracker_url: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "rfc_id": self.rfc_id,
            "rfc_number": self.rfc_number,
            "rfc_title": self.rfc_title,
            "wg": self.wg,
            "section_number": self.section_number,
            "section_title": self.section_title,
            "text": self.text,
            "similarity": self.similarity,
            "citation_label": self.citation_label,
            "datatracker_url": self.datatracker_url,
        }


class RAGRetriever:
    """Handles semantic retrieval of RFC chunks for user queries."""

    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        embedder: Optional[OllamaEmbedder] = None,
    ) -> None:
        self.vector_store = vector_store or VectorStore(persist_directory=settings.chroma_dir)
        self.embedder = embedder or OllamaEmbedder(
            base_url=settings.ollama_base_url,
            api_token=settings.ollama_api_token,
            model=settings.ollama_embed_model,
        )

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        wg_filter: Optional[str] = None,
        client: Optional[httpx.AsyncClient] = None,
        ollama_base_url: Optional[str] = None,
        ollama_api_token: Optional[str] = None,
        embed_model: Optional[str] = None,
    ) -> List[RetrievedChunk]:
        """Retrieve top_k chunks relevant to query with dynamic embedder support."""
        if not query.strip():
            return []

        # Use custom embedder if specified
        active_embedder = self.embedder
        if ollama_base_url or ollama_api_token or embed_model:
            active_embedder = OllamaEmbedder(
                base_url=ollama_base_url or settings.ollama_base_url,
                api_token=ollama_api_token or settings.ollama_api_token,
                model=embed_model or settings.ollama_embed_model,
            )

        # 1. Embed query
        query_vector = await active_embedder.get_embedding(query, client=client)

        # 2. Filter criteria
        where_filter = None
        if wg_filter:
            where_filter = {"wg": {"$contains": wg_filter}}

        # 3. Vector search
        matches = self.vector_store.search(
            query_embedding=query_vector,
            top_k=top_k,
            where_filter=where_filter,
        )

        retrieved: List[RetrievedChunk] = []
        for m in matches:
            meta = m["metadata"]
            rfc_num = str(meta.get("rfc_number", ""))
            sec_num = str(meta.get("section_number", ""))
            sec_title = str(meta.get("section_title", ""))
            rfc_title = str(meta.get("rfc_title", f"RFC {rfc_num}"))

            citation_label = f"RFC {rfc_num}"
            if sec_num and sec_num != "0":
                citation_label += f" Section {sec_num}"

            datatracker_url = f"https://datatracker.ietf.org/doc/rfc{rfc_num}/"

            retrieved.append(
                RetrievedChunk(
                    id=m["id"],
                    rfc_id=str(meta.get("rfc_id", f"rfc{rfc_num}")),
                    rfc_number=rfc_num,
                    rfc_title=rfc_title,
                    wg=str(meta.get("wg", "")),
                    section_number=sec_num,
                    section_title=sec_title,
                    text=m["text"],
                    similarity=float(m["similarity"]),
                    citation_label=citation_label,
                    datatracker_url=datatracker_url,
                )
            )

        return retrieved
