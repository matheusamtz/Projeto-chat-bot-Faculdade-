/* ============================================================
   Acadêmico — frontend
   Streaming SSE, markdown sanitizado (DOMPurify), highlight de
   código, persistência em localStorage, drawer mobile.
   ============================================================ */
"use strict";

const $ = (s) => document.querySelector(s);
const messagesEl = $("#messages");
const chatEl = $("#chat");
const inputEl = $("#input");
const sendBtn = $("#send");
const emptyState = $("#empty-state");
const jumpBtn = $("#jump-btn");
const toastEl = $("#toast");
const charCount = $("#char-count");

const STORAGE_KEY = "academico:chat:v2";
const MAX_SAVED = 60;

let history = [];        // [{role, content, meta?}]
let streaming = false;
let abortCtrl = null;
let lastUserText = "";
let stickToBottom = true;

/* ---------------- ícones (SVG inline) ---------------- */
const ICONS = {
  copy: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>',
  check: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>',
  chevron: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m6 9 6 6 6-6"/></svg>',
  file: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/></svg>',
  retry: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12a9 9 0 1 0 2.6-6.4L3 8"/><path d="M3 3v5h5"/></svg>',
  sparkles: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3z"/></svg>',
  book: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/></svg>',
  calendar: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/></svg>',
  layers: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m12 2-10 5 10 5 10-5z"/><path d="m2 17 10 5 10-5M2 12l10 5 10-5"/></svg>',
};

const INTENT_INFO = {
  conteudo:   { label: "Conteúdo · RAG",      icon: ICONS.book },
  calendario: { label: "Calendário do aluno", icon: ICONS.calendar },
  hibrido:    { label: "Híbrido · RAG + dados", icon: ICONS.layers },
};

/* ---------------- util ---------------- */
function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

marked.setOptions({ breaks: true, gfm: true });

/* Protege trechos LaTeX (\(..\), \[..\], $$..$$) do parser markdown,
   restaurando-os depois para o KaTeX renderizar. */
const MATH_RE = /(\$\$[\s\S]+?\$\$|\\\[[\s\S]+?\\\]|\\\([\s\S]+?\\\))/g;
function renderMarkdown(text) {
  const math = [];
  const protectedText = text.replace(MATH_RE, (m) => {
    math.push(m);
    return `@@MATH_${math.length - 1}@@`;
  });
  let html = DOMPurify.sanitize(marked.parse(protectedText), { ADD_ATTR: ["target"] });
  html = html.replace(/@@MATH_(\d+)@@/g, (_, i) => escapeHtml(math[+i] ?? ""));
  return html;
}

function renderMath(el) {
  if (typeof renderMathInElement !== "function") return;
  try {
    renderMathInElement(el, {
      delimiters: [
        { left: "$$", right: "$$", display: true },
        { left: "\\[", right: "\\]", display: true },
        { left: "\\(", right: "\\)", display: false },
      ],
      throwOnError: false,
    });
  } catch { /* segue sem math */ }
}

function showToast(msg) {
  toastEl.textContent = msg;
  toastEl.classList.add("show");
  clearTimeout(showToast._t);
  showToast._t = setTimeout(() => toastEl.classList.remove("show"), 2200);
}

async function copyText(text, btn) {
  try {
    await navigator.clipboard.writeText(text);
    if (btn) {
      const prev = btn.innerHTML;
      btn.innerHTML = ICONS.check;
      setTimeout(() => { btn.innerHTML = prev; }, 1400);
    }
    showToast("Copiado!");
  } catch {
    showToast("Não foi possível copiar");
  }
}

/* ---------------- persistência ---------------- */
function persist() {
  try {
    const slim = history.slice(-MAX_SAVED).map((m) => ({
      role: m.role, content: m.content, meta: m.meta || null,
    }));
    localStorage.setItem(STORAGE_KEY, JSON.stringify(slim));
  } catch { /* quota cheia: ignora */ }
}
function restore() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return;
    const saved = JSON.parse(raw);
    if (!Array.isArray(saved) || !saved.length) return;
    history = saved;
    for (const m of saved) {
      if (m.role === "user") appendUserMessage(m.content);
      else if (m.role === "assistant") {
        const ui = appendBotShell();
        finalizeBotMessage(ui, m.content, m.meta || {});
      }
    }
    scrollToBottom(true);
  } catch { localStorage.removeItem(STORAGE_KEY); }
}
function clearChat() {
  if (streaming) abortCtrl?.abort();
  history = [];
  localStorage.removeItem(STORAGE_KEY);
  messagesEl.innerHTML = "";
  emptyState.style.display = "";
  inputEl.focus();
}

