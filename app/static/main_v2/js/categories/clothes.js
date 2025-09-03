function clothes_check_sizes_quantity_valid() {
    var sizes = document.querySelectorAll('[id=size_info]');
    return sizes.length >= 1;
}

function clothes_perform_pos_add(async_flag, url) {

    var pos_form = document.getElementById('form_process_main');
    // let isValid = pos_form.reportValidity(); // не подходит

    var chtn = check_tnved('submit');
    var crd = check_rd_docs();
    var scsq = clothes_check_sizes_quantity_valid();
    // var ccm = check_company_marks();
    var ccb = true;
    if (document.getElementById('content').value.length < 3) {
        ccb = false;


    }
    if ((pos_form.checkValidity === true || pos_form.checkValidity()) && ccb && crd && scsq && chtn) {
        // console.log(pos_form.checkValidity());
        // console.log("good valid form")
        if (async_flag === 0) {
            // console.log(pos_form.checkValidity, pos_form.checkValidity());
            pos_form.submit();
        } else {
            clothes_load_upload_table(url);
        }
    } else {
        var allInputs = $('#form_process_main input, #form_process_main select ');
        var errors_list = [];

        allInputs.each(function (index) {
            // console.log(allInputs[index]);
            let error_field_id = check_valid(allInputs[index]);
            if (error_field_id !== true) {
                let label_text = jQuery(`#${error_field_id}`).closest(".form-group").find("label").text();
                // document.getElementById().parent().label.innerText
                // errors_list.push(error_field_name);
                // console.log(allInputs[index]);
                // console.log(error_field_id);
                if (label_text) {
                    errors_list.push(label_text);
                }
            }
        })
        if (ccb === false) {
            errors_list.push("Блок состав одежды! Заполните!");
        }
        if (scsq === false) {
            errors_list.push("Размер одежды. Добавьте хотя бы один");
        }
        if (crd === false) {
            errors_list.push("Разрешительная документация. Должны быть заполнены все поля формы разрешительной документации, либо все должны быть пусты!");
        }


        // console.log('not valid form');
        show_form_errors(errors_list);
        $('#form_errorModal').modal('show');
    }
}


