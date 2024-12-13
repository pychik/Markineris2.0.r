function bck_move_all_orders_stp(url, csrf,){
    // from sent to processed
    // loadingCircle();
    // $('#update_all_info').html('')
    $.ajax({
    url:url,
    headers:{"X-CSRFToken": csrf},
    method:"POST",
    data: {},
    success:function(data)
    {
        // console.log(data);

        make_message(data.message, data.status);
        setTimeout(function() {close_Loading_circle();}, 3000)

        update_crm_info(update_agents_url);
        // close_Loading_circle();
        // setTimeout(function() {location.reload(true);}, 5000);
    },
     error: function() {
        make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');
        // close_Loading_circle();
    }
   });

   setTimeout(function() {clear_user_messages();}, 15000);
}

function bck_all_new_multi_pool(url, csrf,){
    // from NEW to POOL
    // loadingCircle();
    // $('#update_all_info').html('');
    $.ajax({
    url:url,
    headers:{"X-CSRFToken": csrf},
    method:"POST",
    data: {},
    success:function(data)
    {
        make_message(data.message, data.status);
        // setTimeout(function() {close_Loading_circle();}, 3000)
        //
        update_crm_info(update_agents_url);
    },
     error: function() {
        make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');
        // close_Loading_circle();
    }
   });

   setTimeout(function() {clear_user_messages();}, 15000);
}

function bck_move_all_orders(url, csrf, stage_from, stage_to){
    loadingCircle();
    $.ajax({
    url:url,
    headers:{"X-CSRFToken": csrf},
    method:"POST",
    data: {'stage_from': stage_from,
           'stage_to': stage_to},
    success:function(data)
    {
        // console.log(data);

        make_message(data.message, data.status);
        setTimeout(function() {close_Loading_circle();}, 3000)

        update_crm_info(update_agents_url);
        close_Loading_circle();
        // setTimeout(function() {location.reload(true);}, 5000);
    },
     error: function() {
        make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');
        close_Loading_circle();
    }
   });

   setTimeout(function() {clear_user_messages();}, 15000);

}
