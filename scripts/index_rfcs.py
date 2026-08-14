import asyncio
import sys
import time
from pathlib import Path
from typing import List

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rich.console import Console

from app.config import settings
from app.indexer.chunker import DocumentChunk, RFCChunker
from app.indexer.embedder import OllamaEmbedder
from app.indexer.vector_store import VectorStore

console = Console()


async def main() -> None:
    console.print("[bold blue]=== IPv6 RFC Indexing Pipeline ===[/bold blue]")
    start_time = time.time()

    # 1. Check directory
    rfcs_dir = settings.rfcs_dir
    metadata_file = settings.metadata_file

    if not rfcs_dir.exists():
        console.print(f"[red]Error: RFCs directory not found at {rfcs_dir}[/red]")
        return

    rfc_files = sorted(list(rfcs_dir.glob("rfc*.txt")))
    console.print(f"Found [green]{len(rfc_files)}[/green] RFC files in {rfcs_dir}")

    # 2. Chunking
    chunker = RFCChunker(metadata_file=metadata_file)
    all_chunks: List[DocumentChunk] = []

    console.print("Parsing and chunking documents with section-awareness...")
    for file_path in rfc_files:
        chunks = chunker.chunk_file(file_path)
        all_chunks.extend(chunks)

    console.print(f"Generated [bold green]{len(all_chunks)}[/bold green] total chunks across {len(rfc_files)} RFCs.")

    # 3. Embedding
    embedder = OllamaEmbedder(
        base_url=settings.ollama_base_url,
        api_token=settings.ollama_api_token,
        model=settings.ollama_embed_model,
        cache_file=settings.embedding_cache_file,
        batch_size=32,
        max_concurrency=8,
    )

    texts = [c.text for c in all_chunks]
    cached_count = sum(1 for t in texts if embedder._get_hash(t) in embedder.cache)
    console.print(f"Embedding cache hit: [cyan]{cached_count}/{len(texts)}[/cyan] chunks already cached.")

    console.print(f"Generating embeddings via remote Ollama ([cyan]{settings.ollama_embed_model}[/cyan])...")
    embeddings = await embedder.get_embeddings(texts)
    console.print(f"[green]Successfully generated {len(embeddings)} embeddings.[/green]")

    # 4. Store in ChromaDB
    console.print("Saving embeddings and metadata into ChromaDB vector store...")
    vector_store = VectorStore(persist_directory=settings.chroma_dir)
    vector_store.add_chunks(all_chunks, embeddings)

    count = vector_store.count()
    elapsed = time.time() - start_time
    console.print(f"[bold green]✓ Indexing complete in {elapsed:.2f}s! Total vectors in store: {count}[/bold green]")

    # 5. Quick verification query
    console.print("\n[bold]Testing retrieval query: 'IPv6 header format'[/bold]")
    q_emb = await embedder.get_embedding("IPv6 header format")
    matches = vector_store.search(q_emb, top_k=3)
    for i, m in enumerate(matches, 1):
        meta = m["metadata"]
        console.print(f"  [cyan]#{i}[/cyan] RFC {meta.get('rfc_number')} Section {meta.get('section_number')} ({meta.get('section_title')}) - Sim: {m['similarity']:.4f}")


if __name__ == "__main__":
    asyncio.run(main())
