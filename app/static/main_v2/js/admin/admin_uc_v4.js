function copy_buffer(element_id, message_id){
    var data = document.getElementById(element_id);
    var mes = document.getElementById(message_id)
    data.focus()
    data.select();
    data.setSelectionRange(0, 99999);

    try {
        document.execCommand('copy');
        mes.innerHTML = 'ссылка скопирована';

       }
    catch (err) {
        alert('ошибка')
        mes.innerHTML = 'Копирование не удалось. Попробуйте выделить и скопировать.';
      }

    setInterval(clear_message_copy_admin , 3000, message_id);
  }

  function clear_message_copy_admin(el_message_id){

    var mes = document.getElementById(el_message_id)
    mes.innerHTML = '';

  }

  function wait(ms){
   var start = new Date().getTime();
   var end = start;
   while(end < start + ms) {
     end = new Date().getTime();
   }
  }

//     #### finance_control ####
function update_finance_control(category_p){
    if(document.getElementById(`pills-service_accounts`)){
        document.getElementById(`pills-service_accounts`).classList.remove('active');
    }
    if(document.getElementById(`pills-promos`)){
        document.getElementById(`pills-promos`).classList.remove('active');
    }
    if(document.getElementById(`pills-prices`)){
        document.getElementById(`pills-prices`).classList.remove('active');
    }
    document.getElementById('service_accounts_block').style.display='none';
    document.getElementById('promos_block').style.display='none';
    document.getElementById('prices_block').style.display='none';


    document.getElementById(`pills-${category_p}`).classList.add('active');
    document.getElementById(`${category_p}_block`).style.removeProperty('display')
}


function get_promos_history(url){
   $.ajax({
    url: url,
    method:"GET",

    success:function(data)
    {

      $('#promos_table').html(data);
      $("#promos_table").append(data.htmlresponse);
      // update_category(category);
      }
   });

}

function check_promo_form(){
    let form = document.getElementById('promo_form')
    // console.log(form.reportValidity());
    if (!form.checkValidity || form.checkValidity()){
        return true
    }
    else{
        var allInputs = $('#promo_form input');

        allInputs.each(function( index ) {
            // console.log(allInputs[index]);
            check_valid(allInputs[index]);
        })
        return false
    }
}

async function bck_delete_promo(url, csrf, update_url){

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
        if(data_r.status >= 400){
            // console.log(data_r.status);
            make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');
            return false
        }
        const data = await data_r.json();
        // console.log(data.status)
        if (data.status === 'success'){
            get_promos_history(update_url)
        }

        make_message(data.message, data.status);
        setTimeout(function() {
                        clear_user_messages();
                    }, 15000);
        return true


    } catch (e) {
        console.log(e)

        return false;
    }
}

function bck_add_promo(url, update_url)
  {
   var form = $("#promo_form").serialize();

   $.ajax({
    url:url,
    // headers:{"X-CSRFToken": csrf},
    method:"POST",
    data: form,
    success:function(data)
    {
        // console.log(data);

        if(data.status==='success'){
            get_promos_history(update_url);
        }

        make_message(data.message, data.status);
    },
     error: function() {
         make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');
     }
   });

   setTimeout(function() {clear_user_messages();}, 15000);
  }

function check_price_switch(){
    let pat2 = document.getElementById("price_at2");
    // console.log(pat2.checked);
    if (pat2.checked === true){
        pat2.classList.add("bg-warning");
        document.getElementById("label_price_at2").innerHTML = 'Агент <b>единый счет</b';
    }
    else{
        pat2.classList.remove("bg-warning");
        document.getElementById("label_price_at2").innerHTML = '<b>Обычный</b> агент';
    }
}

function check_prices_form(){

    let form = document.getElementById('prices_form')
    // console.log(form.reportValidity());
    if (!form.checkValidity || form.checkValidity()){
        return true
    }
    else{
        var allInputs = $('#prices_form input');

        allInputs.each(function( index ) {
            // console.log(allInputs[index]);
            check_valid(allInputs[index]);
        })
        return false
    }
}

