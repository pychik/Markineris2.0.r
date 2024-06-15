function cancel_order(o_id, url, csrf){
        document.getElementById("cancel_orderModalLabel").innerHTML = `Вы хотите отменить заказ номер ${o_id}!`
        document.getElementById("order_cancel_block").innerHTML = `<form id="cancel_order_form" method="post" action="${url}"
                                title="Отменить заказ № ${o_id}"><input type="hidden" name="csrf_token" value="${csrf}"/>
                                <label style="font_size:14:px">Причина отмены заказа!</label>
                                <input type="text" minlength="3" maxlength="150" name="cancel_order_comment" class="form-control"
                                       placeholder="Введите причину отказа" required>
                                </form>`
        $('#cancel_orderModal').modal('show')
    }

function clear_cancel_order(){
    document.getElementById("cancel_orderModalLabel").innerHTML = ''
    document.getElementById("order_cancel_block").innerHTML = ''
}

function problem_order(o_id, url, csrf){
    document.getElementById("problem_orderModalLabel").innerHTML = `Вы хотите указать проблему в заказе номер ${o_id}!`
    document.getElementById("order_problem_block").innerHTML = `<form method="post" id="problem_order_form" action="${url}"
                            title="Указать проблему заказа № ${o_id}">
                            <input type="hidden" name="csrf_token" value="${csrf}"/>
                            <label style="font_size:14:px">Проблема в заказе!</label>
                            <input type="text" minlength="3" maxlength="150" name="problem_order_comment" class="form-control"
                                   placeholder="Введите описание проблемы" required>

                        </form>`
    $('#problem_orderModal').modal('show')
}

function clear_problem_order(){
    document.getElementById("problem_orderModalLabel").innerHTML = ''
    document.getElementById("order_problem_block").innerHTML = ''
}

function change_operator(o_id, url, csrf){
    var manager_array = '';
    for(var x=0; x<managers_list.length; x++){
        manager_array += `<option value="${managers_list[x][0]}">${managers_list[x][1]}</option>`;
    }

    var oper_form = `<form method="post" id="change_operator_form" action="${url}"
                            title="Поменять оператора(менеджера) заказа ${o_id}">
                            <input type="hidden" name="csrf_token" value="${csrf}"/>
                            <label style="font_size:14:px">Выберите менеджера из выпадающего списка!</label>
                            <select class="form-control" id="operator_id" name="operator_id" required>
                               <option disabled selected value="">Выберите менеджера...</option>` +
                                manager_array + `</select></form>`
    // alert(ob);
    document.getElementById("change_operatorModalLabel").innerHTML = `Вы хотите поменять менеджера в заказе номер ${o_id}!`
    document.getElementById("change_operator_block").innerHTML = oper_form;


    $('#change_operatorModal').modal('show')
}

function clear_change_operator(){
    document.getElementById("change_operatorModalLabel").innerHTML = ''
    document.getElementById("change_operator_block").innerHTML = ''
}

function upload_order_input(input_id, selected_filename, o_id, url, csrf) {

    if (!window.FileReader) { // This is VERY unlikely, browser support is near-universal
        console.log("Попробуйте другой браузер! Ваш не поддерживает функционал загрузки файлов.");
        return;
    }
    var input = document.getElementById(input_id);

    if (!input.files) { // This is VERY unlikely, browser support is near-universal
        alert("Попробуйте другой браузер! Ваш не поддерживает функционал загрузки файлов.");
    } else if (!input.files[0]) {
        alert("Please select a file before clicking 'Load'");
    } else {
        var file = input.files[0];
        if (file.size >= OF_MAX_SIZE) {
            let mes = file.name + " весит " + file.size + " байт. Это больше установленного лимита " +  OF_MAX_SIZE

            // clear input file
            input.value = '';
            attach_link(o_id, mes, url, csrf);
        } else {
            $(selected_filename).text($('#' + input_id)[0].files[0].name);
        }
    }
}

function filter_manager(url){
    window.location.href = url + document.getElementById("selectManager").value;

}


function attach_link(o_id, mes, url, csrf){
        document.getElementById("attach_linkModalLabel").innerHTML = `${mes} Прикрепить ссылку на файл к заказу ${o_id}?`
        document.getElementById("attach_link_block").innerHTML = `<form id="attach_link_form" method="post" action="${url}"
                                title="Прикрепить ссылку на файл к заказу № ${o_id}"><input type="hidden" name="csrf_token" value="${csrf}"/>
                                <label style="font_size:14:px">Ссылка на файл</label>
                                <input type="text" minlength="5" maxlength="100" id="of_link" name="of_link" class="form-control"
                                       placeholder="Вставьте ссылку на файл" required>
                                </form>`
        $('#attach_linkModal').modal('show')
    }

function clear_attach_link(){
    document.getElementById("cancel_orderModalLabel").innerHTML = ''
    document.getElementById("order_cancel_block").innerHTML = ''

}

