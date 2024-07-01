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


function bck_get_users_reanimate(url) {

    let sort_mode = 0;
    if (document.getElementById("asc_type").checked) {
        sort_mode = 1;
    }
    $.ajax({
        url: url,
        method: "GET",
        data: {
            date_quantity: $('#date_quantity').val(),
            date_type: $('#date_type').val(),
            sort_type: sort_mode
        },
        success: function (data) {
            $('#user_response').html(data);
            $("#user_response").append(data.htmlresponse);

        }
    });

}

function get_users_reanimate_report_excel(url, csrf) {
    let sort_mode = 0;
    if (document.getElementById("asc_type").checked) {
        sort_mode = 1;
    }

    $('#overlay_loading').show();
    $.ajax({
        url: url,
        headers: { "X-CSRFToken": csrf },
        method: "POST",
        data: {date_quantity: $('#date_quantity').val(),
               date_type: $('#date_type').val(),
               sort_type: sort_mode},
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
                link.download = decodeURIComponent(dataName) || 'отчет_реанимация_пользователей.xlsx'; //
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