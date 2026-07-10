const RD_CHECK_POLL_INTERVAL_MS = 1500;
const RD_CHECK_POLL_TIMEOUT_MS = 90000;
const RD_CHECK_HEALTH_INTERVAL_MS = 15000;

const RD_CHECK_VERDICT_LABELS = {
    active: {text: 'РД действителен', color: 'success'},
    expired: {text: 'РД недействителен: истёк срок действия', color: 'warning'},
    not_found: {text: 'РД недействителен: не найден в реестре', color: 'secondary'},
    tnved_mismatch: {text: 'РД действителен, но ТНВЭД не совпадает — выберите подходящий ТНВЭД', color: 'warning'},
    country_mismatch: {text: 'РД действителен, но страна не совпадает — выберите подходящую страну', color: 'warning'},
    error: {text: 'РД недействителен: ошибка проверки', color: 'danger'}
};

const RD_CHECK_HEALTH_LABELS = {
    closed: {text: 'работает', color: 'success'},
    half_open: {text: 'проверяется', color: 'warning'},
    open: {text: 'недоступна', color: 'danger'}
};

const RD_CHECK_STATUS_LABELS = {
    queued: 'в очереди',
    processing: 'выполняется'
};

const RD_CHECK_GATE_POLL_MS = 300;

function rdCheckBadgeHtml(text, color) {
    return '<span class="badge badge-soft bg-' + color + ' bg-opacity-10 text-' + color + '">' + text + '</span>';
}

function rdCheckStartFieldGate() {
    rdCheckSyncGate();
    setInterval(rdCheckSyncGate, RD_CHECK_GATE_POLL_MS);
}

function rdCheckSyncGate() {
    var type = document.getElementById('type').value;
    var gender = document.getElementById('gender').value;
    var tnved = document.getElementById('tnved_code').value;
    var country = document.getElementById('country').value;
    var ready = !!(type && gender && tnved && country);

    var rdType = document.getElementById('rd_type');
    var rdName = document.getElementById('rd_name');

    if (rdType.disabled === ready) {
        rdType.disabled = !ready;
        rdName.disabled = !ready;
    }
}

function rdCheckValidateFields() {
    const fields = [
        {id: 'type', label: 'Вид одежды'},
        {id: 'gender', label: 'Пол'},
        {id: 'tnved_code', label: 'ТНВЭД'},
        {id: 'country', label: 'Страна'},
        {id: 'rd_type', label: 'Тип документа'},
        {id: 'rd_name', label: 'Номер документа'}
    ];

    const missing = fields
        .filter(function (f) {
            var el = document.getElementById(f.id);
            return !el || !el.value || !el.value.trim();
        })
        .map(function (f) {
            return f.label;
        });

    return missing;
}

function rdCheckSubmit(submitUrl, statusUrlTemplate, csrf) {
    var missing = rdCheckValidateFields();
    if (missing.length) {
        show_form_errors(missing.map(function (label) {
            return 'Заполните поле: ' + label;
        }));
        $('#form_errorModal').modal('show');
        return;
    }

    var docType = document.getElementById('rd_type').value;
    var number = document.getElementById('rd_name').value.trim();
    var productType = document.getElementById('type').value;
    var gender = document.getElementById('gender').value;
    var tnvedCode = document.getElementById('tnved_code').value;
    var country = document.getElementById('country').value;
    var resultBlock = document.getElementById('rdCheckResult');
    var submitBtn = document.getElementById('rdCheckSubmitBtn');

    submitBtn.disabled = true;
    rdCheckRenderPending(resultBlock, 'Запрос поставлен в очередь...');

    $.ajax({
        url: submitUrl,
        method: 'POST',
        headers: {"X-CSRFToken": csrf},
        data: {
            doc_type: docType,
            number: number,
            type: productType,
            gender: gender,
            tnved_code: tnvedCode,
            country: country
        },
        success: function (data) {
            rdCheckPollStatus(statusUrlTemplate.replace('__id__', data.request_id), Date.now(), submitBtn);
        },
        error: function (xhr) {
            submitBtn.disabled = false;
            var message = (xhr.responseJSON && xhr.responseJSON.message) || 'Ошибка отправки запроса';
            rdCheckRenderMessage(resultBlock, message, 'danger');
        }
    });
}

function rdCheckRenderPending(resultBlock, text) {
    resultBlock.innerHTML = '<div class="card bg-transparent"><div class="card-body d-flex align-items-center gap-3">' +
        '<div class="spinner-border spinner-border-sm text-warning" role="status"></div>' +
        '<span>' + text + '</span></div></div>';
}

function rdCheckRenderMessage(resultBlock, text, color) {
    resultBlock.innerHTML = '<div class="card bg-transparent"><div class="card-body">' +
        rdCheckBadgeHtml(text, color) + '</div></div>';
}