function show_clothes_pos(index, trademark, type, color, pos_quantity, box_quantity, all_quantity, sq_list, content,
                          gender, country, edit_link, copy_link, delete_link, csrf_token) {
    let main = document.getElementById('ShowModalTable');
    main.innerHTML = '';
    let sq_block = ''
    sq_list.forEach(function (el) {
            let size_temp = el.split('##')[0];
            let quantity_temp = el.split('##')[1];
            let size_type_temp = el.split('##')[2];
            sq_block += `<div class="important-card__item important-card__size ms-2">
                        <div class="d-flex align-items-center g-3">
<!--                            <svg xmlns="http://www.w3.org/2000/svg" width="26" height="26" viewBox="0 0 26 26" fill="none">-->
<!--                                <path fill-rule="evenodd" clip-rule="evenodd" d="M5.50501 0.396617C10.2365 -0.132206 15.1279 -0.132206 19.8595 0.396617C22.4999 0.691723 24.63 2.77206 24.9402 5.42294C25.5058 10.2602 25.5058 15.1468 24.9402 19.9839C24.63 22.6348 22.4999 24.7152 19.8595 25.0102C15.1279 25.539 10.2365 25.539 5.50501 25.0102C2.86457 24.7152 0.734354 22.6348 0.424309 19.9839C-0.141436 15.1468 -0.141436 10.2602 0.424309 5.42294C0.734354 2.77206 2.86457 0.691723 5.50501 0.396617ZM12.6822 11.5472H13.8385H19.2231C19.8616 11.5472 20.3793 12.0649 20.3793 12.7034C20.3793 13.342 19.8616 13.8597 19.2231 13.8597H13.8385C13.8385 13.8597 13 13.8597 12.6822 13.8597C12.3645 13.8597 12 13.8597 12 13.8597H11.526H6.14155C5.50296 13.8597 4.9853 13.342 4.9853 12.7034C4.9853 12.0649 5.50296 11.5472 6.14155 11.5472H11.526H12.6822Z" fill="#575757"/>-->
<!--                              </svg>-->
                            <span class="ms-2">${size_temp}</span>&nbsp;<span style="font-size:10px">${size_type_temp}</span>
                        </div>
                        <div class="important-card__val">${quantity_temp} <span>шт.</span></div>
                    </div>`;
        }
    )
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
                    <h5 class="modal-title border-0" >${index}</h5>
                </div>
                <div class="important-card important-card--light pt-0">
                    <div class="important-card__item d-flex align-items-center">
                        <div class="important-card__prop">${type + ' ' + trademark}
                        </div>
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

                    <div class="important-card__item">
                        <div class="important-card__prop">
                            Вид одежды
                        </div>
                        <div class="important-card__val">${type}</div>
                    </div>
                    <div class="important-card__item">
                        <div class="important-card__prop">
                            Цвет
                        </div>
                        <div class="important-card__val">${color}</div>
                    </div>
                    <div class="important-card__item">
                        <div class="important-card__prop">
                            Кол-во в коробке
                        </div>
                        <div class="important-card__val">${pos_quantity}</div>
                    </div>
                    <div class="important-card__item">
                        <div class="important-card__prop">
                            Кол-во коробок
                        </div>
                        <div class="important-card__val">${box_quantity}</div>
                    </div>
                    <div class="important-card__item">
                        <div class="important-card__prop">
                            Общее количество
                        </div>
                        <div class="important-card__val">${all_quantity}</div>
                    </div>
                    <div class="important-card__item border-bottom-0">
                        <div class="important-card__prop">
                            Размеры
                        </div>
                    </div>
                    ${sq_block}
                    <div class="important-card__item" style="overflow: scroll">
                        <div class="important-card__prop">
                            Состав
                        </div>
                        <div class="important-card__val">${content}</div>
                    </div>
                    <div class="important-card__item">
                        <div class="important-card__prop">
                          Пол
                        </div>
                        <div class="important-card__val">${gender}</div>
                    </div>
                    <div class="important-card__item">
                        <div class="important-card__prop">
                          Страна
                        </div>
                        <div class="important-card__val">${country}</div>
                    </div>
                </div>

            </div>
        </div>
    </div>`
    main.insertAdjacentHTML('beforeend', data_modal);
    $('#showElementTable').modal('show');
}


function clothes_make_research_by_article(url, csrf_token) {
    var search = $('#search_by_article_text').val();
    if (search.length >= 2) {
        clothes_load_search_data(search, url, csrf_token);
    } else {
        // load_search_data()
        $('#search_article_info').empty();
    }
}

function clothes_load_search_data(query, url, csrf_token) {
    $.ajax({
        url: url,
        headers: {"X-CSRFToken": csrf_token},
        method: "POST",
        data: {query: query},
        success: function (data) {
            $('#search_article_info').html(data);
            $("#search_article_info").append(data.htmlresponse);
        }
    });
}

async function async_clothes_delete_pos(url, csrf, block) {
    // loadingCircle();
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
        // console.log(data)
        if (data.status === 'success' && data.type === 'async') {

            $('#step-3_update').html(data);
            $('#step-3_update').append(data.htmlresponse);

            $('#orders_row_count').html(data.pos_count);
            $('#orders_pos_count').html(data.orders_pos_count);
            $('#modal_orders_pos_count').html(`<span>${data.orders_pos_count}</span>шт.`);

            // $(block).closest('tr').remove();
            // close_Loading_circle();
            make_message('Успешно удалена позиция', 'success');
            setTimeout(function () {
                clear_user_messages();
            }, 15000);
        } else if (data.status === 'success' && data.type === 'order_delete') {

            $(block).closest('tr').remove();
            window.location = data.url;


        } else {
            // close_Loading_circle();
            alert(data.status);

        }


    } catch (e) {
        console.log(e)
        close_Loading_circle();
        make_connection_error_message('Произошла ошибка. Обратитесь к администратору', 'error');
        setTimeout(function () {
            clear_user_messages();
        }, 5000);
        return false;
    }

}

function clothes_load_upload_table(url) {
    // var csrf_token = "{{ csrf_token() }}";
    var form = $("#form_process_main").serialize();
    var article = $('#article').val();
    var message = '';
    var message_type = '';

    $.ajax({
        url: url,
        // headers:{"X-CSRFToken": csrf_token},
        method: "POST",
        data: form,
        success: function (data) {
            // console.log(data);
            if (data.status === 'success') {
                $('#step-3_update').html(data);
                $("#step-3_update").append(data.htmlresponse);
                $('#orders_row_count').html(data.pos_count);
                $('#orders_pos_count').html(data.orders_pos_count);
                $('#modal_orders_pos_count').html(`<span>${data.orders_pos_count}</span>шт.`);

                let add_edit = '';
                if (window.location.pathname.includes('edit_order')) {
                    add_edit += 'изменена'
                } else {
                    add_edit += 'добавлена'
                }
                message = `Позиция с артикулом ${article} успешно ${add_edit}`;
                message_type = 'success';
                make_message(message, message_type);
                clothes_clear_pos();
                // Повторная инициализация чекбоксов (если используется)
                if (typeof initAggrCheckboxes === 'function') {
                    initAggrCheckboxes();
                }

                // Обновим кнопку создания набора
                const btn = document.getElementById('create_aggr_btn');
                if (btn) {
                    const currentAggrNumber = btn.dataset.aggrNum || '—';
                    btn.textContent = `Создать набор ${currentAggrNumber}`;
                    restoreAggrCountFromStorage();
                }
            } else {
                if (data.message) {
                    message = data.message;
                } else {
                    message = 'Произошла ошибка во время сохранения позиции';
                }
                message_type = 'danger';
                make_message(message, message_type);
            }
        },
        error: function () {
            console.log('error')
            make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');
        }
    });

    // clothes_clear_pos();
    setTimeout(function () {
        clear_user_messages();
    }, 15000);
}


async function clothes_update_table(page) {
    try {
        const res = await fetch(page);
        const data = await res.json();

        if (data.status === 'success') {
            document.getElementById('step-3_update').innerHTML = data.htmlresponse;

            // Повторная инициализация чекбоксов (если используется)
            if (typeof initAggrCheckboxes === 'function') {
                initAggrCheckboxes();
            }

            // Обновим кнопку создания набора
            const btn = document.getElementById('create_aggr_btn');
            if (btn) {
                const currentAggrNumber = btn.dataset.aggrNum || '—';
                btn.textContent = `Создать набор ${currentAggrNumber}`;
                restoreAggrCountFromStorage();
            }
        } else {
            alert(data.message || 'Ошибка обновления блока заказа');
        }
    } catch (e) {
        alert('Ошибка связи с сервером');
    }
}


function clothes_clear_pos() {
    $('#article').val("");
    $('#trademark').val("");

    $('#type').val('').trigger("change");
    $('#color').val('').trigger("change");
    $('#customColor').val("");
    $('#gender').val('').trigger("change");
    $('#multi_content').val('').trigger("change");
    $('#country').val('').trigger("change");
    $('#rd_type').val('').trigger("change");
    $('#tax').val('').trigger("change");

    $('#content').val("");
    $('#tnved_code').val("");
    // $('#article_price').val("");
    $('#rd_name').val("");
    $('#rd_date').val("");

    $('#sizes_quantity').empty();
    check_valid(document.getElementById('tax'));
    check_valid(document.getElementById('article_price'));
    // check_valid(document.getElementById('trademark'));
    // check_valid(document.getElementById('article'));
}

function clothes_content_add() {
    var multi_box = document.getElementById('multi_content');
    var content = multi_box.value;
    var content_box = document.getElementById("content");
    var add_content = ''
    if (content_box.value.length !== 0) {

        if (content_box.value.includes(content) !== true && content_box.value.length + content.length + 2 <= content_box.maxLength) {
            add_content += ', ' + content;

        }
    } else {
        add_content += content;

    }

    content_box.value += add_content;
    content_box.value = content_box.value.slice(0, 101);
}

function check_nat_content(content) {
    if (clothes_nat_array.includes(content)) {
        var nmc = document.getElementById("nat_materials_check")
        nmc.checked = true;
        set_tnved();
    }
}

function manual_content_edit() {
    var mccb = document.getElementById('manual_content_checkbox')
    var nmc = document.getElementById("nat_materials_check")
    var ctb = document.getElementById("content")
    if (mccb.checked === true) {
        nmc.disabled = false;
        ctb.readOnly = false
        ctb.classList.remove('bg-light')
    } else {
        nmc.disabled = true;
        ctb.readOnly = true
        ctb.classList.add('bg-light')

    }

}

function check_content() {
    var ctb = document.getElementById("content")
    if (ctb.value.length > 100) {
        ctb.value = ctb.value.slice(0,100);
    }
}

function countClothes() {
    var total = 0;
    document.querySelectorAll('[id=quantity_info]').forEach(el => total += parseInt(el.innerText, 10));
    return total

}


function setClothes() {
    var total = 0;

    var wp = document.getElementById('with_packages');
    var q_box = 1;
    if (wp.value === "True") {
        let q_box_raw = document.getElementById('box_quantity')
        if (q_box_raw) {
            q_box = document.getElementById('box_quantity').value;
        }

    }

    document.querySelectorAll('[id=quantity_info]').forEach(el => total += parseInt(el.innerText, 10));
    document.getElementById('clothes_in_box_info').innerHTML = '';
    if (isNaN(total)){total=0;}
    document.getElementById('clothes_in_box_info').innerText = total;
}

function check_add_same_size(size, quantity) {
    var sizes = document.querySelectorAll('[id=size_info]');
    for (let i = 0; i < sizes.length; ++i) {
        // console.log(sizes[i].innerText, size);
        if (sizes[i].innerText === size) {
            // console.log(sizes[i].innerText, size);
            let quantities = document.querySelectorAll('[id=quantity_info]');
            let quantities_hidden = document.querySelectorAll('[id=quantity]');
            let quantity_block = quantities[i];
            let quantity_block_hidden = quantities_hidden[i];
            // console.log(`обнаружен похожий размер ${size}`);
            let quantity_pre = parseInt(quantity_block.innerText, 10);
            let quantity_val = quantity_pre + quantity;
            quantity_block.innerHTML = '';
            quantity_block.innerText = quantity_val;
            quantity_block_hidden.value = quantity_val
            setClothes();
            // $('#size_order').val('').trigger("change");
            document.getElementById('size_order').value = '';
            document.getElementById('quantity_order').value = '1';
            return true
        }
    }

    return false
}

function check_clothes_size(value) {


    // console.log(value);
    if (value.length > 0) {

        for (let i = 0; i < check_list.length; i++) {

            if (check_list[i].startsWith(value)) {
                // console.log(check_list[i]);
                return true
            }
        }
        show_form_errors(["Введите корректный размер: от 12 до 74 с шагом 2, либо особый размер вида 12-14, OVERSIZE !",]);
        $('#form_errorModal').modal('show');
        return false
    } else {
        return false
    }
}

function check_clothes_size_on_add(value) {

    // console.log(value);
    if (value.length > 0) {

        if (check_list.includes(value)) {
            // console.log(check_list[i]);
            return true
        }

        show_form_errors(["Введите корректный размер: от 12 до 74 с шагом 2, либо особый размер вида 12-14, OVERSIZE !",]);
        $('#form_errorModal').modal('show');
        return false
    } else {
        return false
    }
}

function perform_free_size_input(clothingType){
    // let subcategoryInputBlock = '';

    // Если subcategory == 'underwear', добавляем input
    // if (subcategory === 'underwear') {
    let subcategoryInputBlock = `
        <button class="btn btn-outline-secondary mb-3" type="button" onclick="document.getElementById('freeInputBlock${clothingType}').classList.toggle('d-none')">Свободный ввод</button>
        <div id="freeInputBlock${clothingType}" class="d-none">
            <p>Поле свободного ввода размера типа ${clothingType} (введите размер, количество и нажмите добавить)</p>
            <div class="input-group mb-3">
                <input type="text" class="form-control" id="subcategorySizeInput${clothingType}" placeholder="Введите размер" maxlength="8"  pattern="[A-Za-z0-9]([-,.;]?[A-Za-z0-9]){0,7}" title="Только латиница и цифры (до 8 символов)" required>
                <input type="number" class="form-control" id="subcategorySizeQuantity${clothingType}" placeholder="Кол-во" min="1" required>
                <button class="btn btn-accent" type="button" onclick="subcategory_size_add('${clothingType}')">Добавить</button>
                <div class="invalid-feedback d-block" id="subcategorySizeError${clothingType}"></div>
            </div>
        </div>`;
    // }
    return subcategoryInputBlock
}

function chooseSizeClothes(subcategory) {
    let divBlock = document.getElementById('sizesClothesDiv');
    let content = '';
    // let subcategoryInputBlock = '';

    // Если subcategory == 'underwear', добавляем input
    // if (subcategory === 'underwear') {
    // subcategoryInputBlock = `
    //     <button class="btn btn-outline-secondary mb-3" type="button" onclick="document.getElementById('freeInputBlock').classList.toggle('d-none')">Свободный ввод</button>
    //     <div id="freeInputBlock" class="d-none">
    //         <p>Поле свободного ввода размера (введите размер, количество и нажмите добавить)</p>
    //         <div class="input-group mb-3">
    //             <input type="text" class="form-control" id="subcategorySizeInput" placeholder="Введите размер" maxlength="8" pattern="[A-Za-z0-9]{1,8}" title="Только латиница и цифры (до 5 символов)" required>
    //             <input type="number" class="form-control" id="subcategorySizeQuantity" placeholder="Кол-во" min="1" required>
    //             <button class="btn btn-accent" type="button" onclick="subcategory_size_add()">Добавить</button>
    //             <div class="invalid-feedback d-block" id="subcategorySizeError"></div>
    //         </div>
    //     </div>`;
    // }



    // Перебираем типы одежды и их размеры
    for (let clothingType in clothes_types_sizes_dict) {
        if (clothes_types_sizes_dict.hasOwnProperty(clothingType)) {
            let sizes = clothes_types_sizes_dict[clothingType];
            let sizesBlock = create_size_blocks(sizes, clothingType);
            let free_size_input = '';
            if (clothingType !== 'ОСОБЫЕ_РАЗМЕРЫ'){
                free_size_input = perform_free_size_input(clothingType);
                }

            content += `
                <div class="accordion-item">
                    <h2 class="accordion-header" id="heading_${clothingType}">
                        <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#collapse_${clothingType}" aria-expanded="false" aria-controls="collapse_${clothingType}">
                            ${clothingType}
                        </button>
                    </h2>
                    <div id="collapse_${clothingType}" class="accordion-collapse collapse" aria-labelledby="heading_${clothingType}">
                        <div class="accordion-body">
                            <div>${free_size_input}</div>
                            <div class="row">${sizesBlock}</div>
                        </div>
                    </div>
                </div>`;
        }
    }

    divBlock.innerHTML = `
        <div class="modal fade" id="sizesClothesModal" tabindex="-1" role="dialog" aria-labelledby="sizesClothesModalLabel" aria-hidden="true"  data-bs-backdrop="static" data-bs-keyboard="false">
            <div class="modal-dialog modal-lg modal-dialog-scrollable" role="document">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title" id="sizesClothesModalLabel">Выберите размеры одежды.</h5>
                        <button type="button" class="btn-close" onclick="clear_clothesSizes_modal();" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body px-5">
                        
                        <p>Для выбора размера, кликните по нему, справа от размера появится поле - введите количество. После ввода всех необходимых размеров нажмите кнопку <b>Закрыть</b></p>
                        <p>Если нужно убрать размер, кликните на него</p>
                        
                        <div class="accordion" id="accordionSizes" style="background-color: #f0f0f0;">${content}</div>
                    </div>
                    <div class="modal-footer d-flex flex-column">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal" onclick="clear_clothesSizes_modal();">Закрыть</button>
                    </div>
                </div>
            </div>
        </div>`;

    $('#sizesClothesModal').modal('show');
}

