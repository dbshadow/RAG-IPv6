# IPv6 RAG Hub 🌐

**繁體中文** | [**English**](./README.md)

專為 IPv6 網路協定規範打造的雙引擎檢索增強生成（RAG）智慧問答平台。收錄來自 IETF **6man**（IPv6 Maintenance 核心規範）與 **v6ops**（IPv6 Operations 營運實務）工作組的 **153 篇正式 RFC 文件**，提供嚴謹、有據可查且精確標註章節出處的 IPv6 專業解答。

---

## ✨ 核心特色

- **雙引擎檢索架構 (Vector + Fast-GraphRAG)**：
  - **向量檢索 (Vector RAG)**：基於 ChromaDB 對 7,030 個章節感知段落進行 768 維語意搜尋（`embeddinggemma:latest`）。
  - **知識圖譜 (Fast-GraphRAG)**：記憶體知識圖譜（840 個實體節點、3,094 條關係邊），透過個人化 PageRank (PPR) 隨機漫步走訪協定演進關係（`OBSOLETES`、`UPDATES`、`DEFINES`、`USES`、`EXTENDS`）。
  - **三模式自由切換**：支援 `📊 向量`、`🕸️ 圖譜`、`⚡ 混合` 三種檢索模式，兼具微觀數值細節與宏觀協定脈絡。
- **多輪對話記憶與智慧檢索路由 (3-Tier Smart Router)**：
  - **策略 1（零檢索直連）**：自動辨識表格排版、翻譯、感謝等指令，0ms 延遲直連生成（`⚡ 對話直連`）。
  - **策略 2（上下文複用）**：追問上一輪回答中的細節或名詞（如「詳細解釋第 2 點」、「上面提到的 Hop Limit」）時，0ms 沿用現有 Context（`🔄 沿用上下文`）。
  - **策略 3（LLM 獨立問題重寫）**：自動將代名詞追問（如「那它廢棄了什麼舊標準？」）還原為語意完整的獨立檢索問題後再搜尋（`🔍 獨立檢索焦點`）。
- **嚴謹文獻引用與出處佐證**：每一則回答皆標註精確的 RFC 出處（如 `[RFC 8200 Section 3]`），並提供可互動點擊的引用徽章，一鍵展開引文片段與查看 IETF Datatracker 官網原文。
- **零配置啟動與自動向量同步**：
  - 伺服器啟動時自動檢查並建立向量與圖譜索引，支援文件變更自動增量同步與已刪除文件清理。
- **動態自訂 Ollama 連線與模型**：
  - 前端提供設定彈窗，支援自訂 Ollama 連線位址、API Bearer Token、Chat 問答模型（如 `gemma4:26b`、`qwen3.6:27b`）以及 Embedding 嵌入模型，內建連線測試與可用模型自動獲取。
- **即時串流與現代化 SPA 介面**：
  - 滿版對話介面，採用 Server-Sent Events (SSE) 實現極速即時 Token 串流、即時路由狀態呈現與 Markdown 渲染。
  - 簡約深灰 (Dark) / 明亮 (Light) 主題一鍵切換，內建 153 篇 RFC 典藏庫檢視器。

---

## 🏗️ 系統架構

```mermaid
flowchart TD
    UserQuery(["👤 使用者提問"]) --> Router{"對話智慧路由器<br/>(3-Tier Intent & Retention)"}

    Router -->|策略 1: 格式排版 / 翻譯| NoSearch["⚡ 對話直連 (零檢索延遲 0ms)"]
    Router -->|策略 2: 名詞 / 重點深入鑽研| ReuseSearch["🔄 沿用上下文 (零檢索延遲 0ms)"]
    Router -->|策略 3: 代名詞 / 需新檢索| Rewriter["🔍 LLM 問題重寫器<br/>(還原為獨立檢索問題)"]

    subgraph RetrievalEngines ["雙引擎檢索系統"]
        Rewriter -->|向量 / 混合模式| Chroma[("ChromaDB 向量資料庫<br/>7,030 RFC 段落 Chunks")]
        Rewriter -->|圖譜 / 混合模式| GraphEngine[("Fast-GraphRAG 圖譜引擎<br/>PPR 關聯子圖走訪")]
    end

    Chroma --> Fusion["🧩 提示詞融合引擎 & 出處對齊"]
    GraphEngine --> Fusion
    ReuseSearch --> Fusion
    NoSearch --> LLM["🤖 Ollama LLM 生成模型 (gemma4:26b)"]
    Fusion --> LLM

    LLM -- SSE 即時串流 + 路由與出處徽章 --> UI["🖥️ 現代化 SPA 互動介面"]
```

---

## 🚀 快速開始

### 環境需求

- Python 3.10+
- [`uv`](https://github.com/astral-sh/uv)（推薦的 Python 套件管理工具）
- 運作中的 [Ollama](https://ollama.com/) 服務（本地或遠端），並具備相應模型：
  - 生成模型：`gemma4:26b`（或 `qwen3.6:27b`、`llama3` 等）
  - 嵌入模型：`embeddinggemma:latest`（或 `mxbai-embed-large:latest`）

### 1. 複製專案與安裝依賴

```bash
git clone https://github.com/dbshadow/RAG-IPv6.git
cd RAG-IPv6

# 使用 uv 安裝虛擬環境與依賴套件
uv sync
```

### 2. (選填) 下載 RFC 文件或重建圖譜

*專案中已預先收錄完整的 153 篇 RFC 純文字文件於 `data/rfcs/` 及圖譜索引於 `data/graph/`。* 若需重新抓取或索引：

```bash
# 重新抓取 RFC 文件
uv run python scripts/download_rfcs.py

# 重新建立知識圖譜索引
uv run python scripts/index_graph.py
```

### 3. 啟動應用程式

```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

> **注意**：首次啟動時，系統將自動於背景非同步建立向量資料庫。

開啟瀏覽器前往：
👉 **`http://localhost:8000`**

---

## ⚙️ 系統設定

可透過環境變數或直接於 Web 前端設定彈窗進行調整：

| 環境變數 | 說明 | 預設值 |
|---|---|---|
| `OLLAMA_BASE_URL` | Ollama 服務 API 位址 | `https://llm.ainvc.i234.me` |
| `OLLAMA_API_TOKEN` | 反向代理驗證用 Bearer Token | *(預設內建 Token)* |
| `OLLAMA_CHAT_MODEL` | 預設問答生成模型 | `gemma4:26b` |
| `OLLAMA_EMBED_MODEL` | 預設向量嵌入模型 | `embeddinggemma:latest` |

---

## 📡 API 介面一覽

- `POST /api/chat/stream`：透過 SSE 串流傳回多輪問答 Token、路由決策與引用清單。
- `POST /api/chat`：標準 JSON 格式問答回應與多輪歷史、路由元資料。
- `GET /api/graph/stats`：取得 Fast-GraphRAG 知識圖譜統計（節點數、邊數、關係分佈）。
- `POST /api/ollama/models`：代理查詢目標 Ollama 伺服器之可用模型清單。
- `GET /api/rfcs`：取得全部 153 篇 RFC 清單與元資料（支援 WG 與關鍵字篩選）。
- `GET /api/rfcs/{rfc_id}`：取得特定 RFC 之完整純文字內容。
- `GET /api/health`：系統健康狀態、向量數量與即時同步進度。

---

## 📄 授權條款

MIT License. 詳情請參閱 [LICENSE](./LICENSE)。
