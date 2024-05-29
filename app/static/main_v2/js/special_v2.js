// ######### auth group #########

function check_num(){
    var check = document.getElementById('phone').value;
    var check_num = check.slice(-1);

    if (isNaN(check_num) || check_num==='__' || check_num==='')
      {
        document.getElementById('phone').classList.remove("is-valid");
        document.getElementById('phone').classList.add("is-invalid");
        return false
      }
    else{
        document.getElementById('phone').classList.remove("is-invalid");
        document.getElementById('phone').classList.add("is-valid");
        return true
    }

}

function check_login_name(){
    let login = document.getElementById('login_name');
    if (login.value.length < 6 || login.value.length > 20){
        login.classList.remove("is-valid");
        login.classList.add("is-invalid");
        return false
    }
    else{
        login.classList.remove("is-invalid");
        login.classList.add("is-valid");
        return true
    }
}

function check_intel_num(){

    if (iti.isPossibleNumber()){
        // console.log('possible');
        document.getElementById('phone').classList.remove("is-invalid");
        document.getElementById('phone').classList.add("is-valid");
        document.getElementById("full_phone").value = iti.getNumber();

        return true
    }
    else{
        // console.log('not possible');
        document.getElementById('phone').classList.remove("is-valid");
        document.getElementById('phone').classList.add("is-invalid");
        return false
    }
}

function exclude_spaces(block){
    block.value = block.value.replace(/ /g,'');
}

function verifySignPassword() {

  // if(check_num()!== true){
  //       return false
  //   }

  //check empty password field
  var pw = document.getElementById("password_sign").value;
  if(pw === "") {
     document.getElementById("message").innerHTML = "Заполните пароль";
     setInterval(clear_message_copy , 5000);
     document.getElementById("password_sign").classList.add("is-invalid");
     return false;
  }
  else{
      document.getElementById("password_sign").classList.remove("is-invalid");
      document.getElementById("password_sign").classList.add("is-valid");
  }

 //minimum password length validation
  if(pw.length < 6) {
     document.getElementById("message").innerHTML = "Пароль должен содержать хотя бы 6 символов";
     setInterval(clear_message_copy , 5000);
     document.getElementById("password_sign").classList.add("is-invalid");
     return false;

  }
  else{
      document.getElementById("password_sign").classList.remove("is-invalid");
      document.getElementById("password_sign").classList.add("is-valid");
  }

//maximum length of password validation
  if(pw.length > 15) {
     document.getElementById("message").innerHTML = "Длина пароля не должна превышать 15 символов";
     setInterval(clear_message_copy , 5000);
     document.getElementById("password_sign").classList.add("is-invalid");
     return false;
  }
  else{
      document.getElementById("password_sign").classList.remove("is-invalid");
      document.getElementById("password_sign").classList.add("is-valid");
  }
  var pw_check = document.getElementById("password_sign_check").value;
  if(pw !== pw_check) {
     document.getElementById("password_sign_check").classList.add("is-invalid");
     document.getElementById("message").innerHTML = "Пароли не совпадают";
     setInterval(clear_message_copy , 5000);
     return false;
  }
  else {
      document.getElementById("password_sign_check").classList.remove("is-invalid");
      document.getElementById("password_sign_check").classList.add("is-valid");
  }
  return true

}

function verify_sign_up_form(){
    if (check_intel_num() && verifySignPassword() && check_login_name()){
        loadingCircle();
        return true
    }
    return false
}