function copy_buffer(str, message_block) {
    let tmp = document.createElement('INPUT'), // Создаём новый текстовой input
        focus = document.activeElement; // Получаем ссылку на элемент в фокусе (чтобы не терять фокус)

    tmp.value = str; // Временному input вставляем текст для копирования

    document.body.appendChild(tmp); // Вставляем input в DOM
    tmp.select(); // Выделяем весь текст в input
    document.execCommand('copy'); // Магия! Копирует в буфер выделенный текст (см. команду выше)
    document.body.removeChild(tmp); // Удаляем временный input
    focus.focus(); // Возвращаем фокус туда, где был


    var text = 'ссылка скопирована в буфер';
    alert(text);
}

function loadingCircle() {

      var overlay = document.getElementById("overlay_loading");
      overlay.style.display = "block";

    }
function close_Loading_circle(){
    var overlay = document.getElementById("overlay_loading");
  overlay.style.display = "";
}

function timer_pad ( val ) { return val > 9 ? val : "0" + val; }

function timing_management(delta, obj_id, min_id, sec_id){
    setInterval( function(){

       if (delta > delta_timer_color*60 && document.getElementById(obj_id).classList.contains('blink_me') !== true){

                    document.getElementById(obj_id).classList.remove('badge-warning');
                    document.getElementById(obj_id).classList.add('bg-error');
                    document.getElementById(obj_id).classList.add('blink_me')

            }
            $(`#${sec_id}`).html(timer_pad(++delta%60));
            $(`#${min_id}`).html(timer_pad(Math.floor(delta/60)));

        }, 1000);

}


function change_external_problem_stage(url, update_url, csrf) {
    $.ajax({
        url: url,
        headers: {"X-CSRFToken": csrf},
        method: "POST",
        data: {},
        success: function (data) {
            // make_message(data.message, data.status);


            if (data.status === 'success') {
                update_crm_info(update_url);
            }
            make_message(data.message, data.status);
        },
        error: function () {
            make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');
            // close_Loading_circle();
        }
    });
}


function update_crm_info(url){

   $.ajax({
    url:url,
    method:"GET",
    success:function(data)
    {
        // console.log(data)

      $('#update_all_info').html(data);
      $("#update_all_info").append(data.htmlresponse);
      // make_message('Страница обновлена успешно', 'success');
        // make_message(msg, data.status);
        // setTimeout(function() {location.reload(true);}, 5000);
    },
     error: function() {
        make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');
    }
   });

   setTimeout(function() {clear_user_messages();}, 15000);

}

function make_message(message, type) {
    document.getElementById('all_messages').innerHTML = '';
    let title = '';
    if (type === 'error') {
        type = 'danger';
    }

    if (type === 'danger') {
        title = 'Ошибка';
    } else if (type === 'warning') {
        title = 'Предупреждение';
    } else {
        title = 'Успех';
    }

    var block_messages = document.getElementById('all_messages');
    block_messages.insertAdjacentHTML('beforeend', `<div id="alert-message-${type}" class="alert alert-${type} alert-dismissible fade show" role="alert">
                            <button type="button" class="close" data-dismiss="alert" aria-label="Close">
                                <span aria-hidden="true">&times;</span>
                            </button>
                            <b>${title}</b> ${message}
                        </div>`);
    setTimeout(function() {clear_user_messages();}, 15000);

}

function clear_user_messages() {
    var allAlerts = document.querySelectorAll('.alert');

    allAlerts.forEach(function (el) {
        el.getElementsByTagName("button")[0].click();
     });
    // $('#alert-message-error').alert('close');
    // $('#alert-message-warning').alert('close');
    // $('#alert-message-success').alert('close');
    // ;
}


function clear_search_order_res(){
        $('#OrderSearchResult').html('');
    }


function search_crm_order(url, csrf){
    // clear_search_order_res();
    let search = document.getElementById('searchOrdertext').value;
    if (search.length < 2){
        make_message('Введите полный номер заказа', 'warning');
        return
    }
    // console.log(search);
    $.ajax({
    url:url,
    headers:{"X-CSRFToken": csrf},
    method:"POST",
    data: {'search_order_idn': search},
    success:function(data)
    {
        // make_message(data.message, data.status);

        // update_crm_info(update_agents_url);
        if (data.status !== 'success'){
            make_message(data.message, data.status);
            return
        }

        $('#OrderSearchResult').html(data);
        $("#OrderSearchResult").append(data.htmlresponse);
    },
     error: function() {
        make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');
        // close_Loading_circle();
    }
   });

   setTimeout(function() {clear_user_messages();}, 15000);
}



function update_spec_block_info(url, block, stage, csrf){
   loadingCircle();
   $.ajax({
    url:url,
    method:"POST",
    headers:{"X-CSRFToken": csrf},
    data:{'stage': stage},
    success:function(data)
    {
        // console.log(data)
      close_Loading_circle();
      $('#' + block).html(data);
      $('#' + block).append(data.htmlresponse);
      // make_message('Страница обновлена успешно', 'success');
        // make_message(msg, data.status);
        // setTimeout(function() {location.reload(true);}, 5000);
    },
     error: function() {
        close_Loading_circle();
        make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');
    }
   });

   setTimeout(function() {clear_user_messages();}, 15000);

}