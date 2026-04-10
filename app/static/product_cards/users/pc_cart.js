const O_B_CART_STORAGE_KEY = "o_b_cart_orders_v2";

// Отдельное хранилище настроек (когда корзина пуста)
const O_B_CART_SETTINGS_KEY = "o_b_cart_settings_v1";


let oBCartMessageTimer = null;

function make_cart_message(html, type = "info") {
  const el = document.getElementById("o-b-cart-messages");
  if (!el) return;

  if (type === "error") type = "danger";

  // вставляем сообщение
  el.innerHTML = `<div class="alert alert-${type} py-2 mb-2">${html}</div>`;

  // если уже был таймер — сбрасываем
  if (oBCartMessageTimer) {
    clearTimeout(oBCartMessageTimer);
    oBCartMessageTimer = null;
  }

  // автоочистка через 15 сек
  oBCartMessageTimer = setTimeout(() => {
    el.innerHTML = "";
    oBCartMessageTimer = null;
  }, 15000);
}


// Выбор маркировки в корзине (фикс поведения модалок оставляем как у тебя)
function cart_process_mark(mark_id, slice_length) {
  const image_input_value = document.getElementById(mark_id)?.value || "";
  const mark_field = document.getElementById("mark_type");
  const mark_field_hidden = document.getElementById("mark_type_hidden");

  if (mark_field) {
    mark_field.value = image_input_value.slice(slice_length);
    mark_field.classList.remove("is-invalid");
    mark_field.classList.add("is-valid");
  }
  if (mark_field_hidden) {
    mark_field_hidden.value = image_input_value;
  }

  // 1) закрываем markModal
  const markModalEl = document.getElementById("markModal");
  if (markModalEl && window.bootstrap?.Modal) {
    const mm = bootstrap.Modal.getInstance(markModalEl);
    if (mm) mm.hide();
    else new bootstrap.Modal(markModalEl).hide();
  }

  // 2) СРАЗУ поднимаем обратно модалку настроек (если её почему-то закрыло)
  setTimeout(() => {
    const settingsEl = document.getElementById("o-b-cart-settings-modal");
    if (!settingsEl || !window.bootstrap?.Modal) return;

    // если она уже видима — ничего не делаем
    if (settingsEl.classList.contains("show")) {
      document.body.classList.add("modal-open");
      return;
    }

    // если закрылась — открываем обратно
    const sm = bootstrap.Modal.getInstance(settingsEl) || new bootstrap.Modal(settingsEl, {
      backdrop: "static",
      keyboard: false
    });
    sm.show();
  }, 50);
}

// --- helpers ---
function oBCartLoad() {
  try { return JSON.parse(localStorage.getItem(O_B_CART_STORAGE_KEY) || "[]"); }
  catch { return []; }
}

function oBCartSave(orders) {
  localStorage.setItem(O_B_CART_STORAGE_KEY, JSON.stringify(orders));
  oBCartRender();
  oBCartUpdateBadge();
  oBCartSyncOpenCardModalInputsFromCart();
  oBCartSyncParfumQtyFromCart();
}

function oBCartLoadSettings() {
  try { return JSON.parse(localStorage.getItem(O_B_CART_SETTINGS_KEY) || "{}") || {}; }
  catch { return {}; }
}

function oBCartSaveSettings(settings) {
  localStorage.setItem(O_B_CART_SETTINGS_KEY, JSON.stringify(settings || {}));
}

function oBCartUpdateBadge() {
  const orders = oBCartLoad();
  const count = orders.reduce((acc, o) => acc + (o.items?.length || 0), 0);
  const el = document.getElementById("o-b-cart-count");
  if (el) el.textContent = String(count);
}

function oBGetCurrentCategoryTitles() {
  const cfg = document.getElementById("categories_config");
  const catTitle = (cfg?.dataset?.currentCategoryTitle || "").trim();
  const subTitle = (cfg?.dataset?.currentSubcategoryTitle || "").trim();
  return {
    category_title: catTitle,          // "одежда", "обувь" ...
    subcategory_title: subTitle,       // "нижнее белье" ...
  };
}

function pcSetApplyBtnState(btn, qty) {
  if (!btn) return;
  const q = parseInt(qty, 10) || 0;

  btn.classList.remove("pc-btn-yellow", "pc-btn-green");
  btn.classList.add(q > 0 ? "pc-btn-green" : "pc-btn-yellow");
}

function oBNormalizeCardId(cardId) {
  const num = parseInt(cardId, 10);
  return Number.isFinite(num) ? String(num) : "";
}

