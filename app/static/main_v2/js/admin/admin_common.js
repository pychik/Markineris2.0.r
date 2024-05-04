function get_information(link, callback) {
    var xhr = new XMLHttpRequest();
    xhr.open("GET", link, true);
    xhr.onreadystatechange = function () {
        if (xhr.readyState === 4) {
            if (!xhr.responseText.startsWith('http')) {
                callback(xhr.responseText);
            } else {
                window.location.href = window.location.origin;
            }

        }
    };
    xhr.send(null);
}

function perform_modal_copy_link(u_id, u_name) {
    var modal_block = document.getElementById('copy_link_modals');
    modal_block.innerHTML = ` <div class="modal fade" id="user_linkModal${u_id}" tabindex="-1" role="dialog" data-bs-backdrop="static" aria-labelledby="user_linkModal${u_id}Label" aria-hidden="true">
          <div class="modal-dialog modal-lg" data-backdrop="static" role="document">
            <div class="modal-content">
              <div class="modal-header bg-warning">
                <h5 class="modal-title" id="user_linkModal${u_id}Label">Ссылка для смены пароля по запросу.</h5>
                <button type="button" class="btn-close" onclick="clear_copy_link();" data-bs-dismiss="modal" aria-label="Close">
                </button>
              </div>
              <div class="modal-body">
                <h5>Ссылка для смены пароля пользователя ${u_name}. Нажмите на дискету, чтобы скопировать</h5>
                  <div class="row">
                    <div class="col-11 text-center" >
                      <input class="form-control" readonly="true" type="text"
                             onclick=""
                             id="user_link${u_id}" >
                    </div>
                    <div class="col-1 text-center" >
                      <a id="copyText" type="button"
                         title="Скопировать ссылку"
                         onclick="javascript:copy_buffer('user_link${u_id}',
                                             'user_link_message${u_id}');">&#128190;</a>
                    </div>

                  </div>
                  <small class="text-secondary">Срок работы ссылки для смены пароля <b>3 часа</b> с момента ее создания.
                       После смены пароля ссылка будет недействительна.</small>
                  <span id="user_link_message${u_id}" style="color:#23c1fc"></span>
              </div>
              <div class="modal-footer">
                <button type="button" class="btn btn-secondary" onclick="clear_copy_link();" data-bs-dismiss="modal">Закрыть</button>

              </div>
            </div>
          </div>
        </div>`;

}


function clear_copy_link() {
    document.getElementById("copy_link_modals").innerHTML = '';
}