function setQuantitySize(size) {
 let quantityInput = document.getElementById(`size_${size}`);

    if (quantityInput.disabled) {
        quantityInput.classList.remove('input-light-grey');
        quantityInput.classList.add('input-white');
        $(`#size_${size}`).fadeIn("slow").addClass("fadeInLeft");;
        quantityInput.style.display = "block";

        quantityInput.value = 1;
    } else {

        quantityInput.classList.remove('input-white');
        quantityInput.classList.remove('fadeInLeft');
        quantityInput.classList.add('input-light-grey');

        quantityInput.style.display = 'none';
        quantityInput.value = '';
    }
    quantityInput.disabled = !quantityInput.disabled;
        updateSizesQuantityBlock();
}

function updateSizesQuantityBlock() {
    let sizesQuantityBlock = document.getElementById('sizes_quantity');

    // Создаем объект для хранения уже добавленных размеров
    let existingSizes = {};
    sizesQuantityBlock.querySelectorAll('.important-card__item').forEach(item => {
        let size = item.querySelector('#size_info').textContent.trim();
        let quantity = parseInt(item.querySelector('#quantity_info').textContent.trim(), 10);
        let sizeType = item.querySelector('#size_type_info').textContent.trim();
        existingSizes[size] = { quantity, sizeType, element: item };
    });

    // Обрабатываем выбранные размеры из формы
    let selectedSizes = document.querySelectorAll('#sizesClothesModal .form-control:not([readonly]):not([disabled])');
    let newSizes = {};
    selectedSizes.forEach(input => {
        let size = input.getAttribute('id').replace('size_', '').trim();
        let quantity = parseInt(input.value.trim(), 10);
        let sizeType = input.getAttribute('data-size-type') || "";

        if (size.startsWith('subcategorySize')) return;
        if (special_clothes_sizes.includes(size)) {
            sizeType = 'РОССИЯ';
        }

        newSizes[size] = { quantity, sizeType };

        // Если размер уже есть, обновляем количество
        if (existingSizes[size]) {
            existingSizes[size].element.querySelector('#quantity_info').textContent = quantity;
            existingSizes[size].element.querySelector('input[name="quantity"]').value = quantity;
        } else {
            // Создаем новый элемент
            let sizeQuantityHTML = `
                <div class="important-card__item important-card__size ms-2">
                    <div class="d-flex align-items-center g-3">
                        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" onclick="$(this).closest('div').parent().remove();setClothes();"
                            viewBox="0 0 20 20" fill="none">
                            <path fill-rule="evenodd" clip-rule="evenodd"
                                d="M4.34074 0.312213C8.07158 -0.104071 11.9285 -0.104071 15.6593 0.312213C17.7413 0.544517 19.4209 2.18214 19.6655 4.26889C20.1115 8.07671 20.1115 11.9234 19.6655 15.7312C19.4209 17.8179 17.7413 19.4555 15.6593 19.6878C11.9285 20.1041 8.07158 20.1041 4.34074 19.6878C2.25873 19.4555 0.579043 17.8179 0.33457 15.7312C-0.111523 11.9234 -0.111523 8.07671 0.33457 4.26889C0.579043 2.18214 2.25873 0.544517 4.34074 0.312213ZM10 9.08981H10.9117H15.1575C15.661 9.08981 16.0692 9.49734 16.0692 10C16.0692 10.5027 15.661 10.9102 15.1575 10.9102H10.9117C10.9117 10.9102 10.2506 10.9102 10 10.9102C9.74947 10.9102 9.46208 10.9102 9.46208 10.9102H9.08832H4.84265C4.33912 10.9102 3.93094 10.5027 3.93094 10C3.93094 9.49734 4.33912 9.08981 4.84265 9.08981H9.08832H10Z"
                                fill="white" />
                        </svg>
                        <div class="ms-2">
                            <span id="size_info">${size}</span>
                            <span id="size_type_info" style="font-size: 10px">${sizeType}</span>
                        </div>
                    </div>
                    <div class="important-card__val"><span id="quantity_info">${quantity}</span> <span>шт.</span></div>
                    <input type="hidden" id="size" name="size" value="${size}">
                    <input type="hidden" id="quantity" name="quantity" value="${quantity}">
                    <input type="hidden" id="size_type" name="size_type" value="${sizeType}">
                </div>`;

            sizesQuantityBlock.innerHTML += sizeQuantityHTML;
        }
    });

    Object.keys(existingSizes).forEach(size => {
        if (!newSizes[size] && !Object.values(clothes_types_sizes_dict).some(sizes => sizes.includes(size))) {
            return;
        }
        if (!newSizes[size]) {
            existingSizes[size].element.remove();
        }
    });
    setClothes();
}


