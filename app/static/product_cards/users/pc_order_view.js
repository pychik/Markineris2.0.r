(function () {
  function cfg() {
    const el = document.getElementById("config");
    if (!el) return null;
    return {
      el,
      csrf: el.getAttribute("data-csrf") || "",
      orderId: el.getAttribute("data-order-id") || "",
      tableUrl: el.getAttribute("data-table-url") || "",
      deleteOrderUrl: el.getAttribute("data-delete-order-url") || "",
      posUrlTpl: el.getAttribute("data-pos-url-template") || "",
      deletePosUrlTpl: el.getAttribute("data-delete-pos-url-template") || "",
    };
  }

  function buildUrlFromTemplate(tpl, posId) {
    // tpl вида /.../pos/0 или .../pos/0/delete
    return tpl.replace(/\/0(\/delete)?$/, `/${posId}$1`);
  }

  function getOrdersPosCount() {
    const root = document.getElementById("pc-order-table-root");
    if (!root) return 0;
    const v = root.getAttribute("data-orders-pos-count");
    const n = parseInt(v || "0", 10);
    return isNaN(n) ? 0 : n;
  }

  async function loadPcOrderTable() {
    const c = cfg();
    if (!c || !c.tableUrl) return;

    // 1) спиннер + плейсхолдер в блоке
    const mount = document.getElementById("pc-order-table");
    if (mount) {
      mount.innerHTML = `
        <div class="text-center py-4">
          <div class="spinner-border" role="status"></div>
          <div class="mt-2 text-muted">Загрузка заказа...</div>
        </div>
      `;
    }

    // если у тебя глобальный оверлей-спиннер:
    try { loadingCircle(); } catch (e) {}

    try {
      const r = await fetch(c.tableUrl, { method: "GET" });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);

      const html = await r.text();
      if (mount) mount.innerHTML = html;

      // обновим скрытое поле количества позиций (если оно есть на странице)
      const cnt = getOrdersPosCount();
      const inp = document.getElementById("orders_pos_count");
      if (inp) inp.value = String(cnt);

    } catch (e) {
      if (mount) {
        mount.innerHTML = `
          <div class="alert alert-danger mb-0">
            Ошибка загрузки заказа. Обновите страницу или попробуйте позже.
          </div>
        `;
      }
      console.error("loadPcOrderTable error:", e);
    } finally {
      // закрыть оверлей-спиннер
      try { close_Loading_circle(); } catch (e) {}
    }
  }


  async function deletePcOrder() {
    const c = cfg();
    if (!c || !c.deleteOrderUrl) return;

    const r = await fetch(c.deleteOrderUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": c.csrf,
      },
      body: JSON.stringify({}),
    });

    const data = await r.json().catch(() => ({}));
    if (data.status === "success") {
      if (data.redirect_url) {
        window.location.href = data.redirect_url;
      } else {
        window.location.reload();
      }
      return;
    }
    alert(data.message || "Ошибка удаления заказа");
  }

  async function pcDeletePos(posId) {
    const c = cfg();
    if (!c) return;

    const beforeCnt = getOrdersPosCount(); // сколько было ДО удаления
    const url = buildUrlFromTemplate(c.deletePosUrlTpl, posId);

    const r = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": c.csrf,
      },
      body: JSON.stringify({}),
    });

    const data = await r.json().catch(() => ({}));
    if (data.status !== "success") {
      alert(data.message || "Ошибка удаления позиции");
      return;
    }

    // ✅ Если это была последняя позиция — удаляем заказ полностью
    if (beforeCnt <= 1) {
      await deletePcOrder();
      return;
    }

    // иначе просто обновляем таблицу
    await loadPcOrderTable();
  }

  async function pcOpenPos(posId) {
    const c = cfg();
    if (!c) return;

    const url = buildUrlFromTemplate(c.posUrlTpl, posId);
    const r = await fetch(url, { method: "GET" });

    if (!r.ok) {
      alert("Не удалось загрузить позицию");
      return;
    }

    const html = await r.text();
    const body = document.getElementById("pcPosModalBody");
    if (body) body.innerHTML = html;

    const modalEl = document.getElementById("pcPosModal");
    if (modalEl && window.bootstrap) {
      const modal = new bootstrap.Modal(modalEl);
      modal.show();
    }
  }

  // эти функции должны быть доступны из inline onclick в таблице
  window.pcDeletePos = function (orderId, posId) {
    // orderId не нужен, у нас всё в config
    if (!confirm("Удалить позицию?")) return;
    pcDeletePos(posId);
  };

  window.pcOpenPos = function (orderId, posId) {
    pcOpenPos(posId);
  };

  window.pcFilterTable = function (q) {
    q = (q || "").toLowerCase().trim();
    const rows = document.querySelectorAll("#pc_order_table_body_info tr");
    rows.forEach((r) => {
      const a = (r.getAttribute("data-article") || "").toLowerCase();
      const t = (r.getAttribute("data-trademark") || "").toLowerCase();
      const ok = !q || a.includes(q) || t.includes(q);
      r.style.display = ok ? "" : "none";
    });
  };

  document.addEventListener("DOMContentLoaded", () => {
    loadPcOrderTable();

    const btn = document.getElementById("btnClearPcOrder");
    if (btn) {
      btn.addEventListener("click", () => {
        if (!confirm("Удалить заказ полностью?")) return;
        deletePcOrder();
      });
    }
  });
})();
