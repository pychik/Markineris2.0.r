function copy_buffer(element_id, message_id) {
    var data = document.getElementById(element_id);
    var mes = document.getElementById(message_id)
    data.focus()
    data.select();
    data.setSelectionRange(0, 99999);

    try {
        document.execCommand('copy');
        mes.innerHTML = 'ссылка скопирована';

    } catch (err) {
        alert('ошибка')
        mes.innerHTML = 'Копирование не удалось. Попробуйте выделить и скопировать.';
    }

    setInterval(clear_message_copy_admin, 3000, message_id);
}

function clear_message_copy_admin(el_message_id) {

    var mes = document.getElementById(el_message_id)
    mes.innerHTML = '';

}

function wait(ms) {
    var start = new Date().getTime();
    var end = start;
    while (end < start + ms) {
        end = new Date().getTime();
    }
}


//     #### finance_control ####
function update_finance_control(category_p, btn) {
    var tooltipInstance = bootstrap.Tooltip.getInstance(btn);
    if (tooltipInstance) {
    tooltipInstance.hide();
    }

    if (document.getElementById(`pills-service_accounts`)) {
        document.getElementById(`pills-service_accounts`).classList.remove('active');
    }
    if (document.getElementById(`pills-promos`)) {
        document.getElementById(`pills-promos`).classList.remove('active');
    }
    if (document.getElementById(`pills-bonuses`)) {
        document.getElementById(`pills-bonuses`).classList.remove('active');
    }
    if (document.getElementById(`pills-prices`)) {
        document.getElementById(`pills-prices`).classList.remove('active');
    }
    document.getElementById('service_accounts_block').style.display = 'none';
    document.getElementById('promos_block').style.display = 'none';
    document.getElementById('bonuses_block').style.display = 'none';
    document.getElementById('prices_block').style.display = 'none';


    document.getElementById(`pills-${category_p}`).classList.add('active');
    document.getElementById(`${category_p}_block`).style.removeProperty('display')
}


function get_promos_history(url) {
    let show_archived = document.getElementById('show_archived_promo').checked

    $.ajax({
        url: url,
        method: "GET",
        data: {
            'show_archived': show_archived
        },

        success: function (data) {

            $('#promos_table').html(data);
            $("#promos_table").append(data.htmlresponse);
            toggleArchivedColumn(show_archived, 'promos_table', 'show_archived_promo');
        }
    });

}

function check_promo_form() {
    let form = document.getElementById('promo_form')
    // console.log(form.reportValidity());
    if (!form.checkValidity || form.checkValidity()) {
        return true
    } else {
        var allInputs = $('#promo_form input');

        allInputs.each(function (index) {
            // console.log(allInputs[index]);
            check_valid(allInputs[index]);
        })
        return false
    }
}

async function bck_delete_promo(url, csrf, update_url) {

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
        const data_r = await fetchResponse;
        if (data_r.status >= 400) {
            // console.log(data_r.status);
            make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');
            return false
        }
        const data = await data_r.json();
        // console.log(data.status)
        if (data.status === 'success') {
            get_promos_history(update_url)
        }

        make_message(data.message, data.status);
        setTimeout(function () {
            clear_user_messages();
        }, 15000);
        return true


    } catch (e) {
        console.log(e)

        return false;
    }
}

function bck_add_promo(url, update_url) {
    var form = $("#promo_form").serialize();

    $.ajax({
        url: url,
        // headers:{"X-CSRFToken": csrf},
        method: "POST",
        data: form,
        success: function (data) {
            // console.log(data);

            if (data.status === 'success') {
                get_promos_history(update_url);
            }

            make_message(data.message, data.status);
        },
        error: function () {
            make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');
        }
    });

    setTimeout(function () {
        clear_user_messages();
    }, 15000);
}

function get_bonuses_history(url) {
    let show_archived = document.getElementById('show_archived_bonuses').checked

    $.ajax({
        url: url,
        method: "GET",
        data: {
            'show_archived': show_archived
        },

        success: function (data) {

            $('#bonuses_table').html(data);
            $("#bonuses_table").append(data.htmlresponse);
            toggleArchivedColumn(show_archived, 'bonuses_table', 'show_archived_bonuses');
        }
    });

}

function toggleArchivedColumn(show, table_id, show_archived_id) {
    const table = document.getElementById(table_id);
    const archivedColumns = table.querySelectorAll('.archived-column');
    archivedColumns.forEach(column => {
        column.style.display = show ? '' : 'none';
    });
    let show_archived = document.getElementById(show_archived_id);
    if (show_archived.checked === true)
    {show_archived.classList.add('bg-warning')}
    else
    {show_archived.classList.remove('bg-warning')}
    show_archived.blur()
}

function check_bonuses_form() {
    let form = document.getElementById('bonus_form')
    // console.log(form.reportValidity());
    if (!form.checkValidity || form.checkValidity()) {
        return true
    } else {
        var allInputs = $('#bonus_form input');

        allInputs.each(function (index) {
            // console.log(allInputs[index]);
            check_valid(allInputs[index]);
        })
        return false
    }
}