function get_prices_history(url){
   $.ajax({
    url: url,
    method:"GET",

    success:function(data)
    {
      $('#prices_table').html(data);
      $("#prices_table").append(data.htmlresponse);
      }
   });

}

function bck_add_price(url, update_url)
  {
   var form = $("#prices_form").serialize();
   // console.log(form.csrf_token);
   $.ajax({
    url:url,
    // headers:{"X-CSRFToken": form.csrf_token},
    method:"POST",
    data: form,
    success:function(data)
    {
        // console.log(data);

        if(data.status==='success'){
            get_prices_history(update_url);
        }

        make_message(data.message, data.status);
    },
     error: function() {
         make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');
     }
   });

   setTimeout(function() {clear_user_messages();}, 15000);
  }

function check_price_at2_and_replace_price_text(price_row, p_code){
    if (price_row[2] === 'True' && price_row[1] !== p_code){
        return `<option value="${price_row[0]}">${price_row[1]} - Агенты единый счет</option>`
    }
    else if(price_row[1] !== p_code){
        return `<option value="${price_row[0]}">${price_row[1]}</option>`
    }
    else{
        return ''
    }
}

function bck_delete_replace_price(url, csrf, update_url, p_code){
    let modal_block = document.getElementById('service_prices_modal');

    var option_prices = '<option value="">BASIC</option>'

    prices_array.forEach((element) => {option_prices += `${check_price_at2_and_replace_price_text(element, p_code)}`});

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

function bck_delete_price_post_process(url, update_url){
   var form = $("#service_price_replace_form").serialize();
   $.ajax({
    url:url,
    // headers:{"X-CSRFToken": form.csrf_token},
    method:"POST",
    data: form,
    success:function(data)
    {
        // console.log(data);

        if(data.status==='success'){
            get_prices_history(update_url);
        }

        make_message(data.message, data.status);
    },
     error: function() {
         make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');
     }
   });

   setTimeout(function() {clear_user_messages();}, 15000);
  }

function clear_modal_service_prices() {
    document.getElementById("service_prices_modal").innerHTML = '';
}

function check_sa_form(){

    let form = document.getElementById('service_account_form')
    // console.log(form.reportValidity());
    if (!form.checkValidity || form.checkValidity()){
        return true
    }
    else{
        var allInputs = $('#service_account_form input');
        let errors_list = [];
        allInputs.each(function( index ) {
            // console.log(allInputs[index]);

            let error_field_id = check_valid(allInputs[index]);
            // console.log(error_field_id);
            if (error_field_id !== true){
                let label_text = jQuery(`#${error_field_id}`).closest(".form-group").find("label").text();
                // document.getElementById().parent().label.innerText
                // errors_list.push(error_field_name);
                if (label_text){
                    errors_list.push(label_text);
                }
            }
        })
        if ($('#sa_type').val() === null){
            errors_list.push('Укажите тип счета!');
        }

        show_form_errors(errors_list);
        $('#form_errorModal').modal('show');
        return false
    }
}

function sa_form_update_type(){
    let qr_block = ``
    let req_block = ``
    let sa_type = document.getElementById('sa_type').value
    if (document.getElementById('sa_type').value === 'qr_code'){
        // document.getElementById('change_sa_type_block').innerHTML = qr_block;
        document.getElementById('req_block').style.display='none';
        document.getElementById('sa_req').disabled=true;
        document.getElementById('qr_img_block').style.removeProperty('display');
        document.getElementById('sa_qr_file').disabled=false;

    }
    else{
        document.getElementById('qr_img_block').style.display='none';
        document.getElementById('sa_qr_file').disabled=true;
        document.getElementById('req_block').style.removeProperty('display');
        document.getElementById('req_block').classList.remove('is-valid')
        document.getElementById('sa_req').disabled=false;
    }
    // console.log(sa_type)
}

function get_sa_history(url){
   $.ajax({
    url: url,
    method:"GET",

    success:function(data)
    {

      $('#sa_table').html(data);
      $("#sa_table").append(data.htmlresponse);
      // update_category(category);
      }
   });

}

async function bck_delete_sa(url, csrf, update_url){

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
        if(data_r.status >= 400){
            // console.log(data_r.status);
            make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');
            return false
        }
        const data = await data_r.json();
        // console.log(data.status)
        if (data.status === 'success'){
            get_sa_history(update_url)
        }

        make_message(data.message, data.status);
        setTimeout(function() {
                        clear_user_messages();
                    }, 15000);
        return true


    } catch (e) {
        console.log(e)

        return false;
    }
}

