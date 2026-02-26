"use strict";

function pcChatCfg() {
  const el = document.getElementById("pc-config");
  if (!el) throw new Error("pc-config not found");
  return el.dataset;
}

function pcChatUrlFromTemplate(tpl, id) {
  return tpl.replace(/\/0(\b|\/|$)/, `/${id}$1`);
}

function pcChatShowLoading() {
  if (typeof loadingCircle === "function") loadingCircle();
}
function pcChatHideLoading() {
  if (typeof close_Loading_circle === "function") close_Loading_circle();
}

let PC_CHAT_STATE = {
  cardId: null,
};

function pcChatResetModal() {
  const list = document.getElementById("pc-chat-list");
  const input = document.getElementById("pc-chat-input");
  const counter = document.getElementById("pc-chat-counter");
  const title = document.getElementById("pc-chat-modal-title");

  if (title) title.textContent = "Чат карточки";
  if (list) list.innerHTML = `<div class="text-muted">Загрузка...</div>`;
  if (input) input.value = "";
  if (counter) counter.textContent = "0/300";
}

window.pcChatResetModal = pcChatResetModal;


function pcChatOpen(btnEl) {
  if (window.event) {
    window.event.preventDefault?.();
    window.event.stopPropagation?.();
  }

  pcChatResetModal();

  const cardId = btnEl?.dataset?.cardId;
  if (!cardId) return alert("card-id not found");

  const modalEl = document.getElementById("pc-chat-modal");
  if (!modalEl) {
    alert("pc-chat-modal not found in DOM. Добавь include модалки в base.");
    return;
  }

  PC_CHAT_STATE.cardId = parseInt(cardId, 10);

  const titleEl = document.getElementById("pc-chat-modal-title");
  if (titleEl) titleEl.textContent = `Чат карточки #${cardId}`;

  pcChatShowLoading();

  pcChatReload(true)                // silent=true
    .then(() => {
      const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
      pcChatBindModalHandlersOnce();
      modal.show();
    })
    .catch((err) => {
      // модалку НЕ открываем
      make_message(err.message || "Чат недоступен", "warning");
    })
    .finally(() => pcChatHideLoading());
}


window.pcChatOpen = pcChatOpen;


let __pcChatBound = false;
function pcChatBindModalHandlersOnce() {
  if (__pcChatBound) return;
  __pcChatBound = true;

  const refreshBtn = document.getElementById("pc-chat-refresh-btn");
  const sendBtn = document.getElementById("pc-chat-send-btn");
  const input = document.getElementById("pc-chat-input");

  const modalEl = document.getElementById("pc-chat-modal");
  if (modalEl && !modalEl.__pcChatShownBound) {
    modalEl.__pcChatShownBound = true;

    modalEl.addEventListener("shown.bs.modal", () => {
      // bootstrap завершил анимацию, DOM уже в финальном размере
      pcChatScrollToBottom();
      setTimeout(pcChatScrollToBottom, 120);
      setTimeout(pcChatScrollToBottom, 250);
    });
  }
  if (refreshBtn) refreshBtn.addEventListener("click", pcChatReload);

  if (sendBtn) sendBtn.addEventListener("click", pcChatSend);

  if (input) {
    // счетчик символов
    input.addEventListener("input", () => {
      const counter = document.getElementById("pc-chat-counter");
      if (counter) counter.textContent = `${input.value.length}/300`;
    });

    // ENTER = отправка, SHIFT+ENTER = перенос строки
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();       // не добавляем перевод строки
        pcChatSend();             // отправляем
      }
    });
  }

}

function pcChatReload(silent = false) {
  const cardId = PC_CHAT_STATE.cardId;
  if (!cardId) return Promise.reject(new Error("cardId not set"));

  const cfg = pcChatCfg();
  const url = pcChatUrlFromTemplate(cfg.chatMessagesUrlTemplate, cardId);
  loadingCircle();
  // ВАЖНО: вернуть промис
  return fetch(url, { method: "GET" })
    .then(async (res) => {
      const data = await res.json().catch(() => ({}));
      if (!res.ok || data.status !== "success") {
        throw new Error(data.message || "Чат недоступен");
      }
      return data;
    })
    .then((data) => {
      pcChatRender(data.messages || [], cfg.currentUserId);

      return pcChatMarkReadIfNeeded(data.messages || [])
        .then(() => {
          pcChatUpdateBadge(cardId, 0); // ✅ снимаем только после успеха mark_read
        })
        .catch(() => {
          // если mark_read упал — не трогаем бейдж (пусть останется)
        });
    })
    .catch((e) => {
      if (!silent) alert(e.message);
      throw e;
    })
    .finally(() =>close_Loading_circle());

}

