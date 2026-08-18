"""Multi-turn Conversational Router, Intent Classifier, and LLM Query Rewriter for IPv6 RAG."""

import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# Patterns for Strategy 1: Intent Routing (Zero-RAG direct generation for formatting/translation/politeness)
INTENT_ZERO_RAG_PATTERNS = [
    r"(?:整理|製作|轉換|輸出|畫出|排版|條列)(?:成|為)?.*(?:表格|table|markdown|清單|條列式|重點)",
    r"(?:翻譯|translate|翻成|英文|中文|日文)",
    r"^(?:謝謝|感謝|thank|thx|ok|了解|好的|收到|讚|太棒了|厲害)[!！~～\s\.]*$",
    r"(?:將上述|把上述|將上面|把上面|將剛剛|把剛剛).*(?:簡化|擴充|精簡|重新總結|總結)",
]

# Patterns for Strategy 2: Context Retention / Drill-down into previous points & terms (Zero-RAG context reuse)
INTENT_REUSE_CONTEXT_PATTERNS = [
    r"(?:請)?(?:詳細|進一步|具體)?(?:解釋|說明|介紹|闡述|展開)?(?:一下)?(?:剛剛|上述|上面|剛才)?(?:提到|說到|列出|寫|中)?(?:的)?(?:第\s*[0-9一二三四五六七八九十]+\s*[點項條個部分])",
    r"(?:請)?(?:詳細|進一步|深入)?(?:解釋|說明|介紹|闡述)(?:一下)?(?:上面|上述|剛剛|剛才)(?:提到|所說|說)的",
    r"(?:上面|上述|剛剛|剛才|前面)(?:提到|所說|說到|說|寫)的.*(?:是什麼意思|具體是指什麼|詳細功能為何|有何作用|用途為何|是做什麼)",
    r"^(?:繼續|請繼續|還有嗎|詳細說明上一點|解釋上一段|展開說明|深入解釋)$",
]

# Prompt for Strategy 3: LLM Query Rewriter (Condense conversational follow-up into standalone query)
REWRITE_SYSTEM_PROMPT = """你是一位專精於網路協定的技術查詢重寫助手。
給定先前的「對話歷史」與使用者的「當前問題」，請輸出重寫後的「獨立檢索問題 (Standalone Query)」。

要求：
1. 消除所有代名詞與指代（如「它」、「這篇標準」、「此協定」、「該欄位」），將其替換為對話歷史中明確討論的 RFC 編號或專有名詞（例如將「那它廢棄了什麼？」重寫為「RFC 8200 廢棄了哪些舊標準？」）。
2. 只輸出重寫後的單行問題，切勿添加任何前後綴或問候語。"""


@dataclass
class RoutingResult:
    decision: str  # "DIRECT_GENERATE", "REUSE_CONTEXT", "REWRITE_AND_SEARCH", "STANDALONE_SEARCH"
    standalone_query: str
    reason: str