async function bck_change_sa_activity(url, csrf, update_url, sa_id){

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
        if(data_r.status >= 400){
            // console.log(data_r.status);
            make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');
            return false
        }
        const data = await data_r.json();
        // console.log(data.status)
        if (data.status === 'success'){
            // make style
            let sa_check_box = document.getElementById(sa_id);


             if (sa_check_box.checked){
                sa_check_box.classList.add("bg-warning");
             }
             else{
                 sa_check_box.classList.remove("bg-warning");
             }
        }
        else{get_sa_history(update_url)}

        make_message(data.message, data.status);
        setTimeout(function() {
                        clear_user_messages();
                    }, 15000);
        return true


    } catch (e) {
        console.log(e)

        return false;
    }
}

function bck_add_sa(url, update_url)
  {
      // var form_raw = $("#service_account_form").serialize();
      // var form_raw =document.getElementById('service_account_form');
    var form_raw = $("#service_account_form")
    var formData = new FormData(form_raw[0]);
    if (sa_type==='qr_code'){
        // console.log(sa_type);
        let qr_file = document.getElementById("sa_qr_file").files[0];

        formData.append('sa_qr_file', qr_file, qr_file.name);
    }

   $.ajax({
    url:url,
    // headers:{"X-CSRFToken": form.csrf_token},
    method:"POST",
    data: formData,
    contentType: false,
    processData: false,
    cache: false,
    success:function(data)
    {
        // console.log(data);

        if(data.status==='success'){
            get_sa_history(update_url);
        }

        make_message(data.message, data.status);
    },
     error: function() {
         make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');
     }
   });

   setTimeout(function() {clear_user_messages();}, 15000);
  }


function bck_change_account_type(url, sa_type)
  {
      // var form_raw = $("#service_account_form").serialize();
      // var form_raw =document.getElementById('service_account_form');
    var form = $("#service_account_type_form").serialize()


   $.ajax({
    url:url,
    // headers:{"X-CSRFToken": form.csrf_token},
    method:"POST",
    data: form,
    success:function(data)
    {
        // console.log(data);

        if(data.status==='warning'){
            document.getElementById('desc_account_type').innerHTML = data.change_block;
        }
        else{
            uncheck_sa_switch();
        }

        make_sa_message(data.message, data.status);
    },
     error: function() {
         make_sa_message('Ошибка CSRF. Обновите страницу и попробуйте снова');
         uncheck_sa_switch()
     }
   });

   setTimeout(function() {clear_sa_message();}, 5000);
  }


function make_sa_message(message, status){
    document.getElementById('sa_message_block').classList.remove('text-danger');
    document.getElementById('sa_message_block').classList.remove('text-warning');
    document.getElementById('sa_message_block').classList.add(`text-${status}`);
    document.getElementById('sa_message_block').innerHTML = message;
  }

function clear_sa_message(message){
    document.getElementById('sa_message_block').innerHTML = '';
  }

function uncheck_sa_switch(){
    if(document.getElementById('account_type_switch').checked === true){
        document.getElementById('account_type_switch').checked = false
    }
    else{
        document.getElementById('account_type_switch').checked = true
    }
}

function bck_get_transactions(url){
   $.ajax({
    url: url,
    method:"GET",

    success:function(data)
    {
      $('#transactions_table').html(data);
      $("#transactions_table").append(data.htmlresponse);

      }
   });

}

