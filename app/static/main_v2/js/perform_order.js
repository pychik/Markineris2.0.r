// ===============================
//  CONTACT STEP + ORDER SUBMIT FLOW
//  Требования:
//  - после проверки баланса (и после подтверждения при дублях) ОБЯЗАТЕЛЬНО выбрать тип связи
//  - данные связи отправляются ВМЕСТЕ с финальным сабмитом (perform_process)
// ===============================

// Хранилище выбора контакта (в памяти страницы)
window.__order_contact = { type: null, value: "" };

async function fetchAsync(url) {
    let response = await fetch(url);

    return response.text();
}

// Утилита: показать ошибку внутри модалки
function modal_set_error(html) {
    document.getElementById("data_order_check_insert").innerHTML = html;
}

// Утилита: прелоадер в футере
function modal_set_loading(text) {
    document.getElementById('process_modal_footer').innerHTML =
        `<div class="col text-center text-warning"><b>${text || "Производится обработка"}</b><br><div class="spinner-border" role="status"></div></div>`;
}

function validate_contact_value(type, value) {

    value = value.trim();

    if (!value) {
        return { ok: false, msg: "Поле обязательно" };
    }

    if (type === "telegram") {
        const re = /^@[A-Za-z0-9_]{5,32}$/;
        if (!re.test(value)) {
            return {
                ok: false,
                msg: "Введите корректный username (@username)"
            };
        }
    }

    if (type === "phone") {
        const digits = value.replace(/\D/g, "");
        if (digits.length < 10) {
            return {
                ok: false,
                msg: "Введите корректный номер телефона"
            };
        }
    }

    if (type === "max") {
        if (value.length < 3) {
            return {
                ok: false,
                msg: "Слишком короткие данные"
            };
        }
    }

    return { ok: true, msg: "" };
}


// Восстановить исходный футер модалки (кнопка стартовой проверки)
function reset_process_modal_footer(urlCheckBalance, csrf, o_id, category) {
    document.getElementById("data_order_check_insert").innerHTML = '';
    document.getElementById('process_modal_footer').innerHTML = `
        <button type="button" class="btn btn-accent border-0" id="btn_process"
            onclick="perform_balance_order_check('${urlCheckBalance}', '${csrf}', ${o_id}, '${category}');">
            Оформить накладную
        </button>
        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Назад</button>
    `;
}

// ===============================
// STEP 1: ПОКАЗЫВАЕМ ВЫБОР СПОСОБА СВЯЗИ
// ===============================

