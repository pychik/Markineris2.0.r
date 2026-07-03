function cosmetics_perform_pos_add(async_flag, url) {
    var pos_form = document.getElementById('form_process_main');
    var crd = cosmetics_check_rd_docs();
    var serviceLifePeriodValid = cosmetics_check_service_life_period();
    var tnvedValid = cosmetics_check_tnved();
    var fullNameValid = cosmetics_validate_full_name_requirements();

    if ((pos_form.checkValidity === true || pos_form.checkValidity()) && crd && serviceLifePeriodValid && tnvedValid && fullNameValid) {
        if (async_flag === 0) {
            loadingCircle();
            pos_form.submit();
        } else {
            loadingCircle();
            cosmetics_load_upload_table(url);
        }
    } else {
        close_Loading_circle();
        if (typeof window.clearPendingStep3TransitionAfterAsyncAdd === 'function') {
            window.clearPendingStep3TransitionAfterAsyncAdd();
        }
        var allInputs = $('#form_process_main input, #form_process_main select, #form_process_main textarea');
        var errors_list = [];

        allInputs.each(function (index) {
            let error_field_id = check_valid(allInputs[index]);
            if (error_field_id !== true) {
                let label_text = jQuery(`#${error_field_id}`).closest(".form-group").find("label").text();
                if (label_text) {
                    errors_list.push(label_text);
                }
            }
        });

        if (crd === false) {
            errors_list.push("Разрешительная документация. Должны быть заполнены все поля формы разрешительной документации, либо все должны быть пусты!");
        }

        if (serviceLifePeriodValid === false) {
            const dateToEl = document.getElementById('sl_date_to');
            if (dateToEl) {
                dateToEl.classList.remove('is-valid');
                dateToEl.classList.add('is-invalid');
            }
            errors_list.push('Период годности. Заполните "Дату от" и "Дату до". "Дата до" не может быть позже, чем "Дата от" плюс указанный срок годности в месяцах.');
        }

        if (tnvedValid === false) {
            errors_list.push('Код ТН ВЭД. Выберите одно из разрешённых значений из списка.');
        }

        if (fullNameValid === false) {
            errors_list.push('Полное наименование. Если выбран вариант "БЕЗ ТОВАРНОГО ЗНАКА", заполните поле "Дополнить полное наименование". Иначе полное наименование состоит только из вида товара, так нельзя.');
        }

        show_form_errors(errors_list);
        $('#form_errorModal').modal('show');
    }
}

function cosmetics_clear_tnved_feedback() {
    const tnvedEl = document.getElementById('tnved_code');
    const suppressorEl = document.getElementById('tnved_co_supressor');
    const validEl = document.getElementById('tnved_valid_feedback');
    const invalidEl = document.getElementById('tnved_nv_feedback');

    if (tnvedEl) {
        tnvedEl.classList.remove('is-valid', 'is-invalid');
    }
    if (suppressorEl) {
        suppressorEl.textContent = '';
    }
    if (validEl) {
        validEl.textContent = '';
    }
    if (invalidEl) {
        invalidEl.textContent = '';
    }
}