// ключ позиции:
// - parfum: category + card_id
// - остальные: card_id + size + size_type + unit
function oBItemKey(item) {
  const category = (item.category || "").trim();
  const cardId = oBNormalizeCardId(item.card_id);
  const size = (item.size || "").trim();
  const st = (item.size_type || "").trim();
  const unit = (item.unit || "").trim();

  if (category === "parfum") {
    return oBParfumKey(category, cardId);
  }

  return `${category}||${cardId}||${size}||${st}||${unit}`;
}

// Корзина ДОЛЖНА содержать позиции только одной категории и одной субкатегории.
// Если пользователь добавляет другую категорию/субкатегорию — очищаем корзину.
function oBEnsureSingleContextOrReset(orders, category, subcategory) {
  if (!orders.length) return orders;

  const cur = orders[0];
  const curCat = cur.category || "";
  const curSub = cur.subcategory || "";

  const nextCat = category || "";
  const nextSub = subcategory || "";

  if (curCat !== nextCat || curSub !== nextSub) {
    // очищаем полностью
    return [];
  }
  return orders;
}

// Применение сохранённых настроек (если корзина была пуста и настройки сохранили заранее)
function oBCartApplyDefaultSettingsToOrder(order) {
  const s = oBCartLoadSettings();
  if (!s) return order;

  // company
  if (s.company && typeof s.company === "object") {
    order.company = { ...(order.company || {}), ...s.company };
  }

  // mark_type
  const mt = (order.mark_type || "").trim();
  if (!mt || mt === "МАРКИРОВКА НЕ ВЫБРАНА") {
    const sMt = String(s.mark_type || "").trim();
    if (sMt) order.mark_type = sMt;
  }

  return order;
}

function oBGetOrCreateSingleOrder(orders, payload) {
  const category = payload.category;
  const subcategory = payload.subcategory || "";

  // гарантируем один контекст
  orders = oBEnsureSingleContextOrReset(orders, category, subcategory);

  if (orders.length) return { orders, order: orders[0] };

  const titles = oBGetCurrentCategoryTitles();
  const order = {
    orderId: `tmp-${Date.now()}`,
    category,
    subcategory,
    category_title: titles.category_title || category,
    subcategory_title: titles.subcategory_title || "",
    items: [],
    company: {
      company_idn: "",
      company_type: "",
      company_name: "",
      edo_type: "ЭДО-ЛАЙТ",
      edo_id: ""
    },
    mark_type: "МАРКИРОВКА НЕ ВЫБРАНА"
  };

  // подмешаем настройки, сохранённые при пустой корзине
  oBCartApplyDefaultSettingsToOrder(order);

  orders.push(order);
  return { orders, order };
}

function oBCartGetSingleOrder() {
  const orders = oBCartLoad();
  return orders.length ? orders[0] : null;
}

function oBReadCompanyFromSettingsModal() {
  const company_idn = (document.getElementById("company_idn")?.value || "").trim();
  const company_type = (document.getElementById("company_type")?.value || "").trim();
  const company_name = (document.getElementById("company_name")?.value || "").trim();
  const edo_type = (document.getElementById("edo_type")?.value || "ЭДО-ЛАЙТ").trim();
  const edo_id = (document.getElementById("edo_id")?.value || "").trim(); // если у тебя есть такое поле

  return { company_idn, company_type, company_name, edo_type, edo_id };
}

function oBReadMarkTypeFromSettingsModal() {
  // у тебя есть #mark_type и #mark_type_hidden
  const v = (document.getElementById("mark_type_hidden")?.value
          || document.getElementById("mark_type")?.value
          || "").trim();
  return v || "МАРКИРОВКА НЕ ВЫБРАНА";
}

// Сохраняем настройки в текущий заказ, а если корзина пуста — в отдельное хранилище по умолчанию
function oBCartApplyOrderSettings({ company, mark_type }) {
  const orders = oBCartLoad();
  const mt = String(mark_type || "").trim();

  // Корзина пуста: сохраняем как "настройки по умолчанию"
  if (!orders.length) {
    const saved = oBCartLoadSettings();
    const next = {
      company: { ...(saved.company || {}), ...(company || {}) },
      mark_type: mt || saved.mark_type || "МАРКИРОВКА НЕ ВЫБРАНА",
    };
    oBCartSaveSettings(next);
    return { ok: true, stored_as_defaults: true };
  }

  // Корзина не пуста: обновляем текущий заказ
  orders[0].company = { ...(orders[0].company || {}), ...(company || {}) };
  orders[0].mark_type = mt || orders[0].mark_type || "МАРКИРОВКА НЕ ВЫБРАНА";

  oBCartSave(orders);
  return { ok: true };
}

