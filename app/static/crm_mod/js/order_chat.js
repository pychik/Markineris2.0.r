"use strict";

function orderChatCfg() {
  const el = document.getElementById("crm-config");
  if (!el) throw new Error("crm-config not found");
  return el.dataset;
}

function orderChatUrlFromTemplate(tpl, id) {
  return tpl.replace(/\/0(\b|\/|$)/, `/${id}$1`);
}

function orderChatShowLoading() {
  if (typeof loadingCircle === "function") loadingCircle();
}

function orderChatHideLoading() {
  if (typeof close_Loading_circle === "function") close_Loading_circle();
}

let ORDER_CHAT_STATE = {
  orderId: null,
};

function orderChatResetModal() {
  const list = document.getElementById("order-chat-list");
  const input = document.getElementById("order-chat-input");
  const counter = document.getElementById("order-chat-counter");
  const title = document.getElementById("order-chat-modal-title");

  if (title) title.textContent = "Чат заказа";
  if (list) list.innerHTML = `<div class="text-muted">Загрузка...</div>`;
  if (input) input.value = "";
  if (counter) counter.textContent = "0/300";
}

window.orderChatResetModal = orderChatResetModal;

function orderChatOpen(btnEl) {
  if (window.event) {
    window.event.preventDefault?.();
    window.event.stopPropagation?.();
  }

  orderChatResetModal();

  const orderId = btnEl?.dataset?.orderId;
  const orderIdnRaw = btnEl?.dataset?.orderIdn;
  const orderIdn = String(orderIdnRaw || "").trim();
  if (!orderId) return alert("order-id not found");

  const modalEl = document.getElementById("order-chat-modal");
  if (!modalEl) {
    alert("order-chat-modal not found in DOM");
    return;
  }

  ORDER_CHAT_STATE.orderId = parseInt(orderId, 10);

  const titleEl = document.getElementById("order-chat-modal-title");
  if (titleEl) titleEl.textContent = `Чат заказа #${orderIdn || orderId}`;

  orderChatShowLoading();

  const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
  orderChatBindModalHandlersOnce();
  modal.show();

  orderChatReload(true)
    .catch((err) => {
      make_message(err.message || "Чат недоступен", "warning");
    })
    .finally(() => orderChatHideLoading());
}

window.orderChatOpen = orderChatOpen;

let __orderChatBound = false;
function orderChatBindModalHandlersOnce() {
  if (__orderChatBound) return;
  __orderChatBound = true;

  const refreshBtn = document.getElementById("order-chat-refresh-btn");
  const sendBtn = document.getElementById("order-chat-send-btn");
  const input = document.getElementById("order-chat-input");

  const modalEl = document.getElementById("order-chat-modal");
  if (modalEl && !modalEl.__orderChatShownBound) {
    modalEl.__orderChatShownBound = true;
    modalEl.addEventListener("shown.bs.modal", () => {
      orderChatScrollToBottom();
      setTimeout(orderChatScrollToBottom, 120);
      setTimeout(orderChatScrollToBottom, 250);
    });
  }

  if (refreshBtn) refreshBtn.addEventListener("click", orderChatReload);
  if (sendBtn) sendBtn.addEventListener("click", orderChatSend);

  if (input) {
    input.addEventListener("input", () => {
      const counter = document.getElementById("order-chat-counter");
      if (counter) counter.textContent = `${input.value.length}/300`;
    });

    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        orderChatSend();
      }
    });
  }
}

function orderChatReload(silent) {
  const orderId = ORDER_CHAT_STATE.orderId;
  if (!orderId) return Promise.reject(new Error("orderId not set"));

  const cfg = orderChatCfg();
  const url = orderChatUrlFromTemplate(cfg.orderChatMessagesUrlTemplate, orderId);

  orderChatShowLoading();

  return fetch(url, { method: "GET" })
    .then(async (res) => {
      const data = await res.json().catch(() => ({}));
      if (!res.ok || data.status !== "success") {
        throw new Error(data.message || "Чат недоступен");
      }
      return data;
    })
    .then((data) => {
      orderChatRender(data.messages || [], cfg.currentUserId);
      orderChatMarkReadIfNeeded(data.messages || [])
        .then(() => orderChatUpdateBadge(orderId, 0))
        .catch(() => {});
      return data;
    })
    .catch((e) => {
      if (!silent) alert(e.message);
      throw e;
    })
    .finally(() => orderChatHideLoading());
}

function orderChatScrollToBottom(smooth = true) {
  const list = document.getElementById("order-chat-list");
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

  doScroll();
  requestAnimationFrame(doScroll);
  setTimeout(doScroll, 10);
  setTimeout(doScroll, 50);
  setTimeout(doScroll, 150);
}

