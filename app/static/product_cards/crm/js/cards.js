"use strict";

/* =========================
   CONFIG / URL
========================= */

function pcGetConfigEl() {
  const el = document.getElementById("pc-config");
  if (!el) throw new Error("pc-config not found on this page");
  return el;
}

function pcUrlFromTemplate(tpl, id) {
  if (!tpl) throw new Error("url template missing");
  // replace last "/0" with "/{id}"
  return tpl.replace(/\/0(\b|\/|$)/, `/${id}$1`);
}

function pcGetTakeUrl(cardId) {
  const cfg = pcGetConfigEl().dataset;
  const tpl = cfg.takeCardUrlTemplate;
  if (!tpl) throw new Error("takeCardUrlTemplate missing in pc-config");
  return pcUrlFromTemplate(tpl, cardId);
}

function pcGetMoveUrl(cardId) {
  const cfg = pcGetConfigEl().dataset;
  const tpl = cfg.moveCardUrlTemplate;
  if (!tpl) throw new Error("moveCardUrlTemplate missing in pc-config");
  return pcUrlFromTemplate(tpl, cardId);
}

function pcGetBulkMoveUrl() {
  const cfg = pcGetConfigEl().dataset;
  const url = cfg.bulkMoveUrl;
  if (!url) throw new Error("bulkMoveUrl missing in pc-config");
  return url;
}

function pcGetAssignManagerUrl(cardId) {
  const cfg = pcGetConfigEl().dataset;
  const tpl = cfg.assignManagerUrlTemplate;
  if (!tpl) throw new Error("assignManagerUrlTemplate missing in pc-config");
  return pcUrlFromTemplate(tpl, cardId);
}

/* =========================
   ANIMATION
========================= */

function animateFade(el) {
  if (!el) return;
  el.classList.remove("faded");
  void el.offsetWidth; // force reflow
  el.classList.add("faded");
}

/* =========================
   TOOLTIPS + REBIND
========================= */

function init_tooltip(root = document) {
  if (!root.querySelectorAll) return;

  root.querySelectorAll('[data-bs-toggle="tooltip"]').forEach((el) => {
    bootstrap.Tooltip.getOrCreateInstance(el);
  });
}


function initializeJSPage(root) {
  const r = root || document;

  // tooltips
  init_tooltip(r);

  // view modal open (question icon)
  r.querySelectorAll("[data-pc-action='view']").forEach((el) => {
    if (el.dataset.pcBound === "1") return;
    el.dataset.pcBound = "1";

    el.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      pcOpenViewModal(el.dataset.viewUrl);
    });
  });

  r.querySelectorAll("[data-pc-action='assign-manager']").forEach((el) => {
    if (el.dataset.pcBound === "1") return;
    el.dataset.pcBound = "1";

    el.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      pcOpenAssignManagerModal(el);
    });
  });

  // fold/unfold cards
  r.querySelectorAll(".order").forEach((order) => {
    if (order.dataset.orderBound === "1") return;
    order.dataset.orderBound = "1";

    const orderHeader = order.querySelector(".order__header");
    const orderRoll = order.querySelector(".order__roll");

    const toggleOrder = (event) => {
      event.stopPropagation();
      order.classList.toggle("active");
    };

    if (orderHeader) orderHeader.addEventListener("click", toggleOrder);

    order.addEventListener("click", (event) => {
      if (!event.target.closest(".order__roll") && !order.classList.contains("active")) {
        order.classList.add("active");
      }
    });

    if (orderRoll) {
      orderRoll.addEventListener("click", (event) => {
        event.stopPropagation();
        order.classList.remove("active");
      });
    }
  });
}

function dispose_tooltip(root = document) {
  if (!root.querySelectorAll) return;

  root.querySelectorAll('[data-bs-toggle="tooltip"]').forEach((el) => {
    const inst = bootstrap.Tooltip.getInstance(el);
    if (!inst) return;

    if (inst._timeout) {
      clearTimeout(inst._timeout);
      inst._timeout = null;
    }

    try {
      inst.dispose();
    } catch (_) {
    }
  });
}


function hide_tooltips(root = document) {
  root.querySelectorAll('[data-bs-toggle="tooltip"]').forEach((el) => {
    bootstrap.Tooltip.getInstance(el)?.hide();
  });
}

function withTooltipsRefresh(mutatorFn, root) {
  const r = root || document;

  // 1) закрываем все, чтобы Bootstrap не держал pending hide/leave
  hide_tooltips(r);

  // 2) даём отработать queued callbacks Bootstrap (тот самый setTimeout)
  requestAnimationFrame(() => {
    dispose_tooltip(r);
    mutatorFn();
    initializeJSPage(r);
  });
}

/* =========================
   VIEW MODAL
========================= */

function pcSetModalTitle(title) {
  const modalEl = document.getElementById("pc-view-modal");
  if (!modalEl) throw new Error("pc-view-modal not found");
  const titleEl = modalEl.querySelector(".modal-title");
  if (!titleEl) throw new Error("pc-view-modal .modal-title not found");
  titleEl.textContent = title || "";
}

function pcSetModalHtml(html) {
  const body = document.getElementById("pc-view-modal-body");
  if (!body) throw new Error("pc-view-modal-body not found");
  body.innerHTML = html || "";
}

function pcShowModal() {
  const modalEl = document.getElementById("pc-view-modal");
  if (!modalEl) throw new Error("pc-view-modal not found");
  const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
  modal.show();
  return modal;
}