function oBCartValidateOrderSettings(order) {
  if (!order) return "Корзина пуста";

  const c = order.company || {};
  if (!c.company_idn || !c.company_name || !c.company_type) {
    return "Заполните данные компании (ИНН, тип организации, наименование) в настройках заказа.";
  }
  if (!order.mark_type || order.mark_type === "МАРКИРОВКА НЕ ВЫБРАНА") {
    return "Выберите тип этикетки (маркировку) в настройках заказа.";
  }
  return null;
}

// --- core ops ---
function oBCartAddOrMergeItem(payload) {
  let orders = oBCartLoad();

  // если контекст другой — очищаем
  orders = oBEnsureSingleContextOrReset(orders, payload.category, payload.subcategory || "");

  const res = oBGetOrCreateSingleOrder(orders, payload);
  orders = res.orders;
  const order = res.order;

  // обновим русские заголовки (важно при пагинации/переключениях, чтобы сохранялось до очистки)
  if (!order.category_title || order.category_title === order.category) {
    const titles = oBGetCurrentCategoryTitles();
    if (titles.category_title) order.category_title = titles.category_title;
    if (titles.subcategory_title && !order.subcategory_title) order.subcategory_title = titles.subcategory_title;
  }

  const key = oBItemKey(payload);
  const idx = order.items.findIndex(x => x.key === key);

  if (idx >= 0) {
    // уже есть такая позиция -> суммируем количество
    const old = order.items[idx];
    old.qty = (parseInt(old.qty || 0, 10) || 0) + (parseInt(payload.qty || 0, 10) || 0);

  } else {
    order.items.push({
      key,
      card_id: payload.card_id,
      category: payload.category,
      subcategory: payload.subcategory || "",
      category_title: order.category_title || payload.category,
      subcategory_title: order.subcategory_title || "",
      article: payload.article || "",
      trademark: payload.trademark || "",
      size: payload.size || "",
      size_type: payload.size_type || "",
      unit: payload.unit || "",
      qty: parseInt(payload.qty, 10),
      color: payload.color || ""
    });
  }

  oBCartSave(orders);
}

function oBNormalizeArticle(article) {
  return (article || "").trim();
}

function oBCartRemoveItem(orderId, idx) {
  const orders = oBCartLoad();
  const o = orders.find(x => x.orderId === orderId);
  if (!o) return;

  o.items.splice(idx, 1);

  // если заказ пуст — удаляем всё (один заказ на корзину)
  const filtered = o.items.length ? orders : [];
  oBCartSave(filtered);
}

function oBCartUpdateQty(orderId, idx, newQty, rerender = true) {
  const orders = oBCartLoad();
  const o = orders.find(x => x.orderId === orderId);
  if (!o) return;

  const item = o.items[idx];
  if (!item) return;

  const qty = parseInt(newQty, 10);
  if (!qty || qty < 1) return;

  item.qty = qty;
  localStorage.setItem(O_B_CART_STORAGE_KEY, JSON.stringify(orders));

  if (rerender) {
    oBCartRender();
    oBCartUpdateBadge();
  }
  oBCartSyncOpenCardModalInputsFromCart();
  oBCartSyncParfumQtyFromCart();
}


function oBCartClear() {
  oBCartSave([]);
}