function subcategory_size_add(clothingType) {
    let sizeInput = document.getElementById(`subcategorySizeInput${clothingType}`);
    let quantityInput = document.getElementById(`subcategorySizeQuantity${clothingType}`);
    let errorBlock = document.getElementById(`subcategorySizeError${clothingType}`);

    let size = sizeInput.value.trim();
    let quantity = parseInt(quantityInput.value.trim(), 10);

    let sizePattern = /^[A-Za-z0-9]([-]?[A-Za-z0-9]|[.,]?[0-9]){0,7}$/;

    // Очистка ошибок при вводе
    sizeInput.addEventListener('input', () => errorBlock.textContent = "");
    quantityInput.addEventListener('input', () => errorBlock.textContent = "");

    // Проверка, есть ли размер в словаре
    let foundType = null;
    for (let type in clothes_types_sizes_dict) {
        if (clothes_types_sizes_dict[type].includes(size)) {
            foundType = type;
            break;
        }
    }

    if (foundType) {
        errorBlock.textContent = `Размер '${size}' уже существует в категории '${foundType}'.`;
        return;
    }

    // Проверка на корректность ввода
    if (!sizePattern.test(size)) {
        errorBlock.textContent = "Размер должен содержать только латиницу, цифры и знак дефиса между ними (1-8 символов). Допускаются дробные размеры";
        return;
    }
    if (isNaN(quantity) || quantity < 1) {
        errorBlock.textContent = "Введите корректное количество (минимум 1).";
        return;
    }

    // Очистка ошибок
    errorBlock.textContent = "";

    let sizesQuantityBlock = document.getElementById('sizes_quantity');

    // Проверяем, есть ли уже такой размер в карточке
    let existingSizeBlocks = sizesQuantityBlock.getElementsByClassName('important-card__item');
    let sizeFound = false;

    for (let block of existingSizeBlocks) {
        let sizeSpan = block.querySelector('#size_info');
        if (sizeSpan && sizeSpan.textContent === size) {
            let quantitySpan = block.querySelector('#quantity_info');
            let newQuantity = quantity;
            quantitySpan.textContent = newQuantity; // Обновляем количество
            block.querySelector('input[name="quantity"]').value = newQuantity;
            sizeFound = true;
            break;
        }
    }

    // Если размер не найден, создаем новый блок
    if (!sizeFound) {
        let sizeQuantityHTML = `
            <div class="important-card__item important-card__size ms-2">
                <div class="d-flex align-items-center g-3">
                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" onclick="$(this).closest('div').parent().remove();setClothes();"
                        viewBox="0 0 20 20" fill="none">
                        <path fill-rule="evenodd" clip-rule="evenodd"
                            d="M4.34074 0.312213C8.07158 -0.104071 11.9285 -0.104071 15.6593 0.312213C17.7413 0.544517 19.4209 2.18214 19.6655 4.26889C20.1115 8.07671 20.1115 11.9234 19.6655 15.7312C19.4209 17.8179 17.7413 19.4555 15.6593 19.6878C11.9285 20.1041 8.07158 20.1041 4.34074 19.6878C2.25873 19.4555 0.579043 17.8179 0.33457 15.7312C-0.111523 11.9234 -0.111523 8.07671 0.33457 4.26889C0.579043 2.18214 2.25873 0.544517 4.34074 0.312213ZM10 9.08981H10.9117H15.1575C15.661 9.08981 16.0692 9.49734 16.0692 10C16.0692 10.5027 15.661 10.9102 15.1575 10.9102H10.9117C10.9117 10.9102 10.2506 10.9102 10 10.9102C9.74947 10.9102 9.46208 10.9102 9.46208 10.9102H9.08832H4.84265C4.33912 10.9102 3.93094 10.5027 3.93094 10C3.93094 9.49734 4.33912 9.08981 4.84265 9.08981H9.08832H10Z"
                            fill="white" />
                    </svg>
                    <div class="ms-2">
                        <span id="size_info">${size}</span>
                        <span id="size_type_info" style="font-size: 10px">${clothingType}</span>
                    </div>
                </div>
                <div class="important-card__val"><span id="quantity_info">${quantity}</span> <span>шт.</span></div>
                <input type="hidden" name="size" value="${size}">
                <input type="hidden" name="quantity" value="${quantity}">
                <input type="hidden" id="size_type" name="size_type" value="${clothingType}">
            </div>`;

        sizesQuantityBlock.innerHTML += sizeQuantityHTML;
    }

    // Очистка полей ввода
    sizeInput.value = '';
    quantityInput.value = '';
    setClothes();
}