function show_contact_step() {

    window.__order_contact = { type: null, value: "" };

    document.getElementById("data_order_check_insert").innerHTML = `
    
    <div id="contact_block" class="contact-block faded">
    
        <div class="contact-title">
            Способ связи (обязательно)
        </div>
    
        <div class="contact-subtitle">
            Выберите способ связи по вопросам в заказе
        </div>
    
        <div class="d-grid gap-2 mt-3">
    
    
            <!-- TELEGRAM -->
            <button type="button"
                    class="btn btn-outline-secondary text-start d-flex align-items-center gap-2"
                    onclick="select_contact_method('telegram')">

                <svg width="28" height="28" viewBox="0 0 42 41" fill="none"
                     xmlns="http://www.w3.org/2000/svg">
                    <g>
                        <path
                            d="M21.4053 40.9368C32.7097 40.9368 41.8737 31.7728 41.8737 20.4684C41.8737 9.16403 32.7097 0 21.4053 0C10.1009 0 0.93689 9.16403 0.93689 20.4684C0.93689 31.7728 10.1009 40.9368 21.4053 40.9368Z"
                            fill="#039BE5"/>
                        <path
                            d="M10.3029 20.025L30.0379 12.4159C30.9538 12.085 31.7538 12.6393 31.457 14.0244L28.0985 29.8533C27.8494 30.9756 27.1825 31.2485 26.2495 30.7198L21.1324 26.9485L18.6642 29.3262L17.9956 24.6219L27.4793 16.0541L15.1232 23.2266L10.0709 21.6506C8.97415 21.3026 8.95027 20.5538 10.3029 20.025Z"
                            fill="white"/>
                    </g>
                </svg>

                Телеграм
            </button>
    
    
            <!-- MAX -->
            <button type="button"
                    class="btn btn-outline-secondary text-start d-flex align-items-center gap-2"
                    onclick="select_contact_method('max')">

                <img
                    src="/static/index_v2/images/max_bot.svg"
                    width="28"
                    height="28"
                    alt="MAX messenger">

                Max
            </button>
    
    
            <!-- PHONE -->
            <button type="button"
                    class="btn btn-outline-secondary text-start d-flex align-items-center gap-2"
                    onclick="select_contact_method('phone')">

                <svg width="28" height="28" viewBox="0 0 41 41" fill="none"
                     xmlns="http://www.w3.org/2000/svg">

                    <circle cx="20.5" cy="20.5" r="20.5" fill="#25D366"/>

                    <g transform="translate(20.5 20.5) scale(2) translate(-20.5 -20.5)">
                        <path
                            d="M16.57 20.556C16.4419 20.3852 15.5253 19.1684 15.5253 17.9089C15.5253 16.6494 16.1863 16.0302 16.4208 15.774C16.6554 15.5179 16.9326 15.4541 17.1034 15.4541C17.2741 15.4541 17.4449 15.4559 17.5941 15.4631C17.7513 15.4712 17.9621 15.4033 18.1697 15.9025C18.3831 16.4148 18.8945 17.6748 18.9587 17.8028C19.023 17.9309 19.0652 18.0801 18.9803 18.2513C18.8949 18.422 18.8522 18.5285 18.7246 18.6782L18.3404 19.1266C18.2124 19.2542 18.0789 19.3926 18.2281 19.6487C18.3773 19.9049 18.8909 20.7429 19.6516 21.4219C20.6289 22.294 21.4535 22.5641 21.7096 22.6922C21.9653 22.8202 22.1149 22.7991 22.2641 22.6279L23.0747 21.6245C23.2455 21.3684 23.4158 21.4111 23.6503 21.4965C23.8849 21.5818 25.1431 22.201 25.3987 22.3291C25.6544 22.4572 25.8252 22.5214 25.8894 22.6279C25.9537 22.7349 25.9537 23.2471 25.7402 23.8447C25.5268 24.4424 24.5045 24.9883 24.013 25.0616C23.5722 25.1276 23.0141 25.155 22.4012 24.96C21.9056 24.8062 21.4186 24.6262 20.9421 24.4208C18.3746 23.3118 16.6985 20.7267 16.57 20.556Z"
                            fill="white"/>
                    </g>

                </svg>

                Связаться по телефону
            </button>
    
        </div>
    
        <div id="contact_form_wrap" class="mt-3"></div>
        <div id="contact_error" class="mt-2 text-danger"></div>
    
    </div>
    `;

    document.getElementById('process_modal_footer').innerHTML = `
        <button type="button"
                class="btn btn-accent border-0"
                id="btn_contact_submit"
                onclick="submit_contact_and_form();"
                disabled>
            Оформить заказ
        </button>

        <button type="button"
                class="btn btn-secondary"
                data-bs-dismiss="modal">
            Назад
        </button>
    `;
}

function select_contact_method(type) {

    window.__order_contact.type = type;
    window.__order_contact.value = "";

    let input_type = 'text';
    let label = "";
    let placeholder = "";

    if (type === "telegram") {
        label = "Введите ваш username в Telegram (например: @username)";
        placeholder = "@username";
    }
    else if (type === "max") {
        label = "Введите ваши данные для связи через Max";
        placeholder = "Введите данные";
    }
    else if (type === "phone") {
        input_type = 'tel';
        label = "Введите номер телефона";
        placeholder = "+7 (999) 123-45-67";
    }

    document.getElementById("contact_form_wrap").innerHTML = `
        <label class="mb-2">${label}</label>
        <input class="form-control"
               id="contact_value"
               type="${input_type}"
               placeholder="${placeholder}">
        <div id="contact_input_error" class="contact-error-text"></div>
    `;

    const input = document.getElementById("contact_value");
    const btn = document.getElementById("btn_contact_submit");
    const err = document.getElementById("contact_input_error");

    btn.disabled = true;

    input.addEventListener("input", () => {

        const value = input.value.trim();
        window.__order_contact.value = value;

        const check = validate_contact_value(type, value);

        if (!check.ok) {
            input.classList.add("input-invalid");
            input.classList.remove("input-valid");
            err.innerText = check.msg;
            btn.disabled = true;
        }
        else {
            input.classList.remove("input-invalid");
            input.classList.add("input-valid");
            err.innerText = "";
            btn.disabled = false;
        }

    });
}
// ===============================
// STEP 2: ФИНАЛЬНЫЙ САБМИТ (отправляем контакт вместе с заказом)
// ===============================

function submit_contact_and_form() {

    const type = window.__order_contact.type;
    const value = window.__order_contact.value;

    const err = document.getElementById("contact_error");

    if (!type) {
        err.innerHTML = "Выберите способ связи";
        return;
    }

    if (!value) {
        err.innerHTML = "Заполните контактные данные";
        return;
    }

    // Получаем форму
    const form = document.getElementById("form_process");

    // Создаём hidden поля (если ещё нет)
    let typeInput = document.getElementById("contact_type_input");
    if (!typeInput) {
        typeInput = document.createElement("input");
        typeInput.type = "hidden";
        typeInput.name = "contact_type";
        typeInput.id = "contact_type_input";
        form.appendChild(typeInput);
    }

    let valueInput = document.getElementById("contact_value_input");
    if (!valueInput) {
        valueInput = document.createElement("input");
        valueInput.type = "hidden";
        valueInput.name = "contact_value";
        valueInput.id = "contact_value_input";
        form.appendChild(valueInput);
    }

    typeInput.value = type;
    valueInput.value = value;

    // Прелоадер
    document.getElementById('process_modal_footer').innerHTML =
        `<div class="col text-center text-warning">
            <b>Оформляем заказ…</b><br>
            <div class="spinner-border"></div>
         </div>`;

    // Сабмит формы
    form.submit();
}