// --- render ---
function oBCartRender() {

  const root = document.getElementById("o-b-cart-orders");
  if (!root) return;

  const orders = oBCartLoad();

  const statusEl = document.getElementById("o-b-cart-settings-status");

  // ✅ если заказов нет — рисуем статус из defaults
  if (!orders.length) {
    if (statusEl) {
      const s = oBCartLoadSettings();
      const c = s.company || {};

      const companyOk = !!(String(c.company_idn || "").trim()
        && String(c.company_type || "").trim()
        && String(c.company_name || "").trim());

      const mark = String(s.mark_type || "").trim();
      const markOk = mark && mark !== "МАРКИРОВКА НЕ ВЫБРАНА";

      statusEl.innerHTML = `
        <div class="small">
          <div>
            Компания:
            <span class="${companyOk ? "text-success" : "text-danger"}">
              ${companyOk ? "заполнена" : "не заполнена"}
            </span>
          </div>
          <div>
            Маркировка:
            <span class="${markOk ? "text-success" : "text-danger"}">
              ${markOk ? mark : "не выбрана"}
            </span>
          </div>
        </div>
      `;
    }

    root.innerHTML = `<div class="text-muted">Корзина пуста</div>`;
    return;
  }


  const order = orders[0]; // один заказ


  if (statusEl) {
    const ord = orders[0];
    if (!ord) {
      statusEl.innerHTML = "";
    } else {
      const companyOk = oBIsCompanyFilled(ord);
      const mark = (ord.mark_type || "").trim();
      const markOk = mark && mark !== "МАРКИРОВКА НЕ ВЫБРАНА";

      statusEl.innerHTML = `
        <div class="small">
          <div>
            Компания:
            <span class="${companyOk ? "text-success" : "text-danger"}">
              ${companyOk ? "заполнена" : "не заполнена"}
            </span>
          </div>
          <div>
            Маркировка:
            <span class="${markOk ? "text-success" : "text-danger"}">
              ${markOk ? mark : "не выбрана"}
            </span>
          </div>
        </div>
      `;
    }
  }

  const catTitle = (order.category_title || "").trim() || order.category || "—";
  const subTitle = (order.subcategory_title || "").trim();
  const headTitle = subTitle ? `${catTitle} · ${subTitle}` : `${catTitle}`;

  // группируем по артикулу (одна "шапка" артикула + список размеров)
  const groups = new Map();
  order.items.forEach((it, idx) => {
    const gKey = it.category === "parfum"
      ? oBParfumKey(it.category, it.card_id)
      : `${it.card_id}||${(it.article||"").trim()}||${(it.trademark||"").trim()}`;

    if (!groups.has(gKey)) groups.set(gKey, { it, rows: [] });
    groups.get(gKey).rows.push({ it, idx });
  });

  const itemsHtml = Array.from(groups.values()).map(g => {
    const it0 = g.it;

    const catLine = it0.category_title
      ? `<div class="o-b-cart-meta">Категория: ${it0.category_title}</div>`
      : "";


    const sizesHtml = g.rows.map(({ it, idx }) => {
      const isParfum = it.category === "parfum";
      const sizeLine = isParfum
        ? "Количество"
        : (it.size
          ? `Размер: ${it.size}${it.size_type ? " · " + it.size_type : ""}${it.unit ? " · " + it.unit : ""}`
          : `Без размеров`);
      const removeTitle = isParfum ? "Удалить позицию" : "Удалить размер";

      return `
        <div class="o-b-size-row">
          <div class="o-b-size-left">
            <div class="o-b-cart-meta-pos">${sizeLine}</div>
          </div>
          <div class="d-flex gap-2">
            <input type="number"
                   class="o-b-qty o-b-stack-w"
                   min="1"
                   value="${it.qty}"
                   data-o-b-qty="1"
                   data-order-id="${order.orderId}"
                   data-idx="${idx}">
            <button class="o-b-btn o-b-btn--danger o-b-btn--icon"
                    data-o-b-remove="1"
                    data-order-id="${order.orderId}"
                    data-idx="${idx}"
                    title="${removeTitle}">
              <span class="mx-1" >
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-trash" viewBox="0 0 16 16">
                  <path d="M5.5 5.5A.5.5 0 0 1 6 6v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5m2.5 0a.5.5 0 0 1 .5.5v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5m3 .5a.5.5 0 0 0-1 0v6a.5.5 0 0 0 1 0z"/>
                  <path d="M14.5 3a1 1 0 0 1-1 1H13v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V4h-.5a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1H6a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1h3.5a1 1 0 0 1 1 1zM4.118 4 4 4.059V13a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1V4.059L11.882 4zM2.5 3h11V2h-11z"/>
                </svg>
              </span>
            </button>
          </div>
        </div>
      `;
    }).join("");

    return `
      <div class="o-b-article-block">
        <div class="o-b-article-head">
          <div class="o-b-cart-title">
            <span class="text-truncate">${it0.article || "—"}</span>
            <span class="o-b-cart-meta">(${it0.trademark || "—"})</span>
          
            ${
              it0.category !== "parfum" && it0.color
                ? `<div class="o-b-cart-meta small text-muted" style="font-size: 8px">${it0.color}</div>`
                : ""
            }
          </div>
          ${catLine}
        </div>
        <div class="o-b-sizes-list">
          ${sizesHtml}
        </div>
      </div>
    `;
  }).join("");


  root.innerHTML = `
    <div class="o-b-order-block">
      <div class="o-b-order-head">Заказ: ${headTitle} <span class="o-b-cart-meta">(${order.items.length})</span></div>
      <div class="o-b-cart-list">
        ${itemsHtml}
      </div>
    </div>
  `;

  // bind events (remove + qty change)
  root.querySelectorAll("[data-o-b-remove='1']").forEach(btn => {
    btn.addEventListener("click", () => {
      oBCartRemoveItem(btn.dataset.orderId, parseInt(btn.dataset.idx, 10));
    });
  });

  root.querySelectorAll("[data-o-b-qty='1']").forEach(inp => {
    inp.addEventListener("input", () => {
      oBCartUpdateQty(
        inp.dataset.orderId,
        parseInt(inp.dataset.idx, 10),
        inp.value,
        false // без ререндера
      );
    });

    inp.addEventListener("change", () => {
      oBCartRender();
      oBCartUpdateBadge();
    });
  });
}