async function bck_delete_bonus(url, csrf, update_url) {

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
        const data_r = await fetchResponse;
        if (data_r.status >= 400) {
            // console.log(data_r.status);
            make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');
            return false
        }
        const data = await data_r.json();
        // console.log(data.status)
        if (data.status === 'success') {
            get_bonuses_history(update_url)
        }

        make_message(data.message, data.status);
        setTimeout(function () {
            clear_user_messages();
        }, 15000);
        return true


    } catch (e) {
        console.log(e)

        return false;
    }
}

function bck_add_bonus(url, update_url) {
    var form = $("#bonus_form").serialize();

    $.ajax({
        url: url,
        // headers:{"X-CSRFToken": csrf},
        method: "POST",
        data: form,
        success: function (data) {
            // console.log(data);

            if (data.status === 'success') {
                get_bonuses_history(update_url);
            }

            make_message(data.message, data.status);
        },
        error: function () {
            make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');
        }
    });

    setTimeout(function () {
        clear_user_messages();
    }, 15000);
}

function check_price_switch() {
    let pat2 = document.getElementById("price_at2");
    // console.log(pat2.checked);
    if (pat2.checked === true) {
        pat2.classList.add("bg-warning");
        document.getElementById("label_price_at2").innerHTML = 'Агент <b>единый счет</b';
    } else {
        pat2.classList.remove("bg-warning");
        document.getElementById("label_price_at2").innerHTML = '<b>Обычный</b> агент';
    }
}

function check_prices_form(form_id) {
    let form = document.getElementById(form_id);
    return !!form.reportValidity();
}

function get_prices_history(url) {
    $.ajax({
        url: url,
        method: "GET",

        success: function (data) {
            $('#prices_table').html(data);
            $("#prices_table").append(data.htmlresponse);
        }
    });

}

function bck_add_price(url, update_url) {
    var form = $("#prices_form").serialize();
    // console.log(form.csrf_token);
    $.ajax({
        url: url,
        // headers:{"X-CSRFToken": form.csrf_token},
        method: "POST",
        data: form,
        success: function (data) {
            // console.log(data);

            if (data.status === 'success') {
                get_prices_history(update_url);
            }

            make_message(data.message, data.status);
        },
        error: function () {
            make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');
        }
    });

    setTimeout(function () {
        clear_user_messages();
    }, 15000);
}

function check_price_at2_and_replace_price_text(price_row, p_code) {
    if (price_row[2] === 'True' && price_row[1] !== p_code) {
        return `<option value="${price_row[0]}">${price_row[1]} - Агенты единый счет</option>`
    } else if (price_row[1] !== p_code) {
        return `<option value="${price_row[0]}">${price_row[1]}</option>`
    } else {
        return ''
    }
}

function bck_delete_replace_price(url, csrf, update_url, p_code) {
    let modal_block = document.getElementById('service_prices_modal');

    var option_prices = '<option value="">BASIC</option>'

    prices_array.forEach((element) => {
        option_prices += `${check_price_at2_and_replace_price_text(element, p_code)}`
    });

    let user_price_form = `<form id="service_price_replace_form" action="${url}" class="text-center">
                            <input type="hidden" name="csrf_token" value="${csrf}">
                            <label for="price_id">Выберите ценовой пакет на замену тому, что удаляете!</label>
                            <select class="form-select my-1" id="price_id" name="price_id">
                                ${option_prices}
                            </select>
                             <button type="button" class="btn btn-sm btn-accent" style="width: 100%" data-bs-dismiss="modal" onclick="bck_delete_price_post_process('${url}', '${update_url}');clear_modal_service_prices();">Удалить и обновить</button>
                        </form>`

    modal_block.innerHTML = `<div class="modal fade" id="service_priceModal" tabindex="-1" role="dialog" data-bs-backdrop="static" aria-labelledby="service_priceModalLabel" aria-hidden="true">
          <div class="modal-dialog" data-backdrop="static" role="document">
            <div class="modal-content">
              <div class="modal-header">
                <h5 class="modal-title" id="service_priceModalLabel">Форма удаления ценового пакета ${p_code}.</h5>
                <button type="button" class="btn-close" onclick="clear_modal_service_prices();" data-bs-dismiss="modal" aria-label="Close">
                </button>
              </div>
              <div class="modal-body">
                  <div class="row">
                      <div class="col-2"></div>
                      <div class="col-8">
                        ${user_price_form}
                      </div>
                  </div>
                  <div class="col text-justify">
                        <small class="text-secondary small">Вы можете выбрать ценовой пакет на замену (для пользователей пользовавшимся удаляемым ценовым пакетом),
                                после этого <b>Нажмите Удалить и обновить</b>. Либо нажмите Закрыть.
                        </small>
                  </div>
              </div>
              
              <div class="modal-footer">
                <button type="button" class="btn btn-secondary" onclick="clear_modal_service_prices();" data-bs-dismiss="modal">Закрыть</button>

              </div>
            </div>
          </div>
        </div>`;
    $("#service_priceModal").modal("show");
}

function bck_delete_price_post_process(url, update_url) {
    var form = $("#service_price_replace_form").serialize();
    $.ajax({
        url: url,
        // headers:{"X-CSRFToken": form.csrf_token},
        method: "POST",
        data: form,
        success: function (data) {
            // console.log(data);

            if (data.status === 'success') {
                get_prices_history(update_url);
            }

            make_message(data.message, data.status);
        },
        error: function () {
            make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');
        }
    });

    setTimeout(function () {
        clear_user_messages();
    }, 15000);
}