function rdCheckPollStatus(statusUrl, startedAt, submitBtn) {
    var resultBlock = document.getElementById('rdCheckResult');

    $.ajax({
        url: statusUrl,
        method: 'GET',
        success: function (data) {
            if (data.status === 'queued' || data.status === 'processing') {
                if (Date.now() - startedAt > RD_CHECK_POLL_TIMEOUT_MS) {
                    submitBtn.disabled = false;
                    rdCheckRenderMessage(resultBlock, 'Превышено время ожидания ответа. Попробуйте ещё раз позже.', 'warning');
                    return;
                }
                var statusLabel = RD_CHECK_STATUS_LABELS[data.status] || data.status;
                rdCheckRenderPending(resultBlock, 'Проверка ' + statusLabel + '...');
                setTimeout(function () {
                    rdCheckPollStatus(statusUrl, startedAt, submitBtn);
                }, RD_CHECK_POLL_INTERVAL_MS);
                return;
            }

            submitBtn.disabled = false;

            if (data.status === 'error') {
                rdCheckRenderMessage(resultBlock, data.error || 'Неизвестная ошибка', 'danger');
                return;
            }

            rdCheckRenderResult(data);
        },
        error: function () {
            submitBtn.disabled = false;
            rdCheckRenderMessage(resultBlock, 'Ошибка получения статуса проверки', 'danger');
        }
    });
}

function rdCheckContextHtml(data) {
    return '<table class="table table-sm table-borderless mb-3 text-muted">' +
        '<tr><th class="fw-normal">Вид товара</th><td>' + (data.product_type || '') + '</td></tr>' +
        '<tr><th class="fw-normal">Пол</th><td>' + (data.gender || '') + '</td></tr>' +
        '<tr><th class="fw-normal">ТНВЭД</th><td>' + (data.tnved_code || '') + '</td></tr>' +
        '<tr><th class="fw-normal">Страна</th><td>' + (data.country || '') + '</td></tr>' +
        '<tr><th class="fw-normal">Документ</th><td>' + (data.number || '') + '</td></tr>' +
        '</table>';
}

function rdCheckRenderResult(data) {
    var resultBlock = document.getElementById('rdCheckResult');
    var result = data.result;

    if (!result) {
        rdCheckRenderMessage(resultBlock, 'Пустой результат проверки', 'danger');
        return;
    }

    var verdict = RD_CHECK_VERDICT_LABELS[result.verdict] || {text: result.verdict, color: 'secondary'};
    var html = '<div class="card bg-transparent"><div class="card-body">';
    html += rdCheckContextHtml(data);
    html += '<div class="mb-3">' + rdCheckBadgeHtml(verdict.text, verdict.color) + '</div>';

    if (!result.ok) {
        html += '<p class="text-muted mb-0">' + (result.error || '') + '</p>';
        html += '</div></div>';
        resultBlock.innerHTML = html;
        return;
    }

    if (result.data) {
        var rdTnveds = (result.data.tnved_codes || []).join(', ');
        var tnvedRowClass = result.verdict === 'tnved_mismatch' ? ' class="table-warning"' : '';
        var countryRowClass = result.verdict === 'country_mismatch' ? ' class="table-warning"' : '';
        html += '<table class="table table-bordered mb-0">' +
            '<tr><th>Номер</th><td>' + (result.data.number || '') + '</td></tr>' +
            '<tr><th>Заявитель</th><td>' + (result.data.applicant || '') + '</td></tr>' +
            '<tr><th>Изготовитель</th><td>' + (result.data.manufacturer || '') + '</td></tr>' +
            '<tr><th>Товар</th><td>' + (result.data.product || '') + '</td></tr>' +
            '<tr><th>Дата регистрации</th><td>' + (result.data.reg_date || '') + '</td></tr>' +
            '<tr><th>Действует до</th><td>' + (result.data.end_date || '') + '</td></tr>' +
            '<tr' + tnvedRowClass + '><th>ТНВЭД по РД</th><td>' + (rdTnveds || 'нет данных') + '</td></tr>' +
            '<tr' + countryRowClass + '><th>Страна по РД</th><td>' + (result.data.country || 'нет данных') + '</td></tr>' +
            '</table>';
    }

    html += '</div></div>';
    resultBlock.innerHTML = html;
}

function rdCheckStartHealthPolling(healthUrl) {
    rdCheckRefreshHealth(healthUrl);
    setInterval(function () {
        rdCheckRefreshHealth(healthUrl);
    }, RD_CHECK_HEALTH_INTERVAL_MS);
}

function rdCheckRefreshHealth(healthUrl) {
    var badge = document.getElementById('rdCheckHealthBadge');

    $.ajax({
        url: healthUrl,
        method: 'GET',
        success: function (data) {
            var label = RD_CHECK_HEALTH_LABELS[data.circuit_state] || {text: data.circuit_state, color: 'secondary'};
            badge.textContent = label.text + ' · в очереди: ' + data.queue_length;
            badge.className = 'badge badge-soft bg-' + label.color + ' bg-opacity-10 text-' + label.color;
        },
        error: function () {
            badge.textContent = 'нет данных';
            badge.className = 'badge badge-soft bg-secondary bg-opacity-10 text-secondary';
        }
    });
}
