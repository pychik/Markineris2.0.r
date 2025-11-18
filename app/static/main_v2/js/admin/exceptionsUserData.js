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

        // === Валидация телефона ===
    function validatePhoneInput(input) {
        // Разрешаем только цифры, тире, пробелы и скобки
        let v = input.value.replace(/[^0-9()+\-\s]/g, '');

        // Ограничиваем длину до 20 символов
        if (v.length > 20) {
            v = v.substring(0, 20);
        }

        input.value = v;
    }

    // === Валидация ИНН ===
    function validateIdnInput(input) {
        let v = input.value;

        // Только цифры
        v = v.replace(/\D/g, '');

        // Ограничение длины (макс 12 цифр)
        if (v.length > 12) {
            v = v.substring(0, 12);
        }

        input.value = v;
    }