// --- submit payload builder + validation ---
function oBCartBuildPayloadOrError() {
  const orders = oBCartLoad();

  if (!orders.length) {
    return { error: "Корзина пуста" };
  }

  const out = [];

  for (const ord of orders) {
    if (!ord.items || !ord.items.length) continue;

    // ✅ PARFUM: группируем по card_id, без sizes
    if ((ord.category || "").trim() === "parfum") {
      const byCardId = {};

      for (const it of ord.items) {
        const cardId = oBNormalizeCardId(it.card_id);
        if (!cardId) continue;

        if (!byCardId[cardId]) {
          byCardId[cardId] = {
            article: "",                   // у парфюма не используем
            trademark: it.trademark || "",
            card_id: parseInt(cardId, 10),
            category: it.category,
            subcategory: it.subcategory || "",
            qty: 0,
          };
        }

        // qty может прийти как it.qty либо как it.quantity — учтём оба
        const q = parseInt(it.qty ?? it.quantity ?? 0, 10) || 0;
        byCardId[cardId].qty += q;

        // RD: берём первую непустую
        if (!byCardId[cardId].rd && it.rd && typeof it.rd === "object") {
          byCardId[cardId].rd = it.rd;
        }
      }

      const items = Object.values(byCardId);

      if (!items.length) continue;

      for (const a of items) {

        if (!a.qty || a.qty < 1) {
          return { error: `Некорректное количество для карточки ${a.card_id}` };
        }
      }

      out.push({
        orderId: ord.orderId,
        category: ord.category,
        category_title: ord.category_title || ord.category,
        company: ord.company || null,
        mark_type: ord.mark_type || "МАРКИРОВКА НЕ ВЫБРАНА",
        items: items, // ✅ parfum items без sizes
      });

      continue; // ✅ не падаем в общую ветку
    }

    // ====== остальные категории  ======
    if (!ord.items || !ord.items.length) continue;

    // Для вещевых категорий одна карточка = один товар.
    // Размеры объединяем только внутри одного card_id.
    const byCardId = {};
    for (const it of ord.items) {
      const cardId = oBNormalizeCardId(it.card_id);
      const art = oBNormalizeArticle(it.article);
      if (!cardId || !art) continue;

      byCardId[cardId] = byCardId[cardId] || {
        article: art,
        trademark: it.trademark || "",
        card_id: parseInt(cardId, 10),
        category: it.category,
        subcategory: it.subcategory || "",
        color: it.color || "",
        sizes: []
      };

      byCardId[cardId].sizes.push({
        size: it.size || "",
        size_type: it.size_type || "",
        unit: it.unit || "",
        qty: parseInt(it.qty, 10) || 0
      });
    }

    const articles = Object.values(byCardId);

    for (const a of articles) {
      const bad = a.sizes.find(s => !s.qty || s.qty < 1);
      if (bad) {
        return { error: `Некорректное количество для артикула ${a.article}` };
      }
    }

    out.push({
      orderId: ord.orderId,
      category: ord.category,
      category_title: ord.category_title || ord.category,
      company: ord.company || null,
      mark_type: ord.mark_type || "МАРКИРОВКА НЕ ВЫБРАНА",
      items: articles
    });
  }

  if (!out.length) return { error: "Корзина пуста" };
  return { payload: { orders: out } };
}


async function oBCartSubmitToBackend(postUrl, csrfToken) {
  const order = oBCartGetSingleOrder();

  // ✅ если корзина пуста — просто сообщение, без модалки
  if (!order) {
    make_cart_message("Корзина пуста", "error");
    return;
  }

  const settingsErr = oBCartValidateOrderSettings(order);
  if (settingsErr) {
    make_cart_message(settingsErr, "error");

    // ✅ модалку открываем только если это НЕ "Корзина пуста"
    if (settingsErr !== "Корзина пуста") {
      document.getElementById("o-b-cart-settings")?.click();
    }
    return;
  }

  const built = oBCartBuildPayloadOrError();
  if (built.error) {
    make_message(built.error, "error");
    return;
  }

  try {
    const resp = await fetch(postUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRFToken": csrfToken || ""
      },
      body: JSON.stringify(built.payload)
    });

    const data = await resp.json().catch(() => ({}));
    if (data.status === "success") {
        make_message(data.message, "success");
        oBCartClearAll();

        if (data.redirect_url) {
          setTimeout(() => {
            window.location.href = data.redirect_url;
          }, 1000); // 1 секунда
        }
      }
    else {
      make_cart_message(data.message || "Ошибка при создании заказа", "error");
    }
  } catch (e) {
    console.error(e);
    make_cart_message("Ошибка сети при создании заказа", "error");
  }
}

