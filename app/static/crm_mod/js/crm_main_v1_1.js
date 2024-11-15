function cancel_order(order_idn, o_id, decrement_id,  url_text, csrf){
        document.getElementById("cancel_orderModalLabel").innerHTML = `Вы хотите отменить заказ номер ${order_idn}!`
        document.getElementById("order_cancel_block").innerHTML = `
                <div class="modal-body text-justify">
                    <form id="cancel_order_form" method="post" action="${url_text}"
                                    title="Отменить заказ № ${order_idn}"><input type="hidden" name="csrf_token" value="${csrf}"/>
                                    <label style="font_size:14:px">Причина отмены заказа!</label>
                                    <input type="text" minlength="3" maxlength="150" id="cancel_order_comment" name="cancel_order_comment" class="form-control"
                                           placeholder="Введите причину отказа" required>
                    </form>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-sm btn-secondary" onclick="clear_cancel_order()" data-bs-dismiss="modal">Отмена</button>
                    <button class="btn btn-sm bg-danger text-white mt-1" type="button" data-bs-dismiss="modal"
                            onclick="provide_cancel_order('${url_text}', '${csrf}', '${o_id}', '${decrement_id}'); clear_cancel_order();">
                        Отправить заказ в проблемные</button>
                </div>`
// document.getElementById('problem_order_form').submit()
        $('#cancel_orderModal').modal('show')
    }

function clear_cancel_order(){
    document.getElementById("cancel_orderModalLabel").innerHTML = ''
    document.getElementById("order_cancel_block").innerHTML = ''
}

function provide_cancel_order(url, csrf, o_id, decrement_id){
    if(document.getElementById('cancel_order_form').reportValidity()){
        let card_block_id = 'cancel_order' + o_id;
        $.ajax({
        url: url,
        headers: {"X-CSRFToken": csrf},
        method: "POST",
        data: {'cancel_order_comment': document.getElementById('cancel_order_comment').value},
        success: function (data) {
``            // make_message(data.message, data.status);
            if (data.status === 'success') {
                // update_url_category();
                // update_crm_info();
                 removeOrder(document.getElementById(card_block_id), o_id, decrement_id);
            }
            make_message(data.message, data.status);

        },
        error: function () {
            make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');
            // close_Loading_circle();
        }
    });
    }
}

// url, block, stage, csrf, clicked_block, order_id, order_idn, decrement_id
// document.getElementById('problem_order_form').submit()
function problem_order(url, block, stage, csrf, clicked_block_id, order_id, order_idn, decrement_id){
    document.getElementById("problem_orderModalLabel").innerHTML = `Вы хотите указать проблему в заказе номер ${order_idn}!`
    document.getElementById("order_problem_block").innerHTML = `<div class="modal-body text-justify">
          <form method="post" id="problem_order_form" action="${url}"
            title="Указать проблему заказа № ${order_idn}">
            <input type="hidden" name="csrf_token" value="${csrf}"/>
            <label style="font_size:14:px">Проблема в заказе!</label>
            <input type="text" minlength="3" maxlength="150" id="problem_order_comment" name="problem_order_comment" class="form-control"
                   placeholder="Введите описание проблемы" required>
          </form>
          <div class="modal-footer">
            <button type="button" class="btn btn-sm btn-secondary" onclick="clear_problem_order()" data-bs-dismiss="modal">Отмена</button>
            <button class="btn btn-sm bg-error mt-1" type="button"
                onclick="provide_problem_order('${url}', '${block}', '${stage}', '${csrf}', '${clicked_block_id}', '${order_id}', '${order_idn}', '${decrement_id}')">
            Отправить заказ в проблемные</button>
          </div>
        </div>`
    $('#problem_orderModal').modal('show')
}

function clear_problem_order(){
    document.getElementById("problem_orderModalLabel").innerHTML = ''
    document.getElementById("order_problem_block").innerHTML = ''
}