function initCosmeticsCategorySearch() {
    const searchIndex = Array.isArray(window.COSMETICS_SEARCH_INDEX) ? window.COSMETICS_SEARCH_INDEX : [];
    const input = document.getElementById('cosmetics-category-search');
    const resultEl = document.getElementById('cosmetics-search-result');

    if (!input || !resultEl || !searchIndex.length) {
        return;
    }

    function normalizeText(value) {
        return String(value || '')
            .trim()
            .toUpperCase()
            .replace(/\s+/g, ' ');
    }

    function extractDigits(value) {
        return String(value || '').replace(/\D/g, '');
    }

    function escapeHtml(value) {
        return String(value || '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    function findMatches(query) {
        const normalizedQuery = normalizeText(query);
        const digitQuery = extractDigits(query);
        const matches = [];
        const seen = new Set();

        if (!normalizedQuery) {
            return matches;
        }

        for (const item of searchIndex) {
            if (digitQuery) {
                for (const choice of (item.allowed_tnved_choices || [])) {
                    const key = `${item.slug}::tnved::${choice.code}`;
                    if (!choice.code.includes(digitQuery) || seen.has(key)) {
                        continue;
                    }
                    seen.add(key);
                    matches.push({
                        item,
                        reason: `ТН ВЭД: ${choice.code}`,
                        details: choice.label,
                    });
                }
            }

            for (const type of (item.product_types || [])) {
                const key = `${item.slug}::type::${type}`;
                if (!normalizeText(type).includes(normalizedQuery) || seen.has(key)) {
                    continue;
                }
                seen.add(key);
                matches.push({
                    item,
                    reason: `Вид товара: ${type}`,
                    details: 'Подкатегория определена по названию товара',
                });
            }
        }

        return matches;
    }

    function renderResult(matches, query) {
        if (!matches.length) {
            const safeQuery = escapeHtml(query);
            resultEl.classList.remove('is-empty');
            resultEl.innerHTML = `
                <p class="cosmetics-search-result__title">Совпадений не найдено</p>
                <div class="cosmetics-search-result__meta">Запрос: ${safeQuery}</div>
            `;
            return;
        }

        resultEl.classList.remove('is-empty');
        const limitedMatches = matches.slice(0, 15);
        const itemsHtml = limitedMatches.map((match) => `
            <li class="cosmetics-search-result__item">
                <a class="cosmetics-search-result__link" href="${escapeHtml(match.item.url)}">
                    <div class="cosmetics-search-result__link-title">${escapeHtml(match.item.title)}</div>
                    <div class="cosmetics-search-result__meta">${escapeHtml(match.reason)}</div>
                    <div class="cosmetics-search-result__meta">${escapeHtml(match.details)}</div>
                </a>
            </li>
        `).join('');
        const moreHtml = matches.length > 15
            ? '<div class="cosmetics-search-result__more">Результатов поиска больше 15 ...</div>'
            : '';

        resultEl.innerHTML = `
            <p class="cosmetics-search-result__title">${matches.length === 1 ? 'Найдена подкатегория' : 'Найдено несколько совпадений'}</p>
            <ul class="cosmetics-search-result__list">${itemsHtml}</ul>
            ${moreHtml}
        `;
    }

    input.addEventListener('input', () => {
        const query = input.value.trim();
        if (query.length < 3) {
            resultEl.classList.add('is-empty');
            resultEl.innerHTML = '';
            return;
        }

        renderResult(findMatches(query), query);
    });
}

function cosmetics_check_tnved() {
    const tnvedEl = document.getElementById('tnved_code');
    const invalidEl = document.getElementById('tnved_nv_feedback');
    const validEl = document.getElementById('tnved_valid_feedback');
    const allowed = getCurrentCosmeticsAllowedTnvedCodes();

    if (!tnvedEl) {
        return true;
    }

    const code = String(tnvedEl.value || '').trim();
    cosmetics_clear_tnved_feedback();

    if (!code) {
        tnvedEl.classList.add('is-invalid');
        if (invalidEl) {
            invalidEl.textContent = 'Выберите ТН ВЭД из списка.';
        }
        return false;
    }

    if (!allowed.includes(code)) {
        tnvedEl.classList.add('is-invalid');
        if (invalidEl) {
            invalidEl.textContent = 'Код ТН ВЭД не разрешён для этой подкатегории.';
        }
        return false;
    }

    tnvedEl.classList.add('is-valid');
    if (validEl) {
        validEl.textContent = 'ТН ВЭД выбран.';
    }
    return true;
}

function getCurrentCosmeticsAllowedTnvedCodes() {
    const typeEl = document.getElementById('type');
    const productType = typeEl ? String(typeEl.value || '').trim() : '';
    const mapping = window.COSMETICS_TNVED_CODES_BY_PRODUCT_TYPE || {};
    const mappedCodes = Array.isArray(mapping[productType]) ? mapping[productType] : null;

    if (mappedCodes && mappedCodes.length) {
        return mappedCodes;
    }

    return Array.isArray(window.COSMETICS_ALLOWED_TNVED_CODES) ? window.COSMETICS_ALLOWED_TNVED_CODES : [];
}

function getCurrentCosmeticsAllowedTnvedChoices() {
    const allowedCodes = new Set(getCurrentCosmeticsAllowedTnvedCodes());
    const allChoices = Array.isArray(window.COSMETICS_ALLOWED_TNVED_CHOICES) ? window.COSMETICS_ALLOWED_TNVED_CHOICES : [];
    return allChoices.filter((choice) => Array.isArray(choice) && allowedCodes.has(String(choice[0] || '').trim()));
}

function syncCosmeticsTnvedByProductType(force = false) {
    const tnvedEl = document.getElementById('tnved_code');
    if (!tnvedEl) {
        return;
    }

    const allowedCodes = getCurrentCosmeticsAllowedTnvedCodes();
    const currentCode = String(tnvedEl.value || '').trim();
    const nextCode = allowedCodes.length === 1 ? String(allowedCodes[0] || '').trim() : '';

    if (force || !currentCode || !allowedCodes.includes(currentCode)) {
        tnvedEl.value = nextCode;
    }

    cosmetics_check_tnved();
    cosmeticsUpdateCategoryCode();
    cosmeticsToggleContentTypeBlock();
    cosmeticsToggleComplectationBlock();
}

function cosmeticsResolveCurrentCategoryCode() {
    const tnvedEl = document.getElementById('tnved_code');
    const categoryCodeByTnved = window.COSMETICS_CATEGORY_CODE_BY_TNVED || {};
    const fallbackCode = String(window.COSMETICS_CATEGORY_CODE || '').trim();
    const tnvedCode = tnvedEl ? String(tnvedEl.value || '').trim() : '';

    if (tnvedCode && Object.prototype.hasOwnProperty.call(categoryCodeByTnved, tnvedCode)) {
        const resolved = String(categoryCodeByTnved[tnvedCode] || '').trim();
        if (resolved) {
            return resolved;
        }
    }

    return fallbackCode;
}

function cosmeticsUpdateCategoryCode() {
    const categoryCodeEl = document.getElementById('cosmetics_category_code_value');
    if (!categoryCodeEl) {
        return;
    }

    categoryCodeEl.textContent = cosmeticsResolveCurrentCategoryCode();
}

function cosmeticsShouldShowContentType() {
    if (window.COSMETICS_CONTENT_VALUE_ENABLED === false) {
        return false;
    }

    if (window.COSMETICS_CONTENT_TYPE_ENABLED === false) {
        return false;
    }

    const typeEl = document.getElementById('type');
    const productType = typeEl ? String(typeEl.value || '').trim() : '';
    const triggerProductTypes = Array.isArray(window.COSMETICS_CONTENT_TYPE_TRIGGER_PRODUCT_TYPES)
        ? window.COSMETICS_CONTENT_TYPE_TRIGGER_PRODUCT_TYPES
        : [];

    if (productType && triggerProductTypes.length) {
        return triggerProductTypes.includes(productType);
    }

    const triggerTnveds = Array.isArray(window.COSMETICS_CONTENT_TYPE_TRIGGER_TNVEDS)
        ? window.COSMETICS_CONTENT_TYPE_TRIGGER_TNVEDS
        : [];

    if (!triggerTnveds.length) {
        return true;
    }

    const tnvedEl = document.getElementById('tnved_code');
    const tnvedCode = tnvedEl ? String(tnvedEl.value || '').trim() : '';
    if (tnvedCode) {
        return triggerTnveds.includes(tnvedCode);
    }

    const allowedCodes = getCurrentCosmeticsAllowedTnvedCodes();
    return allowedCodes.length > 0 && allowedCodes.every((code) => triggerTnveds.includes(String(code || '').trim()));
}

function cosmeticsResolveContentLabel() {
    const typeEl = document.getElementById('type');
    const productType = typeEl ? String(typeEl.value || '').trim() : '';
    const contentLabelByProductType = window.COSMETICS_CONTENT_LABEL_BY_PRODUCT_TYPE || {};
    if (productType && Object.prototype.hasOwnProperty.call(contentLabelByProductType, productType)) {
        const resolved = String(contentLabelByProductType[productType] || '').trim();
        if (resolved) {
            return resolved;
        }
    }

    const contentLabelByTnved = window.COSMETICS_CONTENT_LABEL_BY_TNVED || {};
    const fallbackLabel = String(window.COSMETICS_DEFAULT_CONTENT_LABEL || 'Состав товара').trim();
    const tnvedEl = document.getElementById('tnved_code');
    const tnvedCode = tnvedEl ? String(tnvedEl.value || '').trim() : '';

    if (tnvedCode && Object.prototype.hasOwnProperty.call(contentLabelByTnved, tnvedCode)) {
        const resolved = String(contentLabelByTnved[tnvedCode] || '').trim();
        if (resolved) {
            return resolved;
        }
    }

    const allowedCodes = getCurrentCosmeticsAllowedTnvedCodes();
    const resolvedLabels = Array.from(new Set(
        allowedCodes
            .map((code) => String(contentLabelByTnved[String(code || '').trim()] || '').trim())
            .filter(Boolean)
    ));
    if (resolvedLabels.length === 1) {
        return resolvedLabels[0];
    }

    return fallbackLabel;
}

function cosmeticsResolveContentLabelForValues(productType, tnvedCode) {
    const normalizedProductType = String(productType || '').trim();
    const normalizedTnvedCode = String(tnvedCode || '').trim();
    const contentLabelByProductType = window.COSMETICS_CONTENT_LABEL_BY_PRODUCT_TYPE || {};

    if (
        normalizedProductType
        && Object.prototype.hasOwnProperty.call(contentLabelByProductType, normalizedProductType)
    ) {
        const resolved = String(contentLabelByProductType[normalizedProductType] || '').trim();
        if (resolved) {
            return resolved;
        }
    }

    const contentLabelByTnved = window.COSMETICS_CONTENT_LABEL_BY_TNVED || {};
    if (normalizedTnvedCode && Object.prototype.hasOwnProperty.call(contentLabelByTnved, normalizedTnvedCode)) {
        const resolved = String(contentLabelByTnved[normalizedTnvedCode] || '').trim();
        if (resolved) {
            return resolved;
        }
    }

    return String(window.COSMETICS_DEFAULT_CONTENT_LABEL || 'Состав товара').trim();
}

function cosmeticsToggleContentTypeBlock() {
    const rowEl = document.getElementById('content_row');
    const contentBlockEl = document.getElementById('content_block');
    const blockEl = document.getElementById('content_type_block');
    const selectEl = document.getElementById('content_type');
    const contentEl = document.getElementById('content');
    const labelEl = document.getElementById('content_label_text_value');

    if (rowEl && window.COSMETICS_CONTENT_VALUE_ENABLED === false) {
        rowEl.style.display = 'none';
    }
    if (contentBlockEl && window.COSMETICS_CONTENT_VALUE_ENABLED === false) {
        contentBlockEl.style.display = 'none';
    }
    if (contentEl && window.COSMETICS_CONTENT_VALUE_ENABLED === false) {
        contentEl.required = false;
        contentEl.value = '';
    }
    if (selectEl && window.COSMETICS_CONTENT_VALUE_ENABLED === false) {
        selectEl.required = false;
        selectEl.value = '';
    }

    if (labelEl) {
        labelEl.textContent = cosmeticsResolveContentLabel();
    }

    if (!blockEl || !selectEl) {
        return;
    }

    const shouldShow = cosmeticsShouldShowContentType();
    blockEl.style.display = shouldShow ? '' : 'none';
    selectEl.required = shouldShow;

    if (!shouldShow) {
        selectEl.value = '';
        if (typeof window.jQuery !== 'undefined') {
            window.jQuery(selectEl).trigger('change').trigger('change.select2');
        }
    }
}

function cosmeticsToggleForChildrenBlock() {
    const blockEl = document.getElementById('for_children_block');
    const selectEl = document.getElementById('for_children');

    if (!blockEl || !selectEl) {
        return;
    }

    const shouldShow = window.COSMETICS_FOR_CHILDREN_ENABLED !== false;
    blockEl.style.display = shouldShow ? '' : 'none';
    selectEl.required = shouldShow;

    if (!shouldShow) {
        selectEl.value = '';
        if (typeof window.jQuery !== 'undefined') {
            window.jQuery(selectEl).trigger('change').trigger('change.select2');
        }
    }
}

function get_cosmetics_tnveds() {
    const insertEl = document.getElementById('manual_tnved_insert');
    const choices = getCurrentCosmeticsAllowedTnvedChoices();

    if (!insertEl) {
        show_form_errors(['Обновите страницу и попробуйте снова']);
        $('#form_errorModal').modal('show');
        return;
    }

    if (!choices.length) {
        show_form_errors(['Сначала выберите вид товара, чтобы определить доступный ТН ВЭД.']);
        $('#form_errorModal').modal('show');
        return;
    }

    const cardsHtml = choices.map((tnved, index) => `
      <div class="card my-1" title="Нажмите чтобы раскрыть блок" data-bs-toggle="collapse" style="cursor: pointer"
            data-bs-target="#collapse${index + 1}" aria-expanded="true" aria-controls="collapse${index + 1}">
        <div class="card-header" style="background-color:#f8f5f5" id="heading${index + 1}">
          <h6 class="mb-0">
            <b>${tnved[0]}</b>: ${String(tnved[1] || '').slice(0, 50)} ...
          </h6>
        </div>
        <div id="collapse${index + 1}" class="collapse ${index === 0 ? 'show' : ''}" aria-labelledby="heading${index + 1}">
          <div class="card-body">
            ${tnved[1] || ''}
            <div class="mt-3">
              <button type="button" onclick="selectTnved('${tnved[0]}')" data-dismiss="modal" class="btn btn-sm btn-primary">Выбрать</button>
            </div>
          </div>
        </div>
      </div>
    `).join('');

    insertEl.innerHTML = `<div class="container-fluid"><div id="accordionBlockies">${cardsHtml}</div></div>`;
    $('#manualTnvedModal').modal('show');
}

function selectTnved(code) {
    const tnvedEl = document.getElementById('tnved_code');

    if (!tnvedEl) {
        return;
    }

    tnvedEl.value = String(code || '').trim();
    cosmetics_check_tnved();
    cosmeticsUpdateCategoryCode();
    cosmeticsToggleContentTypeBlock();
    cosmeticsToggleComplectationBlock();
    cosmeticsToggleForChildrenBlock();
    clear_manual_tnved();
    $('#manualTnvedModal').modal('hide');
}

function clear_manual_tnved() {
    const insertEl = document.getElementById('manual_tnved_insert');
    if (insertEl) {
        insertEl.innerHTML = '';
    }
}

function cosmetics_check_rd_docs() {
    const switchEl = document.getElementById("has-rd-switch");
    const rdType = document.getElementById("rd_type");
    const rdName = document.getElementById("rd_name");
    const rdDate = document.getElementById("rd_date");

    if (!switchEl || !rdType || !rdName || !rdDate) {
        return true;
    }

    const hasAnyValue = rdType.value.length > 0 || rdName.value.length > 0 || rdDate.value.length > 0;

    if (!switchEl.checked) {
        return !hasAnyValue;
    }

    return rdType.value.length > 0
        && rdName.value.length > 0
        && rdDate.value.length > 0;
}

function cosmetics_parse_ru_date(dateStr) {
    if (!dateStr || typeof dateStr !== 'string') {
        return null;
    }

    const parts = dateStr.split('.');
    if (parts.length !== 3) {
        return null;
    }

    const day = Number(parts[0]);
    const month = Number(parts[1]) - 1;
    const year = Number(parts[2]);

    if (!Number.isInteger(day) || !Number.isInteger(month) || !Number.isInteger(year)) {
        return null;
    }

    const date = new Date(year, month, day, 12, 0, 0, 0);
    if (date.getFullYear() !== year || date.getMonth() !== month || date.getDate() !== day) {
        return null;
    }

    return date;
}

function cosmetics_check_service_life_period() {
    const serviceLifeEl = document.getElementById('service_life');
    const dateFromEl = document.getElementById('sl_date_from');
    const dateToEl = document.getElementById('sl_date_to');

    if (!serviceLifeEl || !dateFromEl || !dateToEl) {
        return true;
    }

    const serviceLife = Number(serviceLifeEl.value);
    const dateFrom = cosmetics_parse_ru_date(dateFromEl.value);
    const dateTo = cosmetics_parse_ru_date(dateToEl.value);

    dateFromEl.classList.remove('is-invalid');
    dateToEl.classList.remove('is-invalid');

    if (!serviceLifeEl.value || !dateFromEl.value || !dateToEl.value) {
        if (!dateFromEl.value) {
            dateFromEl.classList.add('is-invalid');
        }
        if (!dateToEl.value) {
            dateToEl.classList.add('is-invalid');
        }
        return false;
    }

    if (!Number.isFinite(serviceLife) || serviceLife < 0 || !dateFrom || !dateTo) {
        if (!dateFrom) {
            dateFromEl.classList.add('is-invalid');
        }
        if (!dateTo) {
            dateToEl.classList.add('is-invalid');
        }
        return false;
    }

    const maxDate = new Date(dateFrom.getTime());
    maxDate.setMonth(maxDate.getMonth() + serviceLife);

    if (dateTo > maxDate) {
        dateToEl.classList.add('is-invalid');
        return false;
    }

    return true;
}

function updateCosmeticsFullName() {
    const trademarkEl = document.getElementById('trademark');
    const typeEl = document.getElementById('type');
    const extraEl = document.getElementById('full_name_extra');
    const targetEl = document.getElementById('generated_full_name');

    if (!targetEl) {
        return;
    }

    const isPlaceholderOnly = (value) => /^\s*([^\p{L}\p{N}\s])(?:\s*\1)*\s*$/u.test(value);
    const trademarkRaw = trademarkEl ? String(trademarkEl.value || '').trim() : '';
    const trademark = (!trademarkRaw || trademarkRaw === 'БЕЗ ТОВАРНОГО ЗНАКА' || isPlaceholderOnly(trademarkRaw))
        ? ''
        : trademarkRaw;
    const type = typeEl ? String(typeEl.value || '').trim() : '';
    const extraRaw = extraEl ? String(extraEl.value || '').trim() : '';
    const extra = isPlaceholderOnly(extraRaw) ? '' : extraRaw;
    const fullName = [type, trademark, extra].filter(Boolean).join(' ').trim();
    targetEl.textContent = fullName || 'Будет сформировано автоматически';
    targetEl.classList.toggle('text-secondary', !fullName);
    targetEl.classList.toggle('text-dark', Boolean(fullName));
}

function cosmetics_validate_full_name_requirements() {
    const trademarkEl = document.getElementById('trademark');
    const typeEl = document.getElementById('type');
    const extraEl = document.getElementById('full_name_extra');
    const noTMSwitchEl = document.getElementById('noTMSwitch');
    const extraSwitchEl = document.getElementById('fullNameExtraSwitch');

    const isPlaceholderOnly = (value) => /^\s*([^\p{L}\p{N}\s])(?:\s*\1)*\s*$/u.test(String(value || ''));
    const trademarkRaw = trademarkEl ? String(trademarkEl.value || '').trim() : '';
    const trademark = (!trademarkRaw || trademarkRaw === 'БЕЗ ТОВАРНОГО ЗНАКА' || isPlaceholderOnly(trademarkRaw))
        ? ''
        : trademarkRaw;
    const type = typeEl ? String(typeEl.value || '').trim() : '';
    const extraRaw = extraEl ? String(extraEl.value || '').trim() : '';
    const extra = isPlaceholderOnly(extraRaw) ? '' : extraRaw;
    const noTrademarkSelected = Boolean(noTMSwitchEl && noTMSwitchEl.checked) || !trademark;
    const invalid = Boolean(type) && noTrademarkSelected && !extra;

    if (extraEl) {
        extraEl.classList.toggle('is-invalid', invalid);
        extraEl.classList.remove('is-valid');
        extraEl.setCustomValidity(
            invalid
                ? 'Если выбран вариант "БЕЗ ТОВАРНОГО ЗНАКА", заполните поле "Дополнить полное наименование".'
                : ''
        );
    }

    if (trademarkEl) {
        trademarkEl.classList.toggle('is-invalid', invalid);
        trademarkEl.classList.remove('is-valid');
    }

    if (extraSwitchEl) {
        extraSwitchEl.classList.toggle('border-danger', invalid);
    }

    return !invalid;
}

function normalizeCosmeticsContentInput(inputEl) {
    if (!inputEl) {
        return;
    }

    const keyboardMap = {
        q: 'й', w: 'ц', e: 'у', r: 'к', t: 'е', y: 'н', u: 'г', i: 'ш', o: 'щ', p: 'з',
        a: 'ф', s: 'ы', d: 'в', f: 'а', g: 'п', h: 'р', j: 'о', k: 'л',
        l: 'д', z: 'я', x: 'ч', c: 'с', v: 'м', b: 'и', n: 'т', m: 'ь',
        Q: 'Й', W: 'Ц', E: 'У', R: 'К', T: 'Е', Y: 'Н', U: 'Г', I: 'Ш', O: 'Щ', P: 'З',
        A: 'Ф', S: 'Ы', D: 'В', F: 'А', G: 'П', H: 'Р', J: 'О', K: 'Л',
        L: 'Д', Z: 'Я', X: 'Ч', C: 'С', V: 'М', B: 'И', N: 'Т', M: 'Ь'
    };

    let value = String(inputEl.value || '');
    value = value.split('').map((char) => keyboardMap[char] || char).join('');
    value = value.replace(/[^А-Яа-яЁё0-9\s,.;:!?()%+\-/"'№@#&*_=\\|[\]{}<>«»\n\r]/g, '');
    inputEl.value = value;
}

function cosmeticsUpdateNominalQuantityTypeOptions() {
    const typeEl = document.getElementById('type');
    const nominalTypeEl = document.getElementById('nominal_quantity_type');

    if (!typeEl || !nominalTypeEl) {
        return;
    }

    const currentValue = nominalTypeEl.value;
    const productType = String(typeEl.value || '');
    const specialTypes = COSMETICS_NOMINAL_QUANTITY_TYPES_BY_PRODUCT_TYPE[productType] || null;
    const allowedTypes = specialTypes || COSMETICS_NOMINAL_QUANTITY_TYPES;
    const defaultValue = specialTypes ? allowedTypes[0] : 'шт';

    nominalTypeEl.innerHTML = '';

    const placeholderOpt = document.createElement('option');
    placeholderOpt.value = '';
    placeholderOpt.textContent = 'Выберите тип';
    placeholderOpt.disabled = true;
    placeholderOpt.selected = true;
    nominalTypeEl.appendChild(placeholderOpt);

    allowedTypes.forEach((item) => {
        const option = document.createElement('option');
        option.value = item;
        option.textContent = item;
        if (currentValue === item) {
            option.selected = true;
            placeholderOpt.selected = false;
        }
        nominalTypeEl.appendChild(option);
    });

    if (!allowedTypes.includes(currentValue)) {
        nominalTypeEl.value = allowedTypes.includes(defaultValue) ? defaultValue : '';
    }

    if (!nominalTypeEl.value && allowedTypes.includes(defaultValue)) {
        nominalTypeEl.value = defaultValue;
    }

    if (typeof window.jQuery !== 'undefined') {
        const $nominalTypeEl = window.jQuery(nominalTypeEl);
        $nominalTypeEl.trigger('change');
        $nominalTypeEl.trigger('change.select2');
    }
}

function cosmeticsShouldShowComplectation() {
    const typeEl = document.getElementById('type');
    const tnvedEl = document.getElementById('tnved_code');
    const triggerTypes = Array.isArray(window.COSMETICS_COMPLECTATION_TRIGGER_TYPES)
        ? window.COSMETICS_COMPLECTATION_TRIGGER_TYPES
        : [];
    const triggerTnveds = Array.isArray(window.COSMETICS_COMPLECTATION_TRIGGER_TNVEDS)
        ? window.COSMETICS_COMPLECTATION_TRIGGER_TNVEDS
        : [];
    const productType = typeEl ? String(typeEl.value || '').trim() : '';
    const tnvedCode = tnvedEl ? String(tnvedEl.value || '').trim() : '';

    return triggerTypes.includes(productType) || triggerTnveds.includes(tnvedCode);
}

function cosmeticsToggleComplectationBlock() {
    const blockEl = document.getElementById('complectation_block');
    const inputEl = document.getElementById('complectation');

    if (!blockEl || !inputEl) {
        return;
    }

    const shouldShow = cosmeticsShouldShowComplectation();
    blockEl.style.display = shouldShow ? '' : 'none';
    inputEl.required = shouldShow;

    if (!shouldShow) {
        inputEl.value = '';
    }
}

function toggleCosmeticsFullNameExtra(switchEl) {
    const extraBlock = document.getElementById('full_name_extra_block');
    const extraInput = document.getElementById('full_name_extra');

    if (!extraBlock || !extraInput || !switchEl) {
        return;
    }

    switchEl.classList.toggle('bg-warning', switchEl.checked);

    if (switchEl.checked) {
        extraBlock.style.display = '';
    } else {
        extraBlock.style.display = 'none';
        extraInput.value = '';
    }

    updateCosmeticsFullName();
    cosmetics_validate_full_name_requirements();
}

function show_cosmetics_pos(index, full_name, trademark, type, nominal_quantity, nominal_quantity_type, for_children,
                            usage_term_type, service_life, blade_count, complectation, layers_characteristic, content_type, content, sl_date_from, sl_date_to,
                            quantity, country, tnved_code, subcategory, rd_name, edit_link, copy_link, delete_link, csrf_token) {
    let main = document.getElementById('ShowModalTable');
    main.innerHTML = '';
    const isRazorSubcategory = String(subcategory || '').trim() === 'razor_blades_and_cassettes';
    const contentLabel = cosmeticsResolveContentLabelForValues(type, tnved_code);
    const shouldShowForChildren = !isRazorSubcategory && window.COSMETICS_FOR_CHILDREN_ENABLED !== false;
    const shouldShowContent = !isRazorSubcategory && window.COSMETICS_CONTENT_VALUE_ENABLED !== false;
    const razorForChildrenBlock = !shouldShowForChildren ? '' : `
                    <div class="important-card__item"><div class="important-card__prop">Для детей</div><div class="important-card__val">${for_children || ''}</div></div>
    `;
    const contentTypeBlock = shouldShowContent && window.COSMETICS_CONTENT_TYPE_ENABLED !== false && content_type ? `
                    <div class="important-card__item"><div class="important-card__prop">Тип состава</div><div class="important-card__val">${content_type || ''}</div></div>
    ` : '';
    const contentBlocks = !shouldShowContent ? '' : `
                    ${contentTypeBlock}
                    <div class="important-card__item" style="overflow: auto"><div class="important-card__prop">${contentLabel || 'Состав'}</div><div class="important-card__val">${content || ''}</div></div>
    `;
    const bladeCountBlock = isRazorSubcategory ? `
                    <div class="important-card__item"><div class="important-card__prop">Количество лезвий</div><div class="important-card__val">${blade_count || ''}</div></div>
    ` : '';
    const layersCharacteristicBlock = layers_characteristic ? `
                    <div class="important-card__item"><div class="important-card__prop">Кол-во слоев</div><div class="important-card__val">${layers_characteristic}</div></div>
    ` : '';
    const complectationBlock = complectation ? `
                    <div class="important-card__item" style="overflow: auto"><div class="important-card__prop">Комплектация</div><div class="important-card__val">${complectation}</div></div>
    ` : '';

    let data_modal = `<div class="modal fade " id="showElementTable" tabindex="-1" role="dialog" aria-labelledby="showElementTableLabel"
        aria-modal="true">
        <div class="modal-dialog modal-dialog-centered" role="document">
            <div class="modal-content p-3 p-md-4">
                <span type="button" class="close ms-auto" data-bs-dismiss="modal" aria-label="Close">
                    <span aria-hidden="true">
                        <svg xmlns="http://www.w3.org/2000/svg" width="36" height="35" viewBox="0 0 36 35" fill="none">
                            <path d="M9.51367 27.4861L27.4859 9.51384" stroke="#575757" stroke-width="1.5" stroke-linecap="round"/>
                            <path d="M9.51367 9.51386L27.4859 27.4861" stroke="#575757" stroke-width="1.5" stroke-linecap="round"/>
                        </svg>
                    </span>
                </span>
                <div class="modal-header ">
                    <h5 class="modal-title border-0">${index}</h5>
                </div>
                <div class="important-card important-card--light pt-0">
                    <div class="important-card__item d-flex align-items-center">
                        <div class="important-card__prop">${full_name || (trademark + ' ' + type)}</div>
                        <div class="row g-3 justify-content-end  important-card__btn">
                            <a href="${edit_link}" class="btn-table me-2" title="Изменить позицию заказа">
                                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18"
                                    viewBox="0 0 18 18" fill="none">
                                    <path
                                        d="M6.82983 14.0851C7.25223 13.9668 7.63764 13.7432 7.94983 13.4351L17.4898 3.89505C17.8165 3.56706 18 3.12299 18 2.66005C18 2.19711 17.8165 1.75304 17.4898 1.42505L16.5498 0.49505C16.2172 0.177305 15.7748 0 15.3148 0C14.8548 0 14.4125 0.177305 14.0798 0.49505L4.53983 10.0251C4.23117 10.3352 4.01032 10.7217 3.89983 11.1451L3.15983 13.9051C3.12472 14.0311 3.12381 14.1643 3.15721 14.2908C3.1906 14.4174 3.25708 14.5327 3.34983 14.625C3.49137 14.7642 3.68135 14.8431 3.87983 14.8451L6.82983 14.0851ZM7.23983 12.725C7.05547 12.9127 6.82407 13.0474 6.56983 13.115L5.59983 13.375L4.59983 12.3751L4.85983 11.4051C4.92977 11.1518 5.06414 10.9209 5.24983 10.7351L5.62983 10.3651L7.61983 12.3551L7.23983 12.725ZM8.32983 11.6451L6.33983 9.65505L13.0698 2.92505L15.0598 4.91505L8.32983 11.6451ZM16.7798 3.19505L15.7698 4.20505L13.7798 2.21505L14.7898 1.19505C14.8593 1.12527 14.9419 1.06989 15.0329 1.03211C15.1238 0.994329 15.2213 0.97488 15.3198 0.97488C15.4183 0.97488 15.5158 0.994329 15.6068 1.03211C15.6977 1.06989 15.7803 1.12527 15.8498 1.19505L16.7798 2.13505C16.9193 2.27619 16.9975 2.46662 16.9975 2.66505C16.9975 2.86348 16.9193 3.05391 16.7798 3.19505Z"
                                        fill="#8F8F8F" />
                                    <path
                                        d="M0.600098 17.8451H17.5001C17.6327 17.8451 17.7599 17.7924 17.8537 17.6986C17.9474 17.6048 18.0001 17.4777 18.0001 17.3451C18.0001 17.2125 17.9474 17.0853 17.8537 16.9915C17.7599 16.8977 17.6327 16.8451 17.5001 16.8451H0.600098C0.467489 16.8451 0.340312 16.8977 0.246544 16.9915C0.152776 17.0853 0.100098 17.2125 0.100098 17.3451C0.100098 17.4777 0.152776 17.6048 0.246544 17.6986C0.340312 17.7924 0.467489 17.8451 0.600098 17.8451Z"
                                        fill="#8F8F8F" />
                                </svg>
                            </a>
                            <a href="${copy_link}" class="btn-table me-2" title="Копировать позицию заказа">
                                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24"
                                    viewBox="0 0 24 24" fill="none">
                                    <path
                                        d="M9 3.25C5.82436 3.25 3.25 5.82436 3.25 9V16.1069C3.25 16.5211 3.58579 16.8569 4 16.8569C4.41421 16.8569 4.75 16.5211 4.75 16.1069V9C4.75 6.65279 6.65279 4.75 9 4.75H16.0129C16.4271 4.75 16.7629 4.41421 16.7629 4C16.7629 3.58579 16.4271 3.25 16.0129 3.25H9Z"
                                        fill="#8F8F8F" />
                                    <path fill-rule="evenodd" clip-rule="evenodd"
                                        d="M18.4026 6.79327C15.1616 6.43105 11.8384 6.43105 8.59748 6.79327C7.6742 6.89646 6.93227 7.62305 6.82344 8.55349C6.43906 11.84 6.43906 15.16 6.82344 18.4465C6.93227 19.377 7.6742 20.1035 8.59748 20.2067C11.8384 20.569 15.1616 20.569 18.4026 20.2067C19.3258 20.1035 20.0678 19.377 20.1766 18.4465C20.561 15.16 20.561 11.84 20.1766 8.55349C20.0678 7.62305 19.3258 6.89646 18.4026 6.79327ZM8.76409 8.28399C11.8943 7.93414 15.1057 7.93414 18.2359 8.28399C18.4733 8.31051 18.6599 8.49822 18.6867 8.72774C19.0576 11.8984 19.0576 15.1016 18.6867 18.2723C18.6599 18.5018 18.4733 18.6895 18.2359 18.716C15.1057 19.0659 11.8943 19.0659 8.76409 18.716C8.52674 18.6895 8.34013 18.5018 8.31329 18.2723C7.94245 15.1016 7.94245 11.8984 8.31329 8.72774C8.34013 8.49822 8.52674 8.31051 8.76409 8.28399Z"
                                        fill="#8F8F8F" />
                                </svg>
                            </a>
                            <form method="post" class="btn-table me-2" action="${delete_link}#orders_table">
                                <input type="hidden" name="csrf_token" value="${csrf_token}"/>
                                <label>
                                    <input style="display: none;" type="submit" />
                                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24"
                                          style="cursor:pointer" viewBox="0 0 24 24" fill="none">
                                        <path
                                            d="M10.1001 2.25C9.68589 2.25 9.3501 2.58579 9.3501 3V3.75H5.1001C4.68589 3.75 4.3501 4.08579 4.3501 4.5C4.3501 4.91421 4.68589 5.25 5.1001 5.25H19.1001C19.5143 5.25 19.8501 4.91421 19.8501 4.5C19.8501 4.08579 19.5143 3.75 19.1001 3.75H14.8501V3C14.8501 2.58579 14.5143 2.25 14.1001 2.25H10.1001Z"
                                            fill="#7C7C7C" />
                                        <path
                                            d="M10.1001 10.65C10.5143 10.65 10.8501 10.9858 10.8501 11.4V18.4C10.8501 18.8142 10.5143 19.15 10.1001 19.15C9.68589 19.15 9.3501 18.8142 9.3501 18.4V11.4C9.3501 10.9858 9.68589 10.65 10.1001 10.65Z"
                                            fill="#7C7C7C" />
                                        <path
                                            d="M14.8501 11.4C14.8501 10.9858 14.5143 10.65 14.1001 10.65C13.6859 10.65 13.3501 10.9858 13.3501 11.4V18.4C13.3501 18.8142 13.6859 19.15 14.1001 19.15C14.5143 19.15 14.8501 18.8142 14.8501 18.4V11.4Z"
                                            fill="#7C7C7C" />
                                        <path fill-rule="evenodd" clip-rule="evenodd"
                                            d="M6.0914 7.91718C6.13361 7.53735 6.45466 7.25 6.83682 7.25H17.3632C17.7453 7.25 18.0664 7.53735 18.1086 7.91718L18.3087 9.71852C18.6715 12.9838 18.6715 16.2793 18.3087 19.5446L18.289 19.722C18.145 21.0181 17.1404 22.0517 15.8489 22.2325C13.3618 22.5807 10.8382 22.5807 8.35106 22.2325C7.05952 22.0517 6.05498 21.0181 5.91096 19.722L5.89126 19.5446C5.52844 16.2793 5.52844 12.9838 5.89126 9.71852L6.0914 7.91718ZM7.5081 8.75L7.38208 9.88417C7.0315 13.0394 7.0315 16.2238 7.38208 19.379L7.40178 19.5563C7.47009 20.171 7.9465 20.6612 8.55903 20.747C10.9082 21.0758 13.2918 21.0758 15.6409 20.747C16.2535 20.6612 16.7299 20.171 16.7982 19.5563L16.8179 19.379C17.1685 16.2238 17.1685 13.0394 16.8179 9.88417L16.6919 8.75H7.5081Z"
                                            fill="#7C7C7C" />
                                    </svg>
                                </label>
                            </form>
                        </div>
                    </div>
                    <div class="important-card__item"><div class="important-card__prop">Полное наименование</div><div class="important-card__val">${full_name || ''}</div></div>
                    <div class="important-card__item"><div class="important-card__prop">Вид товара</div><div class="important-card__val">${type || ''}</div></div>
                    <div class="important-card__item"><div class="important-card__prop">Номинальное количество</div><div class="important-card__val">${nominal_quantity || ''} ${nominal_quantity_type || ''}</div></div>
                    ${bladeCountBlock}
                    ${layersCharacteristicBlock}
                    ${complectationBlock}
                    ${razorForChildrenBlock}
                    <div class="important-card__item"><div class="important-card__prop">Тип срока использования</div><div class="important-card__val">${usage_term_type || ''}</div></div>
                    <div class="important-card__item"><div class="important-card__prop">Срок годности, мес.</div><div class="important-card__val">${service_life ? `${service_life} мес.` : ''}</div></div>
                    ${contentBlocks}
                    <div class="important-card__item"><div class="important-card__prop">Дата от</div><div class="important-card__val">${sl_date_from || ''}</div></div>
                    <div class="important-card__item"><div class="important-card__prop">Дата до</div><div class="important-card__val">${sl_date_to || ''}</div></div>
                    <div class="important-card__item"><div class="important-card__prop">Количество</div><div class="important-card__val">${quantity || ''}</div></div>
                    <div class="important-card__item"><div class="important-card__prop">Страна</div><div class="important-card__val">${country || ''}</div></div>
                    <div class="important-card__item"><div class="important-card__prop">ТН ВЭД</div><div class="important-card__val">${tnved_code || ''}</div></div>
                    <div class="important-card__item"><div class="important-card__prop">РД</div><div class="important-card__val">${rd_name || ''}</div></div>
                </div>
            </div>
        </div>
    </div>`;

    main.insertAdjacentHTML('beforeend', data_modal);
    $('#showElementTable').modal('show');
}

async function async_cosmetics_delete_pos(url, csrf, block) {
    loadingCircle();
    const settings = {
        method: 'POST',
        headers: {
            Accept: 'application/json',
            'Content-Type': 'application/json',
            'X-CSRFTOKEN': csrf
        }
    };
    try {
        const fetchResponse = await fetch(`${url}`, settings);
        const data = await fetchResponse.json();
        if (data.status === 'success' && data.type === 'async') {
            $('#step-3_update').html(data.htmlresponse);
            $('#orders_row_count').html(data.pos_count);
            $('#orders_pos_count').html(data.orders_pos_count);
            $('#modal_orders_pos_count').html(`<span>${data.orders_pos_count}</span>шт.`);
            make_message('Успешно удалена позиция', 'success');
            setTimeout(function () { clear_user_messages(); }, 15000);
        } else if (data.status === 'success' && data.type === 'order_delete') {
            $(block).closest('tr').remove();
            window.location = data.url;
        } else {
            alert(data.status);
        }
    } catch (e) {
        console.log(e);
        close_Loading_circle();
        make_connection_error_message('Произошла ошибка. Обратитесь к администратору', 'error');
        setTimeout(function () { clear_user_messages(); }, 5000);
        return false;
    }
    close_Loading_circle();
}

function cosmetics_load_upload_table(url) {
    var form = $("#form_process_main").serialize();
    var trademark = $('#trademark').val();
    $.ajax({
        url: url,
        method: "POST",
        data: form,
        success: function (data) {
            if (data.status === 'success') {
                close_Loading_circle();
                $('#step-3_update').html(data.htmlresponse);
                $('#orders_row_count').html(data.pos_count);
                $('#orders_pos_count').html(data.orders_pos_count);
                $('#modal_orders_pos_count').html(`<span>${data.orders_pos_count}</span>шт.`);
                make_message(`Позиция с товарным знаком ${trademark} успешно добавлена`, 'success');
                cosmetics_clear_pos();
                if (typeof window.runPendingStep3TransitionAfterAsyncAdd === 'function') {
                    window.runPendingStep3TransitionAfterAsyncAdd();
                }
            } else {
                close_Loading_circle();
                if (typeof window.clearPendingStep3TransitionAfterAsyncAdd === 'function') {
                    window.clearPendingStep3TransitionAfterAsyncAdd();
                }
                make_message(data.message || 'Ошибка добавления позиции', 'danger');
            }
        },
        error: function () {
            close_Loading_circle();
            if (typeof window.clearPendingStep3TransitionAfterAsyncAdd === 'function') {
                window.clearPendingStep3TransitionAfterAsyncAdd();
            }
            make_connection_error_message('Произошла ошибка. Обратитесь к администратору', 'error');
        }
    });

    setTimeout(function () {
        clear_user_messages();
    }, 15000);
}

async function cosmetics_update_table(page) {
    try {
        const res = await fetch(page);
        const data = await res.json();
        if (data.status === 'success') {
            document.getElementById('step-3_update').innerHTML = data.htmlresponse;
        } else {
            alert(data.message || 'Ошибка обновления блока заказа');
        }
    } catch (e) {
        alert('Ошибка связи с сервером');
    }
}

function cosmetics_clear_pos() {
    const defaultTnvedCode = String(window.COSMETICS_DEFAULT_TNVED_CODE || '').trim();
    $('#trademark').val("");
    $('#full_name_extra').val("");
    $('#type').val('').trigger("change");
    $('#nominal_quantity_type').val('').trigger("change");
    $('#nominal_quantity').val("");
    $('#blade_count').val("1");
    $('#complectation').val("");
    $('#layers_characteristic').val('').trigger("change");
    $('#for_children').val('').trigger("change");
    $('#content_type').val('').trigger("change");
    $('#content').val("");
    $('#usage_term_type').val('').trigger("change");
    $('#service_life').val("");
    $('#sl_date_from').val("");
    $('#sl_date_to').val("");
    $('#quantity').val("");
    $('#country').val('').trigger("change");
    $('#tnved_code').val(defaultTnvedCode);
    $('#rd_type').val('').trigger("change");
    $('#rd_name').val("");
    $('#rd_date').val("");
    const rdSwitch = document.getElementById('has-rd-switch');
    const fullNameSwitch = document.getElementById('fullNameExtraSwitch');
    if (rdSwitch) {
        rdSwitch.checked = false;
        if (typeof cosmeticsApplyRdState === 'function') {
            cosmeticsApplyRdState();
        }
    }
    if (fullNameSwitch) {
        fullNameSwitch.checked = false;
        toggleCosmeticsFullNameExtra(fullNameSwitch);
    } else {
        updateCosmeticsFullName();
    }

    cosmetics_clear_tnved_feedback();
    cosmeticsUpdateNominalQuantityTypeOptions();
    cosmeticsUpdateCategoryCode();
    cosmeticsToggleContentTypeBlock();
    cosmeticsToggleComplectationBlock();
    cosmeticsToggleForChildrenBlock();
}

document.addEventListener("DOMContentLoaded", function () {
    document.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' && e.target.tagName.toLowerCase() === 'input') {
            e.preventDefault();
            return false;
        }
    });

    const fullNameExtraInput = document.getElementById('full_name_extra');
    if (fullNameExtraInput) {
        fullNameExtraInput.addEventListener('input', function () {
            updateCosmeticsFullName();
            cosmetics_validate_full_name_requirements();
        });
    }

    const productTypeEl = document.getElementById('type');
    if (productTypeEl) {
        productTypeEl.addEventListener('change', cosmeticsUpdateNominalQuantityTypeOptions);
        productTypeEl.addEventListener('change', cosmeticsToggleComplectationBlock);
        productTypeEl.addEventListener('change', function () {
            syncCosmeticsTnvedByProductType(true);
            cosmetics_validate_full_name_requirements();
        });
    }

    const trademarkEl = document.getElementById('trademark');
    if (trademarkEl) {
        trademarkEl.addEventListener('input', cosmetics_validate_full_name_requirements);
        trademarkEl.addEventListener('change', cosmetics_validate_full_name_requirements);
    }

    initCosmeticsCategorySearch();
    updateCosmeticsFullName();
    cosmetics_validate_full_name_requirements();
    cosmeticsUpdateNominalQuantityTypeOptions();
    syncCosmeticsTnvedByProductType(false);
    cosmetics_check_tnved();
    cosmeticsUpdateCategoryCode();
    cosmeticsToggleContentTypeBlock();
    cosmeticsToggleComplectationBlock();
    cosmeticsToggleForChildrenBlock();

    const contentEl = document.getElementById('content');
    if (contentEl) {
        normalizeCosmeticsContentInput(contentEl);
    }
});
