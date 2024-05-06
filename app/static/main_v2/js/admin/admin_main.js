function telegram_add(){
    if (document.getElementById('radio_is_telegram').checked){
        document.getElementById('tg_select_id').hidden = false;
        document.getElementById('tg_select_id').disabled = false;
        document.getElementById('tg_select_id').required = true;
    }
    else{
        document.getElementById('tg_select_id').hidden = true;
        document.getElementById('tg_select_id').disabled = true;
        document.getElementById('tg_select_id').required = false;
    }
}

async function get_tg_data(url_link){
    var data = await fetchAsync(url_link);

        var data_list = data.split(';');
        if (data_list[0] !== "5"){
            alert(data_list[1])
        }
        else{
            document.getElementById("data_tg_insert").innerHTML = `<b>Пользователи</b> привязанные к этому телеграмм каналу:<br>`
            var processed_data = data_list[1].split(',');
            processed_data.forEach(function (el, index) {
                document.getElementById("data_tg_insert").innerHTML += `${index+1}. ${el}<br>`;
                }
            )
            $('#getTgDataModal').modal('show');
        }
}

async function fetchAsync (url) {
  let response = await fetch(url);

  return response.text();
}

function get_request(url){
    let a = document.createElement('a');
    a.href = url;
    a.target = '_blank';
    document.body.appendChild(a);
    setTimeout(() => {
        a.click();
        document.body.removeChild(a);
    }, 500);
}

function change_process_type(u_id, u_name, url, csrf){
    document.getElementById("change_process_at2ModalLabel").innerHTML = `Вы хотите сменить тип агента на ТИП 2, тип обработки заказов через телеграмм и с общим счетом для клиентов для админа ${u_name}`;

    var option_tg = '<option disabled selected value >Выберите телеграмм</option>';
    tg_array.forEach((element) => {option_tg += `<option value="${element[0]}">${element[1]}</option>`});

    document.getElementById("data_change_pt_insert").innerHTML = `
        <form method="post" id="change_pt_form" action="${url}">
              <input type="hidden" name="csrf_token" value="${csrf}"/>
              <div class="input-group mt-3 mb-1">
              <select class="form-select" id="tg_select" name="tg_select" required
                   onchange="this.classList.remove('is-invalid');this.classList.add('is-valid');"
                   aria-label="Выберите телеграмм" aria-describedby="agent_t2">
                ${option_tg}
              </select>
              <span class="input-group-text bg-info text-white" style="cursor: pointer" id="agent_t2" onclick="check_agent_type_form_submit()">Изменить</span>

            </div>
        </form> `;
    $('#change_process_at2Modal').modal("show");
}

function clear_submit_change_pt_modal(){

    document.getElementById("data_change_pt_insert").innerHTML = ''

    document.getElementById("change_process_at2ModalLabel").innerHTML = ''
}


function get_change_fee_or_tl_modal(csrf, u_fee_or_tl, u_name,  url, type){
   let modal_label = '';
   let modal_input = '';
    if (type === 'agent_fee'){
       modal_label= '<label for="agent_fee_value">Укажите ставку агента в процентах от стоимости заказа (0-40,%)</label>';
       modal_input = '<input name="agent_fee_value" id="agent_fee_value_check" class="form-control"  type="number" min="0" max="40" step="1" value="${u_fee_or_tl}" placeholder="Введите ставку 0-40%" required>'
    }
    else{
        modal_label= '<label for="agent_tl_value">Укажите лимит отрицательного баланса агента в руб от 10000 до 1000000, р.</label>';
        modal_input = '<input name="agent_tl_value" id="agent_tl_value_check" class="form-control" type="number" min="10000" max="1000000" step="100" value="${u_fee_or_tl}" placeholder="Введите лимит агента" required>'
    }
    let form_block= `<form method="post"
          action="${url}" onsubmit="this.validate(); return this.valid();">
        <input type="hidden" name="csrf_token" value="${csrf}"/>
        ${modal_label}
        <div class="text-center">
            <div class="row">
                <div class="col-3"></div>
                <div class="col-6">
                    ${modal_input}
                </div>
            </div>

            <button class="btn btn-accent my-2" type="submit">Изменить</button>
            <button type="button" class="btn btn-secondary" onclick="clear_afee_or_tl_modal();" data-bs-dismiss="modal">Закрыть</button>
            </div>
    </form>`


   let modal_block = document.getElementById('agent_fee_or_tl_modal');

    modal_block.innerHTML = `<div class="modal fade" id="agent_feeOrTLModal" tabindex="-1" role="dialog" data-bs-backdrop="static" data-bs-keyboard="false" aria-labelledby="agent_feeModalLabel" aria-hidden="true">
          <div class="modal-dialog" data-backdrop="static" role="document">
            <div class="modal-content">
              <div class="modal-header">
                <h5 class="modal-title" id="agent_feeModalLabel">Форма настройки ставки агента ${u_name}.</h5>
                <button type="button" class="btn-close" onclick="clear_afee_or_tl_modal();" data-bs-dismiss="modal" aria-label="Close">
                </button>
              </div>
              <div class="modal-body">

                  ${form_block}

              </div>

            </div>
          </div>
        </div>`;
    $("#agent_feeOrTLModal").modal("show");
}