function provide_problem_order(url, block, stage, csrf, clicked_block_id, order_id, order_idn, decrement_id){
    if(document.getElementById('problem_order_form').reportValidity()){
        loadingCircle();
        let category = get_current_category();

        $.ajax({
        url:url,
        method:"POST",
        headers:{"X-CSRFToken": csrf},
        data:{'stage': stage,
              'category': category,
              'problem_order_comment': document.getElementById('problem_order_comment').value},
        success:function(data)
        {
            // console.log(data);

          close_Loading_circle();
          if (data.status === 'success') {
               console.log(data);
               removeOrder(document.getElementById(clicked_block_id), order_id, decrement_id);
               make_message(data.message, 'success');
               if(stage>8){return}
               let blockElement = $('#' + block);
               blockElement.html(data);
               $('#' + block + '_quantity').html('(' + data.quantity + ')');
               blockElement.append(data.htmlresponse);
               initializeJSPage(document.getElementById(block));
               blockElement.focus();

               $('#problem_orderModal').modal('hide')
               clear_problem_order();
          }
          else{
              make_message(data.message, data.status);
          }
        },
         error: function() {
            close_Loading_circle();
            make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');
        }
       });

       setTimeout(function() {clear_user_messages();}, 15000);

    }
}

function change_operator(o_id, order_idn, url, csrf){
    var manager_array = '';
    for(var x=0; x<managers_list.length; x++){
        manager_array += `<option value="${managers_list[x][0]}">${managers_list[x][1]}</option>`;
    }

    var oper_form = `<div class="modal-body text-justify">
                                <form method="post" id="change_operator_form" action="${url}"
                                    title="Поменять оператора(менеджера) заказа ${order_idn}">
                                    <input type="hidden" name="csrf_token" value="${csrf}"/>
                                    <label style="font_size:14:px">Выберите оператора из выпадающего списка!</label>
                                    <select class="form-control" id="operator_id" name="operator_id" required>
                                       <option disabled selected value="">Выберите оператора...</option>\` +
                                        ${manager_array} + \`</select>
                                </form>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-sm btn-secondary" onclick="clear_change_operator()" data-bs-dismiss="modal">Отмена</button>
                                <button class="btn btn-sm btn-primary" type="button" onclick="post_change_operator('${url}', '${csrf}', '${o_id}')">Поменять оператора(менеджера заказа)</button>
                            </div>`
    // alert(ob);
    document.getElementById("change_operatorModalLabel").innerHTML = `Вы хотите поменять менеджера в заказе номер ${order_idn}!`
    document.getElementById("change_operator_block").innerHTML = oper_form;


    $('#change_operatorModal').modal('show')
}

function clear_change_operator(){
    document.getElementById("change_operatorModalLabel").innerHTML = ''
    document.getElementById("change_operator_block").innerHTML = ''
}

