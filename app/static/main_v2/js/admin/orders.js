function bck_get_orders(url){
   $.ajax({
    url: url,
    method:"GET",

    success:function(data)
    {
      if (data.status && data.status==='success'){
          $('#OrdersTable').html(data);
          $('#OrdersTable').append(data.htmlresponse);
      }
    },
    error: function() {
        // make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');
        setTimeout(function() {make_message('Ошибка. В базе нет информации об этих пользователях', 'danger');}, 3500);
     }
   });

}

function bck_order_process(url, url_update, csrf, stage)
  {
   $.ajax({
    url:url,
    headers:{"X-CSRFToken": csrf},
    method:"POST",
    data: {'change_stage': stage},
    success:function(data)
    {
        console.log(data);
        if(data.status==='success'){
            if (data.reload){
                window.location.reload();
            }
            else{
            bck_get_orders(url_update);
            }

        }

        make_message(data.message, data.status);
    },
     error: function() {
         make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');
     }
   });

   setTimeout(function() {clear_user_messages();}, 15000);
  }



  // unused
function modal_processOrder(url, update_url, csrf, process_order_type ){
    let modal_block = document.getElementById('modalWindows');


    let bg_color = '';
    if (process_order_type==='push2pool'){
        bg_color = 'bg-success';
    }
    else{
        bg_color = 'bg-danger';
    }
    modal_block.innerHTML = `<div class="modal fade" id="service_priceModal" tabindex="-1" role="dialog" data-bs-backdrop="static" aria-labelledby="service_priceModalLabel" aria-hidden="true">
          <div class="modal-dialog" data-backdrop="static" role="document">
            <div class="modal-content">
              <div class="modal-header ">
                <h5 class="modal-title" id="service_priceModalLabel">Форма удаления ценового пакета ${p_code}.</h5>
                <button type="button" class="btn-close" onclick="clear_modal_processOrder();" data-bs-dismiss="modal" aria-label="Close">
                </button>
              </div>
              <div class="modal-body">
                  <div class="row">
                      <div class="col-2"></div>
                      <div class="col-8">
                        <button type="button" class="btn btn-secondary" onclick="clear_modal_processOrder();" data-bs-dismiss="modal">Закрыть</button>
                      </div>
                  </div>
                  
              </div>
              
              <div class="modal-footer">
                <button type="button" class="btn btn-secondary" onclick="clear_modal_processOrder();" data-bs-dismiss="modal">Закрыть</button>

              </div>
            </div>
          </div>
        </div>`;
    $("#service_priceModal").modal("show");
}

function clear_modal_processOrder(){
    let modal_block = document.getElementById('modalWindows');
    modal_block.innerHTML = '';
}