const state = {
  sessionId: "",
  loading: false,
};

const el = {
  questionInput: document.getElementById("questionInput"),
  sendBtn: document.getElementById("sendBtn"),
  newSessionBtn: document.getElementById("newSessionBtn"),
  sessionId: document.getElementById("sessionId"),
  healthStatus: document.getElementById("healthStatus"),
  docCount: document.getElementById("docCount"),
  requestMeta: document.getElementById("requestMeta"),
  errorBanner: document.getElementById("errorBanner"),
  messageList: document.getElementById("messageList"),
  confidencePill: document.getElementById("confidencePill"),
  latencyPill: document.getElementById("latencyPill"),
  citationsEmpty: document.getElementById("citationsEmpty"),
  citationsList: document.getElementById("citationsList"),
  contextsEmpty: document.getElementById("contextsEmpty"),
  contextsList: document.getElementById("contextsList"),
};

function setLoading(loading) {
  state.loading = loading;
  el.sendBtn.disabled = loading;
  el.sendBtn.textContent = loading ? "发送中" : "发送";
}

function setSessionId(sessionId) {
  state.sessionId = sessionId || "";
  el.sessionId.textContent = state.sessionId || "-";
}

function showError(message) {
  if (!message) {
    el.errorBanner.classList.add("hidden");
    el.errorBanner.textContent = "";
    return;
  }
  el.errorBanner.textContent = message;
  el.errorBanner.classList.remove("hidden");
}

function resetInspector() {
  el.confidencePill.textContent = "Confidence -";
  el.latencyPill.textContent = "Latency -";
  el.citationsList.innerHTML = "";
  el.contextsList.innerHTML = "";
  el.citationsEmpty.classList.remove("hidden");
  el.contextsEmpty.classList.remove("hidden");
  el.citationsList.classList.add("hidden");
  el.contextsList.classList.add("hidden");
}

function clearMessages() {
  el.messageList.innerHTML = `
    <div class="welcome-card">
      <h3>开始提问</h3>
      <p>支持中英文问题、多轮会话、引用答案和检索证据查看。</p>
    </div>
  `;
}

function scrollMessagesToBottom() {
  el.messageList.scrollTop = el.messageList.scrollHeight;
}

function appendMessage(role, title, body, meta = []) {
  const row = document.createElement("div");
  row.className = `message-row ${role}`;

  const card = document.createElement("article");
  card.className = "message-card";

  const roleNode = document.createElement("div");
  roleNode.className = "message-role";
  roleNode.textContent = title;

  const bodyNode = document.createElement("pre");
  bodyNode.className = "message-body";
  bodyNode.textContent = body;

  card.append(roleNode, bodyNode);

  if (meta.length) {
    const metaWrap = document.createElement("div");
    metaWrap.className = "message-meta";
    meta.forEach((item) => {
      const pill = document.createElement("span");
      pill.className = "mini-pill";
      pill.textContent = item;
      metaWrap.appendChild(pill);
    });
    card.appendChild(metaWrap);
  }

  row.appendChild(card);
  el.messageList.appendChild(row);
  scrollMessagesToBottom();
}

function createCard(title, meta, body) {
  const card = document.createElement("article");
  card.className = "card";

  const head = document.createElement("div");
  head.className = "card-head";

  const titleNode = document.createElement("div");
  titleNode.className = "card-title";
  titleNode.textContent = title;

  const metaNode = document.createElement("div");
  metaNode.className = "card-meta";
  metaNode.textContent = meta;

  const bodyNode = document.createElement("pre");
  bodyNode.className = "snippet";
  bodyNode.textContent = body;

  head.append(titleNode, metaNode);
  card.append(head, bodyNode);
  return card;
}

function renderInspector(data) {
  el.confidencePill.textContent = `Confidence ${data.confidence ?? "-"}`;
  el.latencyPill.textContent = `Latency ${data.latency_ms ?? "-"} ms`;
  renderCitations(data.citations || []);
  renderContexts(data.retrieved_contexts || []);
}

function renderCitations(citations) {
  el.citationsList.innerHTML = "";
  if (!citations.length) {
    el.citationsEmpty.classList.remove("hidden");
    el.citationsList.classList.add("hidden");
    return;
  }

  el.citationsEmpty.classList.add("hidden");
  el.citationsList.classList.remove("hidden");
  citations.forEach((item) => {
    const meta = `${item.source_file} · p.${item.page_number} · [${item.index}]`;
    el.citationsList.appendChild(createCard(`Citation ${item.index}`, meta, item.snippet || ""));
  });
}

function renderContexts(contexts) {
  el.contextsList.innerHTML = "";
  if (!contexts.length) {
    el.contextsEmpty.classList.remove("hidden");
    el.contextsList.classList.add("hidden");
    return;
  }

  el.contextsEmpty.classList.add("hidden");
  el.contextsList.classList.remove("hidden");
  contexts.forEach((item) => {
    const meta = `${item.source_file} · p.${item.page_number} · [${item.index}]`;
    el.contextsList.appendChild(createCard(`Context ${item.index}`, meta, item.snippet || ""));
  });
}

async function loadHealth() {
  try {
    const resp = await fetch("/health");
    const data = await resp.json();
    el.healthStatus.textContent = data.status || "ok";
    el.docCount.textContent = String(data.documents_indexed ?? "-");
  } catch {
    el.healthStatus.textContent = "Unavailable";
    el.docCount.textContent = "-";
  }
}

async function sendQuestion() {
  const question = el.questionInput.value.trim();
  if (!question || state.loading) {
    return;
  }

  showError("");
  appendMessage("user", "你", question);
  el.questionInput.value = "";
  setLoading(true);
  el.requestMeta.textContent = "Requesting";

  try {
    const resp = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question,
        session_id: state.sessionId || undefined,
      }),
    });

    const data = await resp.json();
    if (!resp.ok) {
      throw new Error(data.detail || `HTTP ${resp.status}`);
    }

    setSessionId(data.session_id);
    appendMessage("assistant", "Assistant", data.answer || "", [
      `confidence ${data.confidence ?? "-"}`,
      `${data.latency_ms ?? "-"} ms`,
      `citations ${(data.citations || []).length}`,
    ]);
    renderInspector(data);
    el.requestMeta.textContent = `Done · ${data.latency_ms ?? "-"} ms`;
  } catch (err) {
    showError(err.message || "Request failed");
    appendMessage("assistant", "Assistant", "请求失败，请检查服务状态后重试。");
    el.requestMeta.textContent = "Failed";
  } finally {
    setLoading(false);
  }
}

function bindExamples() {
  document.querySelectorAll(".example-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      el.questionInput.value = btn.dataset.question || "";
      el.questionInput.focus();
    });
  });
}

function bindEvents() {
  el.sendBtn.addEventListener("click", sendQuestion);
  el.newSessionBtn.addEventListener("click", () => {
    setSessionId("");
    clearMessages();
    resetInspector();
    showError("");
    el.requestMeta.textContent = "Ready";
    el.questionInput.focus();
  });
  el.questionInput.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
      sendQuestion();
    }
  });
}

async function init() {
  clearMessages();
  resetInspector();
  bindExamples();
  bindEvents();
  await loadHealth();
}

init();