function post_change_operator(url, csrf, o_id){
    if(document.getElementById('change_operator_form').reportValidity()){
        $.ajax({
        url: url,
        headers: {"X-CSRFToken": csrf},
        method: "POST",
        data: {'operator_id': document.getElementById('operator_id').value},
        success: function (data) {
            // make_message(data.message, data.status);
            // console.log(data);
            if (data.status === 'success') {
                $('#change_operatorModal').modal('hide');
                clear_change_operator();
                // document.getElementById(`managerNameBlock_${o_id}`).innerHTML = data.manager_block;
                filter_category_manager(update_managers_url);
                update_crm_info();
                clear_search_order_res();
            }
            make_message(data.message, data.status);

        },
        error: function () {
            make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');
            // close_Loading_circle();
        }
        });

    }
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

function filter_category_manager(url){
    // window.location.href = url + document.getElementById("selectManager").value;
    let category = get_current_category();
    let manager_select = document.getElementById("selectManager");
    let manager_id = manager_select.value;
    removeTooltip(manager_select);
    // Iterate through each element
    update_url_temp = url + '&category=' + category + '&filtered_manager_id=' + manager_id;

    update_crm_info();

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


    var text = `Текст ${str} скопирован в буфер`;
    // alert(text);
    make_message(text, 'success')
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


function change_external_problem_stage(url, csrf, element_id, executor) {
    $.ajax({
        url: url,
        headers: {"X-CSRFToken": csrf},
        method: "POST",
        data: {'executor': executor},
        success: function (data) {
``            // make_message(data.message, data.status);
            if (data.status === 'success') {
                // update_url_category();
                // update_crm_info();
                 $('#' + element_id).html(data.html_block);

            }
            // make_message(data.message, data.status);
        },
        error: function () {
            make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');
            // close_Loading_circle();
        }
    });
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


function update_crm_info(){

   $.ajax({
    url:update_url_temp,
    method:"GET",
    success:function(data)
    {
        if (data.status === 'success') {
            $('#update_all_info').html(data);
            $("#update_all_info").append(data.htmlresponse);
            initializeJSPage(document);
            make_message('Данные успешно обновлены ', 'success');
            // make_message(msg, data.status);
            // setTimeout(function() {location.reload(true);}, 5000);
        }
        else{
            make_message('Нет карточек заказов. Проверьте категории или оператора!', 'warning');
        }
    },
     error: function() {
        make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');
    }
   });

   setTimeout(function() {clear_user_messages();}, 15000);

}


function update_url_category(){
    let category = get_current_category();
    update_url_temp = update_url + '&category=' + category;
}

function update_category_crm_info(url, category, block, manager_flag){
    const items = document.querySelectorAll('.categories__item');

    var url_proc = url + '&category=' + category;
    if (manager_flag==='1'){
        let manager_id = document.getElementById("selectManager").value;
        url_proc = url + '&category=' + category + '&filtered_manager_id=' + manager_id;
    }
    // Iterate through each element
    items.forEach(item => {
      // Remove the 'categories__item--active' class
      item.classList.remove('categories__item--active');
    });
    block.classList.add('categories__item--active');
    update_url_temp = url_proc;
    update_crm_info();

}

function make_message(message, type) {
    document.getElementById('all_messages').innerHTML = '';
    let title = '';
    let message_image = '';
    let icon_block = ''

    if (type === 'danger') {
        type = 'error';
    }

    if (type === 'error') {
        title = 'Ошибка';
        // message_image = message_icon_error;
        icon_block = `<svg xmlns="http://www.w3.org/2000/svg" width="66" height="66" viewBox="0 0 66 66" fill="none">
                        <path fill-rule="evenodd" clip-rule="evenodd" d="M35.569 8.05446C41.3576 8.41751 46.7845 11.322 50.7642 15.3156C55.4675 20.3984 58 26.5703 58 33.8314C58 39.6403 55.8293 45.0862 52.2113 49.8059C48.5934 54.1626 43.5284 57.4301 37.7397 58.5193C31.9511 59.6084 26.1624 58.8823 21.0973 55.9779C16.0323 53.0734 12.0526 48.7167 9.88182 43.2709C7.71107 37.8251 7.34928 31.6531 9.15823 26.2073C10.9672 20.3984 14.2233 15.6786 19.2884 12.4111C23.9917 9.14363 29.7803 7.6914 35.569 8.05446ZM37.3779 54.8887C42.0812 53.7995 46.4227 51.2581 49.6788 47.2645C52.5731 43.2709 54.3821 38.5512 54.0203 33.4684C54.0203 27.6595 51.8496 21.8506 47.8699 17.857C44.2519 14.2264 39.9105 12.0481 34.8454 11.685C30.1421 11.322 25.077 12.4111 21.0973 15.3156C17.1176 18.22 14.2233 22.2136 12.7761 27.2964C11.329 32.0162 11.329 37.099 13.4997 41.8187C15.6705 46.5384 18.9266 50.169 23.2681 52.7104C27.6096 55.2518 32.6746 55.9779 37.3779 54.8887ZM33.0364 31.6531L41.7194 22.5767L44.2519 25.1181L35.569 34.1945L44.2519 43.2709L41.7194 45.8123L33.0364 36.7359L24.3535 45.8123L21.8209 43.2709L30.5039 34.1945L21.8209 25.1181L24.3535 22.5767L33.0364 31.6531Z" fill="#9C9C9C"/>
                      </svg>`
    } else if (type === 'warning') {
        title = 'Предупреждение';
        message_image = message_icon_warning;
        icon_block = `<img src="${message_image}" alt="" width="66" height="66" class="img-fluid ">`
    } else {
        title = 'Успех';
        message_image = message_icon_success;
        icon_block = `<img src="${message_image}" alt="" width="66" height="66" class="img-fluid ">`
    }
    var block_messages = document.getElementById('all_messages');
    block_messages.insertAdjacentHTML('beforeend', `<div id="alert-message-${type}" class="toast toast-${type}" role="alert" data-bs-delay="30000" aria-live="assertive" aria-atomic="true">
                            <div class="toast-header">
                                <strong class="me-auto fw-bold ">${title}</strong>
                                <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Закрыть"></button>
                            </div>
                            <div class="toast-body d-flex align-items-center ">
                                ${icon_block}
                                <p class="mt-2">${message}</p>
                            </div>
                        </div>`);
    show_user_messages()
}


function make_connection_error_message(message) {
    document.getElementById('all_messages').innerHTML = '';
    let title = 'Ошибка соединения!';

    var block_messages = document.getElementById('all_messages');
    block_messages.insertAdjacentHTML('beforeend', `<div id="alert-message-error" class="toast toast-error" role="alert" data-bs-delay="30000" aria-live="assertive" aria-atomic="true">
                            <div class="toast-header">
                                <strong class="me-auto fw-bold ">${title}</strong>
                                <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Закрыть"></button>
                            </div>
                            <div class="toast-body d-flex align-items-center ">
                                <p class="mt-2">${message}</p>
                            </div>
                        </div>`);
    show_user_messages()
}


function clear_search_order_res(){
        $('#OrderSearchResult').html('');
    }


function search_crm_order(url, csrf){
    // clear_search_order_res();
    let search = document.getElementById('searchOrdertext').value;

    const regex = /^[a-zA-Z0-9]+_[a-zA-Z0-9]+$/;
    let re_check = regex.test(search);
    // console.log(re_check);
    if (search.length < 2 || !re_check){
        make_message('Введите полный номер заказа в формате <b>ЧИСЛО</b>_<b>ЧИСЛО</b>', 'warning');
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

        $("#OrderSearchResult").html(data);
        $("#OrderSearchResult").append(data.htmlresponse);
        initializeJSPage(document.getElementById('OrderSearchResult'));
    },
     error: function() {
        make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');
        // close_Loading_circle();
    }
   });

   setTimeout(function() {clear_user_messages();}, 15000);
}

function get_current_category() {
    // Find the active category item
    const activeItem = document.querySelector('.categories__item--active');

    if (activeItem) {
        // Extract the onclick attribute value
        const onclickValue = activeItem.getAttribute('onclick');

        // Extract the category name from the onclick attribute
        // The onclick attribute value is like: update_category_crm_info(update_url, 'category_name', this)
        // So we need to extract 'category_name'
        const matches = onclickValue.match(/'([^']+)'/);

        if (matches && matches[1]) {
            return matches[1];
        }
    }

    // Return null or a default value if no active category is found
    return 'all';
}