// ===============================
// ВАША ТЕКУЩАЯ ПРОВЕРКА БАЛАНСА/ДУБЛЕЙ
// МЕНЯЕМ ТОЛЬКО ТО, ЧТО ВМЕСТО perform_process() ПЕРЕХОДИМ НА show_contact_step()
// ===============================
function perform_balance_order_check(urlCheckBalance, csrf, o_id, category) {
    $.ajax({
        url: urlCheckBalance,
        headers: {"X-CSRFToken": csrf},
        method: "POST",
        data: { o_id: o_id, category: category },
        success: function (data) {
            let agent_2_str = 'Обратитесь к агенту, на данный момент активность невозможна';

            // ВАЖНО: здесь нужен URL финального сабмита (ваша "process" ручка)
            // Подставьте реальный url в вызове perform_balance_order_check(...) через аргумент,
            // либо задайте глобально. Здесь используем глобальную переменную:
            // window.__FINAL_SUBMIT_URL должно быть задано в шаблоне.

            if (data.status_balance === 1 && data.status_order === 0) {
                // Баланс ок, дублей нет -> требуем контакт
                show_contact_step();

            } else if (data.status_balance !== 1 && data.status_order === 0) {
                // Баланс не ок
                if (!data.agent_at2) {
                    modal_set_error(`<span style="color:red"><b>${data.answer_balance}</b></span><br>`);
                } else {
                    modal_set_error(`<span style="color:red"><b>${agent_2_str}</b></span><br>`);
                }
                document.getElementById('process_modal_footer').innerHTML = `
                    <button type="button" class="btn btn-secondary"
                        onclick="reset_process_modal_footer('${urlCheckBalance}', '${csrf}', ${o_id}, '${category}');"
                        data-bs-dismiss="modal">Ок</button>`;

            } else if (data.status_balance !== 1 && data.status_order !== 0) {
                // Баланс не ок + дубли
                if (!data.agent_at2) {
                    modal_set_error(`<span style="color:red"><b>${data.answer_balance}</b></span><br>`);
                } else {
                    modal_set_error(`<span style="color:red"><b>${agent_2_str}</b></span><br>`);
                }
                document.getElementById('process_modal_footer').innerHTML = `
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal"
                        onclick="reset_process_modal_footer('${urlCheckBalance}', '${csrf}', ${o_id}, '${category}');">
                        Ок
                    </button>`;

            } else if (data.status_balance === 1 && data.status_order !== 0) {
                // Баланс ок, но есть дубли -> предупреждаем, и при продолжении всё равно требуем контакт
                modal_set_error(`<span style="color:#ffc400"><b>${data.answer_orders}</b></span><br>`);

                document.getElementById('process_modal_footer').innerHTML = `
                    <button type="button" class="btn btn-accent" id="btn_process"
                        onclick="show_contact_step('${urlFinalSubmit}', '${csrf}', ${o_id}, '${category}', '${urlCheckBalance}');">
                        Все-равно оформить накладную!
                    </button>
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Отмена</button>`;

            } else {
                document.getElementById('process_modal_footer').innerHTML = `
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal"
                        onclick="reset_process_modal_footer('${urlCheckBalance}', '${csrf}', ${o_id}, '${category}');">
                        Ок
                    </button>`;
                modal_set_error(`<span style="color:red"><b>Неизвестная ошибка</b></span><br>`);
            }
        },
        error: function () {
            setTimeout(function () {
                make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');
            }, 1500);
        }
    });

    setTimeout(function () {
        clear_user_messages();
    }, 15000);
}


let __process_modal_initial_footer = null;
let __process_modal_initial_body = null;

document.addEventListener("DOMContentLoaded", function () {

    const modal = document.getElementById('processModal');

    __process_modal_initial_footer =
        document.getElementById('process_modal_footer').innerHTML;

    __process_modal_initial_body =
        document.getElementById('data_order_check_insert').innerHTML;

});
document.getElementById('processModal')
    .addEventListener('hidden.bs.modal', function () {

        // Сброс footer
        document.getElementById('process_modal_footer').innerHTML =
            __process_modal_initial_footer;

        // Сброс body (динамический блок)
        document.getElementById('data_order_check_insert').innerHTML =
            __process_modal_initial_body;

        // Сброс временных данных
        window.__order_contact = { type: null, value: "" };
    });