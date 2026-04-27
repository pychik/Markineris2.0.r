"use strict";

// ===== config helpers =====
function pcConfigEl() {
  const el = document.getElementById("pc-config");
  if (!el) throw new Error("pc-config block not found");
  return el;
}

function pcCfg(name) {
  const el = pcConfigEl();
  const val = el.dataset[name];
  if (val === undefined) throw new Error(`pc-config missing data-${name.replace(/[A-Z]/g, m => "-" + m.toLowerCase())}`);
  return val;
}

// удобные геттеры (можно расширять)
function pcGetCreatedUrl() { return pcConfigEl().dataset.getCreatedCardsUrl; }
function pcSendModerateUrl() { return pcConfigEl().dataset.sendCardsModerateUrl; }
function pcCsrf() { return pcConfigEl().dataset.csrf; }

// ===== modal helpers (твоя модалка) =====
function pcModalInstance() {
  const el = document.getElementById("pcCardViewModal");
  return bootstrap.Modal.getOrCreateInstance(el);
}

function pcModalBody() {
  return document.getElementById("pcCardViewModalBody");
}

function pcSetModalBody(html) {
  pcModalBody().innerHTML = html;
}

function pcShowModal() {
  pcModalInstance().show();
}

function pcHideModal() {
  pcModalInstance().hide();
}

// ===== DOM helpers =====
function pcQ(sel) { return document.querySelector(sel); }
function pcQA(sel) { return Array.from(document.querySelectorAll(sel)); }

// ===== render =====
function pcRenderSendCreated(cards) {
  if (!cards || !cards.length) {
    return `<div class="text-muted">Нет карточек со статусом “Создана”.</div>`;
  }

  return `
    <div class="mb-2 d-flex align-items-center gap-2">
      <div class="form-check m-0">
        <input class="form-check-input" type="checkbox" id="pcCheckAllCreated">
        <label class="form-check-label" for="pcCheckAllCreated">Выбрать все</label>
      </div>

      <button class="btn btn-accent btn-sm ms-auto" id="pcSendCreatedBtn">
        Отправить выбранные
      </button>
    </div>

    <div class="table-responsive">
      <table class="table table-sm align-middle">
        <thead>
          <tr>
            <th></th>
            <th>Категория</th>
            <th>Артикул / Товарный знак</th>
            <th>Размеры</th>
          </tr>
        </thead>
        <tbody>
          ${cards.map(c => `
            <tr>
              <td>
                <input class="form-check-input pc-created-cb" type="checkbox" value="${c.id}">
              </td>
              <td>
                <div><b>${c.category_title}</b></div>
                ${c.subcategory ? `<div class="text-muted small">${c.subcategory}</div>` : ""}
              </td>
              <td>
                <div>${c.article || "-"}</div>
                ${c.color ? `<div class="text-muted" style="font-size:0.72rem;">${c.color}</div>` : ""}
              </td>
              <td>${c.sizes || "-"}</td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    </div>

    <div class="text-danger mt-2" id="pcSendCreatedError" style="display:none;"></div>
    <div class="text-success mt-2" id="pcSendCreatedSuccess" style="display:none;"></div>
  `;
}


function pcClearMsgs() {
  const err = document.getElementById("pcSendCreatedError");
  const ok = document.getElementById("pcSendCreatedSuccess");
  if (err) { err.style.display = "none"; err.textContent = ""; }
  if (ok) { ok.style.display = "none"; ok.textContent = ""; }
}

function pcShowErr(msg) {
  const el = document.getElementById("pcSendCreatedError");
  if (!el) return;
  el.style.display = "block";
  el.textContent = msg;
}

function pcShowOk(msg) {
  const el = document.getElementById("pcSendCreatedSuccess");
  if (!el) return;
  el.style.display = "block";
  el.textContent = msg;
}

// ===== публичная функция для onclick =====
function pcOpenSendCreatedCardsModal() {
  pcSetModalBody(`<div class="text-muted">Загрузка...</div>`);
  pcShowModal();
  pcLoadCreatedCardsIntoModal();
}

// ===== загрузка + бинды =====
async function pcLoadCreatedCardsIntoModal() {
  try {
    const url = pcGetCreatedUrl();
    if (!url) throw new Error("getCreatedCardsUrl is empty");

    const res = await fetch(url, { method: "GET" });
    if (!res.ok) throw new Error("Ошибка загрузки карточек");

    const data = await res.json();
    const cards = (data.status === "success") ? (data.cards || []) : [];

    pcSetModalBody(pcRenderSendCreated(cards));

    if (!cards.length) return;

    // выбрать все
    const checkAll = document.getElementById("pcCheckAllCreated");
    checkAll.addEventListener("change", (e) => {
      pcQA(".pc-created-cb").forEach(cb => cb.checked = e.target.checked);
    });

    // отправить выбранные
    const sendBtn = document.getElementById("pcSendCreatedBtn");
    sendBtn.addEventListener("click", pcSendSelectedCreatedCards);

  } catch (e) {
    pcSetModalBody(`<div class="text-danger">${e.message}</div>`);
  }
}

// ===== отправка =====
async function pcSendSelectedCreatedCards() {
  pcClearMsgs();

  const url = pcSendModerateUrl();
  if (!url) {
    pcShowErr("sendCardsModerateUrl is empty");
    return;
  }

  const selected = pcQA(".pc-created-cb:checked")
    .map(x => parseInt(x.value, 10))
    .filter(Number.isFinite);

  if (!selected.length) {
    pcShowErr("Выберите хотя бы одну карточку.");
    return;
  }

  const btn = document.getElementById("pcSendCreatedBtn");
  btn.disabled = true;
  const oldText = btn.textContent;
  btn.textContent = "Отправка...";

  try {
    const res = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        // если у вас CSRF через заголовок — удобно так
        "X-CSRFToken": pcCsrf()
      },
      body: JSON.stringify({ card_ids: selected })
    });

    const data = await res.json().catch(() => ({}));

    // подстройка под твой формат ответа:
    // - если вернёшь {status:"success"} — ок
    // - если вернёшь {ok:true} — тоже ок
    const isError = (data.status && data.status !== "success") || data.ok === false;
    if (!res.ok || isError) {
      throw new Error(data.error || "Ошибка отправки");
    }

    pcShowOk(data.message || `Отправлено: ${data.updated ?? selected.length}`);

    // обновить страницу/таблицу
    setTimeout(() => window.location.reload(), 900);

  } catch (e) {
    pcShowErr(e.message);
    btn.disabled = false;
    btn.textContent = oldText;
  }
}

// важно: чтобы onclick видел функции в глобальной области
window.pcOpenSendCreatedCardsModal = pcOpenSendCreatedCardsModal;