// function decrement_quantity(decrement_block){
//     let quantityElement = document.getElementById(decrement_block);
//         if (quantityElement) {
//             let currentQuantity = parseInt(quantityElement.textContent.replace(/[()]/g, ''));
//             if (!isNaN(currentQuantity) && currentQuantity > 0) {
//                 let newQuantity = currentQuantity - 1;
//                 quantityElement.textContent = `(${newQuantity})`;
//             }
//         }
// }

function decrement_quantity(decrement_id) {

    let quantityElement = document.getElementById(decrement_id);

    if (quantityElement) {
        let currentQuantity = parseInt(quantityElement.textContent.replace(/[()]/g, ''));
        if (!isNaN(currentQuantity) && currentQuantity > 0) {
            let newQuantity = currentQuantity - 1;
            quantityElement.textContent = `(${newQuantity})`;
        }
    }
}

function removeOrder(element, o_id, decrement_id) {
    // Find the closest parent element with the class 'orders__item'
    removeTooltip(element);

    let card_id = "cardCommonBlock_" + o_id;

    let elements = document.querySelectorAll('[id^="' + card_id + '"]');
    elements.forEach(el => {
        if (el) {
            el.remove();
        }
    });
    if (elements.length > 0) {
        decrement_quantity(decrement_id);
    }
    document.getElementById('OrderSearchResult').innerHTML="";
}

