function pcInitServiceLifeDatepickers() {
  if (!window.jQuery || !jQuery.fn.datepicker) return;

  const today = new Date();
  const minDateFrom = new Date(2023, 0, 1);
  const maxDateFrom = new Date(today);
  maxDateFrom.setDate(maxDateFrom.getDate() + 1);
  const minDateTo = new Date(today);
  minDateTo.setMonth(minDateTo.getMonth() + 1);

  jQuery("#sl_date_from").datepicker({
    dateFormat: "dd.mm.yy",
    changeMonth: true,
    changeYear: true,
    yearRange: "2023:2100",
    minDate: minDateFrom,
    maxDate: maxDateFrom
  });

  jQuery("#sl_date_to").datepicker({
    dateFormat: "dd.mm.yy",
    changeMonth: true,
    changeYear: true,
    yearRange: "2023:2100",
    minDate: minDateTo
  });
}

function toys_parse_ru_date(value) {
  const match = String(value || "").trim().match(/^(\d{2})\.(\d{2})\.(\d{4})$/);
  if (!match) return null;
  const day = Number(match[1]);
  const month = Number(match[2]) - 1;
  const year = Number(match[3]);
  const date = new Date(year, month, day, 12, 0, 0, 0);
  return date.getFullYear() === year && date.getMonth() === month && date.getDate() === day ? date : null;
}

function toys_min_date_to() {
  const date = new Date();
  date.setHours(12, 0, 0, 0);
  date.setMonth(date.getMonth() + 1);
  return date;
}

function toys_max_date_from() {
  const date = new Date();
  date.setHours(12, 0, 0, 0);
  date.setDate(date.getDate() + 1);
  return date;
}

function toys_check_service_life_period() {
  const dateFromEl = document.getElementById("sl_date_from");
  const dateToEl = document.getElementById("sl_date_to");
  if (!dateFromEl || !dateToEl) return true;

  const dateFrom = toys_parse_ru_date(dateFromEl.value);
  const dateTo = toys_parse_ru_date(dateToEl.value);
  const minDateTo = toys_min_date_to();
  const maxDateFrom = toys_max_date_from();
  dateFromEl.classList.remove("is-invalid");
  dateToEl.classList.remove("is-invalid");

  if (!dateFrom || dateFrom > maxDateFrom) dateFromEl.classList.add("is-invalid");
  if (!dateTo || dateTo < minDateTo || (dateFrom && dateTo < dateFrom)) dateToEl.classList.add("is-invalid");
  return Boolean(dateFrom && dateFrom <= maxDateFrom && dateTo && dateTo >= minDateTo && dateTo >= dateFrom);
}