// ✅ FIX: умеет читать JSON {html: "..."} и обычный HTML
function pcOpenViewModal(url) {
  if (!url) return;

  loadingCircle();

  fetch(url, {method: "GET"})
      .then(async (res) => {
        const contentType = (res.headers.get("content-type") || "").toLowerCase();

        if (!res.ok) throw new Error("Ошибка загрузки карточки");

        // if JSON -> take data.html
        if (contentType.includes("application/json")) {
          const data = await res.json().catch(() => ({}));
          if (data && typeof data.html === "string") return data.html;
          // fallback: show whole json nicely
          return `<pre>${escapeHtml(JSON.stringify(data, null, 2))}</pre>`;
        }

        // otherwise treat as html
        return await res.text();
      })
      .then((html) => {
        pcSetModalTitle("Просмотр карточки");
        pcSetModalHtml(html);
        pcShowModal();
        // если внутри модалки есть тултипы
        init_tooltip(document.getElementById("pc-view-modal"));
      })
      .catch((e) => alert(e.message))
      .finally(() => {
        close_Loading_circle();
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

window.pcOpenViewModal = pcOpenViewModal;

/* =========================
   STAGE 1: SENT -> IN_PROGRESS
========================= */

function pcTakeCardToProcessing(btnEl) {
  const cardId = btnEl?.dataset?.cardId;
  if (!cardId) {
    alert("card-id not found");
    return;
  }

  const cfg = pcGetConfigEl().dataset;
  const url = pcGetTakeUrl(cardId);
  const category = pcGetActiveCategory();

  const form = new FormData();
  if (cfg.csrf) form.append("csrf_token", cfg.csrf);
  if (cfg.currentCategory) form.append("category", category);
  if (cfg.currentSubcategory) form.append("subcategory", cfg.currentSubcategory);

  loadingCircle();

  fetch(url, {method: "POST", body: form})
    .then(async (res) => {
      const data = await res.json().catch(() => ({}));
      if (!res.ok || data.status !== "success") throw new Error(data.message || "Ошибка");
      return data;
    })
    .then((data) => {
      withTooltipsRefresh(() => {
        // ✅ универсально обновляем from/to (sent или sent_no_rd -> in_progress)
        if (typeof pcApplyMoveResponse === "function") {
          pcApplyMoveResponse(data);
        }

        if (typeof make_message === "function") make_message(data.message, data.status);
      }, document);
    })
    .catch((e) => alert(e.message))
    .finally(() => {
      close_Loading_circle();
    });
}

window.pcTakeCardToProcessing = pcTakeCardToProcessing;

window.pcTakeCardToProcessing = pcTakeCardToProcessing;

/* =========================
   STAGE 2: IN_PROGRESS -> target
========================= */

function pcMoveCard(btnEl, target) {
  const cardId = btnEl?.dataset?.cardId;
  if (!cardId) return alert("card-id not found");

  const cfg = pcGetConfigEl().dataset;
  const url = pcGetMoveUrl(cardId);

  const fd = new FormData();
  if (cfg.csrf) fd.append("csrf_token", cfg.csrf);
  fd.append("target", target);

  const category = pcGetActiveCategory();        // ✅ теперь из UI


  // протаскиваем фильтры (чтобы бэк перерендерил правильные списки)
  if (cfg.currentCategory) fd.append("category", category);
  if (cfg.currentSubcategory) fd.append("subcategory", cfg.currentSubcategory);

  // если отклонение — пусть кнопка передаёт reason в data-reject-reason,

  if (target === "rejected") {
    const reasonFromBtn = (btnEl?.dataset?.rejectReason || "").trim();
    let reason = reasonFromBtn;
    if (!reason) {
      reason = (prompt("Укажите причину отмены:", "") || "").trim();
    }
    if (!reason) {
      if (typeof make_message === "function") make_message("Нужно указать причину отмены", "warning");
      return;
    }
    fd.append("reject_reason", reason);
  }

  loadingCircle();

  fetch(url, {method: "POST", body: fd})
      .then(async (res) => {
        const data = await res.json().catch(() => ({}));
        if (!res.ok || data.status !== "success") {
          throw new Error(data.message || "Ошибка");
        }
        return data;
      })
      .then((data) => {
        withTooltipsRefresh(() => {
          // применяем ответ (обновляем from/to по данным бэка)
          if (typeof pcApplyMoveResponse === "function") {
            pcApplyMoveResponse(data);
          }
          const fromKey = (data.from_status || data.from || "").toString();
          const toKey   = (data.to_status   || data.to   || "").toString();

          if (fromKey === "in_moderation" || toKey === "in_moderation") {
            // чтобы уже был вставлен DOM после pcApplyMoveResponse
            requestAnimationFrame(() => pcReloadColumn("in_moderation"));
          }

          // если колонка назначения "heavy" — просим обновить вручную
          if (data.to_is_heavy) {
            if (typeof make_message === "function") {
              make_message(
                  data.message || "Перемещено. Колонку назначения обновите кнопкой ↻",
                  "success"
              );
            }
          } else {
            if (typeof make_message === "function") {
              make_message(data.message || "Готово", data.status || "success");
            }
          }
        }, document);
      })
      .catch((e) => {
        if (typeof make_message === "function") make_message(e.message || "Ошибка", "error");
        else alert(e.message);
      })
      .finally(() => {
        close_Loading_circle();
      });
}

window.pcMoveCard = pcMoveCard;

function pcApplyMoveResponse(data) {
  if (!data) return;

  const map = {
    sent_no_rd: {qty: "sent_no_rd_cards_qty", list: "sent_no_rd_cards_list"},
    sent: {qty: "sent_cards_qty", list: "sent_cards_list"},
    in_progress: {qty: "in_progress_cards_qty", list: "in_progress_cards_list"},
    in_moderation: {qty: "in_moderation_cards_qty", list: "in_moderation_cards_list"},
    clarification: {qty: "clarification_cards_qty", list: "clarification_cards_list"},
    approved: {qty: "approved_cards_qty", list: "approved_cards_list"},
    rejected: {qty: "rejected_cards_qty", list: "rejected_cards_list"},
    partially_approved: {qty: "partially_approved_cards_qty", list: "partially_approved_cards_list"},
  };

  function applyBlock(statusKey, qtyVal, htmlVal) {
    const cfg = map[statusKey];
    if (!cfg) return;

    // qty — обновляем только если это число (иначе не трогаем, чтобы не было undefined)
    const qtyEl = document.getElementById(cfg.qty);
    if (qtyEl && typeof qtyVal === "number") {
      qtyEl.textContent = `(${qtyVal})`;
    }

    // list — обновляем только если реально пришёл html-строкой
    const listEl = document.getElementById(cfg.list);
    if (listEl && typeof htmlVal === "string") {
      listEl.innerHTML = htmlVal;
      if (typeof animateFade === "function") animateFade(listEl);
    }
  }

  const fromKey = (data.from_status || data.from || "").toString();
  const toKey = (data.to_status || data.to || "").toString();

  // FROM
  if (fromKey) {
    applyBlock(fromKey, data.from_qty, data.from_list_html);
  }

  // TO
  if (toKey) {
    applyBlock(toKey, data.to_qty, data.to_list_html);
  }
}

function pcApplyBulkMoveResponse(data) {
  if (!data || !data.updated_columns) return;

  const map = {
    sent_no_rd: {qty: "sent_no_rd_cards_qty", list: "sent_no_rd_cards_list"},
    sent: {qty: "sent_cards_qty", list: "sent_cards_list"},
    in_progress: {qty: "in_progress_cards_qty", list: "in_progress_cards_list"},
    in_moderation: {qty: "in_moderation_cards_qty", list: "in_moderation_cards_list"},
    clarification: {qty: "clarification_cards_qty", list: "clarification_cards_list"},
    approved: {qty: "approved_cards_qty", list: "approved_cards_list"},
    rejected: {qty: "rejected_cards_qty", list: "rejected_cards_list"},
    partially_approved: {qty: "partially_approved_cards_qty", list: "partially_approved_cards_list"},
  };

  Object.entries(data.updated_columns).forEach(([statusKey, payload]) => {
    const cfg = map[statusKey];
    if (!cfg) return;

    const qtyEl = document.getElementById(cfg.qty);
    if (qtyEl && typeof payload.qty === "number") {
      qtyEl.textContent = `(${payload.qty})`;
    }

    const listEl = document.getElementById(cfg.list);
    if (listEl && typeof payload.list_html === "string") {
      listEl.innerHTML = payload.list_html;
      if (typeof animateFade === "function") animateFade(listEl);
    }
  });
}

function pcBulkCheckboxes(statusKey) {
  return Array.from(document.querySelectorAll(`.pc-bulk-check[data-bulk-status="${statusKey}"]`));
}

function pcSetBulkMode(statusKey, enabled) {
  const panel = document.getElementById(`pc-bulk-panel-${statusKey}`);
  const startBtn = document.getElementById(`pc-bulk-start-${statusKey}`);

  if (panel) panel.classList.toggle("d-none", !enabled);
  if (startBtn) startBtn.classList.toggle("d-none", enabled);

  pcBulkCheckboxes(statusKey).forEach((checkbox) => {
    checkbox.checked = false;
    const holder = checkbox.closest(".pc-bulk-select");
    if (holder) holder.classList.toggle("d-none", !enabled);
  });

  pcUpdateBulkCount(statusKey);
}

function pcToggleBulkMode(statusKey) {
  const panel = document.getElementById(`pc-bulk-panel-${statusKey}`);
  pcSetBulkMode(statusKey, !panel || panel.classList.contains("d-none"));
}

function pcUpdateBulkCount(statusKey) {
  const count = pcBulkCheckboxes(statusKey).filter((checkbox) => checkbox.checked).length;
  const el = document.getElementById(`pc-bulk-count-${statusKey}`);
  if (el) el.textContent = String(count);
}

function pcBulkMoveSelected(fromStatus, target) {
  const selectedIds = pcBulkCheckboxes(fromStatus)
      .filter((checkbox) => checkbox.checked)
      .map((checkbox) => checkbox.value)
      .filter(Boolean);

  if (!selectedIds.length) {
    if (typeof make_message === "function") make_message("Выберите карточки", "warning");
    return;
  }

  const cfg = pcGetConfigEl().dataset;
  const fd = new FormData();
  if (cfg.csrf) fd.append("csrf_token", cfg.csrf);
  fd.append("target", target);
  selectedIds.forEach((cardId) => fd.append("card_ids[]", cardId));

  const category = pcGetActiveCategory();
  const subcategory = pcGetActiveSubcategory();
  if (category) fd.append("category", category);
  if (subcategory) fd.append("subcategory", subcategory);

  loadingCircle();

  fetch(pcGetBulkMoveUrl(), {method: "POST", body: fd})
      .then(async (res) => {
        const data = await res.json().catch(() => ({}));
        if (!res.ok || data.status !== "success") {
          throw new Error(data.message || "Ошибка");
        }
        return data;
      })
      .then((data) => {
        withTooltipsRefresh(() => {
          pcApplyBulkMoveResponse(data);
          pcSetBulkMode(fromStatus, false);

          if (target === "in_moderation" || fromStatus === "in_moderation") {
            requestAnimationFrame(() => pcReloadColumn("in_moderation"));
          }

          if (typeof make_message === "function") {
            make_message(data.message || "Готово", data.status || "success");
          }
        }, document);
      })
      .catch((e) => {
        if (typeof make_message === "function") make_message(e.message || "Ошибка", "error");
        else alert(e.message);
      })
      .finally(() => {
        close_Loading_circle();
      });
}

window.pcApplyBulkMoveResponse = pcApplyBulkMoveResponse;
window.pcSetBulkMode = pcSetBulkMode;
window.pcToggleBulkMode = pcToggleBulkMode;
window.pcUpdateBulkCount = pcUpdateBulkCount;
window.pcBulkMoveSelected = pcBulkMoveSelected;

/* =========================
   REJECT MODAL -> move rejected with reason
========================= */

function pcOpenRejectModal(btnEl) {
  const cardId = btnEl?.dataset?.cardId;
  if (!cardId) return alert("card-id not found");

  pcSetModalTitle(`Отмена карточки #${cardId}`);
  pcSetModalHtml(`
    <div class="mb-2 text-muted">Укажите причину отмены:</div>
    <textarea class="form-control" id="pcRejectReason" rows="4" placeholder="Причина..."></textarea>
    <div class="d-flex justify-content-end gap-2 mt-3">
      <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Отмена</button>
      <button type="button" class="btn btn-danger" id="pcRejectSubmitBtn">Отменить</button>
    </div>
  `);

  const modal = pcShowModal();
  const body = document.getElementById("pc-view-modal-body");
  const btn = body.querySelector("#pcRejectSubmitBtn");

  btn.onclick = function () {
    const reason = (body.querySelector("#pcRejectReason").value || "").trim();
    if (!reason) return alert("Укажите причину");

    pcMoveCardWithReason(cardId, "rejected", reason);
    modal.hide();
  };
}

window.pcOpenRejectModal = pcOpenRejectModal;

function pcMoveCardWithReason(cardId, target, rejectReason) {
  const cfg = pcGetConfigEl().dataset;
  const url = pcGetMoveUrl(cardId);

  const fd = new FormData();
  if (cfg.csrf) fd.append("csrf_token", cfg.csrf);
  fd.append("target", target);
  fd.append("reject_reason", rejectReason);

  loadingCircle();

  fetch(url, {method: "POST", body: fd})
      .then(async (res) => {
        const data = await res.json().catch(() => ({}));
        if (!res.ok || data.status !== "success") throw new Error(data.message || "Ошибка");
        return data;
      })
      .then((data) => {
        withTooltipsRefresh(() => {
          pcApplyMoveResponse(data);
          if (typeof make_message === "function") make_message(data.message || "Готово", data.status);
        }, document);
      })
      .catch((e) => alert(e.message))
      .finally(() => {
        close_Loading_circle();
      });
}

/* =========================
   ASSIGN MANAGER
========================= */

function pcOpenAssignManagerModal(btnEl) {
  const cardId = btnEl?.dataset?.cardId;
  if (!cardId) return alert("card-id not found");

  const cfg = pcGetConfigEl().dataset;
  const managersUrl = cfg.managersUrl;
  if (!managersUrl) return alert("managersUrl missing in pc-config");

  loadingCircle();

  fetch(managersUrl, {method: "GET"})
      .then(async (res) => {
        const data = await res.json().catch(() => ({}));
        if (!res.ok || data.status !== "success") {
          throw new Error(data.message || "Ошибка загрузки менеджеров");
        }
        return data;
      })
      .then((data) => {
        const currentManagerId = String(btnEl.dataset.managerId || "");
        const options = (data.managers || []).map((manager) => {
          const id = String(manager.id);
          const selected = id === currentManagerId ? "selected" : "";
          return `<option value="${escapeHtml(id)}" ${selected}>${escapeHtml(manager.login)}</option>`;
        }).join("");

        pcSetModalTitle(`Назначить менеджера карточке #${cardId}`);
        pcSetModalHtml(`
          <div class="mb-2 text-muted">Выберите менеджера сервиса:</div>
          <select class="form-control" id="pcAssignManagerSelect">
            <option value="">Выберите менеджера</option>
            ${options}
          </select>
          <div class="d-flex justify-content-end gap-2 mt-3">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Отмена</button>
            <button type="button" class="btn btn-primary" id="pcAssignManagerSubmitBtn">OK</button>
          </div>
        `);

        const modal = pcShowModal();
        const body = document.getElementById("pc-view-modal-body");
        const submitBtn = body.querySelector("#pcAssignManagerSubmitBtn");

        submitBtn.onclick = function () {
          const select = body.querySelector("#pcAssignManagerSelect");
          const managerId = (select?.value || "").trim();
          if (!managerId) return alert("Выберите менеджера");
          pcAssignManager(cardId, managerId, modal);
        };
      })
      .catch((e) => {
        if (typeof make_message === "function") make_message(e.message || "Ошибка", "error");
        else alert(e.message);
      })
      .finally(() => {
        close_Loading_circle();
      });
}

function pcAssignManager(cardId, managerId, modal) {
  const cfg = pcGetConfigEl().dataset;
  const fd = new FormData();
  if (cfg.csrf) fd.append("csrf_token", cfg.csrf);
  fd.append("manager_id", managerId);

  loadingCircle();

  fetch(pcGetAssignManagerUrl(cardId), {method: "POST", body: fd})
      .then(async (res) => {
        const data = await res.json().catch(() => ({}));
        if (!res.ok || data.status !== "success") {
          throw new Error(data.message || "Ошибка назначения менеджера");
        }
        return data;
      })
      .then((data) => {
        pcUpdateManagerOnCard(data.card_id, data.manager_id, data.manager_login);
        modal?.hide();
        if (typeof make_message === "function") make_message(data.message || "Готово", data.status || "success");
      })
      .catch((e) => {
        if (typeof make_message === "function") make_message(e.message || "Ошибка", "error");
        else alert(e.message);
      })
      .finally(() => {
        close_Loading_circle();
      });
}

function pcUpdateManagerOnCard(cardId, managerId, managerLogin) {
  const cardEl = document.getElementById(`cardCommonBlock_${cardId}`);
  if (!cardEl) return;

  const btn = cardEl.querySelector('[data-pc-action="assign-manager"]');
  if (!btn) return;

  btn.dataset.managerId = managerId || "";
  btn.dataset.managerLogin = managerLogin || "";
  btn.textContent = managerLogin || "не назначен";

  const holder = btn.closest(".order__num");
  if (holder) holder.classList.toggle("text-muted", !managerLogin);
}

window.pcOpenAssignManagerModal = pcOpenAssignManagerModal;
window.pcAssignManager = pcAssignManager;


/* =========================
   BOOT
========================= */

document.addEventListener("DOMContentLoaded", () => {
  try {
    initializeJSPage(document);
  } catch (e) {
    // ignore if not CRM page
  }
});

function pcOpenCardLogs(btnEl) {
  if (window.event) {
    window.event.preventDefault?.();
    window.event.stopPropagation?.();
  }

  pcLogsResetModal();
  const cardId = btnEl?.dataset?.cardId;
  if (!cardId) return;

  const cfg = pcGetConfigEl().dataset;
  const url = cfg.cardLogsUrlTemplate.replace(/\/0(\b|\/|$)/, `/${cardId}$1`);

  const modalEl = document.getElementById("pc-logs-modal");
  const bodyEl = document.getElementById("pc-logs-modal-body");
  const titleEl = document.getElementById("pc-logs-modal-title");

  if (!modalEl || !bodyEl) return;

  bodyEl.textContent = "Загрузка...";
  titleEl.textContent = `Логи карточки #${cardId}`;

  loadingCircle();

  fetch(url, {headers: {"X-Requested-With": "XMLHttpRequest"}})
      .then(r => r.json())
      .then(data => {
        if (data.status !== "success") {
          throw new Error(data.message || "Ошибка загрузки логов");
        }

        bodyEl.textContent = data.logs || "Логи пустые";
        bootstrap.Modal.getOrCreateInstance(modalEl).show();
      })
      .catch(err => {
        make_message(err.message, "error");
      })
      .finally(() => close_Loading_circle());
}

function pcLogsResetModal() {
  const title = document.getElementById("pc-logs-modal-title");
  const body = document.getElementById("pc-logs-modal-body");

  if (title) title.textContent = "Логи карточки";
  if (body) body.textContent = "Загрузка...";
}

function pcGetActiveCategory() {
  const active = document.querySelector(".categories__item--active");
  if (!active) return "";

  const onclickValue = active.getAttribute("onclick") || "";
  // onclick="update_category_crm_info(UPDATE_PRODUCT_CARDS_CRM_URL, 'clothes', this, ...)"
  // вытащим второй аргумент: 'clothes' (может быть '' для "Все")
  const m = onclickValue.match(/update_category_crm_info\([^,]+,\s*'([^']*)'/);
  return (m && typeof m[1] === "string") ? m[1] : "";
}

// если сабкатегория выбирается отдельным UI — сюда позже добавим парсер.
// пока: берём из pc-config (или пусто).
function pcGetActiveSubcategory() {
  const cfg = pcGetConfigEl().dataset;
  return (cfg.currentSubcategory || "").trim();
}

function pcReloadColumn(statusKey) {
  const cfg = pcGetConfigEl().dataset;
  const urlBase = cfg.lazyColumnUrl;
  if (!urlBase) {
    make_message("lazyColumnUrl отсутствует в pc-config", "error");
    return;
  }

  const params = new URLSearchParams();
  params.set("status", statusKey);

  const category = pcGetActiveCategory();        // ✅ теперь из UI
  const subcategory = pcGetActiveSubcategory();

  if (category) params.set("category", category);
  if (subcategory) params.set("subcategory", subcategory);
  if (statusKey === "in_moderation") {
      const sel = document.getElementById("in_moderation_company_select");
      const companyId = (sel?.value || "").trim();
      if (companyId) params.set("company_id", companyId);
    }
  const url = `${urlBase}?${params.toString()}`;

  loadingCircle();

  fetch(url, {method: "GET", headers: {"X-Requested-With": "XMLHttpRequest"}})
      .then(async (res) => {
        const data = await res.json().catch(() => ({}));
        if (!res.ok || data.status !== "success") throw new Error(data.message || "Ошибка");
        return data;
      })
      .then((data) => {
        withTooltipsRefresh(() => {
          const map = {
            sent: {qty: "sent_cards_qty", list: "sent_cards_list"},
            in_progress: {qty: "in_progress_cards_qty", list: "in_progress_cards_list"},
            in_moderation: {qty: "in_moderation_cards_qty", list: "in_moderation_cards_list"},
            approved: {qty: "approved_cards_qty", list: "approved_cards_list"},
            rejected: {qty: "rejected_cards_qty", list: "rejected_cards_list"},
            partially_approved: {qty: "partially_approved_cards_qty", list: "partially_approved_cards_list"},
          };

          const dest = map[statusKey];
          if (!dest) return;

          const qtyEl = document.getElementById(dest.qty);
          const listEl = document.getElementById(dest.list);

          if (qtyEl && typeof data.qty === "number") qtyEl.textContent = `(${data.qty})`;
          if (listEl) {
            listEl.innerHTML = data.list_html || "";
            animateFade(listEl);
          }
        }, document);
      })
      .catch((e) => make_message(e.message, "error"))
      .finally(() => close_Loading_circle());
}

window.pcReloadColumn = pcReloadColumn;


function crmSearchCardClear() {
  const input = document.getElementById('crm-search-card-input');
  const out = document.getElementById('crm-search-card-result');

  input.value = '';
  out.innerHTML = '';
  input.focus();
}

function crmSearchCardKeyHandler(e) {
  // Enter — стандартно сабмитит форму, ничего не делаем
  if (e.key === 'Escape') {
    e.preventDefault();
    crmSearchCardClear();
  }
}

function crmSearchModeChanged() {
  const cb = document.getElementById('crm-search-by-article');
  const label = document.getElementById('crm-search-mode-label');
  const input = document.getElementById('crm-search-card-input');

  if (cb.checked) {
    label.textContent = 'Режим: поиск по артикулу / ТМ';
    input.placeholder = 'Артикул или торговая марка';
  } else {
    label.textContent = 'Режим: поиск по ID';
    input.placeholder = 'Номер карточки';
  }
}

function crmOpenSearchModal(title, html) {
  const titleEl = document.getElementById('crmSearchModalTitle');
  const bodyEl  = document.getElementById('crmSearchModalBody');

  titleEl.textContent = title || 'Результаты поиска';
  bodyEl.innerHTML = html || '';

  // чтобы твои обработчики на вставленном html тоже подтянулись
  initializeJSPage(bodyEl);

  const modalEl = document.getElementById('crmSearchModal');
  const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
  modal.show();
}

function crmCloseSearchModal() {
  const modalEl = document.getElementById('crmSearchModal');
  const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
  modal.hide();
}

async function crmSearchCardSubmit(e) {
  e.preventDefault();

  const cfg = document.getElementById('pc-config');
  const url = cfg.dataset.searchCardUrl;
  const csrf = cfg.dataset.csrf;

  const input = document.getElementById('crm-search-card-input');
  const out = document.getElementById('crm-search-card-result');
  const cb = document.getElementById('crm-search-by-article');

  const raw = (input.value || '').trim();
  if (!raw) {
    crmSearchCardClear();
    return false;
  }

  // клиентская валидация
  if (!cb.checked && !/^\d+$/.test(raw)) {
    out.innerHTML = '<div class="text-danger">Введите номер карточки</div>';
    return false;
  }

  loadingCircle();
  out.innerHTML = '<div class="text-muted">Поиск...</div>';

  const fd = new FormData();
  fd.append('q', raw);
  fd.append('search_mode', cb.checked ? 'article' : 'id');
  fd.append('csrf_token', csrf);

  try {
   const r = await fetch(url, {
  method: 'POST',
  body: fd,
  headers: {'X-Requested-With': 'XMLHttpRequest'}
});

// безопасный парс: иногда сервер на ошибках отдаёт не JSON
let data = null;
const ct = (r.headers.get('content-type') || '').toLowerCase();

if (ct.includes('application/json')) {
  data = await r.json();
} else {
  const text = await r.text();
  // если прилетел HTML/редирект — покажем понятную ошибку
  out.innerHTML = `<div class="text-danger">Ошибка ответа сервера (${r.status})</div>`;
  close_Loading_circle();
  return false;
}

// если статус HTTP не ок — но JSON есть: покажем message
if (!r.ok || data.status !== 'success') {
  out.innerHTML = `<div class="text-danger">${data.message || `Ошибка (${r.status})`}</div>`;
  close_Loading_circle();
  return false;
}

    if (data.status !== 'success') {
      out.innerHTML = `<div class="text-danger">${data.message || 'Ошибка'}</div>`;
      close_Loading_circle();
      return false;
    }

    const isArticle = cb.checked;

    if (isArticle) {
      // результаты — в модалку
      crmOpenSearchModal(
        `Найдено: ${data.found_count || 0}`,
        data.html || ''
      );

      // а под полем можно либо очистить, либо оставить кратко
      out.innerHTML = `<div class="text-muted">Результаты открыты в окне</div>`;
    } else {
      // как раньше — под полем
      out.innerHTML = `
        <div class="mb-2">
          <b>Найдено:</b> ${data.found_count || 0}
        </div>
        ${data.html || ''}
      `;
      initializeJSPage(out);
    }

    close_Loading_circle();
    return false;

  } catch (err) {
    out.innerHTML = '<div class="text-danger">Ошибка запроса</div>';
    close_Loading_circle();
    return false;
  }
}

async function pcSetCompanySlot(cardId, slot) {
  const cfg = document.getElementById('pc-config');
  const csrf = cfg.dataset.csrf;
  const url = cfg.dataset.setCompanySlotUrl.replace(/0\b/, String(cardId));

  const sel = document.getElementById(`pc-company-slot-${slot}`);
  const companyId = sel ? sel.value : "";

  const msg = document.getElementById('pc-companies-msg');
  if (msg) msg.innerHTML = '';

  if (!companyId) {
    if (msg) msg.innerHTML = '<span class="text-danger">Выберите компанию</span>';
    return;
  }

  const fd = new FormData();
  fd.append('slot', String(slot));
  fd.append('company_id', String(companyId));
  fd.append('csrf_token', csrf);

  const r = await fetch(url, {method:'POST', body:fd, headers:{'X-Requested-With':'XMLHttpRequest'}});
  const data = await r.json();

  if (data.status !== 'success') {
    if (msg) msg.innerHTML = `<span class="text-danger">${data.message || 'Ошибка'}</span>`;
    return;
  }

  const box = document.getElementById('pc-card-view-companies');
  if (box) box.outerHTML = data.html;
}

function pcApproveFromPartially(cardId) {
  const cfg = pcGetConfigEl().dataset;
  const csrf = cfg.csrf;

  const tpl = cfg.approveFromPartiallyUrlTemplate; // пробьём так же, как move template
  if (!tpl) throw new Error("approveFromPartiallyUrlTemplate missing in pc-config");
  const url = pcUrlFromTemplate(tpl, cardId);

  const fd = new FormData();
  if (csrf) fd.append("csrf_token", csrf);

  loadingCircle();

  fetch(url, { method: "POST", body: fd })
    .then(async (res) => {
      const data = await res.json().catch(() => ({}));
      if (!res.ok || data.status !== "success") {
        throw new Error(data.message || "Ошибка");
      }
      return data;
    })
    .then(async (data) => {
      if (typeof make_message === "function") make_message("Карточка переведена в APPROVED", "success");

      // сперва закрываем
      pcCloseCardViewModal();

      // потом обновляем колонку (можно без await)
      pcReloadPartiallyApprovedColumn().catch(() => {});
    })

    .catch((e) => {
      if (typeof make_message === "function") make_message(e.message || "Ошибка", "error");
      else alert(e.message);
    })
    .finally(() => close_Loading_circle());
}

window.pcApproveFromPartially = pcApproveFromPartially;


function pcReloadPartiallyApprovedColumn() {
  const cfg = pcGetConfigEl().dataset;
  const url = cfg.lazyColumnUrl; // data-lazy-column-url

  if (!url) throw new Error("lazyColumnUrl missing in pc-config");

  const category = pcGetActiveCategory ? pcGetActiveCategory() : (cfg.currentCategory || "");
  const subcategory = cfg.currentSubcategory || "";

  const qs = new URLSearchParams();
  qs.set("status", "partially_approved");
  if (category) qs.set("category", category);
  if (subcategory) qs.set("subcategory", subcategory);

  return fetch(`${url}?${qs.toString()}`, { headers: { "X-Requested-With": "XMLHttpRequest" } })
    .then(async (res) => {
      const data = await res.json().catch(() => ({}));
      if (!res.ok || data.status !== "success") {
        throw new Error(data.message || "Не удалось обновить partially_approved");
      }
      return data;
    })
    .then((data) => {
      // ✅ ВАЖНО: поставь правильный id контейнера partially_approved списка
      // Обычно это что-то вроде: partially_approved_list / partially_approved_cards / st_... и т.п.
      const listEl =
        document.getElementById("partially_approved_cards_list") ||
        document.querySelector("[data-col='partially_approved'] .pc-cards-list") ||
        document.getElementById("st_partially_approved_list");

      if (!listEl) {
        // не падаем, но сообщим
        if (typeof make_message === "function") make_message("Колонка PARTIALLY_APPROVED не найдена в DOM", "warning");
        return data;
      }

      listEl.innerHTML = data.list_html;

      // qty — если у тебя есть счётчик
      const qtyEl =
        document.getElementById("partially_approved_qty") ||
        document.querySelector("[data-col='partially_approved'] .pc-col-qty");

      if (qtyEl) qtyEl.textContent = data.qty;

      // если у тебя есть хелпер refresh тултипов
      if (typeof withTooltipsRefresh === "function") {
        withTooltipsRefresh(() => {}, document);
      }

      return data;
    });
}

window.pcReloadPartiallyApprovedColumn = pcReloadPartiallyApprovedColumn;


function pcCloseCardViewModal() {
  const el = document.getElementById("pc-view-modal");
  if (!el) return;

  // 1) пробуем Bootstrap 5 API через глобалку
  try {
    if (window.bootstrap && window.bootstrap.Modal) {
      const inst = window.bootstrap.Modal.getOrCreateInstance(el);
      inst.hide();
      return;
    }
  } catch (e) {
    // игнор
  }

  // 2) фоллбек: клик по кнопке закрытия
  const btn = el.querySelector('[data-bs-dismiss="modal"]');
  if (btn) btn.click();

  // 3) hard cleanup на всякий (если анимации/бэкдроп зависли)
  setTimeout(() => {
    el.classList.remove("show");
    el.style.display = "none";
    el.setAttribute("aria-hidden", "true");

    document.body.classList.remove("modal-open");
    document.body.style.removeProperty("overflow");
    document.body.style.removeProperty("padding-right");

    document.querySelectorAll(".modal-backdrop").forEach(b => b.remove());
  }, 100);
}

window.pcCloseCardViewModal = pcCloseCardViewModal;

function getPcdownloadConfig() {
  const el = document.getElementById("pc-config");
  if (!el) return {};
  return {
    userId: el.dataset.currentUserId,
    csrf: el.dataset.csrf,
    url_transfer_sent_to_in_progress: el?.dataset?.transferSentToInProgressUrl || "",
    url: el.dataset.downloadCardsCompaniesInProgress
  };
}

async function transferSentToInProgressCards() {
  const cfgEl = getPcdownloadConfig(); // можешь переименовать, но оставим как у тебя
  const url = cfgEl.url_transfer_sent_to_in_progress; // новый data-атрибут (см. ниже)
  const csrf = cfgEl.csrf;

  if (!url) {
    make_message("transferSentToInProgressUrl отсутствует в pc-config", "error");
    return;
  }

  try {
    const resp = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRFToken": csrf || ""
      },
      body: JSON.stringify({}), // manager_id не шлём — берём current_user.id на бэке
      credentials: "same-origin",
    });

    const data = await resp.json().catch(() => ({}));
    if (!resp.ok) {
      // HTTP-ошибка: 404 / 500 / 403
      make_message(
        data.message || `HTTP ошибка ${data.status}`,
        "error"
      );
      return;
    }

    if (!resp.ok || data.status !== "success") {
      make_message(data.message || "Ошибка", data.status || "error");
      return;
    }


    // ✅ перезагружаем колонки
    if (typeof pcReloadColumn === "function") {
      pcReloadColumn("sent");
      pcReloadColumn("in_progress");
    }
    make_message(data.message || "Карточки перенесены", "success");
  } catch (e) {
    make_message(e.message || "Сетевая ошибка", "error");
  }
}

