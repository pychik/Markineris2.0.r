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

function cosmetics_parse_ru_date(value) {
  const match = String(value || "").trim().match(/^(\d{2})\.(\d{2})\.(\d{4})$/);
  if (!match) return null;
  const day = Number(match[1]);
  const month = Number(match[2]) - 1;
  const year = Number(match[3]);
  const date = new Date(year, month, day, 12, 0, 0, 0);
  return date.getFullYear() === year && date.getMonth() === month && date.getDate() === day ? date : null;
}

function cosmetics_max_date_from() {
  const date = new Date();
  date.setHours(12, 0, 0, 0);
  date.setDate(date.getDate() + 1);
  return date;
}

function cosmetics_check_service_life_period() {
  const serviceLifeEl = document.getElementById("service_life");
  const dateFromEl = document.getElementById("sl_date_from");
  const dateToEl = document.getElementById("sl_date_to");
  if (!serviceLifeEl || !dateFromEl || !dateToEl) return true;

  const serviceLife = Number(serviceLifeEl.value);
  const dateFrom = cosmetics_parse_ru_date(dateFromEl.value);
  const dateTo = cosmetics_parse_ru_date(dateToEl.value);
  const maxDateFrom = cosmetics_max_date_from();
  dateFromEl.classList.remove("is-invalid");
  dateToEl.classList.remove("is-invalid");

  if (!Number.isFinite(serviceLife) || serviceLife < 0 || !dateFrom || !dateTo || dateFrom > maxDateFrom) {
    if (!dateFrom || dateFrom > maxDateFrom) dateFromEl.classList.add("is-invalid");
    if (!dateTo) dateToEl.classList.add("is-invalid");
    return false;
  }

  const maxDate = new Date(dateFrom.getTime());
  maxDate.setMonth(maxDate.getMonth() + serviceLife);
  if (dateTo < dateFrom || dateTo > maxDate) {
    dateToEl.classList.add("is-invalid");
    return false;
  }
  return true;
}

function cosmetics_clear_tnved_feedback() {
  const tnvedEl = document.getElementById("tnved_code");
  const suppressorEl = document.getElementById("tnved_co_supressor");
  const validEl = document.getElementById("tnved_valid_feedback");
  const invalidEl = document.getElementById("tnved_nv_feedback");
  if (tnvedEl) tnvedEl.classList.remove("is-valid", "is-invalid");
  if (suppressorEl) suppressorEl.textContent = "";
  if (validEl) validEl.textContent = "";
  if (invalidEl) invalidEl.textContent = "";
}

function getCurrentCosmeticsAllowedTnvedCodes() {
  const typeEl = document.getElementById("type");
  const productType = typeEl ? String(typeEl.value || "").trim() : "";
  if (cosmeticsIsRazorSubcategory()) {
    const replaceableTnvedCode = String(window.COSMETICS_REPLACEABLE_RAZOR_TNVED_CODE || "").trim();
    const replaceableSwitchEl = document.getElementById("replaceable_razor_switch");
    const standardMapping = window.COSMETICS_STANDARD_TNVED_CODES_BY_PRODUCT_TYPE || {};
    const standardCodes = Array.isArray(standardMapping[productType]) ? standardMapping[productType] : null;

    if (replaceableSwitchEl && replaceableSwitchEl.checked && replaceableTnvedCode) {
      return [replaceableTnvedCode];
    }

    if (standardCodes && standardCodes.length) {
      return standardCodes.map(code => String(code || "").trim());
    }

    return (Array.isArray(window.COSMETICS_ALLOWED_TNVED_CODES) ? window.COSMETICS_ALLOWED_TNVED_CODES : [])
      .map(code => String(code || "").trim())
      .filter(code => code !== replaceableTnvedCode);
  }

  const mapping = window.COSMETICS_TNVED_CODES_BY_PRODUCT_TYPE || {};
  const mappedCodes = Array.isArray(mapping[productType]) ? mapping[productType] : null;
  if (mappedCodes && mappedCodes.length) return mappedCodes.map(code => String(code || "").trim());
  return Array.isArray(window.COSMETICS_ALLOWED_TNVED_CODES)
    ? window.COSMETICS_ALLOWED_TNVED_CODES.map(code => String(code || "").trim())
    : [];
}

