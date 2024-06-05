
function parfum_check_sizes_quantity_valid(){
    var sizes = document.querySelectorAll('[id=size_info]');
    return sizes.length >= 1;
}

function parfum_perform_pos_add(async_flag, url){

    var pos_form =document.getElementById('form_process_main');
    // let isValid = pos_form.reportValidity(); // не подходит

    var chtn = check_tnved('submit');
    var crd = check_rd_docs();
    // var scsq = parfum_check_sizes_quantity_valid();
    if ((!pos_form.checkValidity === true || pos_form.checkValidity()) && crd && chtn) {
        // console.log(pos_form.checkValidity());
        // console.log("good valid form")
        if (async_flag===0){
            pos_form.submit();
        }
        else{
            parfum_load_upload_table(url)
        }
    }
    else{
        var allInputs = $('#form_process_main input, #form_process_main select ');
        var errors_list = [];

        allInputs.each(function( index ) {
            // console.log(allInputs[index]);
            let error_field_id = check_valid(allInputs[index]);
            if (error_field_id !== true){
                let label_text = jQuery(`#${error_field_id}`).closest(".form-group").find("label").text();
                // document.getElementById().parent().label.innerText
                // errors_list.push(error_field_name);
                if (label_text){
                    errors_list.push(label_text);
                }
            }
        })
        // if (scsq === false){
        //     errors_list.push("Размер обуви. Добавьте хотя бы один");
        // }
        if (crd === false){
            errors_list.push("Разрешительная документация. Должны быть заполнены все поля формы разрешительной документации, либо все должны быть пусты!");
        }

        // console.log('not valid form');
        show_form_errors(errors_list);
        $('#form_errorModal').modal('show');
    }
}