function orderChatFormatDate(value) {
  if (!value) return "";

  const dt = new Date(value);
  if (Number.isNaN(dt.getTime())) return "";

  const dd = String(dt.getDate()).padStart(2, "0");
  const mm = String(dt.getMonth() + 1).padStart(2, "0");
  const yyyy = String(dt.getFullYear());
  const hh = String(dt.getHours()).padStart(2, "0");
  const min = String(dt.getMinutes()).padStart(2, "0");

  return `${dd}-${mm}-${yyyy} ${hh}:${min}`;
}

function orderChatRender(messages, currentUserId) {
  const list = document.getElementById("order-chat-list");
  if (!list) return;

  const myId = parseInt(currentUserId || "0", 10);
  let html = "";
  let lastSide = null;

  messages.forEach((m) => {
    const isMine = (m.author_id || 0) === myId;
    const side = isMine ? "right" : "left";
    const time = orderChatFormatDate(m.created_at);
    const login = m.author_login || "";
    const theme = orderChatAuthorTheme(m.author_id, isMine);
    const gap = (lastSide !== null && lastSide !== side) ? "mt-3" : "mt-2";
    lastSide = side;

    html += `
      <div class="d-flex ${isMine ? "justify-content-end" : "justify-content-start"} ${gap}">
        <div style="max-width: 75%; background:${theme.bg}; border:1px solid ${theme.border}; border-left:4px solid ${theme.border};" class="p-2 rounded">
          <div class="small text-muted mb-1">
            <b style="color:${theme.name};">${escapeHtml(login)}</b>
            <span class="ms-2">${escapeHtml(time)}</span>
          </div>
          <div style="white-space: pre-wrap;">${escapeHtml(m.text || "")}</div>
        </div>
      </div>
    `;
  });

  list.innerHTML = html || `<div class="text-muted">Сообщений нет</div>`;
}

function orderChatAuthorTheme(authorId, isMine) {
  if (isMine) {
    return {
      bg: "#fff8e5",
      border: "#f1c75b",
      name: "#8b5e00",
    };
  }

  const palette = [
    { bg: "#eef6ff", border: "#8cb8ff", name: "#174a8b" },
    { bg: "#ecfff6", border: "#7ecfa9", name: "#1f6f4a" },
    { bg: "#fff1f5", border: "#f1a3c4", name: "#8a3458" },
    { bg: "#f3f0ff", border: "#b7a3f2", name: "#4a3a89" },
    { bg: "#fff5ec", border: "#f0b489", name: "#8a4f2f" },
    { bg: "#eefcfe", border: "#7cc7d6", name: "#1f5d68" },
  ];

  const idNum = Number(authorId) || 0;
  const idx = Math.abs(idNum) % palette.length;
  return palette[idx];
}

function orderChatSend() {
  const orderId = ORDER_CHAT_STATE.orderId;
  if (!orderId) return;

  const cfg = orderChatCfg();
  const url = orderChatUrlFromTemplate(cfg.orderChatSendUrlTemplate, orderId);

  const input = document.getElementById("order-chat-input");
  if (!input) return;

  const text = (input.value || "").trim();
  if (!text) return alert("Введите сообщение");
  if (text.length > 300) return alert("Максимум 300 символов");

  const fd = new FormData();
  if (cfg.csrf) fd.append("csrf_token", cfg.csrf);
  fd.append("text", text);

  orderChatShowLoading();

  fetch(url, { method: "POST", body: fd })
    .then(async (res) => {
      const data = await res.json().catch(() => ({}));
      if (!res.ok || data.status !== "success") throw new Error(data.message || "Ошибка отправки");
      return data;
    })
    .then(() => {
      input.value = "";
      const counter = document.getElementById("order-chat-counter");
      if (counter) counter.textContent = "0/300";
      return orderChatReload();
    })
    .then(() => orderChatScrollToBottom())
    .catch((e) => alert(e.message))
    .finally(() => orderChatHideLoading());
}

function orderChatMarkReadIfNeeded(messages) {
  if (!messages || !messages.length) return Promise.resolve(false);

  const cfg = orderChatCfg();
  const orderId = ORDER_CHAT_STATE.orderId;
  const url = orderChatUrlFromTemplate(cfg.orderChatReadUrlTemplate, orderId);

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

function orderChatUpdateBadge(orderId, unreadCount) {
  const btns = document.querySelectorAll(`.order-chat-btn[data-order-id="${orderId}"]`);
  btns.forEach((btn) => {
    const wrap = btn.closest(".pc-chat-wrap") || btn.parentElement;
    if (!wrap) return;

    const badge = wrap.querySelector(".badge");

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
    } else if (badge) {
      badge.remove();
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
