"""FastAPI main application for IPv6 RAG Q&A platform."""

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.config import settings
from app.indexer.sync_service import sync_service
from app.indexer.vector_store import VectorStore
from app.rag.generator import RAGGenerator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context: trigger automatic RFC sync on startup."""
    logger.info("Application starting up. Scheduling automatic RFC vector store sync...")
    # Trigger background non-blocking sync
    sync_task = asyncio.create_task(sync_service.sync())
    yield
    logger.info("Application shutting down.")


app = FastAPI(
    title="IPv6 RFC Knowledge Base & RAG Q&A Platform",
    description="Interactive RAG-powered Q&A platform backed by 6man and v6ops RFCs with strict provenance",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global generator and store instances
rag_generator = RAGGenerator()
vector_store = VectorStore()


class ChatMessage(BaseModel):
    role: str = Field(..., description="Message role ('user' or 'assistant')")
    content: str = Field(..., description="Message text content")


class ChatRequest(BaseModel):
    query: str = Field(..., description="User question regarding IPv6", min_length=1)
    history: Optional[List[ChatMessage]] = Field(None, description="Previous conversation turns")
    top_k: int = Field(5, description="Number of RFC context chunks to retrieve", ge=1, le=15)
    wg_filter: Optional[str] = Field(None, description="Filter by working group (6man or v6ops)")
    rag_mode: Optional[str] = Field("vector", description="RAG retrieval mode: 'vector', 'graph', or 'hybrid'")
    model: Optional[str] = Field(None, description="Chat LLM model name")
    chat_model: Optional[str] = Field(None, description="Chat LLM model name")
    embed_model: Optional[str] = Field(None, description="Embedding model name")
    ollama_base_url: Optional[str] = Field(None, description="Custom Ollama Base URL")
    ollama_api_token: Optional[str] = Field(None, description="Custom Bearer API Token")


class OllamaModelsRequest(BaseModel):
    base_url: Optional[str] = Field(None, description="Ollama instance base URL")
    api_token: Optional[str] = Field(None, description="Bearer API Token")


@app.get("/api/health")
async def health_check() -> Dict[str, Any]:
    """Return system health, vector count, sync status, and default configuration."""
    vector_count = vector_store.count()
    metadata_count = 0
    if settings.metadata_file.exists():
        try:
            metadata_count = len(json.loads(settings.metadata_file.read_text(encoding="utf-8")))
        except Exception:
            pass

    return {
        "status": "healthy",
        "vector_chunks_indexed": vector_count,
        "total_rfcs_metadata": metadata_count,
        "sync_info": sync_service.get_sync_status(),
        "ollama_base_url": settings.ollama_base_url,
        "embed_model": settings.ollama_embed_model,
        "chat_model": settings.ollama_chat_model,
    }


@app.post("/api/rfcs/sync")
async def trigger_sync(force: bool = Query(False, description="Force re-indexing of all files")):
    """Trigger background RFC synchronization manually."""
    task = asyncio.create_task(sync_service.sync(force=force))
    return {
        "message": "RFC synchronization triggered in background",
        "current_status": sync_service.get_sync_status(),
    }


@app.post("/api/ollama/models")
@app.get("/api/ollama/models")
async def list_ollama_models(req: Optional[OllamaModelsRequest] = None, base_url: Optional[str] = None, token: Optional[str] = None):
    """Proxy endpoint to query /api/tags from target Ollama instance."""
    target_url = (req.base_url if req and req.base_url else base_url) or settings.ollama_base_url
    target_url = target_url.rstrip("/")
    target_token = (req.api_token if req and req.api_token else token) or settings.ollama_api_token

    headers = {}
    if target_token:
        headers["Authorization"] = f"Bearer {target_token}"

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"{target_url}/api/tags", headers=headers)
            if resp.status_code != 200:
                raise HTTPException(
                    status_code=resp.status_code,
                    detail=f"Ollama server returned HTTP {resp.status_code}: {resp.text[:300]}",
                )
            data = resp.json()
            raw_models = data.get("models", [])

            chat_models = []
            embed_models = []

            for m in raw_models:
                m_name = m.get("name", "")
                caps = m.get("capabilities", [])
                details = m.get("details", {})
                family = details.get("family", "")

                is_embedding = "embedding" in caps or "embed" in m_name.lower()
                is_completion = "completion" in caps or not is_embedding

                model_info = {
                    "name": m_name,
                    "model": m.get("model", m_name),
                    "size": m.get("size", 0),
                    "family": family,
                    "capabilities": caps,
                }

                if is_embedding:
                    embed_models.append(model_info)
                if is_completion:
                    chat_models.append(model_info)

            return {
                "base_url": target_url,
                "total_models": len(raw_models),
                "chat_models": chat_models,
                "embed_models": embed_models,
                "raw_models": raw_models,
            }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to query Ollama models: %s", exc)
        raise HTTPException(status_code=502, detail=f"Failed to connect to Ollama: {str(exc)}")


@app.get("/api/rfcs")
async def list_rfcs(
    wg: Optional[str] = Query(None, description="Filter by working group (6man / v6ops)"),
    search: Optional[str] = Query(None, description="Search keyword in title or RFC number"),
) -> List[Dict[str, Any]]:
    """List all available RFCs and metadata."""
    if not settings.metadata_file.exists():
        return []
    try:
        items = json.loads(settings.metadata_file.read_text(encoding="utf-8"))
        if wg:
            items = [item for item in items if wg.lower() in item.get("wg", "").lower()]
        if search:
            q = search.lower()
            items = [
                item
                for item in items
                if q in item.get("rfc_number", "").lower()
                or q in item.get("title", "").lower()
                or q in item.get("rfc_id", "").lower()
            ]
        return items
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/rfcs/{rfc_id}")
async def get_rfc_detail(rfc_id: str) -> Dict[str, Any]:
    """Retrieve full text and metadata for a specific RFC."""
    clean_id = rfc_id.lower()
    if not clean_id.startswith("rfc"):
        clean_id = f"rfc{clean_id}"

    txt_path = settings.rfcs_dir / f"{clean_id}.txt"
    if not txt_path.exists():
        raise HTTPException(status_code=404, detail=f"RFC {clean_id} text file not found")

    content = txt_path.read_text(encoding="utf-8", errors="replace")

    meta = {}
    if settings.metadata_file.exists():
        try:
            items = json.loads(settings.metadata_file.read_text(encoding="utf-8"))
            for item in items:
                if item.get("rfc_id") == clean_id:
                    meta = item
                    break
        except Exception:
            pass

    return {
        "rfc_id": clean_id,
        "metadata": meta,
        "content": content,
    }


@app.get("/api/graph/stats")
async def graph_stats() -> Dict[str, Any]:
    """Retrieve statistics of the Fast-GraphRAG Knowledge Graph."""
    return rag_generator.graph_traverser.store.stats()


@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest) -> Dict[str, Any]:
    """Standard non-streaming Q&A with dynamic Ollama parameters, multi-turn history and RAG mode."""
    try:
        chosen_chat_model = request.chat_model or request.model
        history_list = [m.model_dump() for m in request.history] if request.history else None
        result = await rag_generator.answer(
            query=request.query,
            history=history_list,
            top_k=request.top_k,
            wg_filter=request.wg_filter,
            rag_mode=request.rag_mode or "vector",
            model=chosen_chat_model,
            ollama_base_url=request.ollama_base_url,
            ollama_api_token=request.ollama_api_token,
            embed_model=request.embed_model,
        )
        return result
    except Exception as exc:
        logger.error("Chat endpoint error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/chat/stream")
async def chat_stream_endpoint(request: ChatRequest):
    """Server-Sent Events (SSE) streaming Q&A with dynamic Ollama parameters, multi-turn history and RAG mode."""
    chosen_chat_model = request.chat_model or request.model
    chosen_rag_mode = request.rag_mode or "vector"
    history_list = [m.model_dump() for m in request.history] if request.history else None

    async def event_generator():
        try:
            async for event_item in rag_generator.answer_stream(
                query=request.query,
                history=history_list,
                top_k=request.top_k,
                wg_filter=request.wg_filter,
                rag_mode=chosen_rag_mode,
                model=chosen_chat_model,
                ollama_base_url=request.ollama_base_url,
                ollama_api_token=request.ollama_api_token,
                embed_model=request.embed_model,
            ):
                event_type = event_item.get("event", "message")
                data_payload = json.dumps(event_item.get("data", {}), ensure_ascii=False)
                yield f"event: {event_type}\ndata: {data_payload}\n\n"
        except Exception as exc:
            logger.error("Stream generation error: %s", exc)
            yield f"event: error\ndata: {json.dumps({'error': str(exc)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# Mount static directory for frontend
static_dir = Path(__file__).resolve().parent / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/")
async def serve_index():
    """Serve main SPA index page."""
    index_file = static_dir / "index.html"
    if index_file.exists():
        return HTMLResponse(content=index_file.read_text(encoding="utf-8"))
    return HTMLResponse(
        "<h1>IPv6 RAG Q&A Platform Backend</h1><p>Frontend is loading...</p>"
    )