function show_parfum_pos(index, trademark, volume, volume_type, package_type, material_package, type,
                         quantity, box_quantity,
                         country, edit_link, copy_link, delete_link, csrf_token){
    let main = document.getElementById('ShowModalTable');
    main.innerHTML = '';

    let data_modal=`<div class="modal fade " id="showElementTable" tabindex="-1" role="dialog" aria-labelledby="showElementTableLabel"
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
                        <div class="important-card__prop">${type+ ' ' + trademark}
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
                            Вид парфюма
                        </div>
                        <div class="important-card__val">${type}</div>
                    </div>
                    <div class="important-card__item">
                        <div class="important-card__prop">
                            Объем
                        </div>
                        <div class="important-card__val">${volume}, ${volume_type}</div>
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
                        <div class="important-card__val">${quantity}</div>
                    </div>
                    <div class="important-card__item">
                        <div class="important-card__prop">
                            Тип упаковки
                        </div>
                        <div class="important-card__val">${package_type}</div>
                    </div>
                    <div class="important-card__item">
                        <div class="important-card__prop">
                            Материал упаковки
                        </div>
                        <div class="important-card__val">${material_package}</div>
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

function parfum_make_research_by_trademark(url, csrf_token){
    var search = $('#search_by_trademark_text').val();
    if(search.length >= 2){
        parfum_load_search_data(search, url, csrf_token);
    }
    else{
    // load_search_data()
        $('#search_trademark_info').empty();
    }
}

function parfum_load_search_data(query, url, csrf_token)
{
    $.ajax({
    url:url,
    headers:{"X-CSRFToken": csrf_token},
    method:"POST",
    data:{query:query},
    success:function(data)
    {
      $('#search_trademark_info').html(data);
      $("#search_trademark_info").append(data.htmlresponse);
    }
    });
}

async function async_parfum_delete_pos(url, csrf,block){
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
        if (data.status === 'success' && data.type==='async'){

            $('#step-3_update').html(data);
            $('#step-3_update').append(data.htmlresponse);

            $('#orders_row_count').html(data.pos_count);
            $('#orders_pos_count').html(data.orders_pos_count);
            $('#modal_orders_pos_count').html(`<span>${data.orders_pos_count}</span>шт.`);

            // $(block).closest('tr').remove();
            // close_Loading_circle();
            make_message('Успешно удалена позиция', 'success');
            setTimeout(function() {
                        clear_user_messages();
                    }, 15000);
        }
        else if (data.status === 'success' && data.type==='order_delete'){

            $(block).closest('tr').remove();
            window.location = data.url;


        }
        else{
            // close_Loading_circle();
            alert(data.status);

        }


    } catch (e) {
        console.log(e)
        close_Loading_circle();
        make_connection_error_message('Произошла ошибка. Обратитесь к администратору', 'error');
            setTimeout(function() {
                        clear_user_messages();
                    }, 5000);
        return false;
    }

}


  function parfum_load_upload_table(url)
  {

   // var csrf_token = "{{ csrf_token() }}";
   var form = $("#form_process_main").serialize();
   var trademark = $('#trademark').val();
   var message = '';
   var message_type = '';

   $.ajax({
    url:url,
    // headers:{"X-CSRFToken": csrf_token},
    method:"POST",
    data: form,
    success:function(data)
    {
        if(data.status==='success'){
          $('#step-3_update').html(data);
          $("#step-3_update").append(data.htmlresponse);
          $('#orders_row_count').html(data.pos_count);
          $('#orders_pos_count').html(data.orders_pos_count);
          $('#modal_orders_pos_count').html(`<span>${data.orders_pos_count}</span>шт.`);

          let add_edit = '';
          if(window.location.pathname.includes('edit_order')){
               add_edit += 'изменена'
          }
          else{
              add_edit += 'добавлена'
          }
          message = `Позиция с товарным знаком ${trademark} успешно ${add_edit}`;
          message_type = 'success';
          make_message(message, message_type);
          parfum_clear_pos();
        }
        else{
           message = 'Произошла ошибка во время сохранения позиции';
           message_type = 'danger';
           make_message(message, message_type);
        }
    },
    error: function() {
        make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');
    }
   });

   // parfum_clear_pos();
   setTimeout(function() {clear_user_messages();}, 15000);
  }


async function parfum_update_table(page)
  {
   // console.log('Обновляю')
   $.ajax({
    url:page,
    method:"GET",
    success:function(data)
    {
      $('#step-3_update').html(data);
      $("#step-3_update").append(data.htmlresponse);
    }
   });

  }


function parfum_clear_pos(){
    $('#trademark').val("");
    $('#volume').val("");

    $('#type').val('').trigger("change");
    $('#volume_type').val('').trigger("change");
    $('#package_type').val('').trigger("change");
    $('#material_package').val('').trigger("change");
    $('#country').val('').trigger("change");
    $('#rd_type').val('').trigger("change");
    $('#tax').val('').trigger("change");

    $('#tnved_code').val("");
    // $('#article_price').val("");
    $('#rd_name').val("");
    $('#rd_date').val("");

    $('#quantity').val('1');
    check_valid(document.getElementById('tax'));
    check_valid(document.getElementById('article_price'));

}

// function countParfum(){
//     var total = 1;
//     document.querySelectorAll('[id=quantity_info]').forEach(el=>total+=+parseInt(el.innerText, 10));
//     return total
//
// }


function setParfum(){
    var total = 0;

    var wp = document.getElementById('with_packages');
    var q_box = 1;
    if (wp.value === "True"){
        let q_box_raw = document.getElementById('box_quantity')
        if(q_box_raw){q_box = document.getElementById('box_quantity').value;}

    }

    document.getElementById('quantity').value;
    // document.getElementById('parfum_in_pos_info').innerHTML = '';
    // document.getElementById('parfum_in_pos_info').innerText= q_box*total;
    document.getElementById('parfum_in_box_info').innerHTML = '';
    document.getElementById('parfum_in_box_info').innerText = total;
}

function updateVolumeParams() {
        let volumeType = document.getElementById('volume_type').value;
        let volumeInput = document.getElementById('volume');


        if (volumeType === 'мл') {
            volumeInput.min = 5;
            volumeInput.step = 5;
            volumeInput.max = 5000;
        } else if (volumeType === 'л') {
            volumeInput.min = 1;
            volumeInput.step = 1;
            volumeInput.max = 100;
        } else {
            volumeInput.min = 1;
            volumeInput.step = 1;
            volumeInput.max = 10000;
        }
        volumeInput.value = volumeInput.min;
    }

function check_volume_input(field){
    if (!field.checkValidity()){
        if (parseInt(field.value, 10) > 10){
            field.value= field.min;
            make_message('Проверьте корретность заполняемого значения Объема. в соответсвии с выбранными единицами измерения', 'error')}
        }

}