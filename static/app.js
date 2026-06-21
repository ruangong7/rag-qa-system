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
  answerEmpty: document.getElementById("answerEmpty"),
  answerBlock: document.getElementById("answerBlock"),
  answerText: document.getElementById("answerText"),
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
  el.sendBtn.textContent = loading ? "Sending" : "Send";
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

  head.append(titleNode, metaNode);

  const bodyNode = document.createElement("pre");
  bodyNode.className = "snippet";
  bodyNode.textContent = body;

  card.append(head, bodyNode);
  return card;
}

function renderAnswer(data) {
  el.answerEmpty.classList.add("hidden");
  el.answerBlock.classList.remove("hidden");
  el.answerText.textContent = data.answer || "";
  el.confidencePill.textContent = `Confidence ${data.confidence ?? "-"}`;
  el.latencyPill.textContent = `Latency ${data.latency_ms ?? "-"} ms`;
}

function renderCitations(citations) {
  el.citationsList.innerHTML = "";
  if (!citations || citations.length === 0) {
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
  if (!contexts || contexts.length === 0) {
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

function resetResult() {
  el.answerEmpty.classList.remove("hidden");
  el.answerBlock.classList.add("hidden");
  el.answerText.textContent = "";
  el.citationsList.innerHTML = "";
  el.contextsList.innerHTML = "";
  el.citationsEmpty.classList.remove("hidden");
  el.citationsList.classList.add("hidden");
  el.contextsEmpty.classList.remove("hidden");
  el.contextsList.classList.add("hidden");
}

async function loadHealth() {
  try {
    const resp = await fetch("/health");
    if (!resp.ok) {
      throw new Error(`HTTP ${resp.status}`);
    }
    const data = await resp.json();
    el.healthStatus.textContent = data.status || "ok";
    el.docCount.textContent = String(data.documents_indexed ?? "-");
  } catch (err) {
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
    renderAnswer(data);
    renderCitations(data.citations || []);
    renderContexts(data.retrieved_contexts || []);
    el.requestMeta.textContent = `Done · ${data.latency_ms ?? "-"} ms`;
  } catch (err) {
    showError(err.message || "Request failed");
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
    resetResult();
    showError("");
    el.requestMeta.textContent = "Ready";
  });
  el.questionInput.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
      sendQuestion();
    }
  });
}

async function init() {
  bindExamples();
  bindEvents();
  resetResult();
  await loadHealth();
}

init();