function clear_clothesSizes_modal() {
    document.getElementById('sizesClothesDiv').innerHTML = '';
}

function check_clothes_quantity_input(block){
    var value = parseFloat(block.value);
    var min = parseFloat(block.min);
    var max = parseFloat(block.max);

    // Check if the input value falls outside the specified range
    if (value < min || value > max || isNaN(value)) {
        // If so, set the input value to 0
        block.value = 1;
    }
}


function create_size_blocks(sizes, clothingType) {
    let sizesBlock = '';
    const special_clothes_sizes = ["ЕДИНЫЙ РАЗМЕР", "ONE SIZE"];
    let quantityMap = {}; // Объект для хранения количества каждого специального размера

    // Сначала собираем данные о наличии размеров и их количестве
    document.querySelectorAll('#sizes_quantity .important-card__size').forEach(item => {
        let sizeTypeInCard = item.querySelector('#size_type_info').textContent;
        let sizeInCard = item.querySelector('#size_info').textContent;
        let quantity = parseInt(item.querySelector('#quantity_info').textContent);

        // Если это специальный размер, добавляем его в карту (объект)
        if (clothingType === 'ОСОБЫЕ_РАЗМЕРЫ' && sizeTypeInCard === 'РОССИЯ' && special_clothes_sizes.includes(sizeInCard)) {
            quantityMap[sizeInCard] = quantity; // Запоминаем количество каждого уникального размера
        } else if (sizeTypeInCard === clothingType) {
            quantityMap[sizeInCard] = quantity;
        }
    });

    // Теперь строим блоки с учетом собранных данных
    for (let i = 0; i < sizes.length; i++) {
        let size = sizes[i];
        let sizeAlreadyExists = quantityMap.hasOwnProperty(size); // Проверяем, есть ли размер в quantityMap
        let quantity = sizeAlreadyExists ? quantityMap[size] : 0;

        if (!sizeAlreadyExists) {
            sizesBlock += `
                <div class="col-md-4 border-bottom border-0 border-warning text-center mt-1" >
                    <div class="row">
                        <div class="col-5 my-2" onclick="setQuantitySize('${size}');"><span style="cursor: pointer">${size}</span></div>
                        <div class=" col-7"><input type="number" class="form-control ms-1 input-light-grey"
                         min="1" max="50000" id="size_${size}" name="size_${size}" style="display: none;" placeholder="0"
                         data-size-type="${clothingType}" disabled onchange="check_clothes_quantity_input(this);updateSizesQuantityBlock()"></div>
                    </div>  
                </div>`;
        } else {
            sizesBlock += `
                <div class="col-md-4 border-bottom border-0 border-warning text-center mt-1" >
                    <div class="row">
                        <div class="col-5 my-2" onclick="setQuantitySize('${size}');"><span style="cursor: pointer">${size}</span></div>
                        <div class=" col-7"><input type="number" class="form-control ms-1"
                         min="1" max="50000" id="size_${size}" name="size_${size}" value="${quantity}" placeholder="0"
                         data-size-type="${clothingType}" onchange="check_clothes_quantity_input(this);updateSizesQuantityBlock()"></div>
                    </div>  
                </div>`;
        }
    }
    return sizesBlock;
}