/* ---------------- scroll ---------------- */
function isNearBottom() {
  return chatEl.scrollHeight - chatEl.scrollTop - chatEl.clientHeight < 130;
}
function scrollToBottom(force = false) {
  if (force || stickToBottom) chatEl.scrollTop = chatEl.scrollHeight;
}
chatEl.addEventListener("scroll", () => {
  stickToBottom = isNearBottom();
  jumpBtn.classList.toggle("visible", !stickToBottom);
});
jumpBtn.addEventListener("click", () => {
  chatEl.scrollTo({ top: chatEl.scrollHeight, behavior: "smooth" });
});

/* ---------------- render de mensagens ---------------- */
function hideEmptyState() { emptyState.style.display = "none"; }

function appendUserMessage(text) {
  hideEmptyState();
  const wrap = document.createElement("div");
  wrap.className = "msg user";
  wrap.innerHTML = `
    <div class="msg-avatar">${escapeHtml(userInitial)}</div>
    <div class="msg-body"><div class="msg-bubble"></div></div>`;
  wrap.querySelector(".msg-bubble").textContent = text;
  messagesEl.appendChild(wrap);
  scrollToBottom(true);
}

function appendBotShell() {
  hideEmptyState();
  const wrap = document.createElement("div");
  wrap.className = "msg bot";
  wrap.innerHTML = `
    <div class="msg-avatar">${ICONS.sparkles}</div>
    <div class="msg-body">
      <div class="msg-meta"></div>
      <div class="msg-bubble">
        <span class="thinking">
          <span class="thinking-dots"><span></span><span></span><span></span></span>
          consultando…
        </span>
      </div>
      <div class="msg-foot"></div>
    </div>`;
  messagesEl.appendChild(wrap);
  scrollToBottom();
  return {
    wrap,
    meta: wrap.querySelector(".msg-meta"),
    bubble: wrap.querySelector(".msg-bubble"),
    foot: wrap.querySelector(".msg-foot"),
  };
}

function setIntentChip(ui, intent, prob) {
  const info = INTENT_INFO[intent];
  if (!info) return;
  const pct = prob != null ? ` <span class="pct">${Math.round(prob * 100)}%</span>` : "";
  ui.meta.innerHTML =
    `<span class="intent-chip ${escapeHtml(intent)}" title="Rota decidida pelo classificador de intenção">
       ${info.icon} ${info.label}${pct}
     </span>`;
}

function enhanceCodeBlocks(bubble) {
  bubble.querySelectorAll("pre").forEach((pre) => {
    const code = pre.querySelector("code");
    if (code && window.hljs) { try { hljs.highlightElement(code); } catch { /* segue sem highlight */ } }
    if (!pre.querySelector(".code-copy")) {
      const btn = document.createElement("button");
      btn.className = "code-copy";
      btn.setAttribute("aria-label", "Copiar código");
      btn.innerHTML = ICONS.copy;
      btn.addEventListener("click", () => copyText(code ? code.innerText : pre.innerText, btn));
      pre.appendChild(btn);
    }
  });
}

function renderSources(ui, sources) {
  if (!sources || !sources.length) return;
  const list = document.createElement("div");
  list.className = "sources-list";
  list.innerHTML = sources.map((s) => `
    <div class="source-item">
      ${ICONS.file}
      <span class="source-name">${escapeHtml(s.source)}</span>
      <span class="source-sec">${escapeHtml(s.section)}</span>
      <span class="score-bar"><span class="score-fill" style="width:${Math.round(Math.min(1, Math.max(0, s.score)) * 100)}%"></span></span>
      <span class="score-num">${Number(s.score).toFixed(2)}</span>
    </div>`).join("");

  const toggle = document.createElement("button");
  toggle.className = "sources-toggle";
  toggle.innerHTML = `${sources.length} fonte${sources.length > 1 ? "s" : ""} consultada${sources.length > 1 ? "s" : ""} ${ICONS.chevron}`;
  toggle.addEventListener("click", () => {
    toggle.classList.toggle("open");
    list.classList.toggle("open");
  });

  const row = ui.foot.querySelector(".foot-row") || ui.foot.appendChild(Object.assign(document.createElement("div"), { className: "foot-row" }));
  row.prepend(toggle);
  ui.foot.appendChild(list);
}

function addCopyAction(ui, text) {
  const row = ui.foot.querySelector(".foot-row") || ui.foot.appendChild(Object.assign(document.createElement("div"), { className: "foot-row" }));
  const btn = document.createElement("button");
  btn.className = "action-btn";
  btn.setAttribute("aria-label", "Copiar resposta");
  btn.innerHTML = `${ICONS.copy} copiar`;
  btn.addEventListener("click", () => copyText(text, btn));
  row.appendChild(btn);
}