function bck_edit_price_get_process(url) {
    $.ajax({
        url: url,
        // headers:{"X-CSRFToken": form.csrf_token},
        method: "GET",
        success: function (data) {
            // console.log(data);

            if (data.status === 'success') {
                document.getElementById('service_prices_modal').innerHTML = data.htmlresponse;
                $('#service_priceModal').modal('show');
            }
            else {
                make_message(data.message, data.status);
            }
        },
        error: function () {
            make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');
        }
    });

    setTimeout(function () {
        clear_user_messages();
    }, 15000);
}


function bck_edit_price_post_process(url, update_url) {
    var form = $("#service_price_edit_form").serialize();
    $.ajax({
        url: url,
        // headers:{"X-CSRFToken": form.csrf_token},
        method: "POST",
        data: form,
        success: function (data) {
            // console.log(data);

            if (data.status === 'success') {
                get_prices_history(update_url);
            }
            $('#service_priceModal').modal('hide');
            clear_modal_service_prices();
            make_message(data.message, data.status);
        },
        error: function () {
            make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');
        }
    });

    setTimeout(function () {
        clear_user_messages();
    }, 15000);
}

function clear_modal_service_prices() {
    document.getElementById("service_prices_modal").innerHTML = '';
}


function get_not_basic_prices_report(url, csrf_token, btn) {
    var tooltipInstance = bootstrap.Tooltip.getInstance(btn);
    if (tooltipInstance) {
    tooltipInstance.hide();
    }

    $.ajax({
        url: url,
        headers: { "X-CSRFToken": csrf_token },
        method: "POST",
        xhrFields: {
            responseType: 'blob' // Set response type to blob
        },

        success: function(response, status, xhr) {
            $('#overlay_loading').hide();
            if (xhr.status === 200) {
                var blob = new Blob([response], { type: 'application/xlsx' });
                var link = document.createElement('a');

                var dataName = xhr.getResponseHeader('data_file_name');

                link.href = window.URL.createObjectURL(blob);
                // console.log()
                link.download = decodeURIComponent(dataName) || 'Отчет по ценам.xlsx'; //
                link.click();
            } else {
                // Handle other status codes
                console.error('Error:', xhr.status);
            }
        },
        error: function(xhr, status, error) {
            $('#overlay_loading').hide();
            // Error handling
            console.error('Error:', error);
        }
    });
}


function get_marks_count_report(url, csrf_token, btn) {
    var tooltipInstance = bootstrap.Tooltip.getInstance(btn);

    if (tooltipInstance) {
    tooltipInstance.hide();
    }

    $.ajax({
        url: url,
        headers: { "X-CSRFToken": csrf_token },
        method: "POST",
        xhrFields: {
            responseType: 'blob' // Set response type to blob
        },

        success: function(response, status, xhr) {
            $('#overlay_loading').hide();
            if (xhr.status === 200) {
                var blob = new Blob([response], { type: 'application/xlsx' });
                var link = document.createElement('a');

                var dataName = xhr.getResponseHeader('data_file_name');

                link.href = window.URL.createObjectURL(blob);
                // console.log()
                link.download = decodeURIComponent(dataName) || 'Отчет по ценам.xlsx'; //
                link.click();
            } else {
                // Handle other status codes
                console.error('Error:', xhr.status);
            }
        },
        error: function(xhr, status, error) {
            $('#overlay_loading').hide();
            // Error handling
            console.error('Error:', error);
        }
    });
}

function check_sa_form() {
    let form = document.getElementById('service_account_form');
    let accountType = document.getElementById('sa_type')?.value;
    let saName = document.getElementById('sa_name')?.value;

    let errors_list = [];

    if (!saName || saName.length < 3 || saName.length > 100) {
        errors_list.push("Введите корректное наименование счета (от 3 до 100 символов)!");
    }

    if (!accountType) {
        errors_list.push("Укажите тип счета!");
    } else if (accountType === "requisites") {
        const validationResult = validateAllFields();
        if (!validationResult.isValid) {
            errors_list.push(...validationResult.errors);
        }
    } else if (accountType === "qr_code") {
        let qrFile = document.getElementById('sa_qr_file');
        if (!qrFile.value) {
            errors_list.push("Загрузите файл QR-кода!");
        }
    } else if (accountType === "external_payment") {
    let outerPaymentField = document.getElementById('outer_payment_req');
    if (!outerPaymentField || !outerPaymentField.value.trim()) {
        errors_list.push("Введите реквизиты для внешнего платежа (минимум 10 символов)!");
    } else if (outerPaymentField.value.trim().length < 10) {
        errors_list.push("Реквизиты для внешнего платежа должны содержать не менее 10 символов!");
    }
}

    if (errors_list.length > 0) {
        show_form_errors(errors_list);
        $('#form_errorModal').modal('show');
        return false;
    }

    return true;
}



function handleInputChange(event) {
    const input = event.target;
    const pattern = input.getAttribute('pattern');

    validateField(input, pattern);

    updateSaReq();
}