async function downloadTransferInProgressCards() {
  const cfgEl = getPcdownloadConfig();

  const url = cfgEl.url;          // положи data-download-url в pc-config
  const csrf = cfgEl.csrf;

  if (!url) {
    make_message("downloadUrl отсутствует в pc-config", "error");
    return;
  }

  try {
    const resp = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRFToken": csrf || ""
      },
      body: JSON.stringify({}),         // manager_id НЕ шлём
      credentials: "same-origin",
    });

    const ct = (resp.headers.get("content-type") || "").toLowerCase();

    // ошибка в JSON
    if (ct.includes("application/json")) {
      const data = await resp.json().catch(() => ({}));
      make_message(data.message || "Ошибка", data.status || "error");
      return;
    }

    if (!resp.ok) {
      make_message("Ошибка скачивания", "error");
      return;
    }

    // скачиваем файл
    const blob = await resp.blob();

    let filename = "cards_in_progress.zip";
    const cd = resp.headers.get("content-disposition") || "";
    const mStar = cd.match(/filename\*\s*=\s*UTF-8''([^;]+)/i);
    const m = cd.match(/filename\s*=\s*"?([^"]+)"?/i);
    if (mStar && mStar[1]) filename = decodeURIComponent(mStar[1]);
    else if (m && m[1]) filename = m[1];

    const link = document.createElement("a");
    const objUrl = window.URL.createObjectURL(blob);
    link.href = objUrl;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(objUrl);

    make_message("Архив сформирован", "success");

    // ✅ если бэк сообщил, что карточки переведены — перезагружаем колонки
    const moved = resp.headers.get("X-PC-Moved");
    if (moved === "1") {
      if (typeof pcReloadColumn === "function") {
        pcReloadColumn("in_progress");
        pcReloadColumn("in_moderation");
      }
    }
  } catch (e) {
    make_message(e.message || "Сетевая ошибка", "error");
  }
}

