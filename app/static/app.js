/**
 * IPv6 RAG Q&A Platform Frontend Logic
 */

let allRFCs = [];
let currentCitations = [];

// Default fallback configuration
const DEFAULT_CONFIG = {
  ollamaBaseUrl: 'https://llm.ainvc.i234.me',
  ollamaApiToken: 'llm_2MeuVYrI4YvvLAO/xLrjf+tbPF45XebpWBFL+5m6ViI=',
  chatModel: 'gemma4:26b',
  embedModel: 'embeddinggemma:latest',
};

// Current active configuration
let userConfig = { ...DEFAULT_CONFIG };

// Initialize marked
marked.setOptions({
  breaks: true,
  highlight: function (code, lang) {
    const language = hljs.getLanguage(lang) ? lang : 'plaintext';
    return hljs.highlight(code, { language }).value;
  },
});

document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  loadUserConfig();
  loadSystemStatus();
  loadRFCsList();
  setupAutoResizeTextarea();
});

// ----------------------------------------------------
// Theme Management (Dark / Light Toggle)
// ----------------------------------------------------
function initTheme() {
  const savedTheme = localStorage.getItem('ipv6_rag_theme') || 'dark';
  setTheme(savedTheme, false);
}

function toggleTheme() {
  const current = document.documentElement.getAttribute('data-theme') || 'dark';
  const next = current === 'dark' ? 'light' : 'dark';
  setTheme(next, true);
}

function setTheme(theme, save = true) {
  document.documentElement.setAttribute('data-theme', theme);
  if (save) {
    localStorage.setItem('ipv6_rag_theme', theme);
  }

  // Update theme icons: when dark, show sun ☀️; when light, show moon 🌙
  const icon = theme === 'dark' ? '☀️' : '🌙';
  const title = theme === 'dark' ? '切換為明亮模式 (Light)' : '切換為深灰模式 (Dark)';

  const iconElem = document.getElementById('theme-icon');
  if (iconElem) iconElem.innerText = icon;

  const btnElem = document.getElementById('theme-toggle-btn');
  if (btnElem) btnElem.setAttribute('title', title);
}

// ----------------------------------------------------
// Ollama Configuration Management
// ----------------------------------------------------
function loadUserConfig() {
  const saved = localStorage.getItem('ipv6_rag_ollama_config');
  if (saved) {
    try {
      userConfig = { ...DEFAULT_CONFIG, ...JSON.parse(saved) };
    } catch (e) {
      userConfig = { ...DEFAULT_CONFIG };
    }
  }
  updateActiveModelDisplay();
}

function saveUserConfigToStorage() {
  localStorage.setItem('ipv6_rag_ollama_config', JSON.stringify(userConfig));
  updateActiveModelDisplay();
}

function updateActiveModelDisplay() {
  const chatBadge = document.getElementById('cur-chat-model');
  const embedBadge = document.getElementById('cur-embed-model');
  const hostText = document.getElementById('cur-ollama-host');

  if (chatBadge) chatBadge.innerText = userConfig.chatModel;
  if (embedBadge) embedBadge.innerText = userConfig.embedModel;
  if (hostText) {
    try {
      const u = new URL(userConfig.ollamaBaseUrl);
      hostText.innerText = u.host;
    } catch (e) {
      hostText.innerText = userConfig.ollamaBaseUrl;
    }
  }
}

function openSettingsModal() {
  document.getElementById('cfg-base-url').value = userConfig.ollamaBaseUrl;
  document.getElementById('cfg-api-token').value = userConfig.ollamaApiToken || '';

  // Populate models dropdown
  ensureModelInSelect('cfg-chat-model', userConfig.chatModel);
  ensureModelInSelect('cfg-embed-model', userConfig.embedModel);

  document.getElementById('fetch-status-text').innerText = '';
  document.getElementById('settings-modal-overlay').classList.add('active');
  document.getElementById('settings-modal').classList.add('open');

  // Trigger model fetch automatically if empty
  fetchModelsFromOllama(false);
}