function getCurrentCosmeticsAllowedTnvedChoices() {
  const allowedCodes = new Set(getCurrentCosmeticsAllowedTnvedCodes());
  const allChoices = Array.isArray(window.COSMETICS_ALLOWED_TNVED_CHOICES) ? window.COSMETICS_ALLOWED_TNVED_CHOICES : [];
  return allChoices.filter(choice => Array.isArray(choice) && allowedCodes.has(String(choice[0] || "").trim()));
}

function cosmetics_check_tnved() {
  const tnvedEl = document.getElementById("tnved_code");
  const invalidEl = document.getElementById("tnved_nv_feedback");
  const validEl = document.getElementById("tnved_valid_feedback");
  if (!tnvedEl) return true;

  const code = String(tnvedEl.value || "").trim();
  const allowed = getCurrentCosmeticsAllowedTnvedCodes();
  cosmetics_clear_tnved_feedback();

  if (!code || !allowed.includes(code)) {
    tnvedEl.classList.add("is-invalid");
    if (invalidEl) invalidEl.textContent = code ? "Код ТН ВЭД не разрешен для этой подкатегории." : "Выберите ТН ВЭД из списка.";
    return false;
  }

  tnvedEl.classList.add("is-valid");
  if (validEl) validEl.textContent = "ТН ВЭД выбран.";
  return true;
}

function cosmeticsResolveCurrentCategoryCode() {
  const tnvedEl = document.getElementById("tnved_code");
  const categoryCodeByTnved = window.COSMETICS_CATEGORY_CODE_BY_TNVED || {};
  const fallbackCode = String(window.COSMETICS_CATEGORY_CODE || "").trim();
  const tnvedCode = tnvedEl ? String(tnvedEl.value || "").trim() : "";
  const resolved = tnvedCode ? String(categoryCodeByTnved[tnvedCode] || "").trim() : "";
  return resolved || fallbackCode;
}

function cosmeticsUpdateCategoryCode() {
  const visibleEl = document.getElementById("cosmetics_category_code_value");
  if (visibleEl) visibleEl.textContent = cosmeticsResolveCurrentCategoryCode();
}

function syncCosmeticsTnvedByProductType(force = false) {
  const tnvedEl = document.getElementById("tnved_code");
  if (!tnvedEl) return;
  const allowedCodes = getCurrentCosmeticsAllowedTnvedCodes();
  const currentCode = String(tnvedEl.value || "").trim();
  const nextCode = allowedCodes.length === 1 ? String(allowedCodes[0] || "").trim() : "";
  if (force || !currentCode || !allowedCodes.includes(currentCode)) tnvedEl.value = nextCode;
  pcCosmeticsSyncConditionalFields();
}

function cosmeticsResolveContentLabel() {
  const typeEl = document.getElementById("type");
  const productType = typeEl ? String(typeEl.value || "").trim() : "";
  const byProductType = window.COSMETICS_CONTENT_LABEL_BY_PRODUCT_TYPE || {};
  if (productType && byProductType[productType]) return String(byProductType[productType]).trim();
  const tnvedEl = document.getElementById("tnved_code");
  const tnvedCode = tnvedEl ? String(tnvedEl.value || "").trim() : "";
  const byTnved = window.COSMETICS_CONTENT_LABEL_BY_TNVED || {};
  if (tnvedCode && byTnved[tnvedCode]) return String(byTnved[tnvedCode]).trim();
  return String(window.COSMETICS_DEFAULT_CONTENT_LABEL || "Состав товара").trim();
}

function cosmeticsShouldShowContentType() {
  if (window.COSMETICS_CONTENT_VALUE_ENABLED === false || window.COSMETICS_CONTENT_TYPE_ENABLED === false) return false;
  const typeEl = document.getElementById("type");
  const productType = typeEl ? String(typeEl.value || "").trim() : "";
  const productTypeTriggers = Array.isArray(window.COSMETICS_CONTENT_TYPE_TRIGGER_PRODUCT_TYPES) ? window.COSMETICS_CONTENT_TYPE_TRIGGER_PRODUCT_TYPES : [];
  if (productType && productTypeTriggers.length) return productTypeTriggers.includes(productType);
  const tnvedTriggers = Array.isArray(window.COSMETICS_CONTENT_TYPE_TRIGGER_TNVEDS) ? window.COSMETICS_CONTENT_TYPE_TRIGGER_TNVEDS : [];
  if (!tnvedTriggers.length) return true;
  const tnvedEl = document.getElementById("tnved_code");
  return tnvedTriggers.includes(String(tnvedEl?.value || "").trim());
}

