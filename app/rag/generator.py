"""LLM Generation Engine interfacing with remote Ollama instance supporting Vector, Graph, and Hybrid RAG."""

import json
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx

from app.config import settings
from app.graph.traverser import GraphTraverser
from app.rag.prompt import SYSTEM_PROMPT, build_rag_prompt
from app.rag.retriever import RAGRetriever, RetrievedChunk

logger = logging.getLogger(__name__)


class RAGGenerator:
    """Coordinates Vector, Graph, and Hybrid retrieval and streaming/non-streaming response generation."""

    def __init__(
        self,
        retriever: Optional[RAGRetriever] = None,
        graph_traverser: Optional[GraphTraverser] = None,
        base_url: Optional[str] = None,
        api_token: Optional[str] = None,
        model: Optional[str] = None,
    ) -> None:
        self.retriever = retriever or RAGRetriever()
        self.graph_traverser = graph_traverser or GraphTraverser()
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.api_token = api_token or settings.ollama_api_token
        self.model = model or settings.ollama_chat_model

    async def answer_stream(
        self,
        query: str,
        top_k: int = 5,
        wg_filter: Optional[str] = None,
        rag_mode: str = "vector",  # "vector", "graph", "hybrid"
        model: Optional[str] = None,
        ollama_base_url: Optional[str] = None,
        ollama_api_token: Optional[str] = None,
        embed_model: Optional[str] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream answer tokens and citation metadata using SSE events supporting Vector, Graph, and Hybrid modes."""
        target_model = model or self.model
        target_base_url = (ollama_base_url or self.base_url).rstrip("/")
        target_api_token = ollama_api_token or self.api_token
        mode = rag_mode.lower() if rag_mode in ("vector", "graph", "hybrid") else "vector"

        limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)

        async with httpx.AsyncClient(limits=limits, timeout=120.0) as client:
            chunks: List[RetrievedChunk] = []
            graph_ctx: Dict[str, Any] = {}

            # 1. Vector Retrieval (if vector or hybrid)
            if mode in ("vector", "hybrid"):
                chunks = await self.retriever.retrieve(
                    query=query,
                    top_k=top_k,
                    wg_filter=wg_filter,
                    client=client,
                    ollama_base_url=target_base_url,
                    ollama_api_token=target_api_token,
                    embed_model=embed_model,
                )

            # 2. Graph Retrieval (if graph or hybrid)
            if mode in ("graph", "hybrid"):
                try:
                    graph_ctx = await self.graph_traverser.retrieve_subgraph(
                        query=query,
                        max_nodes=8,
                        max_edges=12,
                    )
                except Exception as g_err:
                    logger.warning("Graph traversal error: %s", g_err)

            # 3. Build augmented prompt and unified citations
            user_prompt, citations = build_rag_prompt(
                query=query,
                chunks=chunks,
                graph_context=graph_ctx,
                rag_mode=mode,
            )

            # 4. Yield initial metadata event with citations & mode
            yield {
                "event": "citations",
                "data": {
                    "query": query,
                    "rag_mode": mode,
                    "citations": citations,
                    "graph_nodes": graph_ctx.get("nodes", []),
                    "model": target_model,
                },
            }

            # 5. Stream LLM generation from Ollama
            headers = {
                "Authorization": f"Bearer {target_api_token}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": target_model,
                "prompt": user_prompt,
                "system": SYSTEM_PROMPT,
                "stream": True,
                "options": {
                    "temperature": 0.2,
                    "top_p": 0.9,
                },
            }

            try:
                async with client.stream(
                    "POST",
                    f"{target_base_url}/api/generate",
                    headers=headers,
                    json=payload,
                    timeout=180.0,
                ) as response:
                    if response.status_code != 200:
                        err_text = await response.aread()
                        yield {
                            "event": "error",
                            "data": f"Remote LLM returned HTTP {response.status_code}: {err_text.decode('utf-8', errors='ignore')}",
                        }
                        return

                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue
                        try:
                            data = json.loads(line)
                            token = data.get("response", "")
                            is_done = data.get("done", False)

                            if token:
                                yield {"event": "token", "data": token}

                            if is_done:
                                yield {
                                    "event": "done",
                                    "data": {
                                        "total_duration": data.get("total_duration"),
                                        "eval_count": data.get("eval_count"),
                                        "rag_mode": mode,
                                    },
                                }
                                break
                        except Exception as parse_err:
                            logger.warning("Error parsing SSE chunk: %s", parse_err)
            except Exception as exc:
                logger.error("LLM generation stream failed: %s", exc)
                yield {"event": "error", "data": str(exc)}

    async def answer(
        self,
        query: str,
        top_k: int = 5,
        wg_filter: Optional[str] = None,
        rag_mode: str = "vector",
        model: Optional[str] = None,
        ollama_base_url: Optional[str] = None,
        ollama_api_token: Optional[str] = None,
        embed_model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Non-streaming Q&A method supporting Vector, Graph, and Hybrid modes."""
        target_model = model or self.model
        target_base_url = (ollama_base_url or self.base_url).rstrip("/")
        target_api_token = ollama_api_token or self.api_token
        mode = rag_mode.lower() if rag_mode in ("vector", "graph", "hybrid") else "vector"

        limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)

        async with httpx.AsyncClient(limits=limits, timeout=120.0) as client:
            chunks: List[RetrievedChunk] = []
            graph_ctx: Dict[str, Any] = {}

            if mode in ("vector", "hybrid"):
                chunks = await self.retriever.retrieve(
                    query=query,
                    top_k=top_k,
                    wg_filter=wg_filter,
                    client=client,
                    ollama_base_url=target_base_url,
                    ollama_api_token=target_api_token,
                    embed_model=embed_model,
                )

            if mode in ("graph", "hybrid"):
                try:
                    graph_ctx = await self.graph_traverser.retrieve_subgraph(
                        query=query,
                        max_nodes=8,
                        max_edges=12,
                    )
                except Exception as g_err:
                    logger.warning("Graph traversal error: %s", g_err)

            user_prompt, citations = build_rag_prompt(
                query=query,
                chunks=chunks,
                graph_context=graph_ctx,
                rag_mode=mode,
            )

            headers = {
                "Authorization": f"Bearer {target_api_token}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": target_model,
                "prompt": user_prompt,
                "system": SYSTEM_PROMPT,
                "stream": False,
                "options": {
                    "temperature": 0.2,
                    "top_p": 0.9,
                },
            }

            resp = await client.post(
                f"{target_base_url}/api/generate",
                headers=headers,
                json=payload,
                timeout=180.0,
            )
            if resp.status_code != 200:
                raise RuntimeError(f"Remote LLM returned HTTP {resp.status_code}: {resp.text}")

            result = resp.json()
            return {
                "query": query,
                "rag_mode": mode,
                "answer": result.get("response", ""),
                "citations": citations,
                "graph_nodes": graph_ctx.get("nodes", []),
                "model": target_model,
            }