function oBIsCompanyFilled(order) {
  const c = order?.company || {};
  return !!(String(c.company_idn || "").trim()
    && String(c.company_type || "").trim()
    && String(c.company_name || "").trim());
}



function oBCartClearAll() {
  // очистить корзину
  oBCartClear();

  // ✅ очистить сохранённые настройки (company/mark_type defaults)
  try { localStorage.removeItem(O_B_CART_SETTINGS_KEY); } catch(e) {}

  // обновить UI (на всякий)
  oBCartRender();
  oBCartUpdateBadge();

  // закрыть offcanvas
  const offcanvasEl = document.getElementById("o-b-cart-offcanvas");
  if (offcanvasEl && window.bootstrap?.Offcanvas) {
    bootstrap.Offcanvas.getInstance(offcanvasEl)?.hide();
  }
}

function oBCartClearAllLocal() {
  // очистить позиции
  localStorage.setItem(O_B_CART_STORAGE_KEY, "[]");

  // очистить сохранённые настройки компании/этикетки
  try { localStorage.removeItem(O_B_CART_SETTINGS_KEY); } catch(e) {}

  // обновить UI
  oBCartRender();
  oBCartUpdateBadge();

  make_cart_message("Корзина очищена", "success");
}

function oBGetOpenCardModalContext() {
  const body = document.getElementById("pcCardViewModalBody");
  if (!body) return null;

  // ✅ берем данные из любой подходящей кнопки в модалке
  const anyBtn =
    body.querySelector(".pc-apply-qty-btn") ||
    body.querySelector(".pc-add-to-cart-btn") ||   // fallback на старое
    body.querySelector("#pc-parfum-add");          // fallback на парфюм

  if (!anyBtn) return null;

  return {
    category: (anyBtn.dataset.category || "").trim(),
    subcategory: (anyBtn.dataset.subcategory || "").trim(),
    card_id: parseInt(anyBtn.dataset.cardId, 10) || null,
  };
}


function oBCartGetQtyForSize(order, ctx, size, sizeType, unit) {
  if (!order || !ctx) return 0;

  // если модалка другой категории/подкатегории — 0
  if ((order.category || "") !== (ctx.category || "")) return 0;
  if ((order.subcategory || "") !== (ctx.subcategory || "")) return 0;

  const k = oBSizeKey(ctx.category, ctx.card_id, size, sizeType, unit);

  const it = (order.items || []).find(x => {
    // 1) новый формат: key уже card_id-based
    if (oBKeyNorm(x.key) === oBKeyNorm(k)) return true;

    // 2) fallback: вычислим ключ из полей элемента корзины
    return oBKeyNorm(oBStoredSizeKey(x)) === oBKeyNorm(k);
  });

  return parseInt(it?.qty || 0, 10) || 0;
}


function oBCartSyncOpenCardModalInputsFromCart() {
  const ctx = oBGetOpenCardModalContext();
  if (!ctx) return;

  const order = oBCartGetSingleOrder();

  // Все инпуты размеров в модалке
  const body = document.getElementById("pcCardViewModalBody");
  const inputs = body.querySelectorAll("input.pc-size-qty");
  inputs.forEach(inp => {
    const size = inp.dataset.size || "";
    const st = inp.dataset.sizeType || "";
    const unit = inp.dataset.unit || "";

    const qty = oBCartGetQtyForSize(order, ctx, size, st, unit);

    // ВАЖНО: если нет в корзине — показываем 0 (не добавлено)
    inp.value = String(qty || 0);
  });
}

function oBCartGetParfumQtyFromCart() {
  const order = oBCartGetSingleOrder();
  if (!order || (order.category || "").toLowerCase() !== "parfum") return 0;

  // ✅ берём card_id из текущей открытой карточки
  const btn = document.getElementById("pc-parfum-add");
  const cardId = oBNormalizeCardId(btn?.dataset?.cardId);
  if (!cardId) return 0;

  const key = oBParfumKey("parfum", cardId);
  const it = (order.items || []).find(
    x => oBParfumKey(x.category, x.card_id) === key
  );

  return parseInt(it?.qty || 0, 10) || 0;
}

function oBCartSyncParfumQtyFromCart() {
  const inp = document.getElementById("pc-parfum-qty");
  if (!inp) return;

  inp.value = String(oBCartGetParfumQtyFromCart() || 0);
}
// ===== CART KEYS =====

// ключ для парфюма (1 позиция = 1 карточка)
function oBParfumKey(category, cardId) {
  return `${(category || "").trim()}||${oBNormalizeCardId(cardId)}`;
}