function cosmeticsToggleContentTypeBlock() {
  const rowEl = document.getElementById("content_row");
  const contentBlockEl = document.getElementById("content_block");
  const blockEl = document.getElementById("content_type_block");
  const selectEl = document.getElementById("content_type");
  const contentEl = document.getElementById("content");
  const labelEl = document.getElementById("content_label_text_value");
  if (labelEl) labelEl.textContent = cosmeticsResolveContentLabel();
  if (window.COSMETICS_CONTENT_VALUE_ENABLED === false) {
    if (rowEl) rowEl.style.display = "none";
    if (contentBlockEl) contentBlockEl.style.display = "none";
    if (contentEl) {
      contentEl.required = false;
      contentEl.value = "";
    }
    if (selectEl) {
      selectEl.required = false;
      selectEl.value = "";
    }
    return;
  }
  if (!blockEl || !selectEl) return;
  const shouldShow = cosmeticsShouldShowContentType();
  blockEl.style.display = shouldShow ? "" : "none";
  selectEl.required = shouldShow;
  if (!shouldShow) {
    selectEl.value = "";
    window.jQuery?.(selectEl).trigger("change").trigger("change.select2");
  }
}

function cosmeticsToggleForChildrenBlock() {
  const blockEl = document.getElementById("for_children_block");
  const selectEl = document.getElementById("for_children");
  if (!blockEl || !selectEl) return;
  const shouldShow = window.COSMETICS_FOR_CHILDREN_ENABLED !== false;
  blockEl.style.display = shouldShow ? "" : "none";
  selectEl.required = shouldShow;
  if (!shouldShow) {
    selectEl.value = "";
    window.jQuery?.(selectEl).trigger("change").trigger("change.select2");
  }
}

function cosmeticsShouldShowComplectation() {
  if (cosmeticsIsRazorSubcategory()) {
    const switchEl = document.getElementById("replaceable_razor_switch");
    return Boolean(switchEl && switchEl.checked);
  }

  const typeEl = document.getElementById("type");
  const tnvedEl = document.getElementById("tnved_code");
  const triggerTypes = Array.isArray(window.COSMETICS_COMPLECTATION_TRIGGER_TYPES) ? window.COSMETICS_COMPLECTATION_TRIGGER_TYPES : [];
  const triggerTnveds = Array.isArray(window.COSMETICS_COMPLECTATION_TRIGGER_TNVEDS) ? window.COSMETICS_COMPLECTATION_TRIGGER_TNVEDS : [];
  return triggerTypes.includes(String(typeEl?.value || "").trim()) || triggerTnveds.includes(String(tnvedEl?.value || "").trim());
}

function cosmeticsToggleComplectationBlock() {
  const blockEl = document.getElementById("complectation_block");
  const inputEl = document.getElementById("complectation");
  if (!blockEl || !inputEl) return;
  const shouldShow = cosmeticsShouldShowComplectation();
  blockEl.style.display = shouldShow ? "" : "none";
  inputEl.required = shouldShow;
  if (!shouldShow) inputEl.value = "";
}

function cosmeticsIsRazorSubcategory() {
  return window.COSMETICS_IS_RAZOR_SUBCATEGORY === true || Boolean(document.getElementById("replaceable_razor_switch"));
}

function cosmeticsTriggerSelectChange(selectEl) {
  if (!selectEl || typeof window.jQuery === "undefined") return;
  const $selectEl = window.jQuery(selectEl);
  $selectEl.trigger("change");
  $selectEl.trigger("change.select2");
}