function removeTooltip(element){
    var tooltipInstance = bootstrap.Tooltip.getInstance(element);
    if (tooltipInstance) {
        tooltipInstance.hide();
    }
}

// update columns of stages and moves special orders
function update_spec_block_info(url, block, stage, csrf, clicked_block, order_id, order_idn, decrement_id){
   loadingCircle();
   let category = get_current_category();

   $.ajax({
    url:url,
    method:"POST",
    headers:{"X-CSRFToken": csrf},
    data:{'stage': stage,
          'category': category,
          'order_id': order_id},
    success:function(data)
    {
        // console.log(data);

      close_Loading_circle();
      if (data.status === 'success') {
          if (clicked_block){
               // console.log({'orderblock': order_block});
               removeOrder(clicked_block, order_id, decrement_id);
               make_message(data.message, 'success');
               if(stage>8){return}
              }
          let blockElement = $('#' + block);
          blockElement.html(data);
          $('#' + block + '_quantity').html('(' + data.quantity + ')');
          blockElement.append(data.htmlresponse);
          // resetJSPage();
          initializeJSPage(document.getElementById(block));
          blockElement.focus();
          // make_message('Страница обновлена успешно', 'success');
          // make_message(msg, data.status);
          // setTimeout(function() {location.reload(true);}, 5000);
      }
      else{
          make_message(data.message, data.status);
      }
    },
     error: function() {
        close_Loading_circle();
        make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');
    }
   });

   setTimeout(function() {clear_user_messages();}, 15000);

}
function init_tooltip(document){
    document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(tooltipTriggerEl => {
            new bootstrap.Tooltip(tooltipTriggerEl);
        });
}

function initializeJSPage(document) {
 // Инициализация всех тултипов
        init_tooltip(document);

        // Обработка всех элементов заказа
        document.querySelectorAll('.order').forEach(order => {
            const orderHeader = order.querySelector('.order__header');
            const orderRoll = order.querySelector('.order__roll');

            const toggleOrder = (event) => {
                event.stopPropagation();
                order.classList.toggle('active');
            };

            if (orderHeader) {
                orderHeader.addEventListener('click', toggleOrder);
            }

            order.addEventListener('click', (event) => {
                if (!event.target.closest('.order__roll') && !order.classList.contains('active')) {
                    order.classList.add('active');
                }
            });

            if (orderRoll) {
                orderRoll.addEventListener('click', (event) => {
                    event.stopPropagation();
                    order.classList.remove('active');
                });
            }
        });

        //SCROLL

        // document.addEventListener('DOMContentLoaded', function () {
        //     new ScrollBooster({
        //         viewport: document.querySelector('.crm'),
        //         content: document.querySelector('.crm__wrapper'),
        //         scrollMode: 'transform',
        //         direction: 'horizontal',
        //         emulateScroll: true,
        //         textSelection: true,
        //     });
        // });
}