function deleteCell() {
    var cur = $(this).closest('div');
    cur.parent().remove();
    setClothes();
}

function isTenDigits(code){ return /^\d{10}$/.test(code); }

// проверка по префиксам, если включён режим агрегирования
function isAllowedTnved(code){
  if (!window.HAS_AGGR) return isTenDigits(code); // без агрегатора — лишь формат
  return isTenDigits(code) && (window.HAS_AGGR_LIST || []).some(prefix => code.startsWith(prefix));
}

function check_tnved(submit){
  if (submit !== 'submit') return true;

  const code = (document.getElementById('tnved_code').value || '').trim();

  if (!isTenDigits(code)){
    show_form_errors(['Заполните ТНВЭД: 10 цифр']);
    $('#form_errorModal').modal('show');
    return false;
  }

  if (!isAllowedTnved(code)){
    // сообщение в общий модал ошибок
    show_form_errors(['Код ТНВЭД не разрешён для текущего режима заказа. Проверьте ваш тнвэд во втором окне или обратитесь к модератору']);
    $('#form_errorModal').modal('show');

    // и показываем модалку со списком разрешённых (таблица)
    if (typeof showNotAllowedModal === 'function') {
      showNotAllowedModal(code);

    }
    return false;
  }

  return true; // всё ок — отправляем форму
}

