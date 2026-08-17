"""Knowledge Graph Extractor for RFC metadata and semantic entity triples."""

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

from app.config import settings
from app.graph.store import GraphEdge, GraphNode, KnowledgeGraphStore

logger = logging.getLogger(__name__)

GRAPH_EXTRACTION_SYSTEM_PROMPT = """你是一位專精於 IPv6 協定規範與知識圖譜構建的專家。
請從以下提供的 RFC 文本內容中，抽取出關鍵的「協定實體 (Entities)」以及實體之間的「技術關係 (Relationships)」。

輸出必須為合法的 JSON 格式，包含 `entities` 與 `relationships` 兩個陣列：
```json
{
  "entities": [
    {
      "id": "標準化小寫標識符(如: slaac, hop-by-hop, rfc8200, m-flag)",
      "name": "標準名詞(如: SLAAC, Hop-by-Hop Options Header)",
      "type": "protocol | header | mechanism | flag | rfc | concept",
      "description": "簡短的協定功能或定義說明"
    }
  ],
  "relationships": [
    {
      "source": "來源實體ID",
      "target": "目標實體ID",
      "relation": "DEFINES | USES | OBSOLETES | UPDATES | EXTENDS | CONTROLS | CONFLICTS_WITH | REFERENCES",
      "description": "該關係的具體技術因果或互動說明"
    }
  ]
}
```
請務必精準，僅提取高價值、強相關的技術實體與實質關係，不要抽取無意義的通用名詞。"""


class GraphExtractor:
    """Extracts deterministic document metadata relations and semantic entity-relation triples."""

    def __init__(
        self,
        store: Optional[KnowledgeGraphStore] = None,
        ollama_base_url: Optional[str] = None,
        ollama_api_token: Optional[str] = None,
        chat_model: Optional[str] = None,
    ) -> None:
        self.store = store or KnowledgeGraphStore()
        self.base_url = (ollama_base_url or settings.ollama_base_url).rstrip("/")
        self.api_token = ollama_api_token or settings.ollama_api_token
        self.chat_model = chat_model or settings.ollama_chat_model

    def extract_metadata_relations(self, metadata_file: Optional[Path] = None) -> int:
        """Deterministically extract all RFC document nodes, OBSOLETES, UPDATES, and WG relationships."""
        m_file = metadata_file or settings.metadata_file
        if not m_file.exists():
            return 0

        items = json.loads(m_file.read_text(encoding="utf-8"))
        count = 0

        for doc in items:
            rfc_id = doc.get("rfc_id", "").lower()
            rfc_num = doc.get("rfc_number", "")
            title = doc.get("title", "")
            wg = doc.get("wg", "")
            dt_url = doc.get("datatracker_url", "")

            # 1. Add RFC Document Node
            rfc_node = GraphNode(
                id=rfc_id,
                name=f"RFC {rfc_num}",
                type="rfc",
                description=f"IETF {wg} Working Group RFC: {title}",
                properties={"rfc_number": rfc_num, "wg": wg, "url": dt_url, "title": title},
            )
            self.store.add_node(rfc_node)

            # 2. Add Working Group Node & Relation
            wg_id = f"wg_{wg.lower()}"
            self.store.add_node(
                GraphNode(
                    id=wg_id,
                    name=f"IETF {wg} Working Group",
                    type="concept",
                    description=f"IETF Working Group for IPv6 {wg}",
                )
            )
            self.store.add_edge(
                GraphEdge(
                    source=wg_id,
                    target=rfc_id,
                    relation="DEFINES",
                    description=f"IETF {wg} published RFC {rfc_num}",
                    source_rfc=rfc_num,
                )
            )

            # 3. Parse Obsoletes & Updates from RFC file header
            txt_path = settings.rfcs_dir / f"{rfc_id}.txt"
            if txt_path.exists():
                try:
                    header_text = txt_path.read_text(encoding="utf-8", errors="ignore")[:2500]
                    # Parse "Obsoletes: 2460, 1883" or "Obsoletes RFC 2460"
                    obs_match = re.search(r"Obsoletes:\s*([0-9,\s]+)", header_text, re.IGNORECASE)
                    if obs_match:
                        for num in re.findall(r"\d+", obs_match.group(1)):
                            obs_id = f"rfc{num}".lower()
                            self.store.add_edge(
                                GraphEdge(
                                    source=rfc_id,
                                    target=obs_id,
                                    relation="OBSOLETES",
                                    description=f"RFC {rfc_num} obsoletes older standard RFC {num}",
                                    source_rfc=rfc_num,
                                )
                            )

                    # Parse "Updates: 4861, 4862"
                    upd_match = re.search(r"Updates:\s*([0-9,\s]+)", header_text, re.IGNORECASE)
                    if upd_match:
                        for num in re.findall(r"\d+", upd_match.group(1)):
                            upd_id = f"rfc{num}".lower()
                            self.store.add_edge(
                                GraphEdge(
                                    source=rfc_id,
                                    target=upd_id,
                                    relation="UPDATES",
                                    description=f"RFC {rfc_num} updates specifications in RFC {num}",
                                    source_rfc=rfc_num,
                                )
                            )
                except Exception as e:
                    logger.debug("Header parse error for %s: %s", rfc_id, e)

            count += 1

        self.store.save()
        logger.info("Extracted metadata relations for %d RFC documents", count)
        return count

    async def extract_semantic_triples_from_text(
        self,
        rfc_num: str,
        text_snippet: str,
    ) -> Dict[str, Any]:
        """Call Ollama LLM to extract entity/relation triples from a text chunk."""
        user_prompt = f"文件來源: RFC {rfc_num}\n\n待分析的 RFC 協定文本內容如下：\n{text_snippet}\n\n請根據指令輸出抽取出的 JSON 實體與關係："

        headers = {}
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"

        payload = {
            "model": self.chat_model,
            "messages": [
                {"role": "system", "content": GRAPH_EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "format": "json",
            "stream": False,
            "options": {"temperature": 0.1},
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(f"{self.base_url}/api/chat", json=payload, headers=headers)
                if resp.status_code != 200:
                    logger.warning("Extraction failed HTTP %d: %s", resp.status_code, resp.text[:200])
                    return {"entities": [], "relationships": []}

                data = resp.json()
                raw_content = data.get("message", {}).get("content", "{}")
                parsed = json.loads(raw_content)

                # Ingest into store
                for ent in parsed.get("entities", []):
                    if ent.get("id") and ent.get("name"):
                        self.store.add_node(
                            GraphNode(
                                id=ent["id"],
                                name=ent["name"],
                                type=ent.get("type", "concept"),
                                description=ent.get("description", ""),
                                properties={"source_rfc": rfc_num},
                            )
                        )
                        # Link entity to the defining RFC
                        self.store.add_edge(
                            GraphEdge(
                                source=f"rfc{rfc_num}".lower(),
                                target=ent["id"].lower(),
                                relation="DEFINES",
                                description=f"RFC {rfc_num} defines or discusses {ent['name']}",
                                source_rfc=rfc_num,
                            )
                        )

                for rel in parsed.get("relationships", []):
                    if rel.get("source") and rel.get("target") and rel.get("relation"):
                        self.store.add_edge(
                            GraphEdge(
                                source=rel["source"],
                                target=rel["target"],
                                relation=rel["relation"].upper(),
                                description=rel.get("description", ""),
                                source_rfc=rfc_num,
                            )
                        )

                return parsed
        except Exception as e:
            logger.error("Error extracting triples for RFC %s: %s", rfc_num, e)
            return {"entities": [], "relationships": []}