function process_attach_file(file_url, link_url, csrf, o_id, order_idn){
    // order{{ n.id }}_file_input', '#order{{ n.id }}_selected_filename', {{ n.id }}, '{{ url_for('crm_d.attach_of_link', manager=n.manager, manager_id=n.manager_id, o_id=n.id) }}', '{{ csrf_token() }}'
    var modal_block = document.getElementById("blockModalFileLinkAttach")
    modal_block.innerHTML = `<div class="modal fade" id="modalFileLink" tabindex="-1" aria-labelledby="Окно выбора менеджера" aria-hidden="true">
        <div class="modal-dialog modal-dialog-centered">
            <div class="modal-content">
                <div class="modal-header ">
                    <h5 class="modal-title " id="attach_file_title">Прикрепите файлы заказа ${order_idn}</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" onclick="document.getElementById('blockModalFileLinkAttach').innerHTML='';"
                     aria-label="Закрыть"></button>
                </div>
                <div class="modal-body">
                    <form id="mainForm">
                        <!-- Переключатель -->
                        <div class="form-check form-switch mb-4">
                            <input class="form-check-input border border-light" type="checkbox" id="modalLinkFileToggleSwitch"
                                   onclick="attach_file_link_toggle();">
                            <span class="form-check-label" for="modalLinkFiletoggleSwitch" id="moadlFileLinkToggleLabel">Прикрепить архив</span>
                        </div>

                        <!-- Группа для загрузки файла -->
                        <div class="mb-3" id="modalFileUploadGroup">
                            <div class="input-group">
                                <button class="btn btn-secondary font-12" type="button" onclick="document.getElementById('order${o_id}_file_input').click();">Выбрать файл...</button>
                                <span id="order${o_id}_attachFileName" class="form-control">Файл не выбран</span>
                                
                                <input type="file" class="form-control" accept=".rar" id="order${o_id}_file_input" style="display: none;" onchange="attachFileUpdateFileName('${o_id}')"
                                 name="order_file" aria-label="Upload" lang="ru">
                                 
                                <button class="btn btn-outline-warning" type="button" onclick="process_post_attach_file('order${o_id}_file_input', '${file_url}','${csrf}', '${o_id}');">Сохранить</button>
                            </div>

                        </div>

                        <!-- Группа для ввода ссылки -->
                        <div class="mb-3" id="modalLinkInputGroup" style="display: none;">
<!--                            <label for="linkInput" class="form-label">Или прикрепите ссылку</label>-->
                            <div class="input-group">
                                <input type="url" class="form-control" minlength="5" maxlength="100" id="of_link${o_id}" name="of_link" placeholder="Введите ссылку">
                                <button class="btn btn-primary" type="button" onclick="process_post_attach_link('of_link${o_id}', '${link_url}','${csrf}', '${o_id}');">Сохранить</button>
                            </div>
                        </div>
                    </form>
                </div>

                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal" 
                    onclick="document.getElementById('blockModalFileLinkAttach').innerHTML='';">Закрыть</button>
                </div>
            </div>
        </div>
    </div>`
    $('#modalFileLink').modal('show');
}


function check_attach_file(file_input_id) {
    let file_input = document.getElementById(file_input_id);
    if (!file_input.files) { // This is VERY unlikely, browser support is near-universal
        alert("Попробуйте другой браузер! Ваш не поддерживает функционал загрузки файлов.");
    } else if (!file_input.files[0]) {
        alert("Выберите файл для загрузки");
    } else {
        var file = file_input.files[0];
        if (file.size >= OF_MAX_SIZE) {
            let mes = file.name + " весит " + file.size + " байт. Это больше установленного лимита " +  OF_MAX_SIZE

            // clear input file
            file_input.value = '';
            alert(mes);
        }
        else {
            return true
        }
    }
    return false
}

