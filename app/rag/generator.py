"""LLM Generation Engine interfacing with remote Ollama instance supporting Multi-turn, Smart Router, Vector, Graph, and Hybrid RAG."""

import json
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx

from app.config import settings
from app.graph.traverser import GraphTraverser
from app.rag.prompt import SYSTEM_PROMPT, build_rag_prompt
from app.rag.retriever import RAGRetriever, RetrievedChunk
from app.rag.router import ConversationRouter, RoutingResult

logger = logging.getLogger(__name__)


class RAGGenerator:
    """Coordinates Multi-turn smart routing, Vector, Graph, and Hybrid retrieval and response generation."""

    def __init__(
        self,
        retriever: Optional[RAGRetriever] = None,
        graph_traverser: Optional[GraphTraverser] = None,
        router: Optional[ConversationRouter] = None,
        base_url: Optional[str] = None,
        api_token: Optional[str] = None,
        model: Optional[str] = None,
    ) -> None:
        self.retriever = retriever or RAGRetriever()
        self.graph_traverser = graph_traverser or GraphTraverser()
        self.router = router or ConversationRouter()
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.api_token = api_token or settings.ollama_api_token
        self.model = model or settings.ollama_chat_model

    async def answer_stream(
        self,
        query: str,
        history: Optional[List[Dict[str, str]]] = None,
        top_k: int = 5,
        wg_filter: Optional[str] = None,
        rag_mode: str = "vector",  # "vector", "graph", "hybrid"
        model: Optional[str] = None,
        ollama_base_url: Optional[str] = None,
        ollama_api_token: Optional[str] = None,
        embed_model: Optional[str] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream answer tokens and citations using SSE events with multi-turn smart routing."""
        target_model = model or self.model
        target_base_url = (ollama_base_url or self.base_url).rstrip("/")
        target_api_token = ollama_api_token or self.api_token
        mode = rag_mode.lower() if rag_mode in ("vector", "graph", "hybrid") else "vector"

        limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)

        async with httpx.AsyncClient(limits=limits, timeout=120.0) as client:
            # 1. Evaluate Multi-turn Smart Routing
            routing_res: RoutingResult = await self.router.route(
                query=query,
                history=history,
                client=client,
                ollama_base_url=target_base_url,
                ollama_api_token=target_api_token,
                chat_model=target_model,
            )

            # Yield router decision event
            yield {
                "event": "router",
                "data": {
                    "decision": routing_res.decision,
                    "standalone_query": routing_res.standalone_query,
                    "reason": routing_res.reason,
                },
            }

            chunks: List[RetrievedChunk] = []
            graph_ctx: Dict[str, Any] = {}
            active_search_query = routing_res.standalone_query

            # 2. Retrieval Execution based on Routing Decision
            if routing_res.decision in ("STANDALONE_SEARCH", "REWRITE_AND_SEARCH"):
                # Vector Retrieval
                if mode in ("vector", "hybrid"):
                    chunks = await self.retriever.retrieve(
                        query=active_search_query,
                        top_k=top_k,
                        wg_filter=wg_filter,
                        client=client,
                        ollama_base_url=target_base_url,
                        ollama_api_token=target_api_token,
                        embed_model=embed_model,
                    )

                # Graph Retrieval
                if mode in ("graph", "hybrid"):
                    try:
                        graph_ctx = await self.graph_traverser.retrieve_subgraph(
                            query=active_search_query,
                            max_nodes=8,
                            max_edges=12,
                        )
                    except Exception as g_err:
                        logger.warning("Graph traversal error: %s", g_err)

            # 3. Build Augmented Prompt with History & Context
            user_prompt, citations = build_rag_prompt(
                query=query,
                chunks=chunks,
                graph_context=graph_ctx,
                history=history,
                rag_mode=mode,
                standalone_query=active_search_query if active_search_query != query else None,
            )

            # 4. Yield Citations & Metadata Event
            yield {
                "event": "citations",
                "data": {
                    "query": query,
                    "standalone_query": active_search_query,
                    "rag_mode": mode,
                    "routing_decision": routing_res.decision,
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
                                        "routing_decision": routing_res.decision,
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
        history: Optional[List[Dict[str, str]]] = None,
        top_k: int = 5,
        wg_filter: Optional[str] = None,
        rag_mode: str = "vector",
        model: Optional[str] = None,
        ollama_base_url: Optional[str] = None,
        ollama_api_token: Optional[str] = None,
        embed_model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Non-streaming Q&A method supporting Multi-turn, Smart Router, Vector, Graph, and Hybrid modes."""
        target_model = model or self.model
        target_base_url = (ollama_base_url or self.base_url).rstrip("/")
        target_api_token = ollama_api_token or self.api_token
        mode = rag_mode.lower() if rag_mode in ("vector", "graph", "hybrid") else "vector"

        limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)

        async with httpx.AsyncClient(limits=limits, timeout=120.0) as client:
            routing_res = await self.router.route(
                query=query,
                history=history,
                client=client,
                ollama_base_url=target_base_url,
                ollama_api_token=target_api_token,
                chat_model=target_model,
            )

            chunks: List[RetrievedChunk] = []
            graph_ctx: Dict[str, Any] = {}
            active_search_query = routing_res.standalone_query

            if routing_res.decision in ("STANDALONE_SEARCH", "REWRITE_AND_SEARCH"):
                if mode in ("vector", "hybrid"):
                    chunks = await self.retriever.retrieve(
                        query=active_search_query,
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
                            query=active_search_query,
                            max_nodes=8,
                            max_edges=12,
                        )
                    except Exception as g_err:
                        logger.warning("Graph traversal error: %s", g_err)

            user_prompt, citations = build_rag_prompt(
                query=query,
                chunks=chunks,
                graph_context=graph_ctx,
                history=history,
                rag_mode=mode,
                standalone_query=active_search_query if active_search_query != query else None,
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
                "standalone_query": active_search_query,
                "routing_decision": routing_res.decision,
                "routing_reason": routing_res.reason,
                "rag_mode": mode,
                "answer": result.get("response", ""),
                "citations": citations,
                "graph_nodes": graph_ctx.get("nodes", []),
                "model": target_model,
            }