function validateField(input, pattern = null) {
    if (input.required && !input.value.trim()) {
        input.classList.add('is-invalid');
        input.classList.remove('is-valid');
        return false;
    }

    if (pattern && !new RegExp(pattern).test(input.value.trim())) {
        input.classList.add('is-invalid');
        input.classList.remove('is-valid');
        return false;
    }

    input.classList.add('is-valid');
    input.classList.remove('is-invalid');
    return true;
}


function validateAllFields() {
    const bankName = document.getElementById('bank_name');
    const cardNumber = document.getElementById('card_number');
    const phoneNumber = document.getElementById('phone_number');
    const fio = document.getElementById('fio');
    const sbp = document.getElementById('sbp');

    let isValid = true;
    let errors = [];


    if (!validateField(bankName)) {
        isValid = false;
        errors.push('Пожалуйста, заполните поле: НАЗВАНИЕ БАНКА.');
    }

    if (!validateField(fio)) {
        isValid = false;
        errors.push('Пожалуйста, заполните поле: ФИО.');
    }

    const isCardNumberValid = cardNumber.value.trim() ? validateField(cardNumber) : false;
    const isPhoneNumberValid = phoneNumber.value.trim() ? validateField(phoneNumber) : false;
    const isSbpValid = sbp.value.trim() ? validateField(sbp) : false;

    if (!isCardNumberValid && !isPhoneNumberValid && !isSbpValid) {
        isValid = false;
        errors.push('Заполните хотя бы одно из полей: НОМЕР КАРТЫ, НОМЕР ТЕЛЕФОНА или СБП.');
    }

    [cardNumber, phoneNumber, sbp].forEach(input => {
        if (!input.value.trim()) {
            input.classList.remove('is-valid');
            input.classList.add('is-invalid');
        }
    });

    return { isValid, errors };
}


function updateSaReq() {
    const bankName = document.getElementById('bank_name').value.trim();
    const cardNumber = document.getElementById('card_number').value.trim();
    const phoneNumber = document.getElementById('phone_number').value.trim();
    const fio = document.getElementById('fio').value.trim();
    const sbp = document.getElementById('sbp').value.trim();
    const saReqField = document.getElementById('sa_req');
    const saReqPreview = document.getElementById('sa_req_preview');

    if (!bankName || !fio) {
        saReqField.value = '';
        saReqPreview.innerHTML = '';
        return;
    }

    let saReqText = `<h2 class="btn-accent faded">${bankName}</h2>`;
    if (cardNumber) saReqText += `НОМЕР КАРТЫ: ${cardNumber}<br>`;
    saReqText += `ПОЛУЧАТЕЛЬ: ${fio}<br>`;
    if (phoneNumber) saReqText += `Номер телефона: ${phoneNumber}<br>`;
    if (sbp) saReqText += `СБП: ${sbp}`;

    saReqField.value = saReqText;
    saReqPreview.innerHTML = saReqText;
}


function sa_form_update_type() {
    let sa_type = document.getElementById('sa_type').value;

    if (sa_type === 'qr_code') {
        // QR-код блок
        document.getElementById('req_block').style.display = 'none';
        document.getElementById('outer_payment_block').style.display = 'none';
        document.getElementById('sa_req').disabled = true;

        document.getElementById('qr_img_block').style.removeProperty('display');
        document.getElementById('sa_qr_file').disabled = false;
    } else if (sa_type === 'external_payment') {
        // Внешний платежный блок
        document.getElementById('qr_img_block').style.display = 'none';
        document.getElementById('sa_qr_file').disabled = true;

        document.getElementById('req_block').style.display = 'none';
        document.getElementById('outer_payment_block').style.removeProperty('display');
        document.getElementById('sa_req').disabled = false;
    } else {
        // Реквизиты блок
        document.getElementById('qr_img_block').style.display = 'none';
        document.getElementById('sa_qr_file').disabled = true;

        document.getElementById('outer_payment_block').style.display = 'none';
        document.getElementById('req_block').style.removeProperty('display');
        document.getElementById('req_block').classList.remove('is-valid');
        document.getElementById('sa_req').disabled = false;
    }
}


function get_sa_history(url) {
    let show_archived = document.getElementById('show_archived_service_accounts').checked

    $.ajax({
        url: url,
        method: "GET",
        data: {
            'show_archived': show_archived
        },

        success: function (data) {

            $('#sa_table').html(data);
            $("#sa_table").append(data.htmlresponse);
            toggleArchivedColumn(show_archived, 'sa_table', 'show_archived_service_accounts');
        }
    });
}


async function bck_delete_sa(url, csrf, update_url) {

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
        const data_r = await fetchResponse;
        if (data_r.status >= 400) {
            // console.log(data_r.status);
            make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');
            return false
        }
        const data = await data_r.json();
        // console.log(data.status)
        if (data.status === 'success') {
            get_sa_history(update_url)
        }

        make_message(data.message, data.status);
        setTimeout(function () {
            clear_user_messages();
        }, 15000);
        return true


    } catch (e) {
        console.log(e)

        return false;
    }
}