function change_input_view(block_id, eye_toggle_id){
    let block = document.getElementById(block_id);
    let eye_toggle = document.getElementById(eye_toggle_id);
    if(block.type === 'password'){
        block.type = 'text';
        eye_toggle.title = 'Отключить просмотр пароля';
        eye_toggle.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-eye-slash" viewBox="0 0 16 16">
  <path d="M13.359 11.238C15.06 9.72 16 8 16 8s-3-5.5-8-5.5a7 7 0 0 0-2.79.588l.77.771A6 6 0 0 1 8 3.5c2.12 0 3.879 1.168 5.168 2.457A13 13 0 0 1 14.828 8q-.086.13-.195.288c-.335.48-.83 1.12-1.465 1.755q-.247.248-.517.486z"/>
  <path d="M11.297 9.176a3.5 3.5 0 0 0-4.474-4.474l.823.823a2.5 2.5 0 0 1 2.829 2.829zm-2.943 1.299.822.822a3.5 3.5 0 0 1-4.474-4.474l.823.823a2.5 2.5 0 0 0 2.829 2.829"/>
  <path d="M3.35 5.47q-.27.24-.518.487A13 13 0 0 0 1.172 8l.195.288c.335.48.83 1.12 1.465 1.755C4.121 11.332 5.881 12.5 8 12.5c.716 0 1.39-.133 2.02-.36l.77.772A7 7 0 0 1 8 13.5C3 13.5 0 8 0 8s.939-1.721 2.641-3.238l.708.709zm10.296 8.884-12-12 .708-.708 12 12z"/>
</svg>`;
    }
    else{
        block.type = 'password';
        eye_toggle.title = 'Включить просмотр пароля';
        eye_toggle.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-eye" viewBox="0 0 16 16">
  <path d="M16 8s-3-5.5-8-5.5S0 8 0 8s3 5.5 8 5.5S16 8 16 8M1.173 8a13 13 0 0 1 1.66-2.043C4.12 4.668 5.88 3.5 8 3.5s3.879 1.168 5.168 2.457A13 13 0 0 1 14.828 8q-.086.13-.195.288c-.335.48-.83 1.12-1.465 1.755C11.879 11.332 10.119 12.5 8 12.5s-3.879-1.168-5.168-2.457A13 13 0 0 1 1.172 8z"/>
  <path d="M8 5.5a2.5 2.5 0 1 0 0 5 2.5 2.5 0 0 0 0-5M4.5 8a3.5 3.5 0 1 1 7 0 3.5 3.5 0 0 1-7 0"/>
</svg>`;
    }

}

function clear_message_copy(){

    var mes = document.getElementById('message')
    mes.innerHTML = '';

  }

  //  ##### uc panel #####


function verifyUCPassword() {
  var pw = document.getElementById("new_password").value;
  //check empty password field

  if(pw === "") {
     document.getElementById("message_new_password").innerHTML = "Заполните пароль";
     document.getElementById("new_password").classList.remove("is-valid");
     document.getElementById("new_password").classList.add("is-invalid");
     setInterval(clear_uc_message , 5000);
     return false;
  }

 //minimum password length validation
  if(pw.length < 6) {
     document.getElementById("message_new_password").innerHTML = "Пароль должен содержать хотя бы 6 символов";
     document.getElementById("new_password").classList.remove("is-valid");
     document.getElementById("new_password").classList.add("is-invalid");
     setInterval(clear_uc_message , 5000);
     return false;
  }

//maximum length of password validation
  if(pw.length > 15) {
     document.getElementById("message_new_password").innerHTML = "Длина пароля не должна превышать 15 символов";
     document.getElementById("new_password").classList.remove("is-valid");
     document.getElementById("new_password").classList.add("is-invalid");
     setInterval(clear_uc_message , 5000);
     return false;
  }
  var pw_check = document.getElementById("password_check_field").value;
  if(pw !== pw_check) {
     document.getElementById("message_new_password").innerHTML = "Пароли не совпадают";
     document.getElementById("new_password").classList.remove("is-invalid");
     document.getElementById("new_password").classList.add("is-valid");
     document.getElementById("password_check_field").classList.remove("is-valid");
     document.getElementById("password_check_field").classList.add("is-invalid");

     setInterval(clear_uc_message , 5000);
     return false;
  }
  else {
     document.getElementById("new_password").classList.remove("is-valid");
     document.getElementById("new_password").classList.add("is-invalid");
     document.getElementById("password_check_field").classList.remove("is-invalid");
     document.getElementById("password_check_field").classList.add("is-valid");
     return true;
  }

}

function clear_uc_message(){

    var mes = document.getElementById("message_new_password")
    mes.innerHTML = '';

  }


  // ##### messages #####
function make_message(message, type){
    document.getElementById('all_messages').innerHTML = '';
    let title= '';
    let message_image = '';

    if(type==='danger'){type='error'; }

    if (type === 'error'){title='Ошибка'; message_image=message_icon_error;}
    else if (type === 'warning'){title='Предупреждение'; message_image=message_icon_warning;}
    else {title='Успех'; message_image=message_icon_success;}
    var block_messages = document.getElementById('all_messages');
    block_messages.insertAdjacentHTML('beforeend',`<div id="alert-message-${type}" class="toast toast-${type}" role="alert" data-bs-delay="30000" aria-live="assertive" aria-atomic="true">
                            <div class="toast-header">
                                <strong class="me-auto fw-bold ">${title}</strong>
                                <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Закрыть"></button>
                            </div>
                            <div class="toast-body d-flex align-items-center ">
                                <img src="${message_image}" alt="" width="66" height="66" class="img-fluid ">
                                <p class="mt-2">${message}</p>
                            </div>
                        </div>`);
    show_user_messages()
}


