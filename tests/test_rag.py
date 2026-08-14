"""Integration tests for IPv6 RAG backend."""

import asyncio
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.rag.generator import RAGGenerator
from app.rag.retriever import RAGRetriever


async def test_retrieval_and_answer():
    print("Testing RAG Retriever and Generator...")
    retriever = RAGRetriever()
    generator = RAGGenerator(retriever=retriever)

    test_queries = [
        "IPv6 標頭的 Next Header 欄位作用是什麼？與 IPv4 的哪個欄位相對應？",
        "Solicited-Node Multicast 位址的前綴與格式為何？",
    ]

    for q in test_queries:
        print(f"\n==========================================")
        print(f"Question: {q}")
        print(f"------------------------------------------")
        result = await generator.answer(query=q, top_k=3)
        print(f"Answer:\n{result['answer']}")
        print(f"\nCitations count: {len(result['citations'])}")
        for c in result["citations"]:
            print(f" - [{c['ref_id']}] {c['citation_label']} ({c['rfc_title']}) - Section {c['section_number']}")


if __name__ == "__main__":
    asyncio.run(test_retrieval_and_answer())