async function bck_change_sa_activity(url, csrf, update_url, sa_id) {

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
        const data_r = await fetchResponse;
        if (data_r.status >= 400) {
            // console.log(data_r.status);
            make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');
            return false
        }
        const data = await data_r.json();
        // console.log(data.status)
        if (data.status === 'success') {
            // make style
            let sa_check_box = document.getElementById(sa_id);


            if (sa_check_box.checked) {
                sa_check_box.classList.add("bg-warning");
            } else {
                sa_check_box.classList.remove("bg-warning");
            }
        } else {
            get_sa_history(update_url)
        }

        make_message(data.message, data.status);
        setTimeout(function () {
            clear_user_messages();
        }, 15000);
        return true


    } catch (e) {
        console.log(e)

        return false;
    }
}

function bck_add_sa(url, update_url) {
    // var form_raw = $("#service_account_form").serialize();
    // var form_raw =document.getElementById('service_account_form');
    var form_raw = $("#service_account_form")
    var formData = new FormData(form_raw[0]);
    if (sa_type === 'qr_code') {
        // console.log(sa_type);
        let qr_file = document.getElementById("sa_qr_file").files[0];

        formData.append('sa_qr_file', qr_file, qr_file.name);
    }

    $.ajax({
        url: url,
        // headers:{"X-CSRFToken": form.csrf_token},
        method: "POST",
        data: formData,
        contentType: false,
        processData: false,
        cache: false,
        success: function (data) {
            // console.log(data);

            if (data.status === 'success') {
                get_sa_history(update_url);
            }

            make_message(data.message, data.status);
        },
        error: function () {
            make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');
        }
    });

    setTimeout(function () {
        clear_user_messages();
    }, 15000);
}


function bck_change_account_type(url, sa_type) {
    // var form_raw = $("#service_account_form").serialize();
    // var form_raw =document.getElementById('service_account_form');
    var form = $("#service_account_type_form").serialize()


    $.ajax({
        url: url,
        // headers:{"X-CSRFToken": form.csrf_token},
        method: "POST",
        data: form,
        success: function (data) {
            // console.log(data);

            if (data.status === 'warning') {
                document.getElementById('desc_account_type').innerHTML = data.change_block;
            } else {
                uncheck_sa_switch();
            }

            make_sa_message(data.message, data.status);
        },
        error: function () {
            make_sa_message('Ошибка CSRF. Обновите страницу и попробуйте снова');
            uncheck_sa_switch()
        }
    });

    setTimeout(function () {
        clear_sa_message();
    }, 5000);
}


function make_sa_message(message, status) {
    document.getElementById('sa_message_block').classList.remove('text-danger');
    document.getElementById('sa_message_block').classList.remove('text-warning');
    document.getElementById('sa_message_block').classList.add(`text-${status}`);
    document.getElementById('sa_message_block').innerHTML = message;
}

function clear_sa_message(message) {
    document.getElementById('sa_message_block').innerHTML = '';
}

function uncheck_sa_switch() {
    if (document.getElementById('account_type_switch').checked === true) {
        document.getElementById('account_type_switch').checked = false
    } else {
        document.getElementById('account_type_switch').checked = true
    }
}

function bck_get_transactions(url) {
    $.ajax({
        url: url,
        method: "GET",

        success: function (data) {
            $('#transactions_table').html(data);
            $("#transactions_table").append(data.htmlresponse);

        }
    });

}

function bck_get_transactions_wp(url) {
    let sort_mode = 0;
    if (document.getElementById("asc_type").checked) {
        sort_mode = 1;
    }
    $.ajax({
        url: url,
        method: "GET",
        data: {
            tr_status: $('#transaction_status').val(),
            transaction_type: $('#transaction_type').val(),
            service_account: $('#service_account').val(),
            operation_type: $('#operation_type').val(),
            date_from: $('#date_from').val(),
            date_to: $('#date_to').val(),
            amount: $('#transaction_amount').val(),
            agent_id: $('#user_filter').val(),
            sort_type: sort_mode
        },
        success: function (data) {
            $('#transactions_table').html(data);
            $("#transactions_table").append(data.htmlresponse);

        }
    });

}


function bck_get_fin_order_report(url) {
    let sort_mode = $('input[name="sort_type"]:checked').val();
    let date_from = $('#date_from').val();
    let date_to = $('#date_to').val();
    let order_type = $('input[name="order_type"]:checked').val()
    let payment_status = $('input[name="payment_status"]:checked').val()

    $.ajax({
        url: url,
        method: "GET",
        data: {
            date_from: date_from,
            date_to: date_to,
            sort_type: sort_mode,
            order_type: order_type,
            payment_status: payment_status,
        },
        success: function (data) {
            $('#orders_table').html(data);
            $("#orders_table").append(data.htmlresponse);
        }
    });
}

function bck_get_fin_codes_history(url, codes_id) {
    let sort_mode = $('input[name="sort_type"]:checked').val();
    let date_from = $('#date_from').val();
    let date_to = $('#date_to').val();
    let selectElement = document.getElementById(codes_id);
    let request_code = selectElement.value;

    $.ajax({
        url: url,
        method: "GET",
        data: {
            date_from: date_from,
            date_to: date_to,
            sort_type: sort_mode,
            promo_code: request_code,
            bonus_code: request_code,
        },
        success: function (data) {
            $('#fin_codes_history_table').html(data);
            $("#fin_codes_history_table").append(data.htmlresponse);
        }
    });
}