function make_connection_error_message(message){
    document.getElementById('all_messages').innerHTML = '';
    let title= 'Ошибка соединения!';

    var block_messages = document.getElementById('all_messages');
    block_messages.insertAdjacentHTML('beforeend',`<div id="alert-message-error" class="toast toast-error" role="alert" data-bs-delay="30000" aria-live="assertive" aria-atomic="true">
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

function zoom_image(){
    // console.log('clicked');
    if(document.getElementById('bill-modal-image').classList.contains('img-zoom-orig-clicked')){
        document.getElementById('bill-modal-image').classList.remove('img-zoom-orig-clicked');
    }
    else{
        document.getElementById('bill-modal-image').classList.add('img-zoom-orig-clicked')
    }
}
 function loadingCircle() {

   var overlay = document.getElementById("overlay_loading");
   overlay.style.display = "block";

 }

  function close_Loading_circle(){
    var overlay = document.getElementById("overlay_loading");
    overlay.style.display = "";
 }


//     ###### form #####
function show_form_errors(errors){
    let errors_block = document.getElementById('form_errormodaldiv');
    errors.forEach(function (el, index) {
                errors_block.innerHTML += `${index+1}. <u>${el}</u><br>`;
                }
            )
}
function clear_errorform(){
    document.getElementById('form_errormodaldiv').innerHTML='';
}

function check_valid(field) {

    if (field.checkValidity() && field.id !== 'size_order' && field.id !== 'sizeX_order' && field.id !== 'sizeY_order'
        && field.id !== 'quantity_order') {
        field.classList.remove('is-invalid');
        field.classList.add('is-valid');
        // console.log('check: valid');
    }
    else {
        if(field.id !== 'size_order' && field.id !== 'sizeX_order' && field.id !== 'sizeY_order'
            && field.id !== 'quantity_order'){
        field.classList.remove('is-valid');
        field.classList.add('is-invalid');
        // console.log('check: invalid');
        return field.id
        }
    }
}

// modal marks
function process_mark(mark_id, slice_length){
        var image_input_value = document.getElementById(mark_id).value;
        var mark_field = document.getElementById("mark_type")
        var mark_field_hidden = document.getElementById("mark_type_hidden")

        mark_field.setAttribute("value", image_input_value.slice(slice_length));
        mark_field.classList.remove('is-invalid');
        mark_field.classList.add('is-valid');
        mark_field_hidden.setAttribute("value", image_input_value);

    }

//      ##### categories #####
function check_blank_start (){
    var company_name = document.getElementById("company_name");

    if (company_name.value.startsWith(' ')){
        company_name.value='';
        alert("Наименование компании не может начинаться с пробела!");
    }
}
function DTTemplate(){

    var download_uri = document.getElementById("DownloadTemplates").value;
    if(download_uri !=='#' ){
        window.location.href = document.getElementById("DownloadTemplates").value;
    }
    else{
        show_form_errors(['Для скачивания шаблона сначала выберите его',]);
        $('#form_errorModal').modal('show');
    }
}

function edit_copied_full_order(){
    let copy_order_edit_org = document.getElementById('copy_order_edit_org').value;
    if (copy_order_edit_org === "edit_org_card"){
        $('#editOrgCardCopyOrderModal').modal('show');
    }
}

function check_rd_docs(){
    if (document.getElementById("rd_type").value.length > 0 || document.getElementById("rd_name").value.length > 0 || document.getElementById("rd_date").value.length > 0){

        if (document.getElementById("rd_type").value.length > 0 && document.getElementById("rd_name").value.length > 0 && document.getElementById("rd_date").value.length > 0){

            return true
        }
        else{
            // alert("Должны быть заполнены все поля формы разрешительной документации, либо все должны быть пусты!");
            return false
        }
    }
    else{
        return true
    }
}

function check_company_marks(){
    if (document.getElementById("company_name").value.length > 0 && document.getElementById("mark_type").value.length > 0){

        return true
    }
    else{
        // alert("Должны быть заполнены все поля формы разрешительной документации, либо все должны быть пусты!");
        return false
    }
}

function perform_process(){
     var user_comment = document.getElementById("order_comment_after").value
    document.getElementById("order_comment").setAttribute("value", user_comment);
    document.getElementById('process_modal_footer').innerHTML=`<div class="col text-center"><b>Производится обработка</b><br>
      <div class="spinner-border text-warning" role="status">
        <span class="visually-hidden">Loading...</span>
      </div>
    </div>`;

    setTimeout(() => {document.getElementById('form_process').submit()}, 500);

}

async function perform_order_check(url_link){
    document.getElementById('process_modal_footer').innerHTML=`<div class="col text-center text-warning"><b>Производится обработка</b><br><div class="spinner-border" role="status"></div></div>`;

    var data = await fetchAsync(url_link);

        var data_list = data.split(';');
        if (data_list[0] !== "1"){
            perform_process();
        }
        else{
            document.getElementById('process_modal_footer').innerHTML = `<button type="button" class="btn btn-accent" id="btn_process" onclick="perform_process();">Все-равно оформить накладную!</button><button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Нет</button>`;
            document.getElementById("data_order_check_insert").innerHTML = `<span style="color:red"><b>${data_list[1]}</b></span><br>`;

        }
}

function perfom_process_model_update(url, csrf, o_id, category){
    document.getElementById("data_order_check_insert").innerHTML = '';
    document.getElementById('process_modal_footer').innerHTML=` <button type="button" class="btn btn-accent border-0" id="btn_process"
                        onclick="perform_balance_order_check('${url}', '${csrf}', ${o_id}, '${category}');" >Оформить накладную</button>
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Назад</button>`;
}

function perform_balance_order_check(url, csrf, o_id, category){
    $.ajax({
    url:url,
    headers:{"X-CSRFToken": csrf},
    method:"POST",
    data:{o_id: o_id,
    category: category},
    success:function(data)
    {
        // console.log(data);

        // balance - 1 ok 0 not ok, orders - 1 got orders in history, 0 - no orders in history
        let agent_2_str = 'Обратитесь к агенту, на данный момент активность невозможна'
        if(data.status_balance === 1 && data.status_order === 0){
            // console.log("performing_process");
            perform_process();

        }
        else if(data.status_balance !== 1 && data.status_order === 0){
            // console.log("balance needs refill");

            if (!data.agent_at2) {
                document.getElementById("data_order_check_insert").innerHTML = `<span style="color:red"><b>${data.answer_balance}</b></span><br>`;
            }
            else{
                document.getElementById("data_order_check_insert").innerHTML = `<span style="color:red"><b>${agent_2_str}</b></span><br>`;
            }
            document.getElementById('process_modal_footer').innerHTML = `<button type="button" class="btn btn-secondary" onclick="perfom_process_model_update('${url}', '${csrf}', ${o_id}, '${category}');" data-bs-dismiss="modal">Ок</button>`;
        }
       else if(data.status_balance !== 1 && data.status_order !== 0){
            // console.log("balance not ok, orders - duplicates");
            document.getElementById('process_modal_footer').innerHTML = `<button type="button" class="btn btn-secondary" data-bs-dismiss="modal" onclick="perfom_process_model_update('${url}', '${csrf}', ${o_id}, '${category}');">Ок</button>`;
            if (!data.agent_at2) {
                document.getElementById("data_order_check_insert").innerHTML = `<span style="color:red"><b>${data.answer_balance}</b></span><br>`;
            }
            else{
                document.getElementById("data_order_check_insert").innerHTML = `<span style="color:red"><b>${agent_2_str}</b></span><br>`;
            }

        }
        else if(data.status_balance === 1 && data.status_order !== 0){
            // console.log("balance ok, orders - duplicates");
            document.getElementById('process_modal_footer').innerHTML = `<button type="button" class="btn btn-accent" id="btn_process" onclick="perform_process();">Все-равно оформить накладную!</button><button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Отмена</button>`;
            // document.getElementById('process_modal_footer').innerHTML = `<button type="button" class="btn btn-secondary" data-bs-dismiss="modal" onclick="perfom_process_model_update('${url}', '${csrf}', ${o_id}, '${category}');">Ок</button>`;
            document.getElementById("data_order_check_insert").innerHTML = `<span style="color:#ffc400"><b>${data.answer_orders}</b></span><br>`;

        }

        else{
            document.getElementById('process_modal_footer').innerHTML = `<button type="button" class="btn btn-secondary" data-bs-dismiss="modal" onclick="perfom_process_model_update('${url}', '${csrf}', ${o_id}, '${category}');">Ок</button>`
            document.getElementById("data_order_check_insert").innerHTML = `<span style="color:red"><b>Неизвестная ошибка</b></span><br>`;
        }

    },
     error: function() {
        // make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');
        setTimeout(function() {make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');}, 1500);
     }
   });

   setTimeout(function() {clear_user_messages();}, 15000);

}

function set_no_tm(){
    $('#trademark').val('БЕЗ ТОВАРНОГО ЗНАКА');
}

function set_no_article(){
    $('#article').val('БЕЗ АРТИКУЛА');
}

function check_step(){
    var url_string = window.location.href;
    if( url_string.includes('orders_table' ) ){
        console.log('got orders_table');
        document.getElementById('step-1').style.display='none';
        document.getElementById('step-2').style.display='none';
        document.getElementById('step-3').style.removeProperty('display')
        document.getElementById('btn-step-1').classList.remove('btn-accent');
        document.getElementById('btn-step-2').classList.remove('btn-accent');
        document.getElementById('btn-step-3').classList.add('btn-accent');
        return true
    }
    return false
}

function make_2_step(){
      document.getElementById('step-1').style.display='none';
      document.getElementById('step-2').style.removeProperty('display')
      document.getElementById('step-3').style.display='none';
      document.getElementById('btn-step-1').classList.remove('btn-accent');
      document.getElementById('btn-step-2').classList.add('btn-accent');
      document.getElementById('btn-step-3').classList.remove('btn-accent');

    }

async function fetchAsync (url) {
  let response = await fetch(url);

  return response.text();
}

//      #### archive  ####

function get_category_history(url, category){
    // $("#pills-shoes").toggle();


   $.ajax({
    url: url,
    method:"GET",

    success:function(data)
    {

      $('#pills-tabContent').html(data);
      $("#pills-tabContent").append(data.htmlresponse);
      update_category(category);
      }
   });

}


function delete_archive_order(ao_id, user_order_idn){
    let div_header = document.getElementById('remove_ao_header');
    div_header.innerHTML = '';
    div_header.insertAdjacentHTML( 'beforeend', `<h5 class="modal-title" id="remove_archiveordersModalLabel">Вы уверены, что хотите удалить из архива заказ ${user_order_idn}?</h5><button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>`);

    let div_btn = document.getElementById('remove_ao_btn');
    div_btn.innerHTML = '';
    div_btn.insertAdjacentHTML( 'beforeend', `<button onclick="$('#remove_archiveordersModal').modal('hide');loadingCircle(); document.getElementById('delete_archive_order_${ao_id }').submit()" class="btn btn-danger" type="button">Да</button>`);

    $('#remove_archiveordersModal').modal('show');
}


function update_category(category_p){

    // if(document.getElementById(`pills-${category_p}`).classList.contains('show')=== false) {
    //     console.log('contains');
    //     $(`#${category_p}_button`).click();
    //     document.getElementById(`pills-${category_p}-tab`).classList.remove('active');
    //     document.getElementById(`pills-${category_p}-tab`).classList.add('active');
    if(document.getElementById(`pills-shoes-tab`)){
        document.getElementById(`pills-shoes-tab`).classList.remove('active');
    }
    if(document.getElementById(`pills-clothes-tab`)) {
        document.getElementById(`pills-clothes-tab`).classList.remove('active');
    }
    if(document.getElementById(`pills-linen-tab`)) {
        document.getElementById(`pills-linen-tab`).classList.remove('active');
    }
    if(document.getElementById(`pills-parfum-tab`)) {
        document.getElementById(`pills-parfum-tab`).classList.remove('active');
    }

    document.getElementById(`pills-${category_p}-tab`).classList.add('active');


    }


function download_with_js_order_pdf(url, csrf) {
    $('#overlay_loading').show();
    $.ajax({
        url: url,
        headers: { "X-CSRFToken": csrf },
        method: "POST",
        data: {},
        xhrFields: {
            responseType: 'blob' // Set response type to blob
        },
        success: function(response, status, xhr) {
            $('#overlay_loading').hide();
            if (xhr.status === 200) {
                // PDF downloaded successfully
                var blob = new Blob([response], { type: 'application/pdf' });
                var link = document.createElement('a');

                // Extract the value of the custom header 'data_name'
                var dataName = xhr.getResponseHeader('data_file_name');

                link.href = window.URL.createObjectURL(blob);
                link.download = dataName || 'order.pdf'; // Change the filename if needed
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

function get_request_download(url){
    let a = document.createElement('a');
    loadingCircle();
    a.href = url;
    a.target = '_blank';
    document.body.appendChild(a);
    setTimeout(() => {
        a.click();
        close_Loading_circle();
        document.body.removeChild(a);
    }, 100);
    // close_Loading_circle()
}

//     #### personal account ####
function update_personal_account(category_p){
    if(document.getElementById(`pills-fill`)){
        document.getElementById(`pills-fill`).classList.remove('active');
    }
    if(document.getElementById(`pills-price`)){
        document.getElementById(`pills-price`).classList.remove('active');
    }
    if(document.getElementById(`pills-transactions_history`)){
        document.getElementById(`pills-transactions_history`).classList.remove('active');
    }
    document.getElementById('fill_block').style.display='none';
    document.getElementById('price_block').style.display='none';
    document.getElementById('transactions_history_block').style.display='none';


    document.getElementById(`pills-${category_p}`).classList.add('active');
    document.getElementById(`${category_p}_block`).style.removeProperty('display')
}

// user personal account
function get_personal_account(url, category){
    // $("#pills-shoes").toggle();


   $.ajax({
    url: url,
    method:"GET",

    success:function(data)
    {

      $('#personal_account_stages').html(data);
      $("#personal_account_stages").append(data.htmlresponse);
      update_personal_account(category);
      },
    error: function() {
        // make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');
        setTimeout(function() {make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');}, 3500);
     }

   });

}

function check_pa_refill_form(){

    let form = document.getElementById('pa_refill_form')
    // console.log(form.reportValidity());
    if (!form.checkValidity || form.checkValidity()){
        return true
    }
    else{
        let allInputs = $('#pa_refill_form input');
        let errors_list = []
        allInputs.each(function( index ) {
            // console.log(allInputs[index]);
            check_valid(allInputs[index]);
            let error_field_id = check_valid(allInputs[index]);
            // console.log(error_field_id);
            if (error_field_id !== true){
                let label_text = ''
                if (error_field_id === 'bill_summ'){
                    label_text += 'Введите сумму пополнения'
                }
                else{
                    label_text += jQuery(`#${error_field_id}`).closest(".form-group").find("label").text();
                }

                // console.log(label_text);
                if (label_text){
                    errors_list.push(label_text);
                }
            }
        })


        show_form_errors(errors_list);
        $('#form_errorModal').modal('show');

        return false
    }
}

function check_agent_wo_form(){

    let form = document.getElementById('agent_wo_form')
    // console.log(form.reportValidity());
    if (!form.checkValidity || form.checkValidity()){
        return true
    }
    else{
        let allInputs = $('#agent_wo_form input');
        let errors_list = []
        allInputs.each(function( index ) {
            // console.log(allInputs[index]);
            check_valid(allInputs[index]);
            let error_field_id = check_valid(allInputs[index]);
            // console.log(error_field_id);
            if (error_field_id !== true){
                let label_text = ''
                if (error_field_id === 'wo_summ'){
                    label_text += 'Введите сумму пополнения от 5000 р. с шагом 100 р.'
                }
                else{
                    label_text += jQuery(`#${error_field_id}`).closest(".form-group").find("label").text();
                }

                // console.log(label_text);
                if (label_text){
                    errors_list.push(label_text);
                }
            }
        })


        show_form_errors(errors_list);
        $('#form_errorModal').modal('show');

        return false
    }
}


function get_transaction_history(url){
   $.ajax({
    url: url,
    method:"GET",

    success:function(data)
    {
      $('#transactions_history_block').html(data);
      $("#transactions_history_block").append(data.htmlresponse);

      update_personal_account('transactions_history');

      },
    error: function() {
        // make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');
        setTimeout(function() {make_message('Ошибка. Обратитесь к администратору', 'danger');}, 3500);
     }
   });

}

function bck_transaction_detalization(url){
    $.ajax({
    url: url,
    method:"GET",

    success:function(data)
    {
      // console.log(data);
      // $('#transactionDetaildiv').html(data);
      // $("#transactionDetaildiv").append(data.transaction_report);
      document.getElementById('transactionDetaildiv').innerHTML=data.transaction_report
      // get modalform_errorModal
      $("#transactionDetailModal").modal('show');

      },
      error: function() {
        // make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');
        setTimeout(function() {make_message('Ошибка. В базе нет такой транзакции', 'danger');}, 3500);
     }
   });
}




function clear_td_modal(){
    document.getElementById('transactionDetaildiv').innerHTML = '';
}



function bck_pa_refill(url, update_url)
  {
   var form_raw = $("#pa_refill_form")
   var formData = new FormData(form_raw[0]);


   let bill_file = document.getElementById("bill_file").files[0];

   formData.append('bill_file', bill_file);
   loadingCircle();

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

            let pb = parseInt(document.getElementById("pa_pending_balance_rf").innerHTML) + data.pending_amount
            document.getElementById("pa_pending_balance_rf").innerHTML = `${pb} р.`;
            document.getElementById("bill_summ").value = '';
            document.getElementById("bill_file").value = '';
            document.getElementById("promo_code").value = '';
            document.getElementById("bill_file_posttext").innerHTML = 'Не выбран';
        }
        close_Loading_circle();make_message(data.message, data.status);
        // setTimeout(function() {close_Loading_circle();make_message(data.message, data.status);}, 1500)
    },
     error: function() {
        close_Loading_circle();make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');
         // setTimeout(function() {close_Loading_circle();make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');}, 1500);
     }
   });

   setTimeout(function() {clear_user_messages();}, 15000);
  }


function bck_agent_wo(url)
  {
    // console.log('bck_agent_wo');
   var form = $("#agent_wo_form").serialize();
   loadingCircle();

   $.ajax({
    url:url,
    // headers:{"X-CSRFToken": form.csrf_token},
    method:"POST",
    data: form,
    success:function(data)
    {
        // console.log(data);

        if(data.status==='success'){

            // let pb = parseInt(document.getElementById("pa_confirmed_balance").innerHTML) - data.pending_amount
            // document.getElementById("pa_confirmed_balance").innerHTML = `${pb} р.`;
            document.getElementById("wo_summ").value = '';
            document.getElementById("wo_summ").classList.remove('is-valid');
            document.getElementById("wo_summ").classList.remove('is-invalid');

            document.getElementById("wo_account_info").value = '';
            document.getElementById("wo_account_info").classList.remove('is-valid');
            document.getElementById("wo_account_info").classList.remove('is-invalid');
        }
        close_Loading_circle();make_message(data.message, data.status);
        // setTimeout(function() {close_Loading_circle();make_message(data.message, data.status);}, 1500)
    },
     error: function() {
        document.getElementById("wo_summ").classList.remove('is-valid');
        document.getElementById("wo_summ").classList.remove('is-invalid');
        document.getElementById("wo_account_info").classList.remove('is-valid');
        document.getElementById("wo_account_info").classList.remove('is-invalid');
        close_Loading_circle();make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');
         // setTimeout(function() {close_Loading_circle();make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');}, 1500);
     }
   });

   setTimeout(function() {clear_user_messages();}, 15000);
  }


function toggle_perform_wo(){
  var switchbox = document.getElementById("perform_wo_switchbox");
  var link = document.getElementById("wo_transactions_link");

  if (switchbox.checked) {
        link.classList.remove('disabled');
        switchbox.classList.add('bg-warning');
    } else {
        link.classList.add('disabled');
        switchbox.classList.remove('bg-warning');
    }
}


function perform_wo_transactions(url, csrf){
    $.ajax({
    url:url,
    headers:{"X-CSRFToken": csrf},
    method:"POST",
    data:{},
    success:function(data)
    {
        console.log(data);
        if(data.status === 1){
            document.getElementById('ServerBalance').innerHTML = `Баланс сервиса: <span class="link-warning"><b>${data.server_balance} р.</b></span>`;
        }
        else if(data.status === 0 && data.server_balance){
            setTimeout(function() {make_message(data.server_balance, 'warning');}, 1500);
        }
        else{
            setTimeout(function() {make_message('Ошибка обновления БД. Посмотрите логи', 'danger');}, 1500);
        }

    },
     error: function() {
        // make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');
        setTimeout(function() {make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');}, 1500);
     }
   });

   setTimeout(function() {clear_user_messages();}, 15000);

}


//      #### unused  ####
function copy_order_with_sort(url){
    loadingCircle();
    var sort_type_order = document.getElementById('sort_type_order').value;
    var sort_type_list = sort_type_order.split(';')
    var sort_type = sort_type_list[0];
    var sort_order = sort_type_list[1];
    window.location.href = `${url}?page={{ page  }}&sort_type=${sort_type}&sort_order=${sort_order}`;
}

// User_cp password resore

function upr_verifyPassword() {
  var pw = document.getElementById("new_password").value;
  //check empty password field

  if(pw === "") {
     document.getElementById("message_new_password").innerHTML = "Заполните пароль";
     setInterval(upr_clear_message , 5000);
     return false;
  }

 //minimum password length validation
  if(pw.length < 6) {
     document.getElementById("message_new_password").innerHTML = "Пароль должен содержать хотя бы 6 символов";
     setInterval(upr_clear_message , 5000);
     return false;
  }

//maximum length of password validation
  if(pw.length > 15) {
     document.getElementById("message_new_password").innerHTML = "Длина пароля не должна превышать 15 символов";
     setInterval(upr_clear_message , 5000);
     return false;
  }
  var pw_check = document.getElementById("password_check_field").value;
  if(pw !== pw_check) {
     document.getElementById("message_new_password").innerHTML = "Пароли не совпадают";
     setInterval(upr_clear_message , 5000);
     return false;
  }
  else {
     // console.log('true')
     return true;
  }

}



function upr_clear_message(){

    var mes = document.getElementById("message_new_password")
    mes.innerHTML = '';

  }

function get_order_book(url){

    $.ajax({
    url:url,
    method:"GET",
    success:function(data)
    {
    document.getElementById('obDetaildiv').innerHTML=data.ob_report;
      // get modalform_errorModal
      $("#obDetailModal").modal('show');

    },
     error: function() {
        // make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');
        setTimeout(function() {make_message('Ошибка. нет списка заказов', 'danger');}, 3500);
     }
   });

   setTimeout(function() {clear_user_messages();}, 15000);

}


function clear_obd_modal(){
    document.getElementById('obDetaildiv').innerHTML = '';
}


function get_tg_notify_info(url){

    $.ajax({
    url:url,
    method:"GET",
    success:function(data)
    {
      // console.log(data);
      document.getElementById('tgNotifydiv').innerHTML=data.tg_verify_report;
      // get modalform_errorModal
      $("#tgNotifyModal").modal('show');

    },
     error: function() {
        // make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');
        setTimeout(function() {make_message('Ошибка. Обратитесь к администратору', 'danger');}, 3500);
     }
   });

   setTimeout(function() {clear_user_messages();}, 15000);

}

function bck_tg_stop_verify(url, csrf){
    // console.log('bck_agent_wo');
   // loadingCircle();

   $.ajax({
    url:url,
    headers:{"X-CSRFToken": csrf},
    method:"POST",
    // data: {},
    success:function(data)
    {
        // console.log(data);

        if(data.status==='success'){
            $("#tgNotifyModal").modal("hide");
            clear_tg_notify_modal();
            get_tg_notify_info();
        }
        else {
            $("#tgNotifyModal").modal("hide");
            clear_tg_notify_modal();
        }
        // close_Loading_circle();
        make_message(data.message, data.status);
        // setTimeout(function() {close_Loading_circle();make_message(data.message, data.status);}, 1500)
    },
     error: function() {
        // close_Loading_circle();
        make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');
         // setTimeout(function() {close_Loading_circle();make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');}, 1500);
     }
   });

   setTimeout(function() {clear_user_messages();}, 15000);
  }


function bck_tg_markineris_verify(url){
    // console.log('bck_agent_wo');
   let js_form = document.getElementById('tgVerificationForm')

    js_form.reportValidity();

   if (!js_form.checkValidity()){
       return
   }

   let form = $('#tgVerificationForm').serialize();
   $.ajax({
    url:url,
    // headers:{"X-CSRFToken": csrf},
    method:"POST",
    data: form,
    success:function(data)
    {
        if(data.status==='success'){
            $("#tgNotifyModal").modal("hide");
            clear_tg_notify_modal();
            get_tg_notify_info();
        }
        else {
            $("#tgNotifyModal").modal("hide");
            clear_tg_notify_modal();
        }
        make_message(data.message, data.status);
        // setTimeout(function() {close_Loading_circle();make_message(data.message, data.status);}, 1500)
    },
     error: function() {

        close_Loading_circle();make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');
         // setTimeout(function() {close_Loading_circle();make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');}, 1500);
     }
   });

   setTimeout(function() {clear_user_messages();}, 15000);
  }


function clear_tg_notify_modal(){
    document.getElementById('tgNotifydiv').innerHTML = '';
}