// function make_message(message, type) {
//     var block_messages = document.getElementById('all_messages');
//     block_messages.insertAdjacentHTML('beforeend', `<div class="alert alert-${type} alert-dismissible fade show" id="alert-message-error"
//                                         role="alert">
//                                        <button type="button"  class="btn-close" data-dismiss="alert" aria-label="Close">
//                                        </button>
//                                        ${message}
//                                    </div>`);
// }
//
//
// function show_form_errors(errors){
//     let errors_block = document.getElementById('form_errormodaldiv');
//     errors.forEach(function (el, index) {
//                 errors_block.innerHTML += `${index+1}. <u>${el}</u><br>`;
//                 }
//             )
// }
//
// function clear_errorform(){
//     document.getElementById('form_errormodaldiv').innerHTML='';
// }

function get_tnveds(url, csrf){
    let cl_type = document.getElementById('type').value;
    if(!cl_type){

        show_form_errors(['Выберите тип одежды до выбора ТНВЕД',]);
        $('#form_errorModal').modal('show');
        return
    }
    $.ajax({
        url: url,
        headers:{"X-CSRFToken": csrf},
        method:"POST",
        data: {'cl_type': cl_type},

        success:function(data)
        {
            if(data.status == 'danger' || data.status == 'error'){
                 show_form_errors([data.message,]);
                 $('#form_errorModal').modal('show');

            }
            else if( data.status == 'success'){
                $('#manual_tnved_insert').html(data);
                $("#manual_tnved_insert").append(data.tnved_report);
                $('#manualTnvedModal').modal('show')

            }
            else{
                 show_form_errors(['Обновите страницу...',]);
                 $('#form_errorModal').modal('show');

            }
        },
        error: function() {
         show_form_errors(['Ошибка CSRF. Обновите страницу и попробуйте снова',]);
         $('#form_errorModal').modal('show');
     }
   });
  }

function clothes_manual_tnved(){
    const m_tnved = (document.getElementById("manual_tnved_input").value || "").trim();

    // 1. Базовая валидация: должно быть 10 цифр
    if (m_tnved && !/^\d{10}$/.test(m_tnved)){
        document.getElementById('manual_tnved_message').textContent =
            'Введите 10-значный код или оставьте пустым';
        setTimeout(clear_clothes_tnved_m, 5000);
        return;
    }

    // 2. Проверка: код есть в глобальном списке all_tnved (тот что бэкенд передаёт для выбранного типа одежды)
    if (m_tnved && !all_tnved.includes(m_tnved)){
        document.getElementById('manual_tnved_message').textContent =
            'Некорректный ТНВЭД, попробуйте другой или обратитесь к вашему менеджеру';
        setTimeout(clear_clothes_tnved_m, 5000);
        return;
    }

    // // 3. Проверка на режим "аггрегатор"
    // if (window.HAS_AGGR && m_tnved){
    //     const ok = (window.HAS_AGGR_LIST || []).some(prefix => m_tnved.startsWith(prefix));
    //     if (!ok){
    //         document.getElementById('manual_tnved_message').textContent = 'Код не разрешён.';
    //         showNotAllowedModal(m_tnved);
    //         return;
    //     }
    // }

    // 4. Всё прошло → пишем в поле формы и закрываем
    document.getElementById('tnved_code').value = m_tnved;
    clear_manual_tnved();
    $('#manualTnvedModal').modal('hide');
}

function clear_manual_tnved(){
    document.getElementById('manual_tnved_insert').innerHTML='';
    $('#manual_tnved_input').val('');

}

function clear_clothes_tnved_m(){
    document.getElementById('manual_tnved_message').innerHTML='';
}


function renderAllowedTable(){
  const body = document.getElementById('tnvedAllowedBody');
  if (!body) return;
  const rows = (window.HAS_AGGR_LIST || []).map(code => {
    const desc = (window.HAS_AGGR_DICT && window.HAS_AGGR_DICT[code]) ? window.HAS_AGGR_DICT[code] : '';
    return `<tr><td><code>${code}</code></td><td>${desc}</td></tr>`;
  }).join('');
  body.innerHTML = rows || '<tr><td colspan="2" class="text-muted">Список пуст</td></tr>';
}

function showNotAllowedModal(code){
    // вставляем введённый код внутрь <span id="tnvedCodeOrderAggrModalValue">
  const span = document.getElementById('tnvedCodeOrderAggrModalValue');
  if (span) {
    span.textContent = code || '';
  }

  renderAllowedTable();
  const el = document.getElementById('tnvedDeniedModal');
  const modal = bootstrap.Modal.getOrCreateInstance(el);
  modal.show();
}

function selectTnved(code){
    // если включён аггрегатор — проверим по префиксам
    // if (window.HAS_AGGR) {
    //     const ok = window.HAS_AGGR_LIST.some(prefix => code.startsWith(prefix));
    //     if (!ok) {
    //         showNotAllowedModal();
    //         return;
    //     }
    // }

    // иначе принимаем
    document.getElementById('tnved_code').value = code;
    clear_manual_tnved();
    $('#manualTnvedModal').modal('hide');
}

document.addEventListener('DOMContentLoaded', function () {
    const switchInput = document.getElementById('aggrModeSwitch');

    function updateSwitchStyle() {
        const label = document.getElementById('aggrModeLabel');
        if (!label) return;

        const switchInput = document.getElementById('aggrModeSwitch');
        if (switchInput.checked) {
            label.textContent = 'Режим заказа по наборам';
            // label.classList.add('text-warning');
            switchInput.classList.add('bg-warning', 'border-warning');
            window.HAS_AGGR = true;
        } else {
            label.textContent = 'Режим заказа по позициям';
            // label.classList.remove('text-warning');
            switchInput.classList.remove('bg-warning', 'border-warning');
            window.HAS_AGGR = false;
        }
    }

    switchInput.addEventListener('change', updateSwitchStyle);

    // при загрузке страницы
    updateSwitchStyle();
});