async function pcDownloadCompaniesByStatus(statusKey) {
  const cfgEl = document.getElementById("pc-config");
  const csrf = cfgEl?.dataset?.csrf;
  const baseUrl = cfgEl?.dataset?.downloadCompaniesUrl;

  if (!baseUrl) {
    make_message("downloadCompaniesUrl отсутствует", "error");
    return;
  }

  const url = `${baseUrl}?status=${encodeURIComponent(statusKey)}`;

  loadingCircle(); // ✅ старт лоадера

  try {
    const resp = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRFToken": csrf || ""
      },
      body: JSON.stringify({}),
      credentials: "same-origin",
    });

    const ct = (resp.headers.get("content-type") || "").toLowerCase();

    // если пришёл JSON — это ошибка
    if (ct.includes("application/json")) {
      const data = await resp.json().catch(() => ({}));
      make_message(data.message || "Ошибка", data.status || "error");
      return;
    }

    if (!resp.ok) {
      make_message("Ошибка скачивания", "error");
      return;
    }

    // скачивание файла
    const blob = await resp.blob();

    let filename = `cards_${statusKey}.zip`;
    const cd = resp.headers.get("content-disposition") || "";
    const mStar = cd.match(/filename\*\s*=\s*UTF-8''([^;]+)/i);
    const m = cd.match(/filename\s*=\s*"?([^"]+)"?/i);
    if (mStar && mStar[1]) filename = decodeURIComponent(mStar[1]);
    else if (m && m[1]) filename = m[1];

    const link = document.createElement("a");
    const objUrl = window.URL.createObjectURL(blob);
    link.href = objUrl;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(objUrl);

    make_message("Архив сформирован", "success");

  } catch (e) {
    make_message(e.message || "Сетевая ошибка", "error");
  } finally {
    close_Loading_circle(); // ✅ всегда закрываем
  }
}