function cosmeticsSetProductTypeOptions(allowedTypes) {
  const typeEl = document.getElementById("type");
  if (!typeEl || !Array.isArray(allowedTypes) || !allowedTypes.length) return;

  const currentValue = String(typeEl.value || "").trim();
  typeEl.innerHTML = "";

  const placeholderOpt = document.createElement("option");
  placeholderOpt.value = "";
  placeholderOpt.textContent = "Выберите из списка..";
  placeholderOpt.disabled = true;
  placeholderOpt.selected = true;
  typeEl.appendChild(placeholderOpt);

  allowedTypes.forEach(item => {
    const option = document.createElement("option");
    option.value = item;
    option.textContent = item;
    if (currentValue === item) {
      option.selected = true;
      placeholderOpt.selected = false;
    }
    typeEl.appendChild(option);
  });

  if (!allowedTypes.includes(currentValue)) {
    typeEl.value = "";
  }

  cosmeticsTriggerSelectChange(typeEl);
}

function cosmeticsToggleRazorExtraFields() {
  if (!cosmeticsIsRazorSubcategory()) return;

  const switchEl = document.getElementById("replaceable_razor_switch");
  const extraRowEl = document.getElementById("razor_extra_fields_row");
  const bladeCountBlockEl = document.getElementById("blade_count_block");
  const bladeCountEl = document.getElementById("blade_count");
  const shouldShow = Boolean(switchEl && switchEl.checked);

  if (extraRowEl) {
    extraRowEl.style.display = shouldShow ? "" : "none";
  }

  if (bladeCountBlockEl) {
    bladeCountBlockEl.style.display = shouldShow ? "" : "none";
  }

  if (bladeCountEl) {
    bladeCountEl.required = shouldShow;
    if (shouldShow && !String(bladeCountEl.value || "").trim()) {
      bladeCountEl.value = "1";
    }
    if (!shouldShow) {
      bladeCountEl.value = "";
      bladeCountEl.classList.remove("is-valid", "is-invalid");
      bladeCountEl.setCustomValidity("");
    }
  }

  cosmeticsToggleComplectationBlock();
}

function cosmeticsApplyRazorSwitchState(forceTnved = false) {
  if (!cosmeticsIsRazorSubcategory()) return;

  const switchEl = document.getElementById("replaceable_razor_switch");
  const tnvedEl = document.getElementById("tnved_code");
  const replaceableTnvedCode = String(window.COSMETICS_REPLACEABLE_RAZOR_TNVED_CODE || "").trim();
  const isReplaceable = Boolean(switchEl && switchEl.checked);
  const allowedTypes = isReplaceable
    ? window.COSMETICS_REPLACEABLE_RAZOR_PRODUCT_TYPES
    : window.COSMETICS_STANDARD_RAZOR_PRODUCT_TYPES;

  if (switchEl) {
    switchEl.classList.toggle("bg-warning", isReplaceable);
  }

  cosmeticsSetProductTypeOptions(allowedTypes);

  if (tnvedEl && replaceableTnvedCode) {
    const currentCode = String(tnvedEl.value || "").trim();
    if (isReplaceable && (forceTnved || !currentCode || currentCode !== replaceableTnvedCode)) {
      tnvedEl.value = replaceableTnvedCode;
    }
    if (!isReplaceable && currentCode === replaceableTnvedCode) {
      tnvedEl.value = "";
    }
  }

  syncCosmeticsTnvedByProductType(forceTnved);
  cosmeticsUpdateCategoryCode();
  cosmeticsToggleRazorExtraFields();
  cosmetics_validate_razor_switch();
}

function cosmetics_validate_razor_switch() {
  if (!cosmeticsIsRazorSubcategory()) return true;

  const switchEl = document.getElementById("replaceable_razor_switch");
  const tnvedEl = document.getElementById("tnved_code");
  const bladeCountEl = document.getElementById("blade_count");
  const complectationEl = document.getElementById("complectation");
  const replaceableTnvedCode = String(window.COSMETICS_REPLACEABLE_RAZOR_TNVED_CODE || "").trim();
  const isReplaceable = Boolean(switchEl && switchEl.checked);
  const tnvedCode = tnvedEl ? String(tnvedEl.value || "").trim() : "";
  const bladeCount = bladeCountEl ? Number(bladeCountEl.value) : 0;
  const complectation = complectationEl ? String(complectationEl.value || "").trim() : "";

  if (switchEl) {
    switchEl.classList.remove("is-invalid");
  }

  if (isReplaceable) {
    return tnvedCode === replaceableTnvedCode && Number.isFinite(bladeCount) && bladeCount > 0 && Boolean(complectation);
  }

  return tnvedCode !== replaceableTnvedCode;
}

