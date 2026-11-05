// Вес одной штуки в граммах для карточек товара (экосбор).
// В форме карточки кнопка «Указать вес» открывает модалку с размерами из серого блока.
// В модалке просмотра карточки клиент правит только вес, без повторной модерации.

const PC_WEIGHT_MAX = 100000;
const PC_WEIGHT_SINGLE_CATEGORIES = ["parfum", "cosmetics", "toys"];
const PC_WEIGHT_FORMAT_ERROR = `Вес: нужно целое число граммов от 1 до ${PC_WEIGHT_MAX}`;
// вес по подписи размера: скрипты категорий пересобирают строки (носки каждый раз целиком), и вес надо вернуть
const pcWeightByRow = new Map();
let pcWeightModalItems = [];
let pcWeightBulkEdited = false;

function pcWeightValid(value) {
    const s = String(value ?? "").trim();
    return /^[1-9]\d{0,5}$/.test(s) && Number(s) <= PC_WEIGHT_MAX;
}

function pcWeightMarkInputs(inputs) {
    let ok = true;
    inputs.forEach(input => {
        const valid = pcWeightValid(input.value);
        input.classList.toggle("is-invalid", !valid);
        input.setAttribute("aria-invalid", valid ? "false" : "true");
        ok = ok && valid;
    });
    return ok;
}

function pcWeightCategory() {
    return document.getElementById("pc-config")?.dataset.currentCategory || "";
}

function pcWeightIsKpb() {
    return pcWeightCategory() === "linen" && typeof linenIsKpbMode === "function" && linenIsKpbMode();
}

function pcWeightIsSingle() {
    return PC_WEIGHT_SINGLE_CATEGORIES.includes(pcWeightCategory()) || pcWeightIsKpb();
}

// ---------- форма карточки ----------

function pcWeightRows() {
    return Array.from(document.querySelectorAll("#sizes_quantity .important-card__size:not(.linen-set-item-row)"));
}

function pcWeightRowValue(row, name) {
    return (row.querySelector(`input[name="${name}"]`)?.value || "").trim();
}

function pcWeightRowLabel(row) {
    const sizeX = pcWeightRowValue(row, "sizeX");
    if (sizeX) return `${sizeX}*${pcWeightRowValue(row, "sizeY")} ${pcWeightRowValue(row, "sizeUnit")}`;
    return `${pcWeightRowValue(row, "size")} ${pcWeightRowValue(row, "size_type")}`.trim();
}

// вес хранится в скрытом input name="weight" внутри строки, бэк берёт size[i] и weight[i] парами
function pcWeightRowInput(row) {
    let input = row.querySelector('input[name="weight"]');
    if (!input) {
        input = document.createElement("input");
        input.type = "hidden";
        input.name = "weight";
        row.appendChild(input);
    }
    return input;
}

function pcWeightRenderRow(row) {
    const input = pcWeightRowInput(row);
    const remembered = pcWeightByRow.get(pcWeightRowLabel(row));
    if (!input.getAttribute("value") && remembered) input.setAttribute("value", remembered);

    const value = input.getAttribute("value") || "";
    let info = row.querySelector(".pc-weight-info");
    if (!info) {
        info = document.createElement("span");
        info.className = "pc-weight-info ms-1";
        info.style.fontSize = "10px";
        (row.querySelector(".ms-2") || row).appendChild(info);
    }
    info.textContent = value ? `· ${value} г` : "· вес не указан";
}

function pcWeightSingleInput() {
    return document.getElementById("weight_grams");
}

function pcWeightSingleLabel() {
    return pcWeightIsKpb() ? "Вес 1 комплекта" : "Вес 1 шт.";
}

function pcWeightRenderSingle() {
    const info = document.getElementById("pc-weight-single-info");
    if (!info) return;
    const value = pcWeightSingleInput()?.value || "";
    info.textContent = pcWeightIsSingle() && value ? `${pcWeightSingleLabel()}: ${value} г` : "";
}

function pcWeightRenderAll() {
    pcWeightRows().forEach(pcWeightRenderRow);
    pcWeightRenderSingle();
}

function pcWeightField(labelText, value, index) {
    const wrap = document.createElement("div");
    wrap.className = "d-flex align-items-center gap-2 mb-2";

    const label = document.createElement("label");
    label.className = "flex-grow-1 mb-0";
    label.htmlFor = `pc-weight-input-${index}`;
    label.textContent = labelText;

    const input = document.createElement("input");
    input.id = `pc-weight-input-${index}`;
    input.type = "number";
    input.min = "1";
    input.max = String(PC_WEIGHT_MAX);
    input.step = "1";
    input.className = "form-control pc-weight-input";
    input.style.maxWidth = "140px";
    input.placeholder = "Пример 100";
    input.value = value;

    const unit = document.createElement("span");
    unit.textContent = "г";

    wrap.append(label, input, unit);
    return wrap;
}