class ConversationRouter:
    """Intelligently routes multi-turn user queries to optimize latency and retrieval accuracy."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_token: Optional[str] = None,
        chat_model: Optional[str] = None,
    ) -> None:
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.api_token = api_token or settings.ollama_api_token
        self.chat_model = chat_model or settings.ollama_chat_model

    def classify_intent_zero_rag(self, query: str) -> bool:
        """Strategy 1: Check if query is a meta-action (formatting, translation, chitchat) needing zero RAG."""
        clean_q = query.strip()
        for pattern in INTENT_ZERO_RAG_PATTERNS:
            if re.search(pattern, clean_q, re.IGNORECASE):
                return True
        return False

    def classify_intent_reuse_context(self, query: str) -> bool:
        """Strategy 2: Check if query is asking to drill-down or explain points/terms already presented in conversation history."""
        clean_q = query.strip()
        for pattern in INTENT_REUSE_CONTEXT_PATTERNS:
            if re.search(pattern, clean_q, re.IGNORECASE):
                return True
        return False

    async def rewrite_query_with_llm(
        self,
        query: str,
        history: List[Dict[str, str]],
        client: Optional[httpx.AsyncClient] = None,
        ollama_base_url: Optional[str] = None,
        ollama_api_token: Optional[str] = None,
        chat_model: Optional[str] = None,
    ) -> str:
        """Strategy 3: Rewrite conversational query into a standalone technical search query."""
        if not history:
            return query

        target_base_url = (ollama_base_url or self.base_url).rstrip("/")
        target_api_token = ollama_api_token or self.api_token
        target_model = chat_model or self.chat_model

        # Format recent history turns (last 4 messages)
        recent_history = history[-4:]
        history_text = "\n".join(
            [f"{msg.get('role', 'user')}: {msg.get('content', '')[:300]}" for msg in recent_history]
        )

        system_prompt = (
            "你是一位專精於網路協定的技術查詢重寫助手。"
            "給定先前的「對話歷史」與使用者的「當前問題」，請消除所有指代詞（如它、該標準），重寫為一個語意完整獨立的問題。"
            "只輸出重寫後的單行問題。"
        )

        user_content = f"對話歷史：\n{history_text}\n\n使用者當前問題：{query}\n\n重寫後的獨立問題："

        headers = {
            "Authorization": f"Bearer {target_api_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": target_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            "stream": False,
        }

        try:
            if client:
                resp = await client.post(
                    f"{target_base_url}/api/chat", json=payload, headers=headers, timeout=30.0
                )
                if resp.status_code == 200:
                    rewritten = resp.json().get("message", {}).get("content", "").strip().strip('"\'')
                    if rewritten and len(rewritten) >= 3:
                        logger.info("Rewrote query from '%s' to '%s'", query, rewritten)
                        return rewritten
            else:
                async with httpx.AsyncClient(timeout=30.0) as local_client:
                    resp = await local_client.post(
                        f"{target_base_url}/api/chat", json=payload, headers=headers
                    )
                    if resp.status_code == 200:
                        rewritten = resp.json().get("message", {}).get("content", "").strip().strip('"\'')
                        if rewritten and len(rewritten) >= 3:
                            logger.info("Rewrote query from '%s' to '%s'", query, rewritten)
                            return rewritten
        except Exception as exc:
            logger.warning("Query rewrite failed, falling back to original: %s", exc)

        return query

    async def route(
        self,
        query: str,
        history: Optional[List[Dict[str, str]]] = None,
        client: Optional[httpx.AsyncClient] = None,
        ollama_base_url: Optional[str] = None,
        ollama_api_token: Optional[str] = None,
        chat_model: Optional[str] = None,
    ) -> RoutingResult:
        """Execute 3-tier routing decision pipeline."""
        if not history:
            return RoutingResult(
                decision="STANDALONE_SEARCH",
                standalone_query=query,
                reason="首輪提問，直接進行全文與圖譜檢索",
            )

        # Tier 1: Check for zero-RAG intent (Format / Translate / Acknowledge)
        if self.classify_intent_zero_rag(query):
            return RoutingResult(
                decision="DIRECT_GENERATE",
                standalone_query=query,
                reason="命中指令/格式/翻譯意圖，直接基於歷史對話生成 (零檢索延遲)",
            )

        # Tier 2: Check for Context Reuse / Drill-down into previous points & terms
        if self.classify_intent_reuse_context(query):
            return RoutingResult(
                decision="REUSE_CONTEXT",
                standalone_query=query,
                reason="追問上一輪已列出之細節/名詞，直接沿用上下文生成 (零檢索延遲)",
            )

        # Tier 3: Multi-turn technical follow-up needing query resolution
        rewritten = await self.rewrite_query_with_llm(
            query=query,
            history=history,
            client=client,
            ollama_base_url=ollama_base_url,
            ollama_api_token=ollama_api_token,
            chat_model=chat_model,
        )

        if rewritten.strip() == query.strip():
            return RoutingResult(
                decision="STANDALONE_SEARCH",
                standalone_query=query,
                reason="問題語意完整，直接以原問題檢索",
            )
        else:
            return RoutingResult(
                decision="REWRITE_AND_SEARCH",
                standalone_query=rewritten,
                reason=f"還原指代詞，重寫為: {rewritten}",
            )