function pcCosmeticsSyncConditionalFields() {
  cosmetics_check_tnved();
  cosmeticsUpdateCategoryCode();
  cosmeticsToggleContentTypeBlock();
  cosmeticsToggleComplectationBlock();
  cosmeticsToggleForChildrenBlock();
  cosmeticsToggleRazorExtraFields();
}

function get_cosmetics_tnveds() {
  const insertEl = document.getElementById("manual_tnved_insert");
  const choices = getCurrentCosmeticsAllowedTnvedChoices();
  if (!insertEl || !choices.length) {
    show_form_errors(["Сначала выберите вид товара, чтобы определить доступный ТН ВЭД."]);
    window.jQuery?.("#form_errorModal").modal("show");
    return;
  }
  insertEl.innerHTML = `<div class="container-fluid"><div id="accordionBlockies">${choices.map((tnved, index) => `
    <div class="card my-1" title="Нажмите чтобы раскрыть блок" data-bs-toggle="collapse" style="cursor: pointer"
         data-bs-target="#collapse${index + 1}" aria-expanded="true" aria-controls="collapse${index + 1}">
      <div class="card-header" style="background-color:#f8f5f5" id="heading${index + 1}">
        <h6 class="mb-0"><b>${tnved[0]}</b>: ${String(tnved[1] || "").slice(0, 50)} ...</h6>
      </div>
      <div id="collapse${index + 1}" class="collapse ${index === 0 ? "show" : ""}" aria-labelledby="heading${index + 1}">
        <div class="card-body">${tnved[1] || ""}<div class="mt-3">
          <button type="button" onclick="selectTnved('${tnved[0]}')" data-dismiss="modal" class="btn btn-sm btn-primary">Выбрать</button>
        </div></div>
      </div>
    </div>`).join("")}</div></div>`;
  window.jQuery?.("#manualTnvedModal").modal("show");
}

function selectTnved(code) {
  const tnvedEl = document.getElementById("tnved_code");
  if (!tnvedEl) return;
  tnvedEl.value = String(code || "").trim();
  pcCosmeticsSyncConditionalFields();
  clear_manual_tnved();
  window.jQuery?.("#manualTnvedModal").modal("hide");
}

function clear_manual_tnved() {
  const insertEl = document.getElementById("manual_tnved_insert");
  if (insertEl) insertEl.innerHTML = "";
}

function updateCosmeticsFullName() {
  const trademarkEl = document.getElementById("trademark");
  const typeEl = document.getElementById("type");
  const extraEl = document.getElementById("full_name_extra");
  const targetEl = document.getElementById("generated_full_name");
  if (!targetEl) return;
  const isPlaceholderOnly = value => /^\s*([^\p{L}\p{N}\s])(?:\s*\1)*\s*$/u.test(value);
  const trademarkRaw = String(trademarkEl?.value || "").trim();
  const trademark = (!trademarkRaw || trademarkRaw === "БЕЗ ТОВАРНОГО ЗНАКА" || isPlaceholderOnly(trademarkRaw)) ? "" : trademarkRaw;
  const extraRaw = String(extraEl?.value || "").trim();
  const extra = isPlaceholderOnly(extraRaw) ? "" : extraRaw;
  const fullName = [String(typeEl?.value || "").trim(), trademark, extra].filter(Boolean).join(" ").trim();
  targetEl.textContent = fullName || "Будет сформировано автоматически";
  targetEl.classList.toggle("text-secondary", !fullName);
  targetEl.classList.toggle("text-dark", Boolean(fullName));
}

function toggleCosmeticsFullNameExtra(switchEl) {
  const blockEl = document.getElementById("full_name_extra_block");
  const inputEl = document.getElementById("full_name_extra");
  if (!blockEl || !inputEl || !switchEl) return;
  const enabled = Boolean(switchEl.checked);
  switchEl.classList.toggle("bg-warning", enabled);
  blockEl.style.display = enabled ? "" : "none";
  if (!enabled) inputEl.value = "";
  updateCosmeticsFullName();
}

