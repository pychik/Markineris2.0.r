function activateAllUsers(url, csrf) {
    $.ajax({
        url: url,
        type: 'POST',
        data: { csrf_token: csrf },
        dataType: 'json',
        success: function(data) {
            make_message(data.message, data.status);
        },
        error: function(xhr, status, error) {
            console.error('Ошибка:', error);
        }
    });
}


function addNewClient(url, csrf, auto = 0, linkUpdateUrl, clientCodeUpdateUrl) {
    let fullUrl = `${url}/${auto}`;
    let code = $('#partnerCode').val();
    let name = $('#partnerName').val();
    let phone = $('#partnerPhone').val();

    if (auto === 0 && (!code || !name || !phone)) {
        alert('Заполните все обязательные поля');
        return;
    }

    let formData = new FormData();
    formData.append('code', code);
    formData.append('name', name);
    formData.append('phone', phone);
    formData.append('csrf_token', csrf);

    $.ajax({
        url: fullUrl,
        type: 'POST',
        data: formData,
        processData: false,
        contentType: false,
        success: function(data) {
            make_message(data.message, data.status);
            updateRegistrationLinks(linkUpdateUrl);
            updateClientCodesList(clientCodeUpdateUrl);
            $('#partnerCodeAdd').modal('hide');
        },
        error: function(xhr) {
            if (xhr.status === 400) {
                let errorData = xhr.responseJSON;
                make_message(errorData.message, 'error');
            }
            console.error('Ошибка:', xhr);
        }
    });
}



function deletePartnerCode(url, csrf, linkUpdateUrl, clientCodeUpdateUrl) {
    $.ajax({
        url: url,
        type: 'POST',
        data: {
            csrf_token: csrf
        },
        success: function(data) {
            make_message(data.message, data.status);
            let modalForm = $('#registeredPartnerCode');
            modalForm.modal('hide');

            modalForm.on('hidden.bs.modal', function () {
                updateRegistrationLinks(linkUpdateUrl);
                updateClientCodesList(clientCodeUpdateUrl);
            });
        },
        error: function(jqXHR, textStatus, errorThrown) {
            console.error('Ошибка:', textStatus, errorThrown);
        }
    });
}


function updateRegistrationLinks(url) {
    $.ajax({
        url: url,
        type: 'GET',
        success: function(response) {
            $('#newUserRegistrationLink table').html(response.htmlresponse);
        },
        error: function(jqXHR, textStatus, errorThrown) {
            console.error('Ошибка при обновлении модального окна:', textStatus, errorThrown);
        }
    });
}


function updateClientCodesList(url) {
    $.ajax({
        url: url,
        type: 'GET',
        success: function(response) {
            $('#registeredPartnerCode table').html(response.htmlresponse);
        },
        error: function(jqXHR, textStatus, errorThrown) {
            console.error('Ошибка при обновлении модального окна:', textStatus, errorThrown);
        }
    });
}


function setUpTelegramMessage(url, csrf_token) {
    const data = {
  send_admin_info: document.getElementById('send_admin_info').checked,
  send_organization_name: document.getElementById('send_organization_name').checked,
  send_organization_idn: document.getElementById('send_organization_idn').checked,
  send_login_name: document.getElementById('send_login_name').checked,
  send_email: document.getElementById('send_email').checked,
  send_phone: document.getElementById('send_phone').checked,
  send_client_code: document.getElementById('send_client_code').checked,
};
  $.ajax({
    url: url,
    headers:{"X-CSRFToken": csrf_token},
    method:"POST",
    data:data,
    success:function(data)
    {
        make_message(data.message,data.type)
        let modalForm = $('#telegramMessageSetup')
        modalForm.modal('hide')
    },
    error: function(data) {
        console.log('Error', data)
    }
   });
}


function setOrderNotification(url, csrf_token) {
  let data= { order_note: document.getElementById('order_note').value}
  $.ajax({
    url: url,
    headers:{"X-CSRFToken": csrf_token},
    data: data,
    method:"POST",
    success:function(data)
    {
        make_message(data.message,data.type)
        let modalForm = $('#orderNotificationPanel')
        modalForm.modal('hide')
    },
    error: function(data) {
        console.log('Error', data)
    }
   });
}


function loadUserSearchResult(query, url, csrf_token)
  {
   $.ajax({
    url: url,
    headers:{"X-CSRFToken": csrf_token},
    method:"POST",
    data:{query:query},
    success:function(data)
    {

      $('#infoModalTable').html(data);
      $('#infoModalLabel').html("Найденные пользователи по тегу " + query);
      $('#infoModalTable').append(data.htmlresponse);
      $('#infoModal').modal('show')
    },
    error: function() {
     make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');
    }
   });
}
function searchUser(url, csrf_token){
    let search = $('#search_text').val();
    if(search !== ''){
    loadUserSearchResult(search, url, csrf_token);
    }
    else{
        make_message('Пустой запрос', 'warning')
    }
}

function searchUserByIdn(url, csrf_token){
    let search = $('#search_by_idn').val();
    if(search !== ''){
        loadUserSearchResult(search, url,  csrf_token);
    }
    else{
        make_message('Пустой запрос', 'warning')
    }
}