function toysEscapeHtml(value) {
  return String(value || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function toys_clear_tnved_feedback() {
  const tnvedEl = document.getElementById("tnved_code");
  const suppressorEl = document.getElementById("tnved_co_supressor");
  const validEl = document.getElementById("tnved_valid_feedback");
  const invalidEl = document.getElementById("tnved_nv_feedback");
  if (tnvedEl) tnvedEl.classList.remove("is-valid", "is-invalid");
  if (suppressorEl) suppressorEl.textContent = "";
  if (validEl) validEl.textContent = "";
  if (invalidEl) invalidEl.textContent = "";
}

function toysGetProductType() {
  const typeEl = document.getElementById("type");
  return typeEl ? String(typeEl.value || "").trim() : "";
}

function toysGetAllowedTnvedCodesForType(productType) {
  const allAllowed = Array.isArray(window.TOYS_ALLOWED_TNVED_CODES)
    ? window.TOYS_ALLOWED_TNVED_CODES.map(code => String(code || "").trim()).filter(Boolean)
    : [];
  const mapping = window.TOYS_ALLOWED_TNVED_CODES_BY_PRODUCT_TYPE || {};
  const mapped = Array.isArray(mapping[productType])
    ? mapping[productType].map(code => String(code || "").trim()).filter(Boolean)
    : [];
  return mapped.length ? mapped : allAllowed;
}

function toysGetSelectedTnvedGroupCodes() {
  const groupEl = document.getElementById("tnved_group");
  const groups = Array.isArray(window.TOYS_TNVED_GROUP_CHOICES) ? window.TOYS_TNVED_GROUP_CHOICES : [];
  const selectedGroup = groupEl ? String(groupEl.value || "").trim() : "";
  if (!selectedGroup || !groups.length) return null;
  const group = groups.find(item => String(item[0] || "").trim() === selectedGroup);
  return group && Array.isArray(group[2]) ? group[2].map(code => String(code || "").trim()).filter(Boolean) : [];
}

function toysGetAllowedTnvedCodes() {
  const allowedForType = toysGetAllowedTnvedCodesForType(toysGetProductType());
  const groupCodes = toysGetSelectedTnvedGroupCodes();
  return groupCodes === null ? allowedForType : allowedForType.filter(code => groupCodes.includes(code));
}

function toysUpdateCategoryCodeByTnved() {
  const tnvedEl = document.getElementById("tnved_code");
  const categoryCodeEl = document.getElementById("category_code");
  const categoryCodeValueEl = document.getElementById("toys_category_code_value");
  const tnved = String(tnvedEl?.value || "").trim();
  const categoryCode = (tnved && (window.TOYS_CATEGORY_CODE_BY_TNVED || {})[tnved]) || window.TOYS_CATEGORY_CODE || "";
  if (categoryCodeEl) categoryCodeEl.value = categoryCode;
  if (categoryCodeValueEl) categoryCodeValueEl.textContent = categoryCode;
}

function handleToysProductTypeChange() {
  const tnvedEl = document.getElementById("tnved_code");
  if (tnvedEl) tnvedEl.value = "";
  toys_clear_tnved_feedback();
  toysClearOkpd2();
  toysUpdateCategoryCodeByTnved();
  updateToysFullName();
}

function handleToysTnvedGroupChange() {
  const tnvedEl = document.getElementById("tnved_code");
  if (tnvedEl) tnvedEl.value = "";
  toys_clear_tnved_feedback();
  toysClearOkpd2();
  toysUpdateCategoryCodeByTnved();
}

function toys_check_tnved() {
  const tnvedEl = document.getElementById("tnved_code");
  const groupEl = document.getElementById("tnved_group");
  const invalidEl = document.getElementById("tnved_nv_feedback");
  const validEl = document.getElementById("tnved_valid_feedback");
  const allowed = toysGetAllowedTnvedCodes();
  if (!tnvedEl) return true;

  const code = String(tnvedEl.value || "").trim();
  toys_clear_tnved_feedback();
  if (groupEl && !String(groupEl.value || "").trim()) {
    tnvedEl.classList.add("is-invalid");
    if (invalidEl) invalidEl.textContent = "Сначала выберите группу ТН ВЭД.";
    return false;
  }
  if (!code || !allowed.includes(code)) {
    tnvedEl.classList.add("is-invalid");
    if (invalidEl) invalidEl.textContent = code ? "Код ТН ВЭД не подходит для выбранных параметров." : "Выберите ТН ВЭД из списка.";
    return false;
  }
  tnvedEl.classList.add("is-valid");
  if (validEl) validEl.textContent = "ТН ВЭД выбран.";
  return true;
}

function get_toys_tnveds() {
  const insertEl = document.getElementById("manual_tnved_insert");
  const groupEl = document.getElementById("tnved_group");
  if (groupEl && !String(groupEl.value || "").trim()) {
    show_form_errors(["Сначала выберите группу ТН ВЭД."]);
    window.jQuery?.("#form_errorModal").modal("show");
    return;
  }
  const allChoices = Array.isArray(window.TOYS_ALLOWED_TNVED_CHOICES) ? window.TOYS_ALLOWED_TNVED_CHOICES : [];
  const allowed = toysGetAllowedTnvedCodes();
  const choices = allChoices.filter(tnved => allowed.includes(String(tnved[0] || "").trim()));
  if (!insertEl || !choices.length) {
    show_form_errors(["Для выбранного вида товара нет доступного ТН ВЭД."]);
    window.jQuery?.("#form_errorModal").modal("show");
    return;
  }
  insertEl.innerHTML = `<div class="container-fluid"><div id="accordionBlockies">${choices.map((tnved, index) => `
    <div class="card my-1" title="Нажмите чтобы раскрыть блок" data-bs-toggle="collapse" style="cursor: pointer"
         data-bs-target="#collapse${index + 1}" aria-expanded="true" aria-controls="collapse${index + 1}">
      <div class="card-header" style="background-color:#f8f5f5" id="heading${index + 1}">
        <h6 class="mb-0"><b>${toysEscapeHtml(tnved[0])}</b>: ${toysEscapeHtml(String(tnved[1] || "").slice(0, 50))} ...</h6>
      </div>
      <div id="collapse${index + 1}" class="collapse ${index === 0 ? "show" : ""}" aria-labelledby="heading${index + 1}">
        <div class="card-body">${toysEscapeHtml(tnved[1])}<div class="mt-3">
          <button type="button" onclick="selectToysTnved('${toysEscapeHtml(tnved[0])}')" data-dismiss="modal" class="btn btn-sm btn-primary">Выбрать</button>
        </div></div>
      </div>
    </div>`).join("")}</div></div>`;
  window.jQuery?.("#manualTnvedModal").modal("show");
}

function selectToysTnved(code) {
  const tnvedEl = document.getElementById("tnved_code");
  if (!tnvedEl) return;
  const previousCode = String(tnvedEl.value || "").trim();
  tnvedEl.value = String(code || "").trim();
  if (previousCode !== tnvedEl.value) toysClearOkpd2();
  toysUpdateCategoryCodeByTnved();
  toys_check_tnved();
  clear_manual_tnved();
  window.jQuery?.("#manualTnvedModal").modal("hide");
}

function clear_manual_tnved() {
  const insertEl = document.getElementById("manual_tnved_insert");
  if (insertEl) insertEl.innerHTML = "";
}

function toysGetOkpd2Choices(tnved) {
  const choicesByTnved = window.TOYS_OKPD2_CHOICES_BY_TNVED || {};
  return Array.isArray(choicesByTnved[tnved]) ? choicesByTnved[tnved] : [];
}

function toysFindOkpd2Choice(code, tnved) {
  const normalizedCode = String(code || "").trim();
  return toysGetOkpd2Choices(tnved).find(choice => String(choice[0] || "").trim() === normalizedCode);
}

function toysClearOkpd2() {
  const okpd2El = document.getElementById("okpd2_code");
  const okpd2NameEl = document.getElementById("okpd2_name");
  const okpd2DescriptionEl = document.getElementById("okpd2_description");
  if (okpd2El) {
    okpd2El.value = "";
    okpd2El.classList.remove("is-valid", "is-invalid");
  }
  if (okpd2NameEl) okpd2NameEl.value = "";
  if (okpd2DescriptionEl) okpd2DescriptionEl.textContent = "";
}

function get_toys_okpd2s() {
  const tnvedEl = document.getElementById("tnved_code");
  const tnved = String(tnvedEl?.value || "").trim();
  if (!tnved) {
    show_form_errors(["Сначала выберите ТН ВЭД."]);
    window.jQuery?.("#form_errorModal").modal("show");
    return;
  }
  const choices = toysGetOkpd2Choices(tnved);
  if (!choices.length) {
    show_form_errors(["Для выбранного ТН ВЭД нет разрешенного ОКПД2."]);
    window.jQuery?.("#form_errorModal").modal("show");
    return;
  }
  const container = document.getElementById("modals-container");
  if (!container) return;
  const cardsHtml = choices.map((choice, index) => `
    <div class="card my-1" title="Нажмите чтобы раскрыть блок" data-bs-toggle="collapse" style="cursor: pointer"
         data-bs-target="#toysOkpd2Collapse${index + 1}" aria-expanded="true" aria-controls="toysOkpd2Collapse${index + 1}">
      <div class="card-header" style="background-color:#f8f5f5" id="toysOkpd2Heading${index + 1}">
        <h6 class="mb-0"><b>${toysEscapeHtml(choice[0])}</b>: ${toysEscapeHtml(String(choice[1] || "").slice(0, 80))} ...</h6>
      </div>
      <div id="toysOkpd2Collapse${index + 1}" class="collapse ${index === 0 ? "show" : ""}" aria-labelledby="toysOkpd2Heading${index + 1}">
        <div class="card-body">${toysEscapeHtml(choice[1])}<div class="mt-3">
          <button type="button" class="btn btn-sm btn-primary toys-okpd2-select" data-code="${toysEscapeHtml(choice[0])}" data-name="${toysEscapeHtml(choice[1])}">Выбрать</button>
        </div></div>
      </div>
    </div>`).join("");
  container.innerHTML = `
    <div class="modal fade" id="toysOkpd2Modal" tabindex="-1" data-bs-backdrop="static" role="dialog" aria-hidden="true">
      <div class="modal-dialog modal-lg modal-dialog-scrollable" role="document">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">Выберите ОКПД2</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
          </div>
          <div class="modal-body"><div class="mb-3 small text-muted">ТН ВЭД: ${toysEscapeHtml(tnved)}.</div>${cardsHtml}</div>
          <div class="modal-footer"><button type="button" class="btn btn-accent" data-bs-dismiss="modal">Закрыть</button></div>
        </div>
      </div>
    </div>`;
  document.querySelectorAll(".toys-okpd2-select").forEach(button => {
    button.addEventListener("click", () => selectToysOkpd2(button.dataset.code || "", button.dataset.name || ""));
  });
  window.jQuery?.("#toysOkpd2Modal").modal("show");
}

function selectToysOkpd2(code, name) {
  const okpd2El = document.getElementById("okpd2_code");
  const okpd2NameEl = document.getElementById("okpd2_name");
  const okpd2DescriptionEl = document.getElementById("okpd2_description");
  if (!okpd2El || !okpd2NameEl) return;
  okpd2El.value = String(code || "").trim();
  okpd2NameEl.value = String(name || "").trim();
  if (okpd2DescriptionEl) okpd2DescriptionEl.textContent = okpd2NameEl.value;
  toys_check_okpd2();
  window.jQuery?.("#toysOkpd2Modal").modal("hide");
}

function toys_check_okpd2() {
  const tnvedEl = document.getElementById("tnved_code");
  const okpd2El = document.getElementById("okpd2_code");
  const okpd2NameEl = document.getElementById("okpd2_name");
  if (!okpd2El) return true;
  const tnved = String(tnvedEl?.value || "").trim();
  const code = String(okpd2El.value || "").trim();
  const hiddenName = String(okpd2NameEl?.value || "").trim();
  const choice = toysFindOkpd2Choice(code, tnved);
  const valid = Boolean(choice) && String(choice[1] || "").trim() === hiddenName;
  okpd2El.classList.toggle("is-invalid", !valid);
  okpd2El.classList.toggle("is-valid", valid);
  return valid;
}

function updateToysFullName() {
  const trademarkEl = document.getElementById("trademark");
  const typeEl = document.getElementById("type");
  const extraEl = document.getElementById("full_name_extra");
  const targetEl = document.getElementById("generated_full_name");
  if (!targetEl) return;
  const trademarkRaw = String(trademarkEl?.value || "").trim();
  const trademark = trademarkRaw.toUpperCase() === "БЕЗ ТОВАРНОГО ЗНАКА" ? "" : trademarkRaw;
  const fullName = [String(typeEl?.value || "").trim(), trademark, String(extraEl?.value || "").trim()].filter(Boolean).join(" ");
  targetEl.textContent = fullName || "Будет сформировано автоматически";
  targetEl.title = fullName;
}

function toggleToysFullNameExtra(switchEl) {
  const blockEl = document.getElementById("full_name_extra_block");
  const inputEl = document.getElementById("full_name_extra");
  if (!blockEl || !inputEl || !switchEl) return;
  const enabled = Boolean(switchEl.checked);
  switchEl.classList.toggle("bg-warning", enabled);
  blockEl.style.display = enabled ? "" : "none";
  if (!enabled) inputEl.value = "";
  updateToysFullName();
}

function toys_validate_full_name_requirements() {
  const trademarkEl = document.getElementById("trademark");
  const extraEl = document.getElementById("full_name_extra");
  const typeEl = document.getElementById("type");
  const trademark = String(trademarkEl?.value || "").trim().toUpperCase();
  const extra = String(extraEl?.value || "").trim();
  const type = String(typeEl?.value || "").trim();
  const invalid = Boolean(type) && (!trademark || trademark === "БЕЗ ТОВАРНОГО ЗНАКА") && !extra;
  if (extraEl) {
    extraEl.classList.toggle("is-invalid", invalid);
    extraEl.setCustomValidity(invalid ? "Заполните дополнение к полному наименованию." : "");
  }
  return !invalid;
}

const TOYS_NO_MODEL_ARTICLE_VALUE = "отсутствует";

function toysIsNoModelArticleValue(value) {
  return String(value || "").trim().toUpperCase() === TOYS_NO_MODEL_ARTICLE_VALUE.toUpperCase();
}

function toggleToysModelArticleField(switchEl) {
  const inputEl = document.getElementById("model_article");
  const displayEl = document.getElementById("model_article_display");
  if (!inputEl || !displayEl || !switchEl) return;
  const emptyValue = inputEl.dataset.emptyValue || TOYS_NO_MODEL_ARTICLE_VALUE;
  const enabled = Boolean(switchEl.checked);
  switchEl.classList.toggle("bg-warning", enabled);
  switchEl.classList.toggle("border-warning", enabled);
  if (enabled) {
    inputEl.value = emptyValue;
    inputEl.style.display = "none";
    displayEl.style.display = "block";
    displayEl.value = "";
    inputEl.classList.remove("is-invalid");
  } else {
    if (toysIsNoModelArticleValue(inputEl.value)) inputEl.value = "";
    inputEl.style.display = "block";
    displayEl.style.display = "none";
  }
  inputEl.dispatchEvent(new Event("input", {bubbles: true}));
  inputEl.dispatchEvent(new Event("change", {bubbles: true}));
}

function toysPrepareModelArticleBeforeSubmit() {
  const inputEl = document.getElementById("model_article");
  const switchEl = document.getElementById("noModelArticleSwitch");
  if (!inputEl) return;
  if ((switchEl && switchEl.checked) || !String(inputEl.value || "").trim()) {
    inputEl.value = inputEl.dataset.emptyValue || TOYS_NO_MODEL_ARTICLE_VALUE;
  }
}

const TOYS_KEYBOARD_LAYOUT_RU = {
  q: "й", w: "ц", e: "у", r: "к", t: "е", y: "н", u: "г", i: "ш", o: "щ", p: "з",
  "[": "х", "]": "ъ", a: "ф", s: "ы", d: "в", f: "а", g: "п", h: "р", j: "о",
  k: "л", l: "д", ";": "ж", "'": "э", z: "я", x: "ч", c: "с", v: "м",
  b: "и", n: "т", m: "ь", "`": "ё"
};

function normalizeToysContentInput(el) {
  if (!el || typeof el.value !== "string") return;
  let value = el.value.split("").map(char => {
    const lower = char.toLowerCase();
    const mapped = TOYS_KEYBOARD_LAYOUT_RU[lower];
    return mapped ? (char === lower ? mapped : mapped.toUpperCase()) : char;
  }).join("");
  value = value.replace(/[^А-Яа-яЁё0-9\s,.;:!?()%+\-/"'№@#&*_=\\|[\]{}<>«»\n\r]/g, "");
  el.value = value;
}

document.addEventListener("DOMContentLoaded", () => {
  pcInitServiceLifeDatepickers();
  const fullNameSwitch = document.getElementById("fullNameExtraSwitch");
  const noModelArticleSwitch = document.getElementById("noModelArticleSwitch");
  if (fullNameSwitch) toggleToysFullNameExtra(fullNameSwitch);
  if (noModelArticleSwitch) {
    const modelArticleEl = document.getElementById("model_article");
    noModelArticleSwitch.checked = noModelArticleSwitch.checked || toysIsNoModelArticleValue(modelArticleEl ? modelArticleEl.value : "");
    toggleToysModelArticleField(noModelArticleSwitch);
  }
  toysUpdateCategoryCodeByTnved();
  toys_check_tnved();
  toys_check_okpd2();
  updateToysFullName();
});