function pcWeightOpen() {
    if (pcWeightIsSingle()) {
        pcWeightModalItems = [{ label: pcWeightSingleLabel(), value: pcWeightSingleInput()?.value || "" }];
    } else {
        pcWeightModalItems = pcWeightRows().map(row => ({
            row,
            label: pcWeightRowLabel(row),
            value: pcWeightRowInput(row).getAttribute("value") || "",
        }));
    }
    if (!pcWeightModalItems.length) {
        make_message("Сначала добавьте размеры, потом укажите их вес", "error");
        return;
    }
    const list = document.getElementById("pcWeightModalList");
    list.replaceChildren(...pcWeightModalItems.map((item, i) => pcWeightField(item.label, item.value, i)));
    document.getElementById("pcWeightBulk").classList.toggle("d-none", pcWeightIsSingle() || pcWeightModalItems.length < 2);
    pcWeightBulkEdited = false;
    pcWeightSyncBulk();
    document.getElementById("pcWeightModalError").textContent = "";
    bootstrap.Modal.getOrCreateInstance(document.getElementById("pcWeightModal")).show();
}

function pcWeightSyncBulk() {
    const input = document.getElementById("pcWeightBulkInput");
    if (!pcWeightBulkEdited) {
        const first = Array.from(document.querySelectorAll("#pcWeightModalList .pc-weight-input"))
            .find(rowInput => pcWeightValid(rowInput.value));
        input.value = first?.value || "";
    }
    document.getElementById("pcWeightBulkApply").disabled = !pcWeightValid(input.value);
}

function pcWeightApplyAll() {
    if (pcWeightIsSingle() || pcWeightModalItems.length < 2) return;
    const input = document.getElementById("pcWeightBulkInput");
    if (!pcWeightValid(input.value)) return;
    const inputs = Array.from(document.querySelectorAll("#pcWeightModalList .pc-weight-input"));
    inputs.forEach(rowInput => { rowInput.value = input.value.trim(); });
    pcWeightMarkInputs(inputs);
    document.getElementById("pcWeightModalError").textContent = "";
}

function pcWeightSave() {
    const inputs = Array.from(document.querySelectorAll("#pcWeightModalList .pc-weight-input"));
    const errorEl = document.getElementById("pcWeightModalError");
    if (!pcWeightMarkInputs(inputs)) {
        errorEl.textContent = PC_WEIGHT_FORMAT_ERROR;
        inputs.find(input => input.classList.contains("is-invalid"))?.focus();
        return;
    }
    errorEl.textContent = "";

    if (pcWeightIsSingle()) {
        pcWeightSingleInput().value = inputs[0].value.trim();
    } else {
        pcWeightModalItems.forEach((item, i) => {
            const value = inputs[i].value.trim();
            pcWeightByRow.set(item.label, value);
            pcWeightRowInput(item.row).setAttribute("value", value);
        });
    }
    pcWeightRenderAll();
    bootstrap.Modal.getOrCreateInstance(document.getElementById("pcWeightModal")).hide();
}

// product_card_submit зовёт это до new FormData: в каждой строке размера должен быть input weight,
// иначе бэк не сопоставит size и weight. Возвращает текст ошибки или null.
// При редактировании вес можно не трогать: пустое значение сохранённый вес не меняет.
function pcWeightCheck() {
    if (document.getElementById("pc-config")?.dataset.crmFlag === "1") return null;
    const required = document.getElementById("pc-config")?.dataset.editMode !== "1";
    pcWeightRenderAll();
    const values = pcWeightIsSingle()
        ? [pcWeightSingleInput()?.value || ""]
        : pcWeightRows().map(row => pcWeightRowInput(row).getAttribute("value") || "");

    if (values.some(value => value && !pcWeightValid(value))) return PC_WEIGHT_FORMAT_ERROR;
    if (required && values.some(value => !value)) {
        return pcWeightIsSingle()
            ? `Вес: укажите ${pcWeightSingleLabel().toLowerCase()} кнопкой «Указать вес»`
            : "Вес: укажите вес каждого размера кнопкой «Указать вес»";
    }
    return null;
}

document.addEventListener("DOMContentLoaded", function () {
    const modalEl = document.getElementById("pcWeightModal");
    if (!modalEl) return;

    pcWeightRows().forEach(row => {
        const value = pcWeightRowInput(row).getAttribute("value");
        if (value) pcWeightByRow.set(pcWeightRowLabel(row), value);
    });
    pcWeightRenderAll();

    const sizesBlock = document.getElementById("sizes_quantity");
    if (sizesBlock) new MutationObserver(() => pcWeightRows().forEach(pcWeightRenderRow)).observe(sizesBlock, { childList: true });
    // у белья смена типа переключает КПБ (один вес на комплект) и обычные размеры
    if (window.jQuery) jQuery(document).on("change", "#type", pcWeightRenderAll);

    modalEl.addEventListener("shown.bs.modal", () => modalEl.querySelector(".pc-weight-input")?.focus());
    modalEl.addEventListener("input", e => {
        if (e.target.id === "pcWeightBulkInput") {
            pcWeightBulkEdited = true;
            pcWeightSyncBulk();
        } else if (e.target.classList.contains("pc-weight-input")) {
            pcWeightSyncBulk();
        }
    });
    modalEl.addEventListener("keydown", e => {
        if (e.key === "Enter" && e.target.id === "pcWeightBulkInput") {
            e.preventDefault();
            pcWeightApplyAll();
            return;
        }
        if (e.key === "Enter" && e.target.classList.contains("pc-weight-input")) {
            e.preventDefault();
            pcWeightSave();
        }
    });
});

