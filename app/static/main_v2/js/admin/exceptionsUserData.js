// универсальная отправка ajax-запроса
    function sendExceptionRequest(url, data, onSuccess) {
        $.ajax({
            url: url,
            type: "POST",
            data: data,
            success: function (resp) {
                if (resp.status === 'success') {
                    if (typeof onSuccess === 'function') {
                        onSuccess(resp);
                    }
                    if (typeof make_message === 'function') {
                        make_message(resp.message || 'Успешно', 'success');
                    } else {
                        console.log(resp.message || 'Успешно');
                    }
                } else {
                    if (typeof make_message === 'function') {
                        make_message(resp.message || 'Ошибка', 'error');
                    } else {
                        console.error(resp.message || 'Ошибка');
                    }
                }
            },
            error: function () {
                if (typeof make_message === 'function') {
                    make_message('Ошибка запроса', 'error');
                } else {
                    console.error('Ошибка запроса');
                }
            }
        });
    }

    // ==================== ИНН ====================

    // добавление ИНН
    $(document).on('submit', '#form-add-company-idn', function (e) {
        e.preventDefault();
        const $form = $(this);
        const action = $form.attr('action');

        sendExceptionRequest(action, $form.serialize(), function (resp) {
            // обновляем только левый блок с ИНН
            $('#col-company-idns').html(resp.html);
        });
    });

    // удаление ИНН
    $(document).on('click', '.btn-del-company-idn', function (e) {
        e.preventDefault();
        const url = $(this).data('url');
        const csrf = $(this).data('csrf');

        sendExceptionRequest(url, {csrf_token: csrf}, function (resp) {
            $('#col-company-idns').html(resp.html);
        });
    });

    // ==================== ТЕЛЕФОНЫ ====================

    // добавление телефона
    $(document).on('submit', '#form-add-phone', function (e) {
        e.preventDefault();
        const $form = $(this);
        const action = $form.attr('action');

        sendExceptionRequest(action, $form.serialize(), function (resp) {
            // обновляем только правый блок с телефонами
            $('#col-phones').html(resp.html);
        });
    });

    // удаление телефона
    $(document).on('click', '.btn-del-phone', function (e) {
        e.preventDefault();
        const url = $(this).data('url');
        const csrf = $(this).data('csrf');

        sendExceptionRequest(url, {csrf_token: csrf}, function (resp) {
            $('#col-phones').html(resp.html);
        });
    });

    // ==================== если нужно перезагружать целиком блоки ====================
    // можно сделать вспомогательную функцию
    function reloadExceptionBlock(kind) {
        // если когда-нибудь сделаешь эндпоинт типа /exceptions/<kind>/list (GET),
        // то его можно будет дергать отсюда и обновлять часть страницы.
    }

     const TEXTAREA_LIMIT = 1500;

    // ================ Общие нормализаторы ================

    function normalizeIdnValue(v) {
        v = v.replace(/\D/g, '');
        if (v.length > 12) v = v.substring(0, 12);
        return v;
    }

    function normalizePhoneValue(v) {
        v = v.replace(/[^0-9()+\-\s]/g, '');
        if (v.length > 20) v = v.substring(0, 20);
        return v;
    }

    // ================ Single-line функции ================

    function validatePhoneInput(input) {
        input.value = normalizePhoneValue(input.value);
    }

    function validateIdnInput(input) {
        input.value = normalizeIdnValue(input.value);
    }

    // ================ Новый функционал для textarea ================

    function enforceTextareaLimit(input) {
        if (input.value.length > TEXTAREA_LIMIT) {
            input.value = input.value.substring(0, TEXTAREA_LIMIT);
        }
    }

    // ИНН textarea
    function validateInnTextarea(input) {
        enforceTextareaLimit(input);

        let raw = input.value;
        raw = raw.replace(/[^0-9,\n; ]/g, '');

        const parts = raw.split(/[,;\n]+/);
        const cleaned = [];

        for (let p of parts) {
            p = p.trim();
            if (!p) continue;

            p = normalizeIdnValue(p);
            if (p) cleaned.push(p);
        }

        let result = cleaned.join('\n');

        if (result.length > TEXTAREA_LIMIT) {
            result = result.substring(0, TEXTAREA_LIMIT);
        }

        input.value = result;
    }

    // Телефоны textarea
    function validatePhoneTextarea(input) {
        enforceTextareaLimit(input);

        let raw = input.value;
        raw = raw.replace(/[^\d()+\-\s,;\n]/g, '');

        const parts = raw.split(/[,;\n]+/);
        const cleaned = [];

        for (let p of parts) {
            p = p.trim();
            if (!p) continue;

            p = normalizePhoneValue(p);
            if (p) cleaned.push(p);
        }

        let result = cleaned.join('\n');

        if (result.length > TEXTAREA_LIMIT) {
            result = result.substring(0, TEXTAREA_LIMIT);
        }

        input.value = result;
    }