function oBKeyNorm(v) {
  return String(v || "").trim();
}

// надёжный ключ для size-based позиций из реальных полей элемента корзины
function oBStoredSizeKey(it) {
  return oBSizeKey(
    it.category,
    it.card_id,
    it.size,
    it.size_type || it.sizeType || "",
    it.unit || ""
  );
}

// ключ для size-based товаров
function oBSizeKey(category, cardId, size, sizeType, unit) {
  return [
    (category || ""),
    oBNormalizeCardId(cardId),
    (size || "").trim(),
    (sizeType || "").trim(),
    (unit || "").trim(),
  ].join("||");
}


function oBCartUpsertFromModalQty(payload) {
  // payload: {card_id, category, subcategory, article, trademark, size, size_type, unit, qty}
  if (!payload || !payload.category) return;

  const qty = Math.max(0, parseInt(payload.qty, 10) || 0);

  let orders = oBCartLoad();
  orders = oBEnsureSingleContextOrReset(orders, payload.category, payload.subcategory || "");

  const res = oBGetOrCreateSingleOrder(orders, payload);
  orders = res.orders;
  const order = res.order;

  // --- PARFUM (ключ по card_id) ---
  if ((payload.category || "").trim() === "parfum") {
    const k = oBParfumKey(payload.category, payload.card_id);
    const idx = order.items.findIndex(x => oBParfumKey(x.category, x.card_id) === k);

    if (qty === 0) {
      if (idx >= 0) order.items.splice(idx, 1);
      oBCartSave(orders);
      return;
    }

    if (idx >= 0) {
      order.items[idx].qty = qty;

    } else {
      order.items.push({
        key: k,
        card_id: payload.card_id,
        category: payload.category,
        subcategory: payload.subcategory || "",
        article: payload.article || "",
        trademark: payload.trademark || "",
        size: payload.size || "",
        size_type: payload.size_type || "",
        unit: payload.unit || "",
        qty: qty
      });
    }

    oBCartSave(orders);
    return;
  }
  // --- NON-PARFUM (ключ по size) ---
  const k = oBSizeKey(
    payload.category,
    payload.card_id,
    payload.size,
    payload.size_type,
    payload.unit
  );

  const idx = order.items.findIndex(x => {
    if (oBKeyNorm(x.key) === oBKeyNorm(k)) return true;
    return oBKeyNorm(oBStoredSizeKey(x)) === oBKeyNorm(k);
  });


  if (qty === 0) {
    if (idx >= 0) order.items.splice(idx, 1);
    oBCartSave(orders);
    return;
  }

  if (idx >= 0) {
    order.items[idx].qty = qty;
  } else {
    order.items.push({
      key: k,
      card_id: payload.card_id,
      category: payload.category,
      subcategory: payload.subcategory || "",
      article: payload.article || "",
      trademark: payload.trademark || "",
      color: payload.color || "",   // если ты добавляешь цвет
      size: payload.size || "",
      size_type: payload.size_type || "",
      unit: payload.unit || "",
      qty: qty
    });
  }

  oBCartSave(orders);

}


function pcSyncApplyButtonsFromInputs() {
  const body = document.getElementById("pcCardViewModalBody");
  if (!body) return;

  // sizes
  body.querySelectorAll("tr").forEach(tr => {
    const inp = tr.querySelector("input.pc-size-qty");
    const btn = tr.querySelector(".pc-apply-qty-btn");
    if (!inp || !btn) return;
    pcSetApplyBtnState(btn, inp.value);
  });

  // parfum
  const pInp = document.getElementById("pc-parfum-qty");
  const pBtn = document.getElementById("pc-parfum-add");
  if (pInp && pBtn) pcSetApplyBtnState(pBtn, pInp.value);
}