function cosmetics_validate_full_name_requirements() {
  const trademarkEl = document.getElementById("trademark");
  const typeEl = document.getElementById("type");
  const extraEl = document.getElementById("full_name_extra");
  const noTMSwitchEl = document.getElementById("noTMSwitch");
  const extraSwitchEl = document.getElementById("fullNameExtraSwitch");
  const trademark = String(trademarkEl?.value || "").trim().toUpperCase();
  const extra = String(extraEl?.value || "").trim();
  const type = String(typeEl?.value || "").trim();
  const invalid = Boolean(type) && (Boolean(noTMSwitchEl?.checked) || !trademark || trademark === "БЕЗ ТОВАРНОГО ЗНАКА") && !extra;
  if (extraEl) {
    extraEl.classList.toggle("is-invalid", invalid);
    extraEl.setCustomValidity(invalid ? "Заполните дополнение к полному наименованию." : "");
  }
  if (extraSwitchEl) extraSwitchEl.classList.toggle("border-danger", invalid);
  return !invalid;
}

const COSMETICS_KEYBOARD_LAYOUT_RU = {
  q: "й", w: "ц", e: "у", r: "к", t: "е", y: "н", u: "г", i: "ш", o: "щ", p: "з",
  "[": "х", "]": "ъ", a: "ф", s: "ы", d: "в", f: "а", g: "п", h: "р", j: "о",
  k: "л", l: "д", ";": "ж", "'": "э", z: "я", x: "ч", c: "с", v: "м",
  b: "и", n: "т", m: "ь", ",": "б", ".": "ю", "`": "ё"
};

function normalizeCosmeticsContentInput(inputEl) {
  if (!inputEl || typeof inputEl.value !== "string") return;
  let value = inputEl.value.split("").map(char => {
    const lower = char.toLowerCase();
    const mapped = COSMETICS_KEYBOARD_LAYOUT_RU[lower];
    return mapped ? (char === lower ? mapped : mapped.toUpperCase()) : char;
  }).join("");
  value = value.replace(/[^А-Яа-яЁё0-9\s,.;:!?()%+\-/"'№@#&*_=\\|[\]{}<>«»\n\r]/g, "");
  inputEl.value = value;
}

function cosmeticsUpdateNominalQuantityTypeOptions() {
  const typeEl = document.getElementById("type");
  const nominalTypeEl = document.getElementById("nominal_quantity_type");
  if (!typeEl || !nominalTypeEl) return;
  const currentValue = nominalTypeEl.value;
  const productType = String(typeEl.value || "");
  const specialTypes = (window.COSMETICS_NOMINAL_QUANTITY_TYPES_BY_PRODUCT_TYPE || {})[productType] || null;
  const allowedTypes = specialTypes || window.COSMETICS_NOMINAL_QUANTITY_TYPES || [];
  const defaultValue = specialTypes ? allowedTypes[0] : "шт";
  nominalTypeEl.innerHTML = '<option value="" selected disabled>Выберите тип</option>';
  allowedTypes.forEach(item => {
    const option = document.createElement("option");
    option.value = item;
    option.textContent = item;
    nominalTypeEl.appendChild(option);
  });
  nominalTypeEl.value = allowedTypes.includes(currentValue) ? currentValue : (allowedTypes.includes(defaultValue) ? defaultValue : "");
  window.jQuery?.(nominalTypeEl).trigger("change").trigger("change.select2");
}

document.addEventListener("DOMContentLoaded", () => {
  pcInitServiceLifeDatepickers();
  const fullNameSwitch = document.getElementById("fullNameExtraSwitch");
  if (fullNameSwitch) toggleCosmeticsFullNameExtra(fullNameSwitch);
  const replaceableRazorSwitch = document.getElementById("replaceable_razor_switch");
  if (replaceableRazorSwitch) {
    replaceableRazorSwitch.addEventListener("change", function () {
      cosmeticsApplyRazorSwitchState(true);
    });
  }
  cosmeticsApplyRazorSwitchState(false);
  cosmeticsUpdateNominalQuantityTypeOptions();
  pcCosmeticsSyncConditionalFields();
  updateCosmeticsFullName();
});