function closeSettingsModal() {
  document.getElementById('settings-modal-overlay').classList.remove('active');
  document.getElementById('settings-modal').classList.remove('open');
}

function toggleTokenVisibility() {
  const tokenInput = document.getElementById('cfg-api-token');
  tokenInput.type = tokenInput.type === 'password' ? 'text' : 'password';
}

function ensureModelInSelect(selectId, modelName) {
  const select = document.getElementById(selectId);
  if (!select || !modelName) return;

  let exists = false;
  for (let i = 0; i < select.options.length; i++) {
    if (select.options[i].value === modelName) {
      exists = true;
      break;
    }
  }

  if (!exists) {
    const opt = document.createElement('option');
    opt.value = modelName;
    opt.innerText = `${modelName} (目前)`;
    select.appendChild(opt);
  }
  select.value = modelName;
}

async function fetchModelsFromOllama(showLoadingText = true) {
  const baseUrl = document.getElementById('cfg-base-url').value.trim() || userConfig.ollamaBaseUrl;
  const apiToken = document.getElementById('cfg-api-token').value.trim();
  const statusElem = document.getElementById('fetch-status-text');

  if (showLoadingText) {
    statusElem.innerText = '正在連線獲取模型清單...';
    statusElem.style.color = 'var(--text-muted)';
  }

  try {
    const resp = await fetch('/api/ollama/models', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ base_url: baseUrl, api_token: apiToken }),
    });

    if (!resp.ok) {
      const err = await resp.json();
      throw new Error(err.detail || `HTTP ${resp.status}`);
    }

    const data = await resp.json();
    const chatSelect = document.getElementById('cfg-chat-model');
    const embedSelect = document.getElementById('cfg-embed-model');

    const curChat = chatSelect.value || userConfig.chatModel;
    const curEmbed = embedSelect.value || userConfig.embedModel;

    // Populate Chat Models
    chatSelect.innerHTML = '';
    const chatModels = data.chat_models || [];
    if (chatModels.length === 0) {
      chatModels.push({ name: 'gemma4:26b' });
    }
    chatModels.forEach((m) => {
      const opt = document.createElement('option');
      opt.value = m.name;
      opt.innerText = `${m.name} ${m.family ? `(${m.family})` : ''}`;
      chatSelect.appendChild(opt);
    });
    chatSelect.value = curChat || chatModels[0].name;

    // Populate Embed Models
    embedSelect.innerHTML = '';
    const embedModels = data.embed_models || [];
    if (embedModels.length === 0) {
      embedModels.push({ name: 'embeddinggemma:latest' });
    }
    embedModels.forEach((m) => {
      const opt = document.createElement('option');
      opt.value = m.name;
      opt.innerText = m.name;
      embedSelect.appendChild(opt);
    });
    embedSelect.value = curEmbed || embedModels[0].name;

    statusElem.innerText = `✓ 連線成功！獲取到 ${data.total_models} 個模型`;
    statusElem.style.color = 'var(--success)';
  } catch (err) {
    console.error('Fetch models error:', err);
    statusElem.innerText = `連線失敗: ${err.message}`;
    statusElem.style.color = '#ef4444';
  }
}

function saveSettings() {
  const baseUrl = document.getElementById('cfg-base-url').value.trim();
  const apiToken = document.getElementById('cfg-api-token').value.trim();
  const chatModel = document.getElementById('cfg-chat-model').value.trim();
  const embedModel = document.getElementById('cfg-embed-model').value.trim();

  if (!baseUrl) {
    alert('請填寫 Ollama 連線位址');
    return;
  }

  userConfig = {
    ollamaBaseUrl: baseUrl,
    ollamaApiToken: apiToken,
    chatModel: chatModel || 'gemma4:26b',
    embedModel: embedModel || 'embeddinggemma:latest',
  };

  saveUserConfigToStorage();
  closeSettingsModal();
}