function bck_get_transactions_wp(url){

    let sort_mode = 0;
    if (document.getElementById("asc_type").checked){
        sort_mode = 1;
    }
    $.ajax({
    url: url,
    method:"GET",
    data: {
        tr_type: $('#transaction_type').val(),
        tr_status: $('#transaction_status').val(),
        date_from: $('#date_from').val(),
        date_to: $('#date_to').val(),
        amount: $('#transaction_amount').val(),
        sort_type: sort_mode
      },
    success:function(data)
    {
      $('#transactions_table').html(data);
      $("#transactions_table").append(data.htmlresponse);

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
        data: {tr_type: $('#transaction_type').val(),
            tr_status: $('#transaction_status').val(),
            date_from: date_from,
            date_to: date_to,
            amount: $('#transaction_amount').val(),
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


function bck_su_transaction_detalization(url){
    $.ajax({
    url: url,
    method:"GET",

    success:function(data)
    {
      // console.log(data);

      document.getElementById('su_transactionDetaildiv').innerHTML=data.transaction_report

      $("#su_transactionDetailModal").modal('show');

      },
    error: function() {
        // make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');
        setTimeout(function() {make_message('Ошибка. В базе нет такой транзакции', 'danger');}, 3500);
     }
   });
}

function clear_su_td_modal(){
    document.getElementById('su_transactionDetaildiv').innerHTML = '';
}

function bck_au_ut_detalization(url){
    $.ajax({
    url: url,
    method:"GET",

    success:function(data)
    {
      // console.log(data);
      if(data.status === 1){
        document.getElementById('au_transactionDetaildiv').innerHTML=data.transaction_report

        $("#au_transactionDetailModal").modal('show');
      }
      else{
          make_message(data.message, 'danger');
          setTimeout(function() {clear_user_messages();}, 15000);
      }
    },
    error: function() {
        // make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');
        setTimeout(function() {make_message('Ошибка. В базе нет такой транзакции', 'danger');}, 3500);
     }
   });
}

function clear_au_userstd_modal(){
    document.getElementById('au_transactionDetaildiv').innerHTML = '';
}


function bck_get_orders_stats(url){
   $.ajax({
    url: url,
    method:"GET",

    success:function(data)
    {
      $('#orders_stats_table').html(data);
      $("#orders_stats_table").append(data.htmlresponse);

      },
    error: function() {
        // make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');
        setTimeout(function() {make_message('Ошибка. В базе нет информации об этих заказах', 'danger');}, 3500);
     }
   });

}

function bck_get_users_activated(url){
   $.ajax({
    url: url,
    method:"GET",

    success:function(data)
    {
      if (data.status && data.status==='success'){
          $('#usersActivateTable').html(data);
          $('#usersActivateTable').append(data.htmlresponse);
      }
    },
    error: function() {
        // make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');
        setTimeout(function() {make_message('Ошибка. В базе нет информации об этих пользователях', 'danger');}, 3500);
     }
   });

}

function bck_activate_user(url, url_update, form_id)
  {
   var form = $("#" + form_id).serialize();
   $.ajax({
    url:url,
    // headers:{"X-CSRFToken": csrf},
    method:"POST",
    data: form,
    success:function(data)
    {
        if(data.status==='success'){
            bck_get_users_activated(url_update);
        }

        make_message(data.message, data.status);
    },
     error: function() {
         make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');
     }
   });

   setTimeout(function() {clear_user_messages();}, 15000);
  }


function bck_delete_user(url, url_update, form_id)
  {
   var form = $("#" + form_id).serialize();
    // console.log(form);
   $.ajax({
    url:url,
    // headers:{"X-CSRFToken": csrf},
    method:"POST",
    data: form,
    success:function(data)
    {

        if(data.status==='success'){
            bck_get_users_activated(url_update);
        }

        make_message(data.message, data.status);
    },
     error: function() {
         make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');
     }
   });

   setTimeout(function() {clear_user_messages();}, 15000);
  }

function bck_pending_transaction_change_status(url, update_url,tr_type, tr_status, csrf)
  {

   // console.log(tr_type, tr_status, csrf);
   $.ajax({
    url:url,
    headers:{"X-CSRFToken": csrf},
    method:"POST",
    data: {'tr_type': tr_type, 'tr_status': tr_status},
    success:function(data)
    {
        // console.log(data);

        if(data.status==='success'){
            bck_get_transactions_wp(update_url);
        }

        make_message(data.message, data.status);
    },
     error: function() {
         make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');
     }
   });

   setTimeout(function() {clear_user_messages();}, 15000);
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