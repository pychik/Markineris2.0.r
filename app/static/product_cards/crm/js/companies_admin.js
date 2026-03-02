"use strict";

function pcGetConfigEl() {
  const el = document.getElementById("pc-config");
  if (!el) throw new Error("pc-config not found");
  return el;
}

function pcCfg() {
  return pcGetConfigEl().dataset;
}

function pcUrlFromTemplate(tpl, id) {
  // ожидаем, что template заканчивается на /0
  if (tpl.endsWith("/0")) return tpl.slice(0, -2) + "/" + id;
  // fallback
  return tpl.replace("0", String(id));
}

function pcGetModalEl() {
  const el = document.getElementById("pc-view-modal");
  if (!el) throw new Error("pc-view-modal not found");
  return el;
}

function pcGetModalBodyEl() {
  const el = document.getElementById("pc-view-modal-body");
  if (!el) throw new Error("pc-view-modal-body not found");
  return el;
}

function pcOpenModal() {
  return bootstrap.Modal.getOrCreateInstance(pcGetModalEl());
}

function pcSetModalHtml(html) {
  pcGetModalBodyEl().innerHTML = html;
}

function pcAjaxJsonOrThrow(res) {
  return res.json().catch(() => ({})).then((data) => {
    if (!res.ok || data.status !== "success") throw new Error(data.message || "Ошибка");
    return data;
  });
}

function pcCompaniesOpen() {
  const cfg = pcCfg();

  fetch(cfg.companiesModalUrl, { method: "GET" })
    .then(pcAjaxJsonOrThrow)
    .then((data) => {
      pcSetModalTitle("Пул фирм");          // ← ВАЖНО
      pcSetModalHtml(data.html);
      pcOpenModal().show();
      pcCompaniesBindModalHandlers();

      pcCompaniesBindModalHandlers();
    })
    .catch((e) => alert(e.message));
}

function pcCompaniesBindModalHandlers() {
  const cfg = pcCfg();
  const root = pcGetModalBodyEl();

  // CREATE
  const createForm = root.querySelector("#pcCompaniesCreateForm");
  if (createForm && !createForm.dataset.bound) {
    createForm.dataset.bound = "1";

    createForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const fd = new FormData(createForm);
      fd.append("csrf_token", cfg.csrf);
      loadingCircle();
      fetch(cfg.companiesCreateUrl, { method: "POST", body: fd })
        .then(pcAjaxJsonOrThrow)
        .then((data) => {
          root.querySelector("#pcCompaniesTableWrap").innerHTML = data.table_html;
          createForm.reset();
          pcCompaniesShowHint(data.message);
        })
        .catch((err) => alert(err.message))
        .finally(() => close_Loading_circle());
    });
  }

  // TABLE ACTIONS (delegate)
  if (!root.dataset.boundTable) {
    root.dataset.boundTable = "1";

    root.addEventListener("click", (e) => {
      const btn = e.target.closest("button[data-action]");
      if (!btn) return;

      const tr = btn.closest("tr[data-company-id]");
      if (!tr) return;

      const companyId = tr.dataset.companyId;
      const action = btn.dataset.action;


      if (action === "delete") {
        if (!confirm("Удалить фирму из пула? Это затронет пользователей и их карточки.")) return;

        const fd = new FormData();
        fd.append("csrf_token", cfg.csrf);

        const url = pcUrlFromTemplate(cfg.companiesDeleteUrlTemplate, companyId);
        loadingCircle();
        fetch(url, { method: "POST", body: fd })
          .then(pcAjaxJsonOrThrow)
          .then((data) => {
            root.querySelector("#pcCompaniesTableWrap").innerHTML = data.table_html;
            pcCompaniesShowHint(data.message);
          })
          .catch((err) => alert(err.message))
        .finally( () => close_Loading_circle());
      }
    });
  }
}

function pcCompaniesShowHint(text) {
  const root = pcGetModalBodyEl();
  const hint = root.querySelector("#pcCompaniesHint");
  if (hint) hint.textContent = text || "";
}

window.pcCompaniesOpen = pcCompaniesOpen;