function resetSettingsToDefault() {
  if (confirm('確定要恢復為預設伺服器與模型設定嗎？')) {
    userConfig = { ...DEFAULT_CONFIG };
    saveUserConfigToStorage();
    document.getElementById('cfg-base-url').value = userConfig.ollamaBaseUrl;
    document.getElementById('cfg-api-token').value = userConfig.ollamaApiToken;
    ensureModelInSelect('cfg-chat-model', userConfig.chatModel);
    ensureModelInSelect('cfg-embed-model', userConfig.embedModel);
    document.getElementById('fetch-status-text').innerText = '已恢復預設值';
    document.getElementById('fetch-status-text').style.color = 'var(--success)';
  }
}

// ----------------------------------------------------
// UI Logic & Interactions
// ----------------------------------------------------
function setupAutoResizeTextarea() {
  const textarea = document.getElementById('user-input');
  textarea.addEventListener('input', function () {
    this.style.height = 'auto';
    this.style.height = Math.min(this.scrollHeight, 140) + 'px';
  });
}

function handleKeyDown(event) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    document.getElementById('chat-form').requestSubmit();
  }
}

function switchTab(tabId) {
  document.querySelectorAll('.nav-btn').forEach((btn) => btn.classList.remove('active'));
  document.querySelectorAll('.view-panel').forEach((panel) => panel.classList.remove('active'));

  if (tabId === 'chat') {
    document.getElementById('tab-chat').classList.add('active');
    document.getElementById('view-chat').classList.add('active');
  } else if (tabId === 'rfcs') {
    document.getElementById('tab-rfcs').classList.add('active');
    document.getElementById('view-rfcs').classList.add('active');
    if (allRFCs.length === 0) {
      loadRFCsList();
    }
  }
}

async function loadSystemStatus() {
  try {
    const res = await fetch('/api/health');
    const data = await res.json();
    document.getElementById('st-rfcs').innerText = data.total_rfcs_metadata || '153';
    document.getElementById('st-vectors').innerText = (data.vector_chunks_indexed || 0).toLocaleString();
  } catch (err) {
    console.error('Failed to load health status:', err);
  }
}

async function loadRFCsList() {
  try {
    const res = await fetch('/api/rfcs');
    allRFCs = await res.json();
    renderRFCGrid(allRFCs);
  } catch (err) {
    console.error('Failed to load RFCs:', err);
    document.getElementById('rfc-list-container').innerHTML =
      '<div class="error-state">無法載入 RFC 清單</div>';
  }
}

function renderRFCGrid(rfcs) {
  const container = document.getElementById('rfc-list-container');
  if (!rfcs || rfcs.length === 0) {
    container.innerHTML = '<div class="empty-state">查無符合條件的 RFC 文件</div>';
    return;
  }

  container.innerHTML = rfcs
    .map(
      (rfc) => `
    <div class="rfc-card">
      <div class="rfc-card-head">
        <span class="rfc-card-num">RFC ${rfc.rfc_number}</span>
        <span class="rfc-card-wg">${rfc.wg}</span>
      </div>
      <div class="rfc-card-title">${escapeHtml(rfc.title || '')}</div>
      <div class="rfc-card-actions">
        <a href="${rfc.datatracker_url}" target="_blank" class="rfc-link-btn" title="查看 IETF 官網">Datatracker ↗</a>
        <a href="${rfc.url}" target="_blank" class="rfc-link-btn" title="查看原始 TXT">TXT 原文 ↗</a>
      </div>
    </div>
  `
    )
    .join('');
}

function filterRFCList() {
  const query = document.getElementById('rfc-search-input').value.toLowerCase().trim();
  if (!query) {
    renderRFCGrid(allRFCs);
    return;
  }
  const filtered = allRFCs.filter(
    (rfc) =>
      (rfc.rfc_number && rfc.rfc_number.toLowerCase().includes(query)) ||
      (rfc.title && rfc.title.toLowerCase().includes(query)) ||
      (rfc.wg && rfc.wg.toLowerCase().includes(query))
  );
  renderRFCGrid(filtered);
}

function askPreset(question) {
  const input = document.getElementById('user-input');
  input.value = question;
  input.style.height = 'auto';
  input.style.height = Math.min(input.scrollHeight, 140) + 'px';
  document.getElementById('chat-form').requestSubmit();
}