function process_post_attach_file(file_input_id, file_url, csrf, o_id){
    if (check_attach_file(file_input_id)){
        $('#modalFileLink').modal('hide');
        loadingCircle();
        let file_input = document.getElementById(file_input_id);
        let formData = new FormData();
        formData.append('order_file', file_input.files[0]);

        $.ajax({
            url: file_url,
            headers:{"X-CSRFToken": csrf},
            method: "POST",
            data: formData,
            processData: false,  // Don't process the files
            contentType: false,  // Set the content type to false as jQuery will tell the server its a query string request
            success: function(data){
                if (data.status === 'success'){
                    let cardBlocks = document.querySelectorAll(`#cardCommonBlock_${o_id}`);

                    for (let i = 0; i < cardBlocks.length; i++) {
                        let cardFileBlock = cardBlocks[i].querySelector(`#orderFile_${o_id}`);
                        let cardFooterBlock = cardBlocks[i].querySelector(`#footer_card_btns${o_id}`);

                        // Apply actions to the subblocks
                        // cardFileBlock.innerHTML = data;
                        cardFileBlock.innerHTML = data.htmlresponse_file; // Equivalent of append
                        // cardFooterBlock.innerHTML = data;
                        cardFooterBlock.innerHTML = data.htmlresponse_footer; // Equivalent of append
                        init_tooltip(cardBlocks[i]);
                    }

                    // let cardFileBlock = `#orderFile_${o_id}`;
                    // let cardFooterBlock = `#footer_card_btns${o_id}`;
                    // $(cardFileBlock).html(data);
                    // $(cardFileBlock).append(data.htmlresponse_file);
                    // $(cardFooterBlock).html(data);
                    // $(cardFooterBlock).append(data.htmlresponse_footer);
                    make_message(data.message, 'success')
                    // init_tooltip(document.getElementById(`cardCommonBlock_${o_id}`));
                }
                else{
                    make_message(data.message, 'error');
                }
                document.getElementById('blockModalFileLinkAttach').innerHTML='';
                close_Loading_circle();
            },
            error: function() {
                document.getElementById('blockModalFileLinkAttach').innerHTML='';
                close_Loading_circle();
                make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');
            }
        });
    }
}

function attachFileUpdateFileName(o_id) {
        const fileInput = document.getElementById('order' + o_id + '_file_input');
        const fileName = document.getElementById('order'+ o_id + '_attachFileName');

        if (fileInput.files.length > 0) {
            fileName.textContent = fileInput.files[0].name;
        } else {
            fileName.textContent = 'Файл не выбран';
        }
    }

function check_link(link_value, link_block) {
    const minLength = parseInt(link_block.getAttribute('minlength'), 10);
    const maxLength = parseInt(link_block.getAttribute('maxlength'), 10);
    if (link_value.length >= minLength && link_value.length <= maxLength && link_block.checkValidity()) {
        return true;
    } else {
        make_message('Некорректная ссылка', 'warning');
        return false;
    }
}

function process_post_attach_link(link_input_id, link_url, csrf, o_id){
    let link_block = document.getElementById(link_input_id);
    let link_value  =link_block.value;
    if (check_link(link_value, link_block)){
        $('#modalFileLink').modal('hide');
        loadingCircle();
        $.ajax({
            url: link_url,
            headers:{"X-CSRFToken": csrf},
            method: "POST",
            data: {'of_link': link_value},
            success: function(data){
                if (data.status === 'success'){
                    let cardBlocks = document.querySelectorAll(`#cardCommonBlock_${o_id}`);

                    for (let i = 0; i < cardBlocks.length; i++) {
                        let cardFileBlock = cardBlocks[i].querySelector(`#orderFile_${o_id}`);
                        let cardFooterBlock = cardBlocks[i].querySelector(`#footer_card_btns${o_id}`);
                        cardFileBlock.innerHTML = data.htmlresponse_file; // Equivalent of append
                        cardFooterBlock.innerHTML = data.htmlresponse_footer; // Equivalent of append
                        init_tooltip(cardBlocks[i]);
                    }

                    // let cardFileBlock = `#orderFile_${o_id}`;
                    // let cardFooterBlock = `#footer_card_btns${o_id}`;
                    // $(cardFileBlock).html(data);
                    // $(cardFileBlock).append(data.htmlresponse_file);
                    // $(cardFooterBlock).html(data);
                    // $(cardFooterBlock).append(data.htmlresponse_footer);
                    make_message(data.message, 'success')
                    // init_tooltip(document.getElementById(`cardCommonBlock_${o_id}`));
                }
                else{
                    make_message(data.message, 'error');
                }
                document.getElementById('blockModalFileLinkAttach').innerHTML='';
                close_Loading_circle();
            },
            error: function() {
                document.getElementById('blockModalFileLinkAttach').innerHTML='';
                close_Loading_circle();
                make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');
            }
        });
    }
    else{
        $('#modalFileLink').modal('hide');
    }
}

