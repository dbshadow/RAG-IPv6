"""Prompt construction and citation formatting for IPv6 Vector & Graph RAG with multi-turn support."""

from typing import Any, Dict, List, Optional, Tuple
from app.rag.retriever import RetrievedChunk

SYSTEM_PROMPT = """你是一位精通 IPv6 協定規範與 IETF 標準的權威技術專家。
你的任務是根據下方提供的「權威 RFC 文件片段」與「知識圖譜實體關係」，並結合先前的對話歷史回答使用者的問題。

請嚴格遵守以下規則：
1. **事實根據與嚴格引用**：若有提供 RFC 內容或圖譜關係，你的回答必須完全基於所提供的資料。在關鍵事實、協定行為、欄位定義、演進歷史或結論後方，必須標註引用出處，格式為 `[RFC <編號> Section <章節>]` 或 `[RFC <編號>]`（例如 `[RFC 8200 Section 3]`）。
2. **多輪對話承接**：若使用者進行追問（如要求條列總結、轉換格式、深入細節、比較），請保持對話連貫性，基於歷史對話與提供的資料進行回答。
3. **回答結構清晰**：
   - 優先以清楚、條理分明、專業的繁體中文解釋問題的核心概念。
   - 若涉及封包格式、旗標（Flags）、位址結構或狀態機，可使用 Markdown 表格或結構化列表輔助說明。
   - 在回答的最下方，若有引用 RFC，必須附上「📚 引用出處 (RFC Citations)」區塊，列出所引用的 RFC 編號、章節標題與簡短說明。
4. **忠於文獻**：如果提供的資料不足以回答使用者的技術細節問題，請明確說明「根據目前檢索到的 6man/v6ops RFC 文件與圖譜，未提及該細節」，切勿捏造未記載於 RFC 的規範。
"""


def build_rag_prompt(
    query: str,
    chunks: Optional[List[RetrievedChunk]] = None,
    graph_context: Optional[Dict[str, Any]] = None,
    history: Optional[List[Dict[str, str]]] = None,
    rag_mode: str = "vector",
    standalone_query: Optional[str] = None,
) -> Tuple[str, List[Dict[str, str]]]:
    """Build context prompt and structured citation list supporting multi-turn dialogue, Vector, Graph, and Hybrid modes."""
    context_sections = []
    citations_summary = []
    seen_citation_labels = set()

    # 1. Process Vector RAG Document Chunks (if vector or hybrid)
    if chunks and rag_mode in ("vector", "hybrid"):
        context_blocks = []
        for i, chunk in enumerate(chunks, 1):
            ref_tag = f"Ref {i}"
            block = (
                f"--- 【{ref_tag}】 {chunk.citation_label} ({chunk.rfc_title}) ---\n"
                f"章節: Section {chunk.section_number} - {chunk.section_title}\n"
                f"內容:\n{chunk.text}\n"
            )
            context_blocks.append(block)
            cit_item = {
                "ref_id": ref_tag,
                "type": "document_chunk",
                "rfc_id": chunk.rfc_id,
                "rfc_number": chunk.rfc_number,
                "rfc_title": chunk.rfc_title,
                "section_number": chunk.section_number,
                "section_title": chunk.section_title,
                "citation_label": chunk.citation_label,
                "datatracker_url": chunk.datatracker_url,
                "similarity": f"{chunk.similarity:.4f}",
                "excerpt": chunk.text[:300] + "..." if len(chunk.text) > 300 else chunk.text,
            }
            citations_summary.append(cit_item)
            seen_citation_labels.add(chunk.citation_label)

        context_sections.append("【RFC 文件段落檢索 (Vector Context)】:\n" + "\n".join(context_blocks))

    # 2. Process Fast-GraphRAG Subgraph Triples (if graph or hybrid)
    if graph_context and rag_mode in ("graph", "hybrid"):
        triples_text = graph_context.get("triples_text", "")
        if triples_text:
            context_sections.append(
                "【知識圖譜實體關係 (Fast-GraphRAG Context)】:\n"
                + triples_text
            )

        # Merge graph citations
        for g_cit in graph_context.get("citations", []):
            label = g_cit.get("citation_label", "")
            if label and label not in seen_citation_labels:
                seen_citation_labels.add(label)
                citations_summary.append(
                    {
                        "ref_id": f"Graph-{g_cit.get('rfc_number')}",
                        "type": "graph_relation",
                        "rfc_id": g_cit.get("rfc_id", ""),
                        "rfc_number": g_cit.get("rfc_number", ""),
                        "rfc_title": g_cit.get("rfc_title", ""),
                        "section_number": "Graph",
                        "section_title": g_cit.get("relation", "Relation"),
                        "citation_label": label,
                        "datatracker_url": g_cit.get("datatracker_url", ""),
                        "similarity": "Graph-PPR",
                        "excerpt": f"知識圖譜關係鏈: {g_cit.get('relation')} in RFC {g_cit.get('rfc_number')}",
                    }
                )

    # 3. Format Dialogue History if present
    history_section = ""
    if history:
        recent_turns = history[-6:]  # Up to last 3 user-assistant exchanges
        hist_lines = []
        for msg in recent_turns:
            role_name = "使用者" if msg.get("role") == "user" else "AI 助手"
            hist_lines.append(f"[{role_name}]: {msg.get('content', '')}")
        history_section = "【先前的對話歷史 (Conversation History)】:\n" + "\n".join(hist_lines) + "\n\n"

    final_context = "\n\n".join(context_sections) if context_sections else "【本輪對話無額外外部檢索資料】"

    query_display = query
    if standalone_query and standalone_query != query:
        query_display = f"{query} (檢索焦點: {standalone_query})"

    user_prompt = f"""{history_section}以下是本輪檢索之相關 IETF RFC 標準文件與知識圖譜資料（檢索模式: {rag_mode.upper()}）：

{final_context}

==================================================
使用者當前問題：{query_display}

請結合對話歷史與上述 RFC 文件/圖譜資料提供專業、準確並帶有精確出處引用的解答："""

    return user_prompt, citations_summary