// ---------- модалка просмотра карточки: правка только веса ----------

function pcWeightUpdateSelectedTotals() {
    const body = document.getElementById("pcCardViewModalBody");
    if (!body) return;
    const format = grams => Number.isSafeInteger(grams) ? `${grams.toLocaleString("ru-RU")} г` : "—";
    let total = 0;
    body.querySelectorAll("input[data-unit-weight]").forEach(input => {
        const qty = input.disabled ? 0 : Math.max(0, parseInt(input.value, 10) || 0);
        const weight = Number(input.dataset.unitWeight) * qty;
        total += weight;
        const rowTotal = input.closest("tr")?.querySelector("[data-pc-row-weight]");
        if (rowTotal) rowTotal.textContent = format(weight);
    });
    body.querySelectorAll("[data-pc-total-weight]").forEach(el => { el.textContent = format(total); });
}

for (const eventName of ["input", "change"]) {
    document.addEventListener(eventName, e => {
        if (e.target.matches("#pcCardViewModalBody input[data-unit-weight]")) pcWeightUpdateSelectedTotals();
    });
}

function pcWeightCsrf() {
    return document.querySelector('meta[name="csrf-token"]')?.content
        || document.getElementById("pc-config")?.dataset.csrf
        || "";
}

// то же, что делают users.js и pc_cart.js после открытия модалки карточки
function pcWeightAfterCardViewRender(body) {
    if (typeof pcInitViewTooltips === "function") pcInitViewTooltips(body);
    if (typeof oBCartSyncOpenCardModalInputsFromCart === "function") oBCartSyncOpenCardModalInputsFromCart();
    if (typeof oBCartSyncSingleUnitQtyFromCart === "function") oBCartSyncSingleUnitQtyFromCart();
    if (typeof pcSyncApplyButtonsFromInputs === "function") pcSyncApplyButtonsFromInputs();
}

async function pcWeightRefreshCardView(block) {
    const body = document.getElementById("pcCardViewModalBody");
    try {
        const response = await fetch(block.dataset.viewUrl, { headers: { "X-Requested-With": "XMLHttpRequest" } });
        const view = response.ok ? await response.json() : {};
        // модалку могли закрыть и открыть другую карточку, пока шёл запрос
        if (!body || !body.contains(block)) return;
        if (view.status !== "success") throw new Error("card view " + response.status);
        body.innerHTML = view.html;
        pcWeightAfterCardViewRender(body);
    } catch (err) {
        console.error("pc weight refresh error:", err);
        const errorEl = block.querySelector(".pc-weight-error");
        if (errorEl) errorEl.textContent = "Вес сохранён. Закройте и откройте карточку заново.";
    }
}

document.addEventListener("click", async function (e) {
    const editBtn = e.target.closest(".pc-weight-edit-btn");
    if (editBtn) {
        const block = editBtn.closest(".pc-weight-block");
        block.querySelectorAll(".pc-weight-view").forEach(el => el.classList.add("d-none"));
        block.querySelectorAll(".pc-weight-edit").forEach(el => el.classList.remove("d-none"));
        block.querySelector("input[data-unit-id]")?.focus();
        return;
    }

    const saveBtn = e.target.closest(".pc-weight-save-btn");
    if (!saveBtn) return;
    const block = saveBtn.closest(".pc-weight-block");
    const errorEl = block.querySelector(".pc-weight-error");
    const inputs = Array.from(block.querySelectorAll("input[data-unit-id]"));
    if (!pcWeightMarkInputs(inputs)) {
        errorEl.textContent = PC_WEIGHT_FORMAT_ERROR;
        inputs.find(input => input.classList.contains("is-invalid"))?.focus();
        return;
    }
    errorEl.textContent = "";

    const weights = {};
    inputs.forEach(input => { weights[input.dataset.unitId] = input.value.trim(); });
    saveBtn.disabled = true;
    try {
        const response = await fetch(block.dataset.weightsUrl, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": pcWeightCsrf(),
                "X-Requested-With": "XMLHttpRequest",
            },
            body: JSON.stringify({ weights }),
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok || data.status !== "success") {
            errorEl.textContent = data.message || "Не удалось сохранить вес";
            return;
        }
    } catch (err) {
        console.error("pc weight save error:", err);
        errorEl.textContent = "Ошибка при сохранении веса";
        return;
    } finally {
        saveBtn.disabled = false;
    }
    // с указанным весом у карточки появляется корзина, поэтому перерисовываем модалку
    await pcWeightRefreshCardView(block);
});