function process_post_delete_file(url, csrf, o_id){
    loadingCircle();
    $.ajax({
        url: url,
        headers:{"X-CSRFToken": csrf},
        method: "POST",
        data: {},
        success: function(data) {
            if (data.status === 'success'){
                let cardBlocks = document.querySelectorAll(`#cardCommonBlock_${o_id}`);
                    for (let i = 0; i < cardBlocks.length; i++) {
                        let cardFileBlock = cardBlocks[i].querySelector(`#orderFile_${o_id}`);
                        let cardFooterBlock = cardBlocks[i].querySelector(`#footer_card_btns${o_id}`);
                        cardFileBlock.innerHTML = data.htmlresponse_file; // Equivalent of append
                        cardFooterBlock.innerHTML = data.htmlresponse_footer; // Equivalent of append
                        init_tooltip(cardBlocks[i]);
                    }
                make_message(data.message, 'success')
                // init_tooltip(document.getElementById(`cardCommonBlock_${o_id}`));
            }
            else{
                make_message(data.message, 'error');
            }
            document.getElementById('blockModalFileLinkAttach').innerHTML='';
            close_Loading_circle();
        },
        error: function() {
            document.getElementById('blockModalFileLinkAttach').innerHTML='';
            close_Loading_circle();
            make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');
        }
    });
}

function attach_file_link_toggle(){
    // Переключение между элементами
        var switcher = document.getElementById("modalLinkFileToggleSwitch");
        var fileUploadGroup = document.getElementById('modalFileUploadGroup');
        var linkInputGroup = document.getElementById('modalLinkInputGroup');
        var toggleLabel = document.getElementById('moadlFileLinkToggleLabel');

        if (switcher.checked) {
            fileUploadGroup.style.display = 'none';
            linkInputGroup.style.display = 'block';
            toggleLabel.textContent = 'Прикрепить ссылку';
            switcher.classList.add('bg-light'); // Добавление фона bg-info
        } else {
            fileUploadGroup.style.display = 'block';
            linkInputGroup.style.display = 'none';
            toggleLabel.textContent = 'Прикрепить архив';
            switcher.classList.remove('bg-light'); // Удаление фона bg-info
        }

}


function bck_avg_order_processing_time_rpt(url) {
    let sort_mode = $('input[name="sort_type"]:checked').val();
    let date_from = $('#date_from').val();
    let date_to = $('#date_to').val();
    let manager = $('#manager_filter').val();

    $.ajax({
        url: url,
        method: "GET",
        data: {
            date_from: date_from,
            date_to: date_to,
            sort_type: sort_mode,
            manager: manager,
        },
        success: function (data) {
            $('#avg_order_processing_time_table').html(data);
            $("#avg_order_processing_time_table").append(data.htmlresponse);
        }
    });
}


function get_avg_order_processing_time_rpt_excel(url, csrf) {
    let sort_mode = $('input[name="sort_type"]:checked').val();
    let date_from = $('#date_from').val();
    let date_to = $('#date_to').val();
    let manager = $('#manager_filter').val();
    $('#overlay_loading').show();
    $.ajax({
        url: url,
        headers: { "X-CSRFToken": csrf },
        method: "POST",
        data: {date_from: date_from,
            date_to: date_to,
            sort_type: sort_mode,
            manager: manager,
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
                link.download = decodeURIComponent(dataName) || 'статистика_по_времени_обработки_заказа.xlsx'; //
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