function clearChat() {
  const container = document.getElementById('chat-messages');
  container.innerHTML = `
    <div class="welcome-container" id="welcome-screen">
      <div class="welcome-hero">
        <div class="hero-icon">🛰️</div>
        <h2>IPv6 標準規範權威問答平台</h2>
        <p>由 153 篇 IETF 6man 與 v6ops 官方 RFC 知識庫支援，每一則回答均具備明確章節出處與引文佐證。</p>
      </div>
      <div class="preset-title">常見探索問題：</div>
      <div class="preset-grid">
        <button class="preset-card" onclick="askPreset('IPv6 標頭有哪些固定欄位？與 IPv4 相比有哪些主要差異？')">
          <span class="card-icon">📦</span>
          <div class="card-text">
            <strong>IPv6 標頭結構與欄位</strong>
            <p>比較固定 40-byte 標頭與 IPv4 標頭的不同</p>
          </div>
        </button>
        <button class="preset-card" onclick="askPreset('SLAAC 無狀態自動設定與 DHCPv6 的運作原理與主要差別為何？')">
          <span class="card-icon">⚡</span>
          <div class="card-text">
            <strong>SLAAC 與 DHCPv6</strong>
            <p>Router Advertisement 旗標與位址配置機制</p>
          </div>
        </button>
        <button class="preset-card" onclick="askPreset('Solicited-Node Multicast 位址是如何計算與產生的？其用途是什麼？')">
          <span class="card-icon">🎯</span>
          <div class="card-text">
            <strong>Solicited-Node 多播位址</strong>
            <p>NDP 鄰居發現與 DAD 重複位址偵測應用</p>
          </div>
        </button>
        <button class="preset-card" onclick="askPreset('IPv6 擴充標頭 (Extension Headers) 的建議順序與處理規則為何？')">
          <span class="card-icon">🔗</span>
          <div class="card-text">
            <strong>擴充標頭處理順序</strong>
            <p>Hop-by-Hop, Routing, Fragment 等順序規範</p>
          </div>
        </button>
      </div>
    </div>
  `;
}