function get_fin_codes_history_report_excel(url, csrf, codes_id) {
    let sort_mode = $('input[name="sort_type"]:checked').val();
    let date_from = $('#date_from').val();
    let date_to = $('#date_to').val();
    let selectElement = document.getElementById(codes_id);
    let request_code = selectElement.value;

    $('#overlay_loading').show();
    $.ajax({
        url: url,
        headers: { "X-CSRFToken": csrf },
        method: "POST",
        data: {date_from: date_from,
            date_to: date_to,
            sort_type: sort_mode,
            promo_code: request_code,
            bonus_code: request_code,
            },
        xhrFields: {
            responseType: 'blob' // Set response type to blob
        },

        success: function(response, status, xhr) {
            $('#overlay_loading').hide();
            if (xhr.status === 200) {
                var blob = new Blob([response], { type: 'application/xlsx' });
                var link = document.createElement('a');

                var dataName = xhr.getResponseHeader('data_file_name');

                link.href = window.URL.createObjectURL(blob);
                // console.log()
                link.download = decodeURIComponent(dataName) || 'история кодов.xlsx'; //
                link.click();
            } else {
                // Handle other status codes
                console.error('Error:', xhr.status);
            }
        },
        error: function(xhr, status, error) {
            $('#overlay_loading').hide();
            // Error handling
            console.error('Error:', error);
        }
    });
}

function bck_get_transactions_excel_report(url, csrf) {
    let sort_mode = 0;
    if (document.getElementById("asc_type").checked) {
        sort_mode = 1;
    }
    let date_from =  $('#date_from').val();
    let date_to =  $('#date_to').val();
    $('#overlay_loading').show();
    $.ajax({
        url: url,
        headers: { "X-CSRFToken": csrf },
        method: "POST",
        data: {
            tr_status: $('#transaction_status').val(),
            transaction_type: $('#transaction_type').val(),
            operation_type: $('#operation_type').val(),
            service_account: $('#service_account').val(),
            date_from: date_from,
            date_to: date_to,
            amount: $('#transaction_amount').val(),
            agent_id: $('#user_filter').val(),
            sort_type: sort_mode},
        xhrFields: {
            responseType: 'blob' // Set response type to blob
        },
        success: function(response, status, xhr) {
            $('#overlay_loading').hide();
            if (xhr.status === 200) {
                // PDF downloaded successfully
                var blob = new Blob([response], { type: 'application/xlsx' });
                var link = document.createElement('a');

                var dataName = xhr.getResponseHeader('data_file_name');

                link.href = window.URL.createObjectURL(blob);
                link.download = dataName || 'report.pdf'; //
                link.click();
            } else {
                // Handle other status codes
                console.error('Error:', xhr.status);
            }
        },
        error: function(xhr, status, error) {
            $('#overlay_loading').hide();
            // Error handling
            console.error('Error:', error);
        }
    });

}

function get_fin_order_report_excel(url, csrf) {
    let sort_mode = $('input[name="sort_type"]:checked').val();
    let date_from = $('#date_from').val();
    let date_to = $('#date_to').val();
    let order_type = $('input[name="order_type"]:checked').val()
    let payment_status = $('input[name="payment_status"]:checked').val()

    $('#overlay_loading').show();
    $.ajax({
        url: url,
        headers: { "X-CSRFToken": csrf },
        method: "POST",
        data: {date_from: date_from,
            date_to: date_to,
            sort_type: sort_mode,
            order_type: order_type,
            payment_status: payment_status,},
        xhrFields: {
            responseType: 'blob' // Set response type to blob
        },

        success: function(response, status, xhr) {
            $('#overlay_loading').hide();
            if (xhr.status === 200) {
                var blob = new Blob([response], { type: 'application/xlsx' });
                var link = document.createElement('a');

                var dataName = xhr.getResponseHeader('data_file_name');

                link.href = window.URL.createObjectURL(blob);
                // console.log()
                link.download = decodeURIComponent(dataName) || 'отчет_по_заказам.xlsx'; //
                link.click();
            } else {
                // Handle other status codes
                console.error('Error:', xhr.status);
            }
        },
        error: function(xhr, status, error) {
            $('#overlay_loading').hide();
            // Error handling
            console.error('Error:', error);
        }
    });

}


function bck_get_ar_orders_report(url) {
    loadingCircle();
    $.ajax({
        url: url,
        method: "GET",
        data: {
            category: $('#category').val(),
            category_pos_type: $('#category_pos_type').val(),
            date_from: $('#date_from').val(),
            date_to: $('#date_to').val()
        },
        success: function (data) {
            if (data.status===1) {
                $('#ar_orders_report_block').html(data);
                $("#ar_orders_report_block").append(data.htmlresponse);
            }
            else{
                make_message(data.message, 'error')
            }

        },
        error: function() {
            $('#overlay_loading').hide();
            make_message('Ошиба обработки данных, перезагрузите страницу', 'error');
        }

    });
    close_Loading_circle();

}


function bck_su_transaction_detalization(url) {
    $.ajax({
        url: url,
        method: "GET",

        success: function (data) {
            // console.log(data);

            document.getElementById('su_transactionDetaildiv').innerHTML = data.transaction_report

            $("#su_transactionDetailModal").modal('show');

        },
        error: function () {
            // make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');
            setTimeout(function () {
                make_message('Ошибка. В базе нет такой транзакции', 'danger');
            }, 3500);
        }
    });
}


