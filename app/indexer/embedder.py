"""Ollama remote embedding client with caching and batch processing."""

import asyncio
import hashlib
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class OllamaEmbedder:
    """Handles generating embeddings via remote Ollama endpoint with local disk caching."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_token: Optional[str] = None,
        model: Optional[str] = None,
        cache_file: Optional[Path] = None,
        batch_size: int = 16,
        max_concurrency: int = 5,
    ) -> None:
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.api_token = api_token or settings.ollama_api_token
        self.model = model or settings.ollama_embed_model
        self.cache_file = cache_file or settings.embedding_cache_file
        self.batch_size = batch_size
        self.max_concurrency = max_concurrency
        self.cache: Dict[str, List[float]] = self._load_cache()

    def _get_hash(self, text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def _load_cache(self) -> Dict[str, List[float]]:
        if self.cache_file and self.cache_file.exists():
            try:
                return json.loads(self.cache_file.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning("Failed to load embedding cache: %s", e)
        return {}

    def save_cache(self) -> None:
        if self.cache_file:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            self.cache_file.write_text(json.dumps(self.cache), encoding="utf-8")

    async def get_embedding(self, text: str, client: Optional[httpx.AsyncClient] = None) -> List[float]:
        """Get embedding for a single string."""
        results = await self.get_embeddings([text], client=client)
        return results[0]

    async def _embed_batch_with_retry(
        self,
        client: httpx.AsyncClient,
        batch_texts: List[str],
        semaphore: asyncio.Semaphore,
        max_retries: int = 3,
    ) -> List[List[float]]:
        """Call Ollama /api/embed with retries."""
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }
        payload = {"model": self.model, "input": batch_texts}

        async with semaphore:
            for attempt in range(max_retries):
                try:
                    resp = await client.post(
                        f"{self.base_url}/api/embed",
                        headers=headers,
                        json=payload,
                        timeout=60.0,
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        embeddings = data.get("embeddings", [])
                        if len(embeddings) == len(batch_texts):
                            return embeddings
                        raise ValueError(f"Mismatch in returned embeddings count: {len(embeddings)} vs {len(batch_texts)}")
                    logger.warning(
                        "Ollama embed returned status %d on attempt %d: %s",
                        resp.status_code,
                        attempt + 1,
                        resp.text[:200],
                    )
                except Exception as exc:
                    logger.warning("Embed error on attempt %d: %s", attempt + 1, exc)
                    if attempt == max_retries - 1:
                        raise exc
                await asyncio.sleep(1.5 * (attempt + 1))
        raise RuntimeError("Failed to generate embeddings after retries")

    async def get_embeddings(
        self,
        texts: List[str],
        client: Optional[httpx.AsyncClient] = None,
        save_cache_interval: int = 50,
    ) -> List[List[float]]:
        """Get embeddings for a list of texts using cache and remote batching."""
        results: List[Optional[List[float]]] = [None] * len(texts)
        missing_indices: List[int] = []
        missing_texts: List[str] = []

        for i, text in enumerate(texts):
            text_hash = self._get_hash(text)
            if text_hash in self.cache:
                results[i] = self.cache[text_hash]
            else:
                missing_indices.append(i)
                missing_texts.append(text)

        if not missing_texts:
            return [r for r in results if r is not None]

        # Prepare batches
        batches = []
        for i in range(0, len(missing_texts), self.batch_size):
            batch_slice = missing_texts[i : i + self.batch_size]
            indices_slice = missing_indices[i : i + self.batch_size]
            batches.append((indices_slice, batch_slice))

        semaphore = asyncio.Semaphore(self.max_concurrency)
        should_close = False
        if client is None:
            client = httpx.AsyncClient(timeout=60.0)
            should_close = True

        try:
            for batch_idx, (indices, batch_text_list) in enumerate(batches):
                embeddings = await self._embed_batch_with_retry(client, batch_text_list, semaphore)
                for idx, text, emb in zip(indices, batch_text_list, embeddings):
                    results[idx] = emb
                    self.cache[self._get_hash(text)] = emb

                if (batch_idx + 1) % save_cache_interval == 0:
                    self.save_cache()
        finally:
            self.save_cache()
            if should_close:
                await client.aclose()

        return [r for r in results if r is not None]