async function handleSend(event) {
  event.preventDefault();
  const input = document.getElementById('user-input');
  const query = input.value.trim();
  if (!query) return;

  // Remove welcome screen if exists
  const welcome = document.getElementById('welcome-screen');
  if (welcome) welcome.remove();

  const chatContainer = document.getElementById('chat-messages');

  // 1. Append User message
  const userRow = document.createElement('div');
  userRow.className = 'msg-row user';
  userRow.innerHTML = `
    <div class="msg-avatar">你</div>
    <div class="msg-bubble">${escapeHtml(query)}</div>
  `;
  chatContainer.appendChild(userRow);

  // Clear input
  input.value = '';
  input.style.height = 'auto';

  // 2. Prepare Assistant message container
  const assistantRow = document.createElement('div');
  assistantRow.className = 'msg-row assistant';
  const msgId = 'msg-' + Date.now();

  assistantRow.innerHTML = `
    <div class="msg-avatar">🤖</div>
    <div class="msg-bubble">
      <div class="citations-box" id="citations-${msgId}" style="display:none;">
        <div class="citations-header">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>
          關聯 RFC 檢索引用：
        </div>
        <div class="citation-chips" id="chips-${msgId}"></div>
      </div>
      <div class="markdown-body typing-cursor" id="body-${msgId}">正在檢索 RFC 知識庫並透過 ${escapeHtml(userConfig.chatModel)} 生成解答...</div>
    </div>
  `;
  chatContainer.appendChild(assistantRow);
  chatContainer.scrollTop = chatContainer.scrollHeight;

  // Disable send button
  const sendBtn = document.getElementById('send-btn');
  sendBtn.disabled = true;

  const topK = parseInt(document.getElementById('top-k').value, 10) || 5;
  const wgFilter = document.getElementById('wg-filter').value || null;

  let fullAnswerText = '';
  const bodyElem = document.getElementById(`body-${msgId}`);
  const citationsBox = document.getElementById(`citations-${msgId}`);
  const chipsContainer = document.getElementById(`chips-${msgId}`);

  try {
    const response = await fetch('/api/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        query: query,
        top_k: topK,
        wg_filter: wgFilter,
        chat_model: userConfig.chatModel,
        embed_model: userConfig.embedModel,
        ollama_base_url: userConfig.ollamaBaseUrl,
        ollama_api_token: userConfig.ollamaApiToken,
      }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const events = buffer.split('\n\n');
      buffer = events.pop() || '';

      for (const eventStr of events) {
        if (!eventStr.trim()) continue;

        let eventType = 'message';
        let eventData = '';

        for (const line of eventStr.split('\n')) {
          if (line.startsWith('event: ')) {
            eventType = line.replace('event: ', '').trim();
          } else if (line.startsWith('data: ')) {
            eventData = line.replace('data: ', '').trim();
          }
        }

        if (eventType === 'citations') {
          try {
            const parsed = JSON.parse(eventData);
            const citations = parsed.citations || [];
            currentCitations = citations;

            if (citations.length > 0) {
              citationsBox.style.display = 'block';
              chipsContainer.innerHTML = citations
                .map(
                  (c, idx) => `
                <button class="citation-chip" onclick="openCitationDrawer(${idx})">
                  🏷️ ${escapeHtml(c.citation_label)}
                </button>
              `
                )
                .join('');
            }
          } catch (e) {
            console.error('Failed to parse citations event:', e);
          }
        } else if (eventType === 'token') {
          try {
            const token = JSON.parse(eventData);
            fullAnswerText += token;
            bodyElem.innerHTML = marked.parse(fullAnswerText);
            chatContainer.scrollTop = chatContainer.scrollHeight;
          } catch (e) {
            fullAnswerText += eventData;
            bodyElem.innerHTML = marked.parse(fullAnswerText);
          }
        } else if (eventType === 'error') {
          bodyElem.innerHTML += `<div class="error-text" style="color:#ef4444; margin-top:10px;">⚠️ 錯誤: ${escapeHtml(
            eventData
          )}</div>`;
        } else if (eventType === 'done') {
          bodyElem.classList.remove('typing-cursor');
        }
      }
    }
  } catch (err) {
    console.error('Stream error:', err);
    bodyElem.innerHTML = `<div class="error-text" style="color:#ef4444;">連線異常或模型回應失敗：${escapeHtml(
      err.message
    )}</div>`;
  } finally {
    bodyElem.classList.remove('typing-cursor');
    sendBtn.disabled = false;
    chatContainer.scrollTop = chatContainer.scrollHeight;
  }
}

function openCitationDrawer(index) {
  const c = currentCitations[index];
  if (!c) return;

  document.getElementById('drawer-title').innerText = c.citation_label;
  document.getElementById('drawer-badge').innerText = `RFC ${c.rfc_number}`;

  const body = document.getElementById('drawer-body');
  body.innerHTML = `
    <div class="drawer-field">
      <label>文件標題</label>
      <p><strong>${escapeHtml(c.rfc_title || '')}</strong></p>
    </div>

    <div class="drawer-field">
      <label>章節資訊</label>
      <p>Section ${escapeHtml(c.section_number)}: ${escapeHtml(c.section_title)}</p>
    </div>

    <div class="drawer-field">
      <label>檢索關聯度 (Cosine Similarity)</label>
      <p style="color:var(--accent); font-family:var(--font-mono);">${c.similarity}</p>
    </div>

    <div class="drawer-field">
      <label>RFC 原始引文內容</label>
      <div class="drawer-excerpt">${escapeHtml(c.excerpt || '')}</div>
    </div>

    <div class="drawer-actions">
      <a href="${c.datatracker_url}" target="_blank" class="btn-primary">
        在 IETF Datatracker 查看此 RFC ↗
      </a>
    </div>
  `;

  document.getElementById('citation-drawer-overlay').classList.add('active');
  document.getElementById('citation-drawer').classList.add('open');
}

function closeDrawer() {
  document.getElementById('citation-drawer-overlay').classList.remove('active');
  document.getElementById('citation-drawer').classList.remove('open');
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