function bck_get_transactions_specific_user(url) {
    let sort_mode = $('input[name="sort_type"]:checked').val();
    let date_from = $('#date_from').val();
    let date_to = $('#date_to').val();

    $.ajax({
        url: url,
        method: "GET",
        data: {
            date_from: date_from,
            date_to: date_to,
            sort_type: sort_mode,
        },
        success: function (data) {
            if (data.status === 'success') {
                $('#transactions_table').html(data);
                $("#transactions_table").append(data.htmlresponse);
            }
            else if (data.status === 'error'){
                make_message(data.message, data.status);
            }

        },
        error: function () {
            make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');
        }
    });
}


function clear_su_td_modal() {
    document.getElementById('su_transactionDetaildiv').innerHTML = '';
}

function bck_au_ut_detalization(url) {
    $.ajax({
        url: url,
        method: "GET",

        success: function (data) {
            // console.log(data);
            if (data.status === 1) {
                document.getElementById('au_transactionDetaildiv').innerHTML = data.transaction_report

                $("#au_transactionDetailModal").modal('show');
            } else {
                make_message(data.message, 'danger');
                setTimeout(function () {
                    clear_user_messages();
                }, 15000);
            }
        },
        error: function () {
            // make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');
            setTimeout(function () {
                make_message('Ошибка. В базе нет такой транзакции', 'danger');
            }, 3500);
        }
    });
}

function clear_au_userstd_modal() {
    document.getElementById('au_transactionDetaildiv').innerHTML = '';
}


function bck_get_orders_stats(url) {
    let date_from = $('#date_from').val()
    let date_to = $('#date_to').val()
    let data = {
            bck: 1,
            date_from: date_from,
            date_to: date_to,
        };
    let extend_agent_elem = document.getElementById('agent_orders')
    if (extend_agent_elem) {
        data['extend_agent'] = +extend_agent_elem.checked
    }

    $.ajax({
        url: url,
        method: "GET",
        data: data,

        success: function (data) {
            $('#orders_stats_table').html(data);
            $("#orders_stats_table").append(data.htmlresponse);

        },
        error: function () {
            // make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');
            setTimeout(function () {
                make_message('Ошибка. В базе нет информации об этих заказах', 'danger');
            }, 3500);
        }
    });

}


function get_order_stats_rpt(url, admin_id, csrf_token) {
    let date_from = $('#date_from').val();
    let date_to = $('#date_to').val();

    let data = {
            date_from: date_from,
            date_to: date_to,
            admin_id: admin_id
        };
    let extend_agent_elem = document.getElementById('agent_orders')
    if (extend_agent_elem) {
        data['extend_agent'] = +extend_agent_elem.checked
    }

    $.ajax({
        url: url,
        headers: { "X-CSRFToken": csrf_token },
        method: "POST",
        data: data,
        xhrFields: {
            responseType: 'blob' // Set response type to blob
        },
        success: function(response, status, xhr) {
            if (xhr.status === 200) {
                var blob = new Blob([response], { type: 'application/xlsx' });
                var link = document.createElement('a');

                var dataName = xhr.getResponseHeader('data_file_name');

                link.href = window.URL.createObjectURL(blob);
                // console.log()
                link.download = decodeURIComponent(dataName) || 'история кодов.xlsx'; //
                link.click();
            } else {
                // Handle other status codes
                console.error('Error:', xhr.status);
            }
        },
        error: function(xhr, status, error) {
            $('#overlay_loading').hide();
            // Error handling
            console.error('Error:', error);
        }
    });
}

function bck_get_users_activated(url) {
    $.ajax({
        url: url,
        method: "GET",

        success: function (data) {
            if (data.status && data.status === 'success') {
                $('#usersActivateTable').html(data);
                $('#usersActivateTable').append(data.htmlresponse);
            }
        },
        error: function () {
            // make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');
            setTimeout(function () {
                make_message('Ошибка. В базе нет информации об этих пользователях', 'danger');
            }, 3500);
        }
    });

}

function bck_activate_user(url, url_update, form_id) {
    var form = $("#" + form_id).serialize();
    $.ajax({
        url: url,
        // headers:{"X-CSRFToken": csrf},
        method: "POST",
        data: form,
        success: function (data) {
            if (data.status === 'success') {
                bck_get_users_activated(url_update);
            }

            make_message(data.message, data.status);
        },
        error: function () {
            make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');
        }
    });

    setTimeout(function () {
        clear_user_messages();
    }, 15000);
}


function bck_delete_user(url, url_update, form_id) {
    var form = $("#" + form_id).serialize();
    // console.log(form);
    $.ajax({
        url: url,
        // headers:{"X-CSRFToken": csrf},
        method: "POST",
        data: form,
        success: function (data) {

            if (data.status === 'success') {
                bck_get_users_activated(url_update);
            }

            make_message(data.message, data.status);
        },
        error: function () {
            make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');
        }
    });

    setTimeout(function () {
        clear_user_messages();
    }, 15000);
}

