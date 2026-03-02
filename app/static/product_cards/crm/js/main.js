let __pcEventsBound = false;

function bindCrmDelegates(root = document) {
  if (__pcEventsBound) return;
  __pcEventsBound = true;

  const wrapper = root.querySelector(".crm__wrapper");
  if (!wrapper) return;

  wrapper.addEventListener("click", (e) => {
    // === 0) INTERACTIVE BUTTONS (не должны раскрывать карточку) ===
    // LOGS (обертка, чтобы клик по svg/бейджу тоже работал)
    const logsWrap = e.target.closest(".pc-logs-wrap");
    if (logsWrap) {
      const btn = logsWrap.querySelector(".pc-logs-btn") || logsWrap;
      e.preventDefault();
      e.stopPropagation();
      pcOpenCardLogs(btn);
      return;
    }

    // CHAT
    const chatWrap = e.target.closest(".pc-chat-wrap");
    if (chatWrap) {
      const btn = chatWrap.querySelector(".pc-chat-btn") || chatWrap;
      e.preventDefault();
      e.stopPropagation();
      pcChatOpen(btn);
      return;
    }

    // VIEW
    const viewEl = e.target.closest("[data-pc-action='view']");
    if (viewEl) {
      e.preventDefault();
      e.stopPropagation();
      pcOpenViewModal(viewEl.dataset.viewUrl);
      return;
    }

    // === 1) ROLL ===
    const rollEl = e.target.closest(".order__roll");
    if (rollEl) {
      const order = rollEl.closest(".order");
      if (order) order.classList.remove("active");
      e.preventDefault();
      e.stopPropagation();
      return;
    }

    // === 2) HEADER TOGGLE ===
    const headerEl = e.target.closest(".order__header");
    if (headerEl) {
      // если клик по любому интерактиву внутри header — не раскрываем
      if (
        e.target.closest(".pc-logs-wrap") ||
        e.target.closest(".pc-chat-wrap") ||
        e.target.closest("[data-pc-action='view']") ||
        e.target.closest("button") ||
        e.target.closest("a")
      ) {
        return;
      }

      const order = headerEl.closest(".order");
      if (order) order.classList.toggle("active");
      e.preventDefault();
      e.stopPropagation();
      return;
    }

    // === 3) CLICK ANYWHERE IN CARD ===
    const order = e.target.closest(".order");
    if (order && !order.classList.contains("active")) {
      // снова страховка на интерактив
      if (
        e.target.closest(".pc-logs-wrap") ||
        e.target.closest(".pc-chat-wrap") ||
        e.target.closest("[data-pc-action='view']") ||
        e.target.closest("button") ||
        e.target.closest("a")
      ) {
        return;
      }
      order.classList.add("active");
    }
  });
}

function resolveRoot(root) {
  return (root && typeof root.querySelectorAll === "function") ? root : document;
}

function disposeTooltips(root) {
  const ctx = resolveRoot(root);
  ctx.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(el => {
    const inst = bootstrap.Tooltip.getInstance(el);
    if (inst) {
      inst.hide();
      inst.dispose();
    }
  });
}

function initTooltips(root) {
  const ctx = resolveRoot(root);
  ctx.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(el => {
    new bootstrap.Tooltip(el);
  });
}

/**
 * Закрыть/убить тултипы -> обновить DOM -> заново инициализировать тултипы
 */
function withTooltipsRefresh(cb, root) {
  const ctx = resolveRoot(root);

  disposeTooltips(ctx);

  if (typeof cb === "function") {
    cb();
  }

  requestAnimationFrame(() => {
    initTooltips(ctx);
  });
}


function initializeJSPage(root) {
  const ctx = (root && root.querySelector) ? root : document;

  bindCrmDelegates(ctx);
  requestAnimationFrame(() => {
    initTooltips(ctx);
  });
}

function pcGetModalTitleEl() {
  const modal = document.getElementById("pc-view-modal");
  if (!modal) throw new Error("pc-view-modal not found");
  const title = modal.querySelector(".modal-title");
  if (!title) throw new Error("modal-title not found");
  return title;
}

function pcSetModalTitle(text) {
  pcGetModalTitleEl().textContent = text;
}


function copy_buffer(str, e) {

    // 🔥 ГАСИМ РОЛЛАП / КЛИК КАРТОЧКИ
    if (e) {
        e.preventDefault();
        e.stopPropagation();
        e.stopImmediatePropagation(); // на случай capture-обработчиков
    }

    let tmp = document.createElement('INPUT'),
        focus = document.activeElement;

    tmp.value = str;

    document.body.appendChild(tmp);
    tmp.select();
    document.execCommand('copy');
    document.body.removeChild(tmp);

    if (focus && focus.focus) {
        focus.focus();
    }

    var text = `Текст ${str} скопирован в буфер`;
    make_message(text, 'success');
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
            console.log(matches[1]);
            return matches[1];
        }
    }

    // Return null or a default value if no active category is found
    return 'all';
}



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




function init_tooltip(document){
    document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(tooltipTriggerEl => {
            new bootstrap.Tooltip(tooltipTriggerEl);
        });
}

function pcOpenViewModal(viewUrl) {
    if (!viewUrl) return;

    fetch(viewUrl, { headers: { "X-Requested-With": "XMLHttpRequest" } })
      .then(r => r.json())
      .then(data => {
        if (data.status !== "success") {
          make_message(data.message || "Не удалось загрузить карточку", "error");
          return;
        }
        pcSetModalTitle("Просмотр карточки");
        const body = document.getElementById("pc-view-modal-body");
        if (body) body.innerHTML = data.html || "";

        const modalEl = document.getElementById("pc-view-modal");
        if (!modalEl) return;

        bootstrap.Modal.getOrCreateInstance(modalEl).show();
      })
      .catch(err => {
        console.error(err);
        make_message("Ошибка при загрузке карточки", "error");
      });
  }


function update_crm_info(){

   $.ajax({
    url: update_url_temp,
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
            // if (update_url_temp) {
            //    history.replaceState(null, '', update_url_temp);
            // }
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
    update_url_temp = UPDATE_PRODUCT_CARDS_CRM_URL+ '&category=' + category;
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