function pcChatScrollToBottom(smooth = true) {
  const list = document.getElementById("pc-chat-list");
  if (!list) return;

  const body = list.closest(".modal-body");
  const target = body || list;

  const doScroll = () => {
    const top = target.scrollHeight;
    if (typeof target.scrollTo === "function") {
      target.scrollTo({ top, behavior: smooth ? "smooth" : "auto" });
    } else {
      target.scrollTop = top;
    }
  };

  // несколько попыток — на разных стадиях рендера/анимации
  doScroll();
  requestAnimationFrame(doScroll);
  setTimeout(doScroll, 10);
  setTimeout(doScroll, 50);
  setTimeout(doScroll, 150);
}




function pcChatRender(messages, currentUserId) {
  const list = document.getElementById("pc-chat-list");
  if (!list) return;

  const myId = parseInt(currentUserId || "0", 10);

  let html = "";
  let lastSide = null;

  messages.forEach((m) => {
    const isMine = (m.author_id || 0) === myId;
    const side = isMine ? "right" : "left";
    const time = m.created_at ? new Date(m.created_at).toLocaleString() : "";
    const login = m.author_login || "";

    // если сменился автор/сторона — можно добавить небольшой отступ
    const gap = (lastSide !== null && lastSide !== side) ? "mt-3" : "mt-2";
    lastSide = side;

    html += `
      <div class="d-flex ${isMine ? "justify-content-end" : "justify-content-start"} ${gap}">
        <div style="max-width: 75%;" class="p-2 rounded border">
          <div class="small text-muted mb-1">
            <b>${escapeHtml(login)}</b>
            <span class="ms-2">${escapeHtml(time)}</span>
          </div>
          <div style="white-space: pre-wrap;">${escapeHtml(m.text || "")}</div>
        </div>
      </div>
    `;
  });

  list.innerHTML = html || `<div class="text-muted">Сообщений нет</div>`;

  // scroll to bottom
  // list.scrollTop = list.scrollHeight;

}

function pcChatSend() {
  const cardId = PC_CHAT_STATE.cardId;
  if (!cardId) return;

  const cfg = pcChatCfg();
  const url = pcChatUrlFromTemplate(cfg.chatSendUrlTemplate, cardId);

  const input = document.getElementById("pc-chat-input");
  if (!input) return;

  const text = (input.value || "").trim();
  if (!text) return alert("Введите сообщение");
  if (text.length > 300) return alert("Максимум 300 символов");

  const fd = new FormData();
  if (cfg.csrf) fd.append("csrf_token", cfg.csrf);
  fd.append("text", text);

  pcChatShowLoading();

  fetch(url, { method: "POST", body: fd })
    .then(async (res) => {
      const data = await res.json().catch(() => ({}));
      if (!res.ok || data.status !== "success") throw new Error(data.message || "Ошибка отправки");
      return data;
    })
    .then(() => {
      input.value = "";
      const counter = document.getElementById("pc-chat-counter");
      if (counter) counter.textContent = `0/300`;
      return pcChatReload();
    })
    .then(() => pcChatScrollToBottom())
    .catch((e) => alert(e.message))
    .finally(() => pcChatHideLoading());
}

function pcChatMarkReadIfNeeded(messages) {
  if (!messages || !messages.length) return Promise.resolve(false);

  const cfg = pcChatCfg();
  const cardId = PC_CHAT_STATE.cardId;
  const url = pcChatUrlFromTemplate(cfg.chatReadUrlTemplate, cardId);

  const lastId = messages[messages.length - 1].id;
  if (!lastId) return Promise.resolve(false);

  const fd = new FormData();
  if (cfg.csrf) fd.append("csrf_token", cfg.csrf);
  fd.append("last_id", lastId);

  return fetch(url, { method: "POST", body: fd })
    .then(async (res) => {
      const data = await res.json().catch(() => ({}));
      if (!res.ok || data.status !== "success") throw new Error(data.message || "mark_read error");
      return true;
    });
}


function pcChatUpdateBadge(cardId, unreadCount) {
  // поддерживаем оба варианта:
  // 1) новая кнопка: button[data-pc-action="chat"]
  // 2) старая иконка: .pc-chat-btn
  const selectors = [
    `[data-pc-action="chat"][data-card-id="${cardId}"]`,
    `.pc-chat-btn[data-card-id="${cardId}"]`,
  ];

  const btns = document.querySelectorAll(selectors.join(","));
  btns.forEach((btn) => {
    const wrap = btn.closest(".pc-chat-wrap") || btn.parentElement;
    if (!wrap) return;

    // ищем существующий бейдж "+N"
    const badge =
      wrap.querySelector(".badge") ||
      Array.from(wrap.querySelectorAll("span")).find((s) => /^\+\d+$/.test((s.textContent || "").trim()));

    if (unreadCount > 0) {
      if (badge) {
        badge.textContent = `+${unreadCount}`;
      } else {
        const b = document.createElement("span");
        b.className = "badge rounded-pill bg-warning text-dark position-absolute";
        b.style.cssText = "top:-8px; right:-10px; font-size:11px;";
        b.textContent = `+${unreadCount}`;
        wrap.appendChild(b);
      }
    } else {
      if (badge) badge.remove();
    }
  });
}



function escapeHtml(str) {
  return String(str)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
