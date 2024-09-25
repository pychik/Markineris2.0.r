function perform_modal_prices(u_id, u_name, p_code, p1, p2, p3, p4, p5, p6, p7, p8, p9, p10, p11, url, csrf){
    let modal_block = document.getElementById('user_prices_modal');
    let prices_desc_block = `<table class="table mt-1 table-result" >
                              <thead class="text-dark">
                                  <tr>
                                      <th scope="col">#</th>
                                      <th scope="col" class="font-12">Наименование</th>
                                  </tr>
                              </thead>
                               <tbody>
                                <tr>
                                  <td>[0, 99]</td>
                                  <td>${p1}</td>
                                </tr>
                                <tr>
                                  <td>[100, 499]</td>
                                  <td>${p2}</td>
                                </tr>
                                <tr>
                                  <td>[500, 999]</td>
                                  <td>${p3}</td>
                                </tr>
                                <tr>
                                  <td>[1000, 2999]</td>
                                  <td>${p4}</td>
                                </tr>
                                <tr>
                                  <td>[3000, 4999]</td>
                                  <td>${p5}</td>
                                </tr>
                                <tr>
                                  <td>[5000, 9999]</td>
                                  <td>${p6}</td>
                                </tr>
                                <tr>
                                  <td>[10000, 19999]</td>
                                  <td>${p7}</td>
                                </tr>
                                <tr>
                                  <td>[20000, 34999]</td>
                                  <td>${p8}</td>
                                </tr>
                                <tr>
                                  <td>[35000, 49999]</td>
                                  <td>${p9}</td>
                                </tr>
                                <tr>
                                  <td>[50000, 99999]</td>
                                  <td>${p10}</td>
                                </tr>
                                <tr>
                                  <td>[100000+]</td>
                                  <td>${p11}</td>
                                </tr>
                              </tbody>
                        </table>`
    var option_prices = '<option value="">BASIC</option>'

    prices_array.forEach((element) => {option_prices += `${check_price_at2_text(element)}`});

    let service_price_form = `<form id="user_price_plug_form" action="${url}" class="text-center">
                            <input type="hidden" name="csrf_token" value="${csrf}">
                            <label for="price_id">Выберите ценовой пакет</label>
                            <select class="form-select my-1" id="price_id" name="price_id">
                                ${option_prices}
                            </select>
                            <button type="button" class="btn btn-sm btn-accent" style="width: 100%" data-bs-dismiss="modal" onclick="bck_edit_user_price('${url}', 'user_price${u_id}'); clear_modal_prices();">Обновить</button>
                        </form>`

    modal_block.innerHTML = `<div class="modal fade" id="user_priceModal" tabindex="-1" role="dialog" data-bs-backdrop="static" aria-labelledby="user_priceModalLabel" aria-hidden="true">
          <div class="modal-dialog" data-backdrop="static" role="document">
            <div class="modal-content">
              <div class="modal-header">
                <h5 class="modal-title" id="user_priceModalLabel">Форма привязки ценового пакета для пользователя ${u_name}.</h5>
                <button type="button" class="btn-close" onclick="clear_modal_prices();" data-bs-dismiss="modal" aria-label="Close">
                </button>
              </div>
              <div class="modal-body">
                <h6>У клиента ценовой пакет <b>${p_code}</b>.</h6>
                  ${prices_desc_block}
                  <div class="row">
                      <div class="col-2"></div>
                      <div class="col-8">
                        ${service_price_form}
                      </div>
                  </div>
                  <div class="col text-justify">
                        <small class="text-secondary small">Вы можете выбрать новый ценовой пакет,
                                после этого <b>Нажмите обновить</b>. Либо нажмите Закрыть.
                        </small>
                  </div>
              </div>
              
              <div class="modal-footer">
                <button type="button" class="btn btn-secondary" onclick="clear_modal_prices();" data-bs-dismiss="modal">Закрыть</button>

              </div>
            </div>
          </div>
        </div>`;
    $("#user_priceModal").modal("show");
}

function check_price_at2_text(price_row){
    if (price_row[2] === 'True') {
        return `<option value="${price_row[0]}">${price_row[1]} - Агенты единый счет</option>`
    } else {
        return `<option value="${price_row[0]}">${price_row[1]}</option>`
    }
}

function clear_modal_prices() {
    document.getElementById("user_prices_modal").innerHTML = '';
}

function bck_edit_user_price(url, user_price_block)
  {
   var form = $("#user_price_plug_form").serialize();
    // console.log(form);
   $.ajax({
    url:url,
    // headers:{"X-CSRFToken": csrf},
    method:"POST",
    data: form,
    success:function(data)
    {
        // console.log(data);

        if(data.status==='success'){
            // document.getElementById(user_price_block).innerHTML = data.user_block;
            var elements = document.querySelectorAll('#'+ user_price_block);

            // Iterate over each selected element and change its content
            elements.forEach(function(element) {
                element.innerHTML = data.user_block;
            });
        }

        make_message(data.message, data.status);
    },
     error: function() {
         make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');
     }
   });

   setTimeout(function() {clear_user_messages();}, 15000);
  }