function clear_afee_or_tl_modal(){
    document.getElementById("agent_fee_or_tl_modal").innerHTML = '';
}

function check_valid_fee_or_tl(field) {
    console.log(field.checkValidity());
    if (!field.checkValidity()){
        field.value=field.min;
    }
}

function bck_get_users_from_markineris(url, csrf)
  {
   loadingCircle();
   $.ajax({
    url:url,
    headers:{"X-CSRFToken": csrf},
    method:"POST",
    data: {},
    success:function(data)
    {
        // console.log(data);
        let msg = `Новых Пользователей добавлено <b>${data.info.users.inserted}</b>, обновлено <b>${data.info.users.updated}</b><br>Новых партнер кодов добавлено <b>${data.info.partner_codes.inserted}</b>, обновлено <b>${data.info.partner_codes.updated}</b><br>Всего агентов: <b>${data.info.agents_total}</b><br>Всего клиентов: <b>${data.info.users_total}</b><br>Страница обновится через 5 секунд!`;
        document.getElementById('users_total').innerHTML = `всего ${data.info.users_total}`;
        make_message(msg, data.status);
        close_Loading_circle();
        setTimeout(function() {location.reload(true);}, 5000);
    },
     error: function() {
        make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');
        close_Loading_circle();
    }
   });

   setTimeout(function() {clear_user_messages();}, 15000);

  }


function get_agent_info_modal(u_name, email){

   let form_block= `
        <div class="text-center">
            <div class="row">
                <div class="col-2"></div>
                <div class="col-8">
                    <label for="agent_info_input">Email агента</label>
                    <input id="agent_info_input" class="form-control" type="text" readonly value="${email}">
                </div>
            </div>


            <button type="button" class="btn btn-secondary mt-3" onclick="clear_agent_info_modal();" data-bs-dismiss="modal">Закрыть</button>
        </div>
    `


   let modal_block = document.getElementById('agent_info_modal');

    modal_block.innerHTML = `<div class="modal fade" id="agent_infoModal" tabindex="-1" role="dialog" data-bs-backdrop="static" data-bs-keyboard="false" aria-labelledby="agent_feeModalLabel" aria-hidden="true">
          <div class="modal-dialog" data-backdrop="static" role="document">
            <div class="modal-content">
              <div class="modal-header">
                <h5 class="modal-title" id="agent_infoModalLabel">Запрос данных агента ${u_name}.</h5>
                <button type="button" class="btn-close" onclick="clear_agent_info_modal();" data-bs-dismiss="modal" aria-label="Close">
                </button>
              </div>
              <div class="modal-body">

                  ${form_block}

              </div>

            </div>
          </div>
        </div>`;

    $("#agent_infoModal").modal("show");
}

function clear_agent_info_modal(){
    document.getElementById("agent_info_modal").innerHTML = '';
}

function check_agent_type_form_submit(){
    let form = document.getElementById('change_pt_form');
    // console.log(form.checkValidity());
    if (form.checkValidity()){
        form.submit()}
    else{
        document.getElementById('tg_select').classList.add('is-invalid');
    }
}

function su_load_data(query, url, csrf_token){
   $.ajax({
    url: url,
    headers:{"X-CSRFToken": csrf_token},
    method:"POST",
    data:{query:query},
    success:function(data)
    {
      $('#su_user_search_result').html(data);
      $("#su_user_search_result").append(data.htmlresponse);
    },
    error: function() {
     make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');
    }
   });
}

function su_search_user(url, csrf_token){
    var search = $('#search_text').val();
    if(search !== ''){
        su_load_data(search, url, csrf_token);
    }
    else{
        $('#su_user_search_result').html('');
    }
}

function cus_load_data(search, url, csrf_token){
    $.ajax({
        url: url,
        headers:{"X-CSRFToken": csrf_token},
        method:"POST",
        data:{query:search},
        success:function(data)
        {
          $('#cross_user_search_result').html(data);
          $("#cross_user_search_result").append(data.htmlresponse);
        },
        error: function() {
             make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');
         }
    });
}

function search_cross_user(url, csrf_token){
    var search = $('#cross_order_idn').val();
    if(search !== ''){
        cus_load_data(search, url,  csrf_token);
    }
    else{
        $('#cross_user_search_result').html('');
    }
}