function get_information(link, callback) {
    var xhr = new XMLHttpRequest();
    xhr.open("GET", link, true);
    xhr.onreadystatechange = function () {
        if (xhr.readyState === 4) {
            if (!xhr.responseText.startsWith('http')) {
                callback(xhr.responseText);
            } else {
                window.location.href = window.location.origin;
            }

        }
    };
    xhr.send(null);
}

function perform_modal_copy_link(u_id, u_name) {
    var modal_block = document.getElementById('copy_link_modals');
    modal_block.innerHTML = ` <div class="modal fade" id="user_linkModal${u_id}" tabindex="-1" role="dialog" data-bs-backdrop="static" aria-labelledby="user_linkModal${u_id}Label" aria-hidden="true">
          <div class="modal-dialog modal-lg" data-backdrop="static" role="document">
            <div class="modal-content">
              <div class="modal-header bg-warning">
                <h5 class="modal-title" id="user_linkModal${u_id}Label">Ссылка для смены пароля по запросу.</h5>
                <button type="button" class="btn-close" onclick="clear_copy_link();" data-bs-dismiss="modal" aria-label="Close">
                </button>
              </div>
              <div class="modal-body">
                <h5>Ссылка для смены пароля пользователя ${u_name}. Нажмите на дискету, чтобы скопировать</h5>
                  <div class="row">
                    <div class="col-11 text-center" >
                      <input class="form-control" readonly="true" type="text"
                             onclick=""
                             id="user_link${u_id}" >
                    </div>
                    <div class="col-1 text-center" >
                      <a id="copyText" type="button"
                         title="Скопировать ссылку"
                         onclick="javascript:copy_buffer('user_link${u_id}',
                                             'user_link_message${u_id}');">&#128190;</a>
                    </div>

                  </div>
                  <small class="text-secondary">Срок работы ссылки для смены пароля <b>3 часа</b> с момента ее создания.
                       После смены пароля ссылка будет недействительна.</small>
                  <span id="user_link_message${u_id}" style="color:#23c1fc"></span>
              </div>
              <div class="modal-footer">
                <button type="button" class="btn btn-secondary" onclick="clear_copy_link();" data-bs-dismiss="modal">Закрыть</button>

              </div>
            </div>
          </div>
        </div>`;

}


function clear_copy_link() {
    document.getElementById("copy_link_modals").innerHTML = '';
}

function change_user_password_main(url, csrf, username){
    var modal_block = document.getElementById('change_user_password_modal');
    modal_block.innerHTML = ` <div class="modal fade" id="cup_modal" tabindex="-1" role="dialog" data-bs-backdrop="static" aria-labelledby="cup_modalLabel" aria-hidden="true">
          <div class="modal-dialog modal-lg" data-backdrop="static" role="document">
            <div class="modal-content">
              <div class="modal-header">
                <h5 class="modal-title">Вы уверены, что хотите поменять пароль для пользователя ${username}?</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"  onclick="clear_change_user_password()" aria-label="Close">
                </button>
              </div>
              <div class="modal-body">
                
                  
                    <div class="input-group mb-3">
                        <input type="text" name="new_password" id="bck_changed_new_password" minlength="6" maxlength="15" class="form-control" placeholder="Введите новый пароль" aria-label="Recipient's password" aria-describedby="basic-addon2" required autofocus>
                        <button class="btn btn-sm btn-accent" type="button" id="basic-addon2" onclick="bck_change_user_password('${url}', '${csrf}');" 
                                data-bs-dismiss="modal">Изменить пароль</button>
                    </div>

        
                  </form>
                  
              </div>
              <div class="modal-footer">
                <button type="button" class="btn btn-secondary" onclick="clear_change_user_password();" data-bs-dismiss="modal">Закрыть</button>

              </div>
            </div>
          </div>
        </div>`;

    $('#cup_modal').modal('show');
    }

function clear_change_user_password(){
    document.getElementById('change_user_password_modal').innerHTML = '';

    }

function bck_change_user_password(url, csrf) {
    var new_password = document.getElementById('bck_changed_new_password').value;
    if (new_password.length < 6) {
        make_message('Пароль должен быть не менее 6 символов', 'danger');
        return;
    }
    $.ajax({
        url: url,
        headers: {"X-CSRFToken": csrf},
        method: "POST",
        data: {'new_password': new_password},
        success: function (data) {
            make_message(data.message, data.status);


        },
        error: function () {
            make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');
        }
    });
}



let reanimateTableRequest = null;
let reanimateAppliedFilters = null;

function getReanimateFilters() {
    return {
        date_quantity: $('#date_quantity').val(),
        date_type: $('#date_type').val(),
        sort_type: $('#reanimate_sort').val(),
        include_without_orders: $('#include_without_orders').is(':checked') ? 1 : 0
    };
}

function sortReanimateUsers(direction) {
    const filters = Object.assign({}, reanimateAppliedFilters || getReanimateFilters(), {sort_type: direction});
    bck_get_users_reanimate(document.getElementById('user_response').dataset.url, filters);
}

function bck_get_users_reanimate(url, filters) {
    const form = document.getElementById('reanimate_filters');
    if (!form.reportValidity()) return;
    const target = new URL(url, window.location.href);
    const params = filters || (target.searchParams.has('date_quantity') ? {
        date_quantity: target.searchParams.get('date_quantity'),
        date_type: target.searchParams.get('date_type'),
        sort_type: target.searchParams.get('sort_type') || $('#reanimate_sort').val(),
        include_without_orders: target.searchParams.get('include_without_orders') || '1'
    } : getReanimateFilters());
    Object.keys(params).forEach(key => target.searchParams.set(key, params[key]));
    target.searchParams.set('bck', '1');
    if (reanimateTableRequest) reanimateTableRequest.abort();
    const container = $('#user_response');
    container.stop(true, true).css('opacity', 1).attr('aria-busy', 'true');
    reanimateTableRequest = $.ajax({
        url: target.href,
        method: 'GET',
        success: function (data) {
            if (typeof data.htmlresponse !== 'string') {
                showReanimateError();
                return;
            }
            reanimateAppliedFilters = Object.assign({}, data.filters);
            $('#date_quantity').val(data.filters.date_quantity);
            $('#date_type').val(data.filters.date_type);
            $('#reanimate_sort').val(data.filters.sort_type);
            $('#include_without_orders').prop('checked', Number(data.filters.include_without_orders) === 1);
            container.css('opacity', 1).html(data.htmlresponse).addClass('reanimate-table-enter');
            setTimeout(() => container.removeClass('reanimate-table-enter'), 220);
        },
        error: function (xhr, status) {
            if (status !== 'abort') showReanimateError();
        },
        complete: function () {
            container.attr('aria-busy', 'false');
        }
    });
    return reanimateTableRequest;
}

function showReanimateError() {
    const container = $('#user_response');
    container.find('[data-reanimate-error], [role="status"]').remove();
    container.stop(true, true).css('opacity', 1).prepend(
        $('<div class="alert alert-danger" role="alert" data-reanimate-error></div>')
            .text('Не удалось загрузить клиентов. Нажмите «Показать клиентов», чтобы повторить.')
    );
}

function get_users_reanimate_report_excel(url, csrf) {
    const filters = getReanimateFilters();
    // Apply the same filter snapshot to the visible table before exporting it.
    const tableRequest = bck_get_users_reanimate(document.getElementById('user_response').dataset.url, filters);
    if (!tableRequest) return;
    $('#overlay_loading').show();
    tableRequest.done(function (data) {
        if (typeof data.htmlresponse !== 'string') {
            $('#overlay_loading').hide();
            return;
        }
        $.ajax({
            url: url,
            headers: {'X-CSRFToken': csrf},
            method: 'POST',
            data: filters,
            xhrFields: {responseType: 'blob'},
            success: function (response, status, xhr) {
                if (xhr.getResponseHeader('data_status') !== 'success') {
                    make_message('Не удалось скачать отчёт. Обновите страницу и попробуйте снова.', 'danger');
                    return;
                }
                const blobUrl = window.URL.createObjectURL(response);
                const link = document.createElement('a');
                link.href = blobUrl;
                link.download = decodeURIComponent(xhr.getResponseHeader('data_file_name') || 'отчет_реанимация_пользователей.xlsx');
                document.body.appendChild(link);
                link.click();
                link.remove();
                window.URL.revokeObjectURL(blobUrl);
            },
            error: function () {
                make_message('Не удалось скачать отчёт. Попробуйте ещё раз.', 'danger');
            },
            complete: function () { $('#overlay_loading').hide(); }
        });
    }).fail(function () { $('#overlay_loading').hide(); });
}

function check_ra_filter_Validity(input) {
// Get the maximum value allowed
    var maxValue = parseFloat(input.getAttribute("max"));
    var minValue = parseFloat(input.getAttribute("min"));

// Get the current value of the input
    var value = parseFloat(input.value);

// Check if the value is greater than the maximum allowed value
    if (value > maxValue) {
        // Clear the input value
        input.value = maxValue;
    }
    else if (value < minValue) {
        // Clear the input value
        input.value = minValue;
    }
}

function uncheck_agent_type_switch(switch_id, button_id){
    var bg_color = 'bg-warning';

    if(document.getElementById(switch_id).checked === true){
        document.getElementById(button_id).classList.remove('disabled');
        document.getElementById(switch_id).classList.add(bg_color);
    }
    else{
        document.getElementById(button_id).classList.add('disabled');
        document.getElementById(switch_id).classList.remove(bg_color)
    }
}

function copy_to_buffer(str) {
    let focus = document.activeElement; // Сохраняем элемент, который в фокусе

    // Проверяем поддержку Clipboard API
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(str)
            .then(() => {
                var text = `Текст "${str}" скопирован в буфер`;
                make_message(text, 'success'); // Вызываем вашу функцию для уведомления
            })
            .catch(err => {
                var text = `Ошибка копирования текста: ${err}`;
                make_message(text, 'error');
            });
    } else {
        // Фолбек для старых браузеров, использующих execCommand
        let tmp = document.createElement('INPUT'); // Создаем временный input
        tmp.value = str; // Вставляем текст
        document.body.appendChild(tmp); // Добавляем input в DOM
        tmp.select(); // Выделяем текст
        try {
            document.execCommand('copy'); // Пытаемся скопировать текст
            var text = `Текст "${str}" скопирован в буфер`;
            make_message(text, 'success');
        } catch (err) {
            var text = `Ошибка копирования текста: ${err}`;
            make_message(text, 'error');
        }
        document.body.removeChild(tmp); // Удаляем временный input
    }

    if (focus) focus.focus(); // Возвращаем фокус на предыдущий элемент
}
