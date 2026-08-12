function toys_perform_pos_add(async_flag, url) {
    var pos_form = document.getElementById('form_process_main');
    toysPrepareModelArticleBeforeSubmit();
    var crd = toys_check_rd_docs();
    var serviceLifePeriodValid = toys_check_service_life_period();
    var tnvedValid = toys_check_tnved();
    var okpd2Valid = toys_check_okpd2();
    var fullNameValid = toys_validate_full_name_requirements();

    if ((pos_form.checkValidity === true || pos_form.checkValidity()) && crd && serviceLifePeriodValid && tnvedValid && okpd2Valid && fullNameValid) {
        if (async_flag === 0) {
            loadingCircle();
            pos_form.submit();
        } else {
            loadingCircle();
            toys_load_upload_table(url);
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
            errors_list.push('Период годности. Заполните "Дату от" и "Дату до". "Дата до" должна быть не раньше чем через месяц от текущей даты.');
        }

        if (tnvedValid === false) {
            errors_list.push('Код ТН ВЭД. Выберите одно из разрешенных значений из списка.');
        }

        if (okpd2Valid === false) {
            errors_list.push('Код ОКПД2. Выберите значение из списка.');
        }

        if (fullNameValid === false) {
            errors_list.push('Полное наименование. Если выбран вариант "без товарного знака", заполните поле "Дополнить полное наименование".');
        }

        show_form_errors(errors_list);
        $('#form_errorModal').modal('show');
    }
}

function initToysCategorySearch() {
    const searchIndex = Array.isArray(window.TOYS_SEARCH_INDEX) ? window.TOYS_SEARCH_INDEX : [];
    const input = document.getElementById('toys-category-search');
    const resultEl = document.getElementById('toys-search-result');

    if (!input || !resultEl || !searchIndex.length) {
        return;
    }

    function normalizeText(value) {
        return String(value || '').trim().toUpperCase().replace(/\s+/g, ' ');
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
                    matches.push({item, reason: `ТН ВЭД: ${choice.code}`, details: choice.label});
                }
            }

            for (const type of (item.product_types || [])) {
                const key = `${item.slug}::type::${type}`;
                if (!normalizeText(type).includes(normalizedQuery) || seen.has(key)) {
                    continue;
                }
                seen.add(key);
                matches.push({item, reason: `Вид товара: ${type}`, details: 'Подкатегория определена по названию товара'});
            }
        }

        return matches;
    }

    function renderResult(matches, query) {
        if (!matches.length) {
            resultEl.classList.remove('is-empty');
            resultEl.innerHTML = `
                <p class="cosmetics-search-result__title">Совпадений не найдено</p>
                <div class="cosmetics-search-result__meta">Запрос: ${escapeHtml(query)}</div>
            `;
            return;
        }

        resultEl.classList.remove('is-empty');
        const itemsHtml = matches.slice(0, 15).map((match) => `
            <li class="cosmetics-search-result__item">
                <a class="cosmetics-search-result__link" href="${escapeHtml(match.item.url)}">
                    <div class="cosmetics-search-result__link-title">${escapeHtml(match.item.title)}</div>
                    <div class="cosmetics-search-result__meta">${escapeHtml(match.reason)}</div>
                    <div class="cosmetics-search-result__meta">${escapeHtml(match.details)}</div>
                </a>
            </li>
        `).join('');

        resultEl.innerHTML = `
            <p class="cosmetics-search-result__title">${matches.length === 1 ? 'Найдена подкатегория' : 'Найдено несколько совпадений'}</p>
            <ul class="cosmetics-search-result__list">${itemsHtml}</ul>
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

function toys_clear_tnved_feedback() {
    const tnvedEl = document.getElementById('tnved_code');
    const suppressorEl = document.getElementById('tnved_co_supressor');
    const validEl = document.getElementById('tnved_valid_feedback');
    const invalidEl = document.getElementById('tnved_nv_feedback');

    if (tnvedEl) tnvedEl.classList.remove('is-valid', 'is-invalid');
    if (suppressorEl) suppressorEl.textContent = '';
    if (validEl) validEl.textContent = '';
    if (invalidEl) invalidEl.textContent = '';
}

function toysGetProductType() {
    const typeEl = document.getElementById('type');
    return typeEl ? String(typeEl.value || '').trim() : '';
}

function toysGetAllowedTnvedCodesForType(productType) {
    const allAllowed = Array.isArray(window.TOYS_ALLOWED_TNVED_CODES)
        ? window.TOYS_ALLOWED_TNVED_CODES.map((code) => String(code || '').trim()).filter(Boolean)
        : [];
    const mapping = window.TOYS_ALLOWED_TNVED_CODES_BY_PRODUCT_TYPE || {};
    const mapped = Array.isArray(mapping[productType])
        ? mapping[productType].map((code) => String(code || '').trim()).filter(Boolean)
        : [];
    return mapped.length ? mapped : allAllowed;
}

function toysUpdateCategoryCodeByTnved() {
    const tnvedEl = document.getElementById('tnved_code');
    const categoryCodeEl = document.getElementById('category_code');
    const tnved = tnvedEl ? String(tnvedEl.value || '').trim() : '';
    const categoryCodeByTnved = window.TOYS_CATEGORY_CODE_BY_TNVED || {};
    const categoryCode = tnved ? String(categoryCodeByTnved[tnved] || '').trim() : '';

    if (categoryCodeEl) {
        categoryCodeEl.value = categoryCode;
    }
}

function handleToysProductTypeChange() {
    const tnvedEl = document.getElementById('tnved_code');
    if (tnvedEl) {
        tnvedEl.value = '';
    }
    toys_clear_tnved_feedback();
    toysClearOkpd2();
    toysUpdateCategoryCodeByTnved();
    updateToysFullName();
}

function toys_check_tnved() {
    const tnvedEl = document.getElementById('tnved_code');
    const invalidEl = document.getElementById('tnved_nv_feedback');
    const validEl = document.getElementById('tnved_valid_feedback');
    const allowed = toysGetAllowedTnvedCodesForType(toysGetProductType());

    if (!tnvedEl) {
        return true;
    }

    const code = String(tnvedEl.value || '').trim();
    toys_clear_tnved_feedback();

    if (!code || !allowed.includes(code)) {
        tnvedEl.classList.add('is-invalid');
        if (invalidEl) {
            invalidEl.textContent = code ? 'Код ТН ВЭД не подходит для выбранного вида товара.' : 'Выберите ТН ВЭД из списка.';
        }
        return false;
    }

    tnvedEl.classList.add('is-valid');
    if (validEl) {
        validEl.textContent = 'ТН ВЭД выбран.';
    }
    return true;
}

function get_toys_tnveds() {
    const insertEl = document.getElementById('manual_tnved_insert');
    const allChoices = Array.isArray(window.TOYS_ALLOWED_TNVED_CHOICES) ? window.TOYS_ALLOWED_TNVED_CHOICES : [];
    const allowedForType = toysGetAllowedTnvedCodesForType(toysGetProductType());
    const choices = allChoices.filter((tnved) => allowedForType.includes(String(tnved[0] || '').trim()));

    if (!insertEl || !choices.length) {
        show_form_errors(['Для выбранного вида товара нет доступного ТН ВЭД.']);
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
              <button type="button" onclick="selectToysTnved('${tnved[0]}')" data-dismiss="modal" class="btn btn-sm btn-primary">Выбрать</button>
            </div>
          </div>
        </div>
      </div>
    `).join('');

    insertEl.innerHTML = `<div class="container-fluid"><div id="accordionBlockies">${cardsHtml}</div></div>`;
    $('#manualTnvedModal').modal('show');
}

function selectToysTnved(code) {
    const tnvedEl = document.getElementById('tnved_code');
    if (!tnvedEl) {
        return;
    }
    const previousCode = String(tnvedEl.value || '').trim();
    tnvedEl.value = String(code || '').trim();
    if (previousCode !== tnvedEl.value) {
        toysClearOkpd2();
    }
    toysUpdateCategoryCodeByTnved();
    toys_check_tnved();
    clear_manual_tnved();
    $('#manualTnvedModal').modal('hide');
}

function clear_manual_tnved() {
    const insertEl = document.getElementById('manual_tnved_insert');
    if (insertEl) {
        insertEl.innerHTML = '';
    }
}

function toysEscapeHtml(value) {
    return String(value || '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

function toysGetOkpd2Choices(tnved) {
    const choicesByTnved = window.TOYS_OKPD2_CHOICES_BY_TNVED || {};
    return Array.isArray(choicesByTnved[tnved]) ? choicesByTnved[tnved] : [];
}

function toysFindOkpd2Choice(code, tnved) {
    const normalizedCode = String(code || '').trim();
    return toysGetOkpd2Choices(tnved).find((choice) => String(choice[0] || '').trim() === normalizedCode);
}

function toysClearOkpd2() {
    const okpd2El = document.getElementById('okpd2_code');
    const okpd2NameEl = document.getElementById('okpd2_name');
    const descriptionEl = document.getElementById('okpd2_description');
    if (okpd2El) {
        okpd2El.value = '';
        okpd2El.classList.remove('is-valid', 'is-invalid');
    }
    if (okpd2NameEl) {
        okpd2NameEl.value = '';
    }
    if (descriptionEl) {
        descriptionEl.textContent = '';
    }
}

function toysRefreshOkpd2State() {
    const tnvedEl = document.getElementById('tnved_code');
    const okpd2El = document.getElementById('okpd2_code');
    const okpd2NameEl = document.getElementById('okpd2_name');
    const descriptionEl = document.getElementById('okpd2_description');
    if (!tnvedEl || !okpd2El || !okpd2El.value) {
        return;
    }

    const tnved = String(tnvedEl.value || '').trim();
    const choice = toysFindOkpd2Choice(okpd2El.value, tnved);
    if (!choice) {
        toysClearOkpd2();
        return;
    }
    if (okpd2NameEl) {
        okpd2NameEl.value = String(choice[1] || '').trim();
    }
    if (descriptionEl) {
        descriptionEl.textContent = String(choice[1] || '').trim();
    }
}

function get_toys_okpd2s() {
    const tnvedEl = document.getElementById('tnved_code');
    const tnved = tnvedEl ? String(tnvedEl.value || '').trim() : '';

    if (!tnved) {
        show_form_errors(['Сначала выберите ТН ВЭД.']);
        $('#form_errorModal').modal('show');
        return;
    }

    const choices = toysGetOkpd2Choices(tnved);
    if (!choices.length) {
        show_form_errors(['Для выбранного ТН ВЭД нет разрешенного ОКПД2.']);
        $('#form_errorModal').modal('show');
        return;
    }

    const cardsHtml = choices.map((choice, index) => `
      <div class="card my-1" title="Нажмите чтобы раскрыть блок" data-bs-toggle="collapse" style="cursor: pointer"
            data-bs-target="#toysOkpd2Collapse${index + 1}" aria-expanded="true" aria-controls="toysOkpd2Collapse${index + 1}">
        <div class="card-header" style="background-color:#f8f5f5" id="toysOkpd2Heading${index + 1}">
          <h6 class="mb-0">
            <b>${toysEscapeHtml(choice[0])}</b>: ${toysEscapeHtml(String(choice[1] || '').slice(0, 80))} ...
          </h6>
        </div>
        <div id="toysOkpd2Collapse${index + 1}" class="collapse ${index === 0 ? 'show' : ''}" aria-labelledby="toysOkpd2Heading${index + 1}">
          <div class="card-body">
            ${toysEscapeHtml(choice[1])}
            <div class="mt-3">
              <button type="button" class="btn btn-sm btn-primary toys-okpd2-select" data-code="${toysEscapeHtml(choice[0])}" data-name="${toysEscapeHtml(choice[1])}">Выбрать</button>
            </div>
          </div>
        </div>
      </div>
    `).join('');

    document.getElementById('modals-container').innerHTML = `
        <div class="modal fade" id="toysOkpd2Modal" tabindex="-1" data-bs-backdrop="static" role="dialog" aria-hidden="true">
            <div class="modal-dialog modal-lg modal-dialog-scrollable" role="document">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Выберите ОКПД2</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <div class="mb-3 small text-muted">ТН ВЭД: ${toysEscapeHtml(tnved)}.</div>
                        <div>${cardsHtml}</div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-accent" data-bs-dismiss="modal">Закрыть</button>
                    </div>
                </div>
            </div>
        </div>
    `;
    document.querySelectorAll('.toys-okpd2-select').forEach((button) => {
        button.addEventListener('click', () => selectToysOkpd2(button.dataset.code || '', button.dataset.name || ''));
    });
    $('#toysOkpd2Modal').modal('show');
}

function selectToysOkpd2(code, name) {
    const okpd2El = document.getElementById('okpd2_code');
    const okpd2NameEl = document.getElementById('okpd2_name');
    const descriptionEl = document.getElementById('okpd2_description');
    if (!okpd2El) {
        return;
    }
    okpd2El.value = String(code || '').trim();
    if (okpd2NameEl) {
        okpd2NameEl.value = String(name || '').trim();
    }
    if (descriptionEl) {
        descriptionEl.textContent = String(name || '').trim();
    }
    toys_check_okpd2();
    $('#toysOkpd2Modal').modal('hide');
}

function toys_check_okpd2() {
    const tnvedEl = document.getElementById('tnved_code');
    const okpd2El = document.getElementById('okpd2_code');
    const okpd2NameEl = document.getElementById('okpd2_name');
    if (!okpd2El) {
        return true;
    }
    const tnved = tnvedEl ? String(tnvedEl.value || '').trim() : '';
    const code = String(okpd2El.value || '').trim();
    const hiddenName = okpd2NameEl ? String(okpd2NameEl.value || '').trim() : '';
    const choice = toysFindOkpd2Choice(code, tnved);
    const valid = Boolean(choice) && String(choice[1] || '').trim() === hiddenName;
    okpd2El.classList.toggle('is-invalid', !valid);
    okpd2El.classList.toggle('is-valid', valid);
    return valid;
}

function toys_parse_ru_date(value) {
    const match = String(value || '').trim().match(/^(\d{2})\.(\d{2})\.(\d{4})$/);
    if (!match) {
        return null;
    }

    const day = Number(match[1]);
    const month = Number(match[2]) - 1;
    const year = Number(match[3]);
    const date = new Date(year, month, day, 12, 0, 0, 0);
    if (date.getFullYear() !== year || date.getMonth() !== month || date.getDate() !== day) {
        return null;
    }
    return date;
}

function toys_min_date_to() {
    const date = new Date();
    date.setHours(12, 0, 0, 0);
    date.setMonth(date.getMonth() + 1);
    return date;
}

function toys_check_service_life_period() {
    const dateFromEl = document.getElementById('sl_date_from');
    const dateToEl = document.getElementById('sl_date_to');

    if (!dateFromEl || !dateToEl) {
        return true;
    }

    const dateFrom = toys_parse_ru_date(dateFromEl.value);
    const dateTo = toys_parse_ru_date(dateToEl.value);
    const minDateTo = toys_min_date_to();

    dateFromEl.classList.remove('is-invalid');
    dateToEl.classList.remove('is-invalid');

    if (!dateFrom) {
        dateFromEl.classList.add('is-invalid');
    }
    if (!dateTo || dateTo < minDateTo || (dateFrom && dateTo < dateFrom)) {
        dateToEl.classList.add('is-invalid');
    }

    return Boolean(dateFrom && dateTo && dateTo >= minDateTo && dateTo >= dateFrom);
}

function updateToysFullName() {
    const trademarkEl = document.getElementById('trademark');
    const typeEl = document.getElementById('type');
    const extraEl = document.getElementById('full_name_extra');
    const targetEl = document.getElementById('generated_full_name');
    if (!targetEl) {
        return;
    }

    const trademarkRaw = trademarkEl ? String(trademarkEl.value || '').trim() : '';
    const trademark = trademarkRaw.toUpperCase() === 'БЕЗ ТОВАРНОГО ЗНАКА' ? '' : trademarkRaw;
    const type = typeEl ? String(typeEl.value || '').trim() : '';
    const extra = extraEl ? String(extraEl.value || '').trim() : '';
    const fullName = [type, trademark, extra].filter(Boolean).join(' ');
    targetEl.textContent = fullName || 'Будет сформировано автоматически';
    targetEl.title = fullName;
}

function toggleToysFullNameExtra(switchEl) {
    const blockEl = document.getElementById('full_name_extra_block');
    const inputEl = document.getElementById('full_name_extra');
    if (!blockEl || !inputEl || !switchEl) {
        return;
    }

    const enabled = Boolean(switchEl && switchEl.checked);
    switchEl.classList.toggle('bg-warning', enabled);
    blockEl.style.display = enabled ? '' : 'none';
    if (!enabled) {
        inputEl.value = '';
    }
    updateToysFullName();
}

function toys_validate_full_name_requirements() {
    const trademarkEl = document.getElementById('trademark');
    const extraEl = document.getElementById('full_name_extra');
    const typeEl = document.getElementById('type');
    const trademark = trademarkEl ? String(trademarkEl.value || '').trim().toUpperCase() : '';
    const extra = extraEl ? String(extraEl.value || '').trim() : '';
    const type = typeEl ? String(typeEl.value || '').trim() : '';
    return !(type && (!trademark || trademark === 'БЕЗ ТОВАРНОГО ЗНАКА') && !extra);
}

const TOYS_NO_MODEL_ARTICLE_VALUE = 'отсутствует';

function toysIsNoModelArticleValue(value) {
    return String(value || '').trim().toUpperCase() === TOYS_NO_MODEL_ARTICLE_VALUE.toUpperCase();
}

function toggleToysModelArticleField(switchEl) {
    const inputEl = document.getElementById('model_article');
    const displayEl = document.getElementById('model_article_display');
    if (!inputEl || !displayEl || !switchEl) {
        return;
    }

    const emptyValue = inputEl.dataset.emptyValue || TOYS_NO_MODEL_ARTICLE_VALUE;
    const enabled = Boolean(switchEl.checked);
    switchEl.classList.toggle('bg-warning', enabled);
    switchEl.classList.toggle('border-warning', enabled);

    if (enabled) {
        inputEl.value = emptyValue;
        inputEl.style.display = 'none';
        displayEl.style.display = 'block';
        displayEl.value = '';
        inputEl.classList.remove('is-invalid');
    } else {
        if (toysIsNoModelArticleValue(inputEl.value)) {
            inputEl.value = '';
        }
        inputEl.style.display = 'block';
        displayEl.style.display = 'none';
    }

    inputEl.dispatchEvent(new Event('input', {bubbles: true}));
    inputEl.dispatchEvent(new Event('change', {bubbles: true}));
}

function toysPrepareModelArticleBeforeSubmit() {
    const inputEl = document.getElementById('model_article');
    const switchEl = document.getElementById('noModelArticleSwitch');
    if (!inputEl) {
        return;
    }

    if ((switchEl && switchEl.checked) || !String(inputEl.value || '').trim()) {
        inputEl.value = inputEl.dataset.emptyValue || TOYS_NO_MODEL_ARTICLE_VALUE;
    }
}

const TOYS_KEYBOARD_LAYOUT_RU = {
    q: 'й', w: 'ц', e: 'у', r: 'к', t: 'е', y: 'н', u: 'г', i: 'ш', o: 'щ', p: 'з',
    '[': 'х', ']': 'ъ', a: 'ф', s: 'ы', d: 'в', f: 'а', g: 'п', h: 'р', j: 'о',
    k: 'л', l: 'д', ';': 'ж', "'": 'э', z: 'я', x: 'ч', c: 'с', v: 'м',
    b: 'и', n: 'т', m: 'ь', ',': 'б', '.': 'ю', '`': 'ё'
};

function normalizeToysContentInput(el) {
    if (!el || typeof el.value !== 'string') {
        return;
    }

    let value = el.value;
    value = value.split('').map((char) => {
        const lower = char.toLowerCase();
        const mapped = TOYS_KEYBOARD_LAYOUT_RU[lower];
        if (!mapped) {
            return char;
        }
        return char === lower ? mapped : mapped.toUpperCase();
    }).join('');
    value = value.replace(/[^А-Яа-яЁё0-9\s,.;:!?()%+\-/"'№@#&*_=\\|[\]{}<>«»\n\r]/g, '');
    el.value = value;
}

function toys_check_rd_docs() {
    const rdType = document.getElementById("rd_type");
    const rdName = document.getElementById("rd_name");
    const rdDate = document.getElementById("rd_date");
    if (!rdType || !rdName || !rdDate) {
        return true;
    }
    const hasAnyValue = rdType.value.length > 0 || rdName.value.length > 0 || rdDate.value.length > 0;
    if (!hasAnyValue) {
        return true;
    }
    return rdType.value.length > 0 && rdName.value.length > 0 && rdDate.value.length > 0;
}

function show_toys_pos(index, full_name, trademark, type, okpd2_code, okpd2_name, model_article_type,
                       model_article, model_article_replace, drive_type, material, min_child_age, usage_term_type,
                       content, service_life_type, service_life, sl_date_from, sl_date_to, quantity, country, tnved_code, rd_name,
                       editUrl, copyUrl, deleteUrl, csrf) {
    const main = document.getElementById('ShowModalTable');
    if (!main) {
        return;
    }

    const escapeHtml = typeof toysEscapeHtml === 'function'
        ? toysEscapeHtml
        : (value) => String(value || '').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    const item = (label, value) => `
                    <div class="important-card__item">
                        <div class="important-card__prop">${escapeHtml(label)}</div>
                        <div class="important-card__val">${escapeHtml(value || '')}</div>
                    </div>
    `;
    const modelArticleValue = [model_article_type, model_article].filter(Boolean).join(': ');
    const okpd2Value = okpd2_code || '';
    const serviceLifeValue = [service_life_type, service_life].filter(Boolean).join(' ');

    main.innerHTML = `
        <div class="modal fade" id="showElementTable" tabindex="-1" role="dialog" aria-labelledby="showElementTableLabel" aria-modal="true">
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
                    <div class="modal-header">
                        <h5 class="modal-title border-0">${escapeHtml(index)}</h5>
                    </div>
                    <div class="important-card important-card--light pt-0">
                        <div class="important-card__item d-flex align-items-center">
                            <div class="important-card__prop">${escapeHtml(full_name || `${trademark || ''} ${type || ''}`.trim())}</div>
                            <div class="row g-3 justify-content-end important-card__btn">
                                <a href="${editUrl}" class="btn-table me-2" title="Изменить позицию заказа">
                                    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 18 18" fill="none">
                                        <path d="M6.82983 14.0851C7.25223 13.9668 7.63764 13.7432 7.94983 13.4351L17.4898 3.89505C17.8165 3.56706 18 3.12299 18 2.66005C18 2.19711 17.8165 1.75304 17.4898 1.42505L16.5498 0.49505C16.2172 0.177305 15.7748 0 15.3148 0C14.8548 0 14.4125 0.177305 14.0798 0.49505L4.53983 10.0251C4.23117 10.3352 4.01032 10.7217 3.89983 11.1451L3.15983 13.9051C3.12472 14.0311 3.12381 14.1643 3.15721 14.2908C3.1906 14.4174 3.25708 14.5327 3.34983 14.625C3.49137 14.7642 3.68135 14.8431 3.87983 14.8451L6.82983 14.0851ZM7.23983 12.725C7.05547 12.9127 6.82407 13.0474 6.56983 13.115L5.59983 13.375L4.59983 12.3751L4.85983 11.4051C4.92977 11.1518 5.06414 10.9209 5.24983 10.7351L5.62983 10.3651L7.61983 12.3551L7.23983 12.725ZM8.32983 11.6451L6.33983 9.65505L13.0698 2.92505L15.0598 4.91505L8.32983 11.6451ZM16.7798 3.19505L15.7698 4.20505L13.7798 2.21505L14.7898 1.19505C14.8593 1.12527 14.9419 1.06989 15.0329 1.03211C15.1238 0.994329 15.2213 0.97488 15.3198 0.97488C15.4183 0.97488 15.5158 0.994329 15.6068 1.03211C15.6977 1.06989 15.7803 1.12527 15.8498 1.19505L16.7798 2.13505C16.9193 2.27619 16.9975 2.46662 16.9975 2.66505C16.9975 2.86348 16.9193 3.05391 16.7798 3.19505Z" fill="#8F8F8F" />
                                        <path d="M0.600098 17.8451H17.5001C17.6327 17.8451 17.7599 17.7924 17.8537 17.6986C17.9474 17.6048 18.0001 17.4777 18.0001 17.3451C18.0001 17.2125 17.9474 17.0853 17.8537 16.9915C17.7599 16.8977 17.6327 16.8451 17.5001 16.8451H0.600098C0.467489 16.8451 0.340312 16.8977 0.246544 16.9915C0.152776 17.0853 0.100098 17.2125 0.100098 17.3451C0.100098 17.4777 0.152776 17.6048 0.246544 17.6986C0.340312 17.7924 0.467489 17.8451 0.600098 17.8451Z" fill="#8F8F8F" />
                                    </svg>
                                </a>
                                <a href="${copyUrl}" class="btn-table me-2" title="Копировать позицию заказа">
                                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none">
                                        <path d="M9 3.25C5.82436 3.25 3.25 5.82436 3.25 9V16.1069C3.25 16.5211 3.58579 16.8569 4 16.8569C4.41421 16.8569 4.75 16.5211 4.75 16.1069V9C4.75 6.65279 6.65279 4.75 9 4.75H16.0129C16.4271 4.75 16.7629 4.41421 16.7629 4C16.7629 3.58579 16.4271 3.25 16.0129 3.25H9Z" fill="#8F8F8F" />
                                        <path fill-rule="evenodd" clip-rule="evenodd" d="M18.4026 6.79327C15.1616 6.43105 11.8384 6.43105 8.59748 6.79327C7.6742 6.89646 6.93227 7.62305 6.82344 8.55349C6.43906 11.84 6.43906 15.16 6.82344 18.4465C6.93227 19.377 7.6742 20.1035 8.59748 20.2067C11.8384 20.569 15.1616 20.569 18.4026 20.2067C19.3258 20.1035 20.0678 19.377 20.1766 18.4465C20.561 15.16 20.561 11.84 20.1766 8.55349C20.0678 7.62305 19.3258 6.89646 18.4026 6.79327ZM8.76409 8.28399C11.8943 7.93414 15.1057 7.93414 18.2359 8.28399C18.4733 8.31051 18.6599 8.49822 18.6867 8.72774C19.0576 11.8984 19.0576 15.1016 18.6867 18.2723C18.6599 18.5018 18.4733 18.6895 18.2359 18.716C15.1057 19.0659 11.8943 19.0659 8.76409 18.716C8.52674 18.6895 8.34013 18.5018 8.31329 18.2723C7.94245 15.1016 7.94245 11.8984 8.31329 8.72774C8.34013 8.49822 8.52674 8.31051 8.76409 8.28399Z" fill="#8F8F8F" />
                                    </svg>
                                </a>
                                <label class="btn-table me-2">
                                    <input style="display: none;" type="button" onclick="async_toys_delete_pos('${deleteUrl}/1', '${csrf}', this)" />
                                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" style="cursor:pointer" viewBox="0 0 24 24" fill="none">
                                        <path d="M10.1001 2.25C9.68589 2.25 9.3501 2.58579 9.3501 3V3.75H5.1001C4.68589 3.75 4.3501 4.08579 4.3501 4.5C4.3501 4.91421 4.68589 5.25 5.1001 5.25H19.1001C19.5143 5.25 19.8501 4.91421 19.8501 4.5C19.8501 4.08579 19.5143 3.75 19.1001 3.75H14.8501V3C14.8501 2.58579 14.5143 2.25 14.1001 2.25H10.1001Z" fill="#7C7C7C" />
                                        <path d="M10.1001 10.65C10.5143 10.65 10.8501 10.9858 10.8501 11.4V18.4C10.8501 18.8142 10.5143 19.15 10.1001 19.15C9.68589 19.15 9.3501 18.8142 9.3501 18.4V11.4C9.3501 10.9858 9.68589 10.65 10.1001 10.65Z" fill="#7C7C7C" />
                                        <path d="M14.8501 11.4C14.8501 10.9858 14.5143 10.65 14.1001 10.65C13.6859 10.65 13.3501 10.9858 13.3501 11.4V18.4C13.3501 18.8142 13.6859 19.15 14.1001 19.15C14.5143 19.15 14.8501 18.8142 14.8501 18.4V11.4Z" fill="#7C7C7C" />
                                        <path fill-rule="evenodd" clip-rule="evenodd" d="M6.0914 7.91718C6.13361 7.53735 6.45466 7.25 6.83682 7.25H17.3632C17.7453 7.25 18.0664 7.53735 18.1086 7.91718L18.3087 9.71852C18.6715 12.9838 18.6715 16.2793 18.3087 19.5446L18.289 19.722C18.145 21.0181 17.1404 22.0517 15.8489 22.2325C13.3618 22.5807 10.8382 22.5807 8.35106 22.2325C7.05952 22.0517 6.05498 21.0181 5.91096 19.722L5.89126 19.5446C5.52844 16.2793 5.52844 12.9838 5.89126 9.71852L6.0914 7.91718ZM7.5081 8.75L7.38208 9.88417C7.0315 13.0394 7.0315 16.2238 7.38208 19.379L7.40178 19.5563C7.47009 20.171 7.9465 20.6612 8.55903 20.747C10.9082 21.0758 13.2918 21.0758 15.6409 20.747C16.2535 20.6612 16.7299 20.171 16.7982 19.5563L16.8179 19.379C17.1685 16.2238 17.1685 13.0394 16.8179 9.88417L16.6919 8.75H7.5081Z" fill="#7C7C7C" />
                                    </svg>
                                </label>
                            </div>
                        </div>
                        ${item('Полное наименование', full_name)}
                        ${item('Товарный знак', trademark)}
                        ${item('Вид товара', type)}
                        ${item('ТН ВЭД', tnved_code)}
                        ${item('ОКПД2', okpd2Value)}
                        ${item('Модель / артикул', modelArticleValue)}
                        ${item('Заменить модель/артикул', model_article_replace)}
                        ${drive_type ? item('Тип привода в движение', drive_type) : ''}
                        ${item('Материал', material)}
                        ${item('Минимальный возраст', min_child_age)}
                        ${item('Хар-ка срока использования', usage_term_type)}
                        ${item('Состав', content)}
                        ${item('Срок службы', serviceLifeValue)}
                        ${item('Дата от', sl_date_from)}
                        ${item('Дата до', sl_date_to)}
                        ${item('Количество', quantity)}
                        ${item('Страна', country)}
                        ${item('Разрешительный документ', rd_name)}
                    </div>
                </div>
            </div>
        </div>
    `;
    $('#showElementTable').modal('show');
}

async function async_toys_delete_pos(url, csrf, block) {
    loadingCircle();
    const response = await fetch(url, {
        method: 'POST',
        headers: {'X-CSRFToken': csrf}
    });
    const data = await response.json();
    close_Loading_circle();
    if (data.status === 'success') {
        $('#step-3_update').html(data.htmlresponse);
        $('#orders_pos_count').text(data.orders_pos_count);
        $('#orders_row_count').text(data.pos_count);
    } else {
        show_form_errors(['Не удалось удалить позицию']);
        $('#form_errorModal').modal('show');
    }
}

function toys_clear_pos() {
    const defaultTnvedCode = String(window.TOYS_DEFAULT_TNVED_CODE || '').trim();

    $('#full_name_extra').val('');
    $('#type').val('').trigger('change');
    $('#drive_type').val('').trigger('change');
    $('#material').val('').trigger('change');
    $('#min_child_age').val('').trigger('change');
    $('#usage_term_type').val('').trigger('change');
    $('#content').val('');
    $('#service_life_type').val('мес').trigger('change');
    $('#service_life').val('36');
    $('#sl_date_from').val('');
    $('#sl_date_to').val('');
    $('#quantity').val('');
    $('#tnved_code').val(defaultTnvedCode);
    $('#okpd2_code').val('');
    $('#okpd2_name').val('');
    $('#okpd2_description').text('');
    $('#model_article_type').val('Артикул').trigger('change');
    $('#model_article').val('');
    $('#country').val('').trigger('change');
    $('#rd_type').val('').trigger('change');
    $('#rd_name').val('');
    $('#rd_date').val('');

    const trademarkSwitch = document.getElementById('noTMSwitch');
    if (trademarkSwitch) {
        trademarkSwitch.checked = false;
        toggleArticleTrademarkField(trademarkSwitch, 'trademark');
    } else {
        $('#trademark').val('');
    }

    const fullNameSwitch = document.getElementById('fullNameExtraSwitch');
    if (fullNameSwitch) {
        fullNameSwitch.checked = false;
        toggleToysFullNameExtra(fullNameSwitch);
    } else {
        updateToysFullName();
    }

    const modelArticleSwitch = document.getElementById('noModelArticleSwitch');
    if (modelArticleSwitch) {
        modelArticleSwitch.checked = false;
        toggleToysModelArticleField(modelArticleSwitch);
    }

    const rdSwitch = document.getElementById('has-rd-switch');
    if (rdSwitch) {
        rdSwitch.checked = false;
        if (typeof cosmeticsApplyRdState === 'function') {
            cosmeticsApplyRdState(false);
        }
    }

    toys_clear_tnved_feedback();
    toysUpdateCategoryCodeByTnved();
    const tnvedEl = document.getElementById('tnved_code');
    if (tnvedEl && tnvedEl.value) {
        toys_check_tnved();
    }
}

function toys_load_upload_table(url) {
    const pos_form = document.getElementById('form_process_main');
    const formData = new FormData(pos_form);
    formData.set('after_add_go_to_step3', '1');
    const generatedFullNameEl = document.getElementById('generated_full_name');
    const trademarkEl = document.getElementById('trademark');
    const messageSubject = (generatedFullNameEl && generatedFullNameEl.textContent.trim())
        || (trademarkEl && trademarkEl.value.trim())
        || 'товар';

    fetch(url, {
        method: 'POST',
        body: formData
    })
        .then((response) => response.json())
        .then((data) => {
            close_Loading_circle();
            if (data.status === 'success') {
                $('#step-3_update').html(data.htmlresponse);
                $('#orders_pos_count').text(data.orders_pos_count);
                $('#orders_row_count').text(data.pos_count);
                $('#modal_orders_pos_count').html(`<span>${data.orders_pos_count}</span>шт.`);
                let actionText = 'добавлена';
                if (window.location.pathname.includes('/edit_order')) {
                    actionText = 'изменена';
                } else if (window.location.pathname.includes('/copy_order/')) {
                    actionText = 'скопирована';
                }
                make_message(`Позиция ${messageSubject} успешно ${actionText}`, 'success');
                toys_clear_pos();
                if (typeof window.runPendingStep3TransitionAfterAsyncAdd === 'function') {
                    window.runPendingStep3TransitionAfterAsyncAdd();
                }
            } else {
                if (typeof window.clearPendingStep3TransitionAfterAsyncAdd === 'function') {
                    window.clearPendingStep3TransitionAfterAsyncAdd();
                }
                clear_errorform();
                show_form_errors([data.message || 'Не удалось добавить позицию']);
                $('#form_errorModal').modal('show');
            }
        })
        .catch(() => {
            close_Loading_circle();
            if (typeof window.clearPendingStep3TransitionAfterAsyncAdd === 'function') {
                window.clearPendingStep3TransitionAfterAsyncAdd();
            }
            clear_errorform();
            show_form_errors(['Не удалось добавить позицию']);
            $('#form_errorModal').modal('show');
        });
}

async function toys_update_table(page) {
    const response = await fetch(page);
    const data = await response.json();
    if (data.status === 'success') {
        $('#step-3_update').html(data.htmlresponse);
    }
}

document.addEventListener('DOMContentLoaded', function () {
    initToysCategorySearch();
    const okpd2El = document.getElementById('okpd2_code');
    const fullNameSwitch = document.getElementById('fullNameExtraSwitch');
    const noModelArticleSwitch = document.getElementById('noModelArticleSwitch');
    if (fullNameSwitch) {
        toggleToysFullNameExtra(fullNameSwitch);
    }
    if (noModelArticleSwitch) {
        const modelArticleEl = document.getElementById('model_article');
        noModelArticleSwitch.checked = noModelArticleSwitch.checked || toysIsNoModelArticleValue(modelArticleEl ? modelArticleEl.value : '');
        toggleToysModelArticleField(noModelArticleSwitch);
    }
    if (okpd2El) {
        toysRefreshOkpd2State();
    }
    toysUpdateCategoryCodeByTnved();
    updateToysFullName();
});