function finalizeBotMessage(ui, content, meta) {
  ui.bubble.innerHTML = renderMarkdown(content);
  renderMath(ui.bubble);
  enhanceCodeBlocks(ui.bubble);
  if (meta.intent) setIntentChip(ui, meta.intent, meta.intentProb);
  renderSources(ui, meta.sources);
  addCopyAction(ui, content);
  if (meta.stopped) {
    const note = document.createElement("span");
    note.className = "stopped-note";
    note.textContent = "geração interrompida";
    (ui.foot.querySelector(".foot-row") || ui.foot).appendChild(note);
  }
}

function showError(ui, message, canRetry) {
  ui.bubble.innerHTML = `
    <div class="error-box">
      <span>⚠ ${escapeHtml(message)}</span>
      ${canRetry ? `<button class="retry-btn">${ICONS.retry} tentar de novo</button>` : ""}
    </div>`;
  const retry = ui.bubble.querySelector(".retry-btn");
  if (retry) retry.addEventListener("click", () => {
    ui.wrap.remove();
    send(lastUserText, { resend: true });
  });
}

/* ---------------- streaming ---------------- */
function setStreamingState(on) {
  streaming = on;
  sendBtn.classList.toggle("streaming", on);
  sendBtn.setAttribute("aria-label", on ? "Parar geração" : "Enviar mensagem");
}

async function send(text, { resend = false } = {}) {
  text = (text ?? inputEl.value).trim();
  if (!text || streaming) return;

  if (!resend) {
    inputEl.value = "";
    inputEl.style.height = "auto";
    updateCharCount();
    appendUserMessage(text);
    history.push({ role: "user", content: text });
    persist();
  }
  lastUserText = text;

  const ui = appendBotShell();
  setStreamingState(true);
  abortCtrl = new AbortController();

  let acc = "";
  const meta = {};
  let renderQueued = false;
  const renderPartial = () => {
    if (renderQueued) return;
    renderQueued = true;
    requestAnimationFrame(() => {
      renderQueued = false;
      ui.bubble.innerHTML = renderMarkdown(acc) + '<span class="typing-cursor"></span>';
      scrollToBottom();
    });
  };

  try {
    const r = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: text,
        history: history.slice(0, -1).map((m) => ({ role: m.role, content: m.content })),
      }),
      signal: abortCtrl.signal,
    });
    if (!r.ok) {
      let detail = "";
      try { detail = (await r.json()).error || ""; } catch { /* corpo não-JSON */ }
      throw new Error(detail || `servidor respondeu ${r.status}`);
    }
    if (!r.body) throw new Error("resposta sem corpo");

    const reader = r.body.getReader();
    const dec = new TextDecoder();
    let buf = "";
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += dec.decode(value, { stream: true });
      const lines = buf.split("\n");
      buf = lines.pop();
      for (const line of lines) {
        if (!line.startsWith("data:")) continue;
        const json = line.slice(5).trim();
        if (!json) continue;
        let obj;
        try { obj = JSON.parse(json); } catch { continue; }
        if (obj.meta) {
          meta.intent = obj.meta.intent;
          meta.intentProb = obj.meta.intent_prob;
          setIntentChip(ui, meta.intent, meta.intentProb);
        } else if (obj.delta) {
          acc += obj.delta;
          renderPartial();
        } else if (obj.error) {
          throw new Error(obj.error);
        } else if (obj.done) {
          meta.sources = obj.sources || [];
          if (obj.intent && !meta.intent) {
            meta.intent = obj.intent;
            meta.intentProb = obj.intent_probs?.[0]?.prob;
          }
        }
      }
    }

    finalizeBotMessage(ui, acc, meta);
    history.push({ role: "assistant", content: acc, meta });
    persist();
  } catch (e) {
    if (e.name === "AbortError") {
      if (acc) {
        meta.stopped = true;
        finalizeBotMessage(ui, acc, meta);
        history.push({ role: "assistant", content: acc, meta });
        persist();
      } else {
        ui.wrap.remove();
      }
    } else {
      showError(ui, e.message || "falha de conexão com o servidor", true);
    }
  } finally {
    setStreamingState(false);
    abortCtrl = null;
    inputEl.focus();
  }
}

function sendQuick(text) {
  if (streaming) { showToast("Aguarde a resposta atual terminar"); return; }
  send(text);
}

/* ---------------- sidebar: dados do aluno ---------------- */
let userInitial = "·";

function daysUntil(isoDate) {
  const today = new Date(); today.setHours(0, 0, 0, 0);
  const target = new Date(isoDate + "T00:00:00");
  return Math.round((target - today) / 86400000);
}
function formatWhen(dias) {
  if (dias === 0) return "hoje";
  if (dias === 1) return "amanhã";
  if (dias < 0) return `há ${-dias}d`;
  return `em ${dias}d`;
}