function bck_pending_transaction_change_status(url, update_url, operation_type, tr_status, csrf) {

    $.ajax({
        url: url,
        headers: {"X-CSRFToken": csrf},
        method: "POST",
        data: {'operation_type': operation_type, 'tr_status': tr_status},
        success: function (data) {
            // console.log(data);

            if (data.status === 'success') {
                bck_get_transactions_wp(update_url);
                make_message(data.message, data.status);
            }
            else{
                make_message(data.message, 'warning');
                setTimeout(() => { location.reload()
                }, 3000);
            }
        },
        error: function () {
            make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');
        }
    });

    setTimeout(function () {
        clear_user_messages();
    }, 15000);
}

function uncheck_transaction_switch(switch_id, button_id){
    var bg_color = 'bg-danger';
    if (switch_id === 'confirm_transaction_switchbox'){
        bg_color = 'bg-success';
    }
    if(document.getElementById(switch_id).checked === true){
        document.getElementById(button_id).classList.remove('disabled');
        document.getElementById(switch_id).classList.add(bg_color);
    }
    else{
        document.getElementById(button_id).classList.add('disabled');
        document.getElementById(switch_id).classList.remove(bg_color)
    }
}

function ordinary_load_data(query, url, csrf_token)
  {
   $.ajax({
    url: url,
    headers:{"X-CSRFToken": csrf_token},
    method:"POST",
    data:{query:query},
    success:function(data)
    {
      $('#user_search_result').html(data);
      $("#user_search_result").append(data.htmlresponse);
    },
    error: function() {
         make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');
     }
   });
  }
function ordinary_search_user(url, csrf_token){
    var search = $('#search_text').val();
    if(search !== ''){
    ordinary_load_data(search, url, csrf_token);
    }
    else{
        $('#user_search_result').html('');
    }
}

function load_idn_data(query, url, csrf_token){
   $.ajax({
    url: url,
    headers:{"X-CSRFToken": csrf_token},
    method:"POST",
    data:{query:query},
    success:function(data)
    {
      $('#user_search_idn_result').html(data);
      $("#user_search_idn_result").append(data.htmlresponse);
    },
    error: function() {
         make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');
     }
   });
  }

function search_user_idn(url, csrf_token){
    var search = $('#search_user_idn').val();
    if(search.length > 4){
        load_idn_data(search, url, csrf_token);
    }
    else{
        $('#user_search_idn_result').html('');
    }
}

function set_current_date_su_filters(){
    var currentDate = new Date();
    var day = currentDate.getDate().toString().padStart(2, '0'); // Add leading zero if necessary
    var month = (currentDate.getMonth() + 1).toString().padStart(2, '0'); // Add leading zero if necessary
    var year = currentDate.getFullYear();
    var formattedDate = day + '.' + month + '.' + year;
    document.getElementById("date_from").value = formattedDate;
    document.getElementById("date_to").value = formattedDate;
}

function admin_uc_isValid(block) {
    const match = block.value.match(/^\d+/);
    block.value = match ? match[0] : '';
     // Change input type to text temporarily (because working with cursor is available only with text type)
    const originalType = block.type;
    block.type = 'text';

    // Set cursor position to the end of input
    block.setSelectionRange(block.value.length, block.value.length);

    // Change input type back to number
    block.type = originalType;
    let number = parseInt(block.value, 10);
    let min = parseInt(block.getAttribute('min'), 10);
    let max = parseInt(block.getAttribute('max'), 10);
    return !isNaN(number) && number <= max && number >= min;
}

function updateCategoryPosType() {
    const category = document.getElementById('category').value;
    const categoryPosType = document.getElementById('category_pos_type');

    // Clear existing options
    categoryPosType.innerHTML = '<option selected value="">Выберите из списка..</option>';

    // Get the new options based on the selected category
    const options = acTypes[category] || [];

    // Populate the select box with new options
    options.forEach(option => {
        const opt = document.createElement('option');
        opt.value = option;
        opt.text = option.toUpperCase();
        categoryPosType.appendChild(opt);
    });
}

function toggleOrderStatusBlock(disable) {
     const paymentStatusRadios = document.getElementsByName('payment_status');
            for (let i = 0; i < paymentStatusRadios.length; i++) {
                paymentStatusRadios[i].disabled = disable;
                if (disable) {
                    paymentStatusRadios[i].checked = false;
                }
                else {
                    let default_payment_status = document.getElementById('pay_in_full');
                    default_payment_status.checked = true;
                }
            }


}


function saveCallResultAndComment(url, u_id, csrf) {
    // Get the comment value
    const comment = document.getElementById(`comment_${ u_id }`).value;
    const selectedCallStatus = document.getElementById(`selected_call_status_${u_id}`).value;

    $.ajax({
    url: url,
    headers:{
        "X-CSRFToken": csrf,
        "Content-Type": "application/json"
    },
    method:"POST",
    data:JSON.stringify({
            user_id: u_id,
            comment: comment,
            call_result: selectedCallStatus
        }),

    success:function(data)
    {
        if (data.status === 'danger'){
            make_message(data.message, 'danger');
            return
        }
        $(`#call_comment_and_result_${u_id}`).html(data);
        $(`#call_comment_and_result_${u_id}`).append(data.htmlresponse);
    },
    error: function() {
         make_message('Не удалось сохранить комментарий', 'danger');
     }
   });
}