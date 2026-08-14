"""Prompt construction and citation formatting for IPv6 RAG."""

from typing import Dict, List, Tuple
from app.rag.retriever import RetrievedChunk

SYSTEM_PROMPT = """你是一位精通 IPv6 協定規範與 IETF 標準的權威技術專家。
你的任務是根據下方提供的「權威 RFC 文件片段」回答使用者的問題。

請嚴格遵守以下規則：
1. **事實根據與嚴格引用**：你的回答內容必須完全基於所提供的 RFC 片段。在回答中的每個關鍵事實、協定行為、欄位定義或結論後方，必須標註引用出處，格式為 `[RFC <編號> Section <章節>]` 或 `[Ref <編號>]`（例如 `[RFC 8200 Section 3]`）。
2. **回答結構清晰**：
   - 優先以清楚、條理分明、專業的繁體中文解釋問題的核心概念。
   - 若涉及封包格式、旗標（Flags）、位址結構或狀態機，可使用 Markdown 表格或結構化列表輔助說明。
   - 在回答的最下方，必須附上「📚 引用出處 (RFC Citations)」區塊，列出回答中所引用的 RFC 編號、章節標題與簡短關聯說明。
3. **忠於文獻**：如果提供的 RFC 片段內容不足以回答使用者的問題，請明確說明「根據目前檢索到的 6man/v6ops RFC 文件，未提及該細節」，切勿捏造未記載於 RFC 的規範。
"""


def build_rag_prompt(query: str, chunks: List[RetrievedChunk]) -> Tuple[str, List[Dict[str, str]]]:
    """Build context prompt and structured citation list."""
    if not chunks:
        context_text = "【未檢索到相關 RFC 文件片段】"
        citations_summary = []
    else:
        context_blocks = []
        citations_summary = []
        for i, chunk in enumerate(chunks, 1):
            ref_tag = f"Ref {i}"
            block = (
                f"--- 【{ref_tag}】 {chunk.citation_label} ({chunk.rfc_title}) ---\n"
                f"章節: Section {chunk.section_number} - {chunk.section_title}\n"
                f"內容:\n{chunk.text}\n"
            )
            context_blocks.append(block)
            citations_summary.append(
                {
                    "ref_id": ref_tag,
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
            )
        context_text = "\n".join(context_blocks)

    user_prompt = f"""以下是相關的 IETF RFC 標準文件資料：

{context_text}

==================================================
使用者問題：{query}

請根據上述 RFC 文件資料提供專業、準確並帶有精確出處引用的解答："""

    return user_prompt, citations_summary