async function loadStudent() {
  try {
    const r = await fetch("/api/student");
    if (!r.ok) throw new Error(r.status);
    const data = await r.json();
    const a = data.aluno;

    userInitial = (a.nome || "A").charAt(0).toUpperCase();
    const nameEl = $("#student-name"), emailEl = $("#student-email");
    nameEl.textContent = a.nome;
    emailEl.textContent = a.email;
    nameEl.classList.remove("skeleton");
    emailEl.classList.remove("skeleton");
    $("#student-avatar").textContent = userInitial;
    $("#student-semestre").textContent = a.semestre_atual + "º";
    $("#student-matricula").textContent = (a.matricula || "").split("-").pop();
    const firstName = (a.nome || "").split(" ")[0];
    $("#empty-title").textContent = `Olá, ${firstName} 👋`;

    const coursesEl = $("#courses-list");
    coursesEl.innerHTML = "";
    data.matriculas.forEach((m) => {
      const btn = document.createElement("button");
      btn.className = "course-chip";
      btn.title = m.horario || "";
      btn.innerHTML = `
        <span class="course-code">${escapeHtml(m.codigo)}</span>
        <span class="course-name">${escapeHtml(m.nome)}</span>`;
      btn.addEventListener("click", () => {
        closeSidebar();
        sendQuick(`Me fala sobre a disciplina ${m.codigo} — ${m.nome}: ementa, avaliações e como ir bem nela.`);
      });
      coursesEl.appendChild(btn);
    });

    const upEl = $("#upcoming-list");
    upEl.innerHTML = "";
    if (!data.proximas.length) {
      upEl.innerHTML = `<div class="upcoming-empty">Nenhuma atividade pendente.</div>`;
    } else {
      data.proximas.forEach((p) => {
        const dias = daysUntil(p.data_entrega);
        let cls = "";
        if (dias <= 3) cls = "urgent";
        else if (dias <= 7) cls = "soon";
        const btn = document.createElement("button");
        btn.className = "upcoming-item " + cls;
        btn.innerHTML = `
          <div class="upcoming-top">
            <span class="upcoming-type">${escapeHtml(p.tipo)}</span>
            <span class="upcoming-when">${formatWhen(dias)}</span>
          </div>
          <div class="upcoming-desc">${escapeHtml(p.descricao)}</div>
          <div class="upcoming-disc">${escapeHtml(p.disciplina_codigo)} · ${escapeHtml(p.disciplina)}</div>`;
        btn.addEventListener("click", () => {
          closeSidebar();
          sendQuick(`Me ajuda a me preparar para: ${p.descricao} (${p.disciplina}). O que cai e como devo estudar?`);
        });
        upEl.appendChild(btn);
      });
    }
  } catch (e) {
    console.error("Falha ao carregar aluno:", e);
    $("#student-name").textContent = "Erro ao carregar";
    $("#student-name").classList.remove("skeleton");
    $("#student-email").classList.remove("skeleton");
  }
}

/* ---------------- drawer mobile ---------------- */
const sidebar = $("#sidebar");
const scrim = $("#scrim");
function openSidebar() {
  sidebar.classList.add("open");
  scrim.classList.add("show");
}
function closeSidebar() {
  sidebar.classList.remove("open");
  scrim.classList.remove("show");
}
$("#menu-btn").addEventListener("click", openSidebar);
$("#sidebar-close").addEventListener("click", closeSidebar);
scrim.addEventListener("click", closeSidebar);
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") closeSidebar();
});

/* ---------------- input ---------------- */
function updateCharCount() {
  const len = inputEl.value.length;
  if (len > 3400) {
    charCount.textContent = `${len}/4000`;
    charCount.classList.toggle("warn", len > 3800);
  } else {
    charCount.textContent = "";
  }
}
inputEl.addEventListener("input", () => {
  inputEl.style.height = "auto";
  inputEl.style.height = Math.min(inputEl.scrollHeight, 180) + "px";
  updateCharCount();
});
inputEl.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    send();
  }
});
sendBtn.addEventListener("click", () => {
  if (streaming) abortCtrl?.abort();
  else send();
});
$("#new-chat").addEventListener("click", clearChat);

document.querySelectorAll(".suggestion-card").forEach((el) => {
  el.addEventListener("click", () => sendQuick(el.dataset.q));
});

/* ---------------- boot ---------------- */
$("#today").textContent = new Date().toLocaleDateString("pt-BR", {
  weekday: "long", day: "numeric", month: "long",
});
loadStudent();
restore();
inputEl.focus();