document.addEventListener("DOMContentLoaded", () => {
  oBCartRender();
  oBCartUpdateBadge();

  // Открытие настроек: если корзина пуста — подставим сохранённые defaults
  document.getElementById("o-b-cart-settings")?.addEventListener("click", () => {
    const order = oBCartGetSingleOrder();
    const defaults = oBCartLoadSettings();

    const c = (order?.company) || (defaults.company || {});
    if (document.getElementById("company_idn")) document.getElementById("company_idn").value = c.company_idn || "";
    if (document.getElementById("company_type")) document.getElementById("company_type").value = c.company_type || "";
    if (document.getElementById("company_name")) document.getElementById("company_name").value = c.company_name || "";
    if (document.getElementById("edo_type")) document.getElementById("edo_type").value = c.edo_type || "ЭДО-ЛАЙТ";
    if (document.getElementById("edo_id")) document.getElementById("edo_id").value = c.edo_id || "";

    const mt = (order?.mark_type) || (defaults.mark_type) || "";
    if (document.getElementById("mark_type")) document.getElementById("mark_type").value = mt;
    if (document.getElementById("mark_type_hidden")) document.getElementById("mark_type_hidden").value = mt;
  });

  document.getElementById("o-b-cart-settings-save")?.addEventListener("click", () => {
    const company = oBReadCompanyFromSettingsModal();
    const mark_type = oBReadMarkTypeFromSettingsModal();

    const res = oBCartApplyOrderSettings({ company, mark_type });
    if (res?.error) {
      make_cart_message(res.error, "error");
      return;
    }

    oBCartRender();
    oBCartUpdateBadge();

    make_cart_message("Настройки заказа сохранены", "success");

    // закрыть модалку настроек
    const modalEl = document.getElementById("o-b-cart-settings-modal");
    bootstrap.Modal.getInstance(modalEl)?.hide();

    // ✅ закрыть offcanvas корзины
    // const offcanvasEl = document.getElementById("o-b-cart-offcanvas");
    // if (offcanvasEl && window.bootstrap?.Offcanvas) {
    //   const oc = bootstrap.Offcanvas.getInstance(offcanvasEl);
    //   oc?.hide();
    // }
  });

  document.getElementById("o-b-cart-clear")?.addEventListener("click", oBCartClearAllLocal);

  // submit to backend (URL + csrf возьмём из data-атрибутов кнопки)
  document.getElementById("o-b-cart-checkout")?.addEventListener("click", () => {
    const btn = document.getElementById("o-b-cart-checkout");
    const postUrl = btn?.dataset?.postUrl || "";
    const csrf = btn?.dataset?.csrf || "";
    if (!postUrl) {
      make_message("Не задан URL отправки корзины", "error");
      return;
    }
    oBCartSubmitToBackend(postUrl, csrf);
  });

   // add from card_view table (sizes)
  document.addEventListener("click", (e) => {
    const btn = e.target.closest(".pc-apply-qty-btn");
    if (!btn) return;

    const row = btn.closest("tr");
    const qtyInput = row?.querySelector("input.pc-size-qty");
    if (!qtyInput) return;

    const nextQty = Math.max(0, parseInt(qtyInput.value, 10) || 0);

    oBCartUpsertFromModalQty({
      card_id: Number(btn.dataset.cardId),
      category: (btn.dataset.category || "").trim(),
      subcategory: (btn.dataset.subcategory || "").trim(),
      article: (btn.dataset.article || "").trim(),
      trademark: (btn.dataset.trademark || "").trim(),
      color: (btn.dataset.color || "").trim(),
      size: (qtyInput.dataset.size || "").trim(),
      size_type: (qtyInput.dataset.sizeType || "").trim(),
      unit: (qtyInput.dataset.unit || "").trim(),
      qty: nextQty,
    });

    // цвет галки: 0 => yellow, >0 => green
    pcSetApplyBtnState(btn, nextQty);
  });



  // parfum add
  document.addEventListener("click", (e) => {
    const btn = e.target.closest("#pc-parfum-add");
    if (!btn) return;

    const qtyEl = document.getElementById("pc-parfum-qty");
    if (!qtyEl) return;

    const nextQty = Math.max(0, parseInt(qtyEl.value, 10) || 0);


    oBCartUpsertFromModalQty({
      card_id: parseInt(btn.dataset.cardId, 10),
      category: (btn.dataset.category || "").trim(),
      subcategory: (btn.dataset.subcategory || "").trim(),
      article: (btn.dataset.article || "").trim(),
      trademark: (btn.dataset.trademark || "").trim(),
      size: "", size_type: "", unit: "",
      qty: nextQty,
    });

    pcSetApplyBtnState(btn, nextQty);
  });



  document.addEventListener("input", (e) => {
    const inp = e.target.closest("input.pc-size-qty");
    if (inp) {
      const row = inp.closest("tr");
      const btn = row?.querySelector(".pc-apply-qty-btn");
      // при ручном вводе считаем "не применено" → warning
      pcSetApplyBtnState(btn, 0);
      return;
    }

    if (e.target && e.target.id === "pc-parfum-qty") {
      const btn = document.getElementById("pc-parfum-add");
      pcSetApplyBtnState(btn, 0);
    }
  });

  const cardModalEl = document.getElementById("pcCardViewModal");
  if (cardModalEl) {
    cardModalEl.addEventListener("shown.bs.modal", () => {
      oBCartSyncOpenCardModalInputsFromCart();
      oBCartSyncParfumQtyFromCart();
      pcSyncApplyButtonsFromInputs();           // парфюм
    });
  }

});
