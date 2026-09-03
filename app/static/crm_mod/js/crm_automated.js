function automatedGetCurrentManagerId() {
  var managerSelect = document.getElementById('selectManager');
  return managerSelect ? managerSelect.value : '';
}

function automatedGetColumnOrdersUrl() {
  var config = automatedGetCrmConfig();
  return (config && config.dataset.columnOrdersUrl) || window.AUTOMATED_COLUMN_URL || '';
}

function automatedGetDefaultPerPage() {
  var config = automatedGetCrmConfig();
  var perPage = config ? parseInt(config.dataset.defaultPerPage || '50', 10) : 50;
  return Number.isFinite(perPage) && perPage > 0 ? perPage : 50;
}

function automatedGetSelectedPerPage() {
  var select = document.getElementById('automatedPerPageSelect');
  var selected = select ? parseInt(select.value || String(automatedGetDefaultPerPage()), 10) : automatedGetDefaultPerPage();
  return Number.isFinite(selected) && selected > 0 ? selected : automatedGetDefaultPerPage();
}

function automatedApplyPerPage(url) {
  var base = new URL(url, window.location.origin);
  base.searchParams.set('per_page', String(automatedGetSelectedPerPage()));
  return base.pathname + base.search;
}

function automatedChangePerPage() {
  var config = automatedGetCrmConfig();
  if (config) {
    config.dataset.defaultPerPage = String(automatedGetSelectedPerPage());
  }
  automatedFetchBoard();
}

function automatedUpdateWeeklyCounters(weeklyCounters) {
  if (!weeklyCounters) {
    return;
  }

  var countersElement = document.getElementById('automatedWeeklyCounters');
  if (!countersElement) {
    return;
  }

  countersElement.textContent =
    weeklyCounters.range +
    ' | Обработано: ' + weeklyCounters.processed +
    ' | Отменено: ' + weeklyCounters.cancelled +
    ' | Проблемных: ' + weeklyCounters.problem;
}

function automatedFetchBoard(options) {
  options = options || {};
  var showSuccessMessage = options.showSuccessMessage === true;
  var requestUrl = automatedApplyPerPage(update_url_temp || update_url);
  $.ajax({
    url: requestUrl,
    method: "GET",
    success: function(data) {
      if (data.status === 'success') {
        $('#update_all_info').html(data.htmlresponse);
        automatedUpdateWeeklyCounters(data.weekly_counters);
        initializeJSPage(document);
        automatedInitColumnPagination(document);
        if (showSuccessMessage) {
          make_message('Данные успешно обновлены', 'success');
        }
      } else {
        make_message('Нет карточек заказов. Проверьте категории или оператора!', 'warning');
      }
    },
    error: function() {
      make_message('Не удалось обновить данные CRM. Обновите страницу и попробуйте снова', 'danger');
    }
  });

  setTimeout(function() { clear_user_messages(); }, 15000);
}

function update_crm_info() {
  automatedFetchBoard();
}

function automatedRefreshBoard() {
  automatedFetchBoard();
}

function automatedRenderColumnItems(columnElement, data, appendMode) {
  if (!columnElement) {
    return;
  }

  var sentinel = columnElement.querySelector('.automated-column-sentinel');

  if (!appendMode) {
    columnElement.innerHTML = '';
    sentinel = null;
  }

  if (data.htmlresponse) {
    if (appendMode && sentinel) {
      sentinel.insertAdjacentHTML('beforebegin', data.htmlresponse);
    } else {
      columnElement.insertAdjacentHTML('beforeend', data.htmlresponse);
    }
  }

  columnElement.dataset.page = String(data.page || 1);
  columnElement.dataset.perPage = String(data.per_page || automatedGetDefaultPerPage());
  columnElement.dataset.nextPage = String(data.next_page || data.page || 1);
  columnElement.dataset.hasMore = data.has_more ? '1' : '0';
  columnElement.dataset.loading = '0';

  var quantityElement = document.getElementById(columnElement.id + '_quantity');
  if (quantityElement) {
    quantityElement.textContent = '(' + (data.quantity || 0) + ')';
  }

  initializeJSPage(columnElement);

  window.requestAnimationFrame(function() {
    automatedProcessVisibleColumns();
  });
}

function automatedLoadColumnPage(columnElement) {
  if (!columnElement || columnElement.dataset.loading === '1' || columnElement.dataset.hasMore !== '1') {
    return;
  }

  var columnUrl = automatedGetColumnOrdersUrl();
  if (!columnUrl) {
    return;
  }

  var stage = parseInt(columnElement.dataset.stage || '0', 10);
  var page = parseInt(columnElement.dataset.nextPage || '1', 10);
  var perPage = automatedGetSelectedPerPage();
  if (!stage) {
    return;
  }

  columnElement.dataset.loading = '1';

  $.ajax({
    url: columnUrl,
    method: 'GET',
    data: {
      stage: stage,
      page: page,
      per_page: perPage,
      category: get_current_category(),
      filtered_manager_id: automatedGetCurrentManagerId(),
    },
    success: function(data) {
      if (data.status === 'success') {
        automatedRenderColumnItems(columnElement, data, true);
      } else {
        columnElement.dataset.loading = '0';
        make_message(data.message || 'Не удалось подгрузить заказы', 'error');
      }
    },
    error: function() {
      columnElement.dataset.loading = '0';
      make_message('Ошибка подгрузки заказов. Обновите страницу и попробуйте снова', 'danger');
    }
  });
}

function automatedColumnNeedsViewportLoad(columnElement) {
  if (!columnElement || columnElement.dataset.loading === '1' || columnElement.dataset.hasMore !== '1') {
    return false;
  }

  var rect = columnElement.getBoundingClientRect();
  var viewportHeight = window.innerHeight || document.documentElement.clientHeight || 0;
  return rect.bottom <= viewportHeight + 160;
}

function automatedProcessVisibleColumns() {
  var columns = document.querySelectorAll('.automated-orders-list[data-stage]');
  columns.forEach(function(columnElement) {
    if (automatedColumnNeedsViewportLoad(columnElement)) {
      automatedLoadColumnPage(columnElement);
    }
  });
}

function automatedInitColumnPagination(root) {
  var scope = root || document;
  var columns = scope.querySelectorAll('.automated-orders-list[data-stage]');

  columns.forEach(function(columnElement) {
    if (columnElement._automatedScrollHandler) {
      columnElement.removeEventListener('scroll', columnElement._automatedScrollHandler);
    }

    columnElement._automatedScrollHandler = function() {
      if (columnElement.dataset.loading === '1' || columnElement.dataset.hasMore !== '1') {
        return;
      }

      var remainingHeight = columnElement.scrollHeight - columnElement.scrollTop - columnElement.clientHeight;
      if (remainingHeight <= 120) {
        automatedLoadColumnPage(columnElement);
      }
    };

    columnElement.addEventListener('scroll', columnElement._automatedScrollHandler, { passive: true });
  });

  if (!window.__automatedColumnObserver && 'IntersectionObserver' in window) {
    window.__automatedColumnObserver = new IntersectionObserver(function(entries) {
      entries.forEach(function(entry) {
        if (!entry.isIntersecting) {
          return;
        }

        var sentinel = entry.target;
        var columnElement = sentinel.closest('.automated-orders-list');
        if (columnElement) {
          automatedLoadColumnPage(columnElement);
        }
      });
    }, {
      root: null,
      rootMargin: '0px 0px 240px 0px',
      threshold: 0,
    });
  }

  if (window.__automatedColumnObserver) {
    window.__automatedColumnObserver.disconnect();
    var sentinels = scope.querySelectorAll('.automated-column-sentinel');
    sentinels.forEach(function(sentinel) {
      window.__automatedColumnObserver.observe(sentinel);
    });
  }

  if (!window.__automatedViewportPaginationHandler) {
    window.__automatedViewportPaginationHandler = function() {
      automatedProcessVisibleColumns();
    };
    window.addEventListener('scroll', window.__automatedViewportPaginationHandler, { passive: true });
    window.addEventListener('resize', window.__automatedViewportPaginationHandler, { passive: true });
  }

  window.requestAnimationFrame(function() {
    automatedProcessVisibleColumns();
  });
}

function automatedScheduleHourlyReload() {
  if (window.__automatedHourlyReloadScheduled) {
    return;
  }

  var config = automatedGetCrmConfig();
  var enabled = config && config.dataset.enableHourlyReload === 'true';
  if (!enabled) {
    return;
  }

  window.__automatedHourlyReloadScheduled = true;
  window.setTimeout(function() {
    window.location.reload();
  }, 60 * 60 * 1000);
}

function automatedGetCrmConfig() {
  return document.getElementById('crm-config');
}

function automatedBuildOrderLogsUrl(orderId) {
  var config = automatedGetCrmConfig();
  var template = config ? config.dataset.orderLogsUrlTemplate : '';
  if (!template) {
    return '';
  }
  return template.replace('/0/', '/' + String(orderId) + '/');
}

function automatedBuildOrderTechnicalInfoUrl(orderId) {
  var config = automatedGetCrmConfig();
  var template = config ? config.dataset.orderTechnicalInfoUrlTemplate : '';
  if (!template) {
    return '';
  }
  return template.replace('/0/', '/' + String(orderId) + '/');
}

function automatedOpenOrderLogs(trigger, event) {
  if (event) {
    event.preventDefault();
    event.stopPropagation();
  }

  var orderId = trigger ? trigger.dataset.orderId : '';
  var orderIdn = trigger ? trigger.dataset.orderIdn : '';
  var logsUrl = automatedBuildOrderLogsUrl(orderId);
  var modalEl = document.getElementById('automatedOrderLogsModal');
  var bodyEl = document.getElementById('automated_order_logs_modal_body');
  var titleEl = document.getElementById('automatedOrderLogsModalLabel');

  if (!logsUrl || !modalEl || !bodyEl || !titleEl) {
    make_message('Не удалось открыть логи заказа', 'error');
    return;
  }

  titleEl.textContent = orderIdn ? ('Логи заказа ' + orderIdn) : 'Логи заказа';
  bodyEl.innerHTML = '<div class="text-muted small">Загрузка...</div>';

  fetch(logsUrl, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
    .then(function(response) {
      return response.json();
    })
    .then(function(data) {
      if (data.status !== 'success') {
        make_message(data.message || 'Не удалось загрузить логи заказа', 'error');
        bodyEl.innerHTML = '<div class="text-danger small">Не удалось загрузить логи заказа</div>';
        return;
      }
      titleEl.textContent = data.title || titleEl.textContent;
      bodyEl.innerHTML = data.html || '<div class="text-muted small">Логи отсутствуют</div>';
      bootstrap.Modal.getOrCreateInstance(modalEl).show();
    })
    .catch(function() {
      bodyEl.innerHTML = '<div class="text-danger small">Ошибка при загрузке логов</div>';
      make_message('Ошибка при загрузке логов заказа', 'error');
    });
}

function automatedOpenOrderTechnicalInfo(trigger, event) {
  if (event) {
    event.preventDefault();
    event.stopPropagation();
  }

  var orderId = trigger ? trigger.dataset.orderId : '';
  var orderIdn = trigger ? trigger.dataset.orderIdn : '';
  var infoUrl = automatedBuildOrderTechnicalInfoUrl(orderId);
  var modalEl = document.getElementById('automatedOrderTechnicalInfoModal');
  var bodyEl = document.getElementById('automated_order_technical_info_modal_body');
  var titleEl = document.getElementById('automatedOrderTechnicalInfoModalLabel');

  if (!infoUrl || !modalEl || !bodyEl || !titleEl) {
    make_message('Не удалось открыть техническую информацию заказа', 'error');
    return;
  }

  titleEl.textContent = orderIdn ? ('Техническая информация заказа ' + orderIdn) : 'Техническая информация заказа';
  bodyEl.innerHTML = '<div class="text-muted small">Загрузка...</div>';

  fetch(infoUrl, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
    .then(function(response) {
      return response.json();
    })
    .then(function(data) {
      if (data.status !== 'success') {
        make_message(data.message || 'Не удалось загрузить техническую информацию заказа', 'error');
        bodyEl.innerHTML = '<div class="text-danger small">Не удалось загрузить техническую информацию заказа</div>';
        return;
      }
      titleEl.textContent = data.title || titleEl.textContent;
      bodyEl.innerHTML = data.html || '<div class="text-muted small">Техническая информация отсутствует</div>';
      bootstrap.Modal.getOrCreateInstance(modalEl).show();
    })
    .catch(function() {
      bodyEl.innerHTML = '<div class="text-danger small">Ошибка при загрузке технической информации</div>';
      make_message('Ошибка при загрузке технической информации заказа', 'error');
    });
}

function process_attach_file(file_url, link_url, csrf, o_id, order_idn, manager_id) {
  var modal_block = document.getElementById("blockModalFileLinkAttach");
  modal_block.innerHTML = `<div class="modal fade" id="modalFileLink" tabindex="-1" aria-labelledby="Окно выбора файла" aria-hidden="true">
    <div class="modal-dialog modal-dialog-centered">
      <div class="modal-content">
        <div class="modal-header ">
          <h5 class="modal-title" id="attach_file_title">Прикрепите файлы заказа ${order_idn}</h5>
          <button type="button" class="btn-close" data-bs-dismiss="modal" onclick="document.getElementById('blockModalFileLinkAttach').innerHTML='';" aria-label="Закрыть"></button>
        </div>
        <div class="modal-body">
          <form id="mainForm">
            <div class="form-check form-switch mb-4">
              <input class="form-check-input border border-light" type="checkbox" id="modalLinkFileToggleSwitch" onclick="attach_file_link_toggle();">
              <span class="form-check-label" for="modalLinkFiletoggleSwitch" id="moadlFileLinkToggleLabel">Прикрепить архив</span>
            </div>
            <div class="mb-3" id="modalFileUploadGroup">
              <div class="input-group">
                <button class="btn btn-secondary font-12" type="button" onclick="document.getElementById('order${o_id}_file_input').click();">Выбрать файл...</button>
                <span id="order${o_id}_attachFileName" class="form-control">Файл не выбран</span>
                <input type="file" class="form-control" accept=".rar, .zip" id="order${o_id}_file_input" style="display: none;" onchange="attachFileUpdateFileName('${o_id}')" name="order_file" aria-label="Upload" lang="ru">
                <button class="btn btn-outline-warning" type="button" onclick="process_post_attach_file('order${o_id}_file_input', '${file_url}','${csrf}', '${o_id}', '${manager_id || ''}');">Сохранить</button>
              </div>
            </div>
            <div class="mb-3" id="modalLinkInputGroup" style="display: none;">
              <div class="input-group">
                <input type="url" class="form-control" minlength="5" maxlength="100" id="of_link${o_id}" name="of_link" placeholder="Введите ссылку">
                <button class="btn btn-primary" type="button" onclick="process_post_attach_link('of_link${o_id}', '${link_url}','${csrf}', '${o_id}', '${manager_id || ''}');">Сохранить</button>
              </div>
            </div>
          </form>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" data-bs-dismiss="modal" onclick="document.getElementById('blockModalFileLinkAttach').innerHTML='';">Закрыть</button>
        </div>
      </div>
    </div>
  </div>`;
  $('#modalFileLink').modal('show');
}

function automatedPost(url, csrf, payload) {
  loadingCircle();
  return $.ajax({
    url: url,
    headers: {"X-CSRFToken": csrf},
    method: "POST",
    data: payload || {},
  }).always(function() {
    close_Loading_circle();
  });
}

function automatedTakeOrder(url, csrf) {
  automatedPost(url, csrf, {}).done(function(data) {
    make_message(data.message, data.status === 'success' ? 'success' : 'error');
    if (data.status === 'success') {
      clear_search_order_res();
      automatedRefreshBoard();
    }
  }).fail(function() {
    make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');
  });
}

function automatedProblemOrder(url, csrf, orderIdn) {
  document.getElementById('problem_orderModalLabel').innerHTML = `Вы хотите указать проблему в заказе номер ${orderIdn}!`;
  document.getElementById('order_problem_block').innerHTML = `
    <div class="modal-body text-justify">
      <form id="problem_order_form">
        <input type="hidden" name="csrf_token" value="${csrf}">
        <label>Проблема в заказе</label>
        <input type="text" minlength="3" maxlength="150" id="problem_order_comment" name="problem_order_comment" class="form-control" placeholder="Введите описание проблемы" required>
      </form>
      <div class="modal-footer">
        <button type="button" class="btn btn-sm btn-secondary" data-bs-dismiss="modal">Отмена</button>
        <button class="btn btn-sm bg-error mt-1" type="button" onclick="automatedSubmitProblem('${url}', '${csrf}')">Отправить заказ в проблемные</button>
      </div>
    </div>`;
  $('#problem_orderModal').modal('show');
}

function automatedSubmitProblem(url, csrf) {
  if (!document.getElementById('problem_order_form').reportValidity()) {
    return;
  }
  automatedPost(url, csrf, {
    problem_order_comment: document.getElementById('problem_order_comment').value,
  }).done(function(data) {
    make_message(data.message, data.status === 'success' ? 'success' : 'error');
    if (data.status === 'success') {
      $('#problem_orderModal').modal('hide');
      document.getElementById('order_problem_block').innerHTML = '';
      clear_search_order_res();
      automatedRefreshBoard();
    }
  }).fail(function() {
    make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');
  });
}

function automatedProcessOrder(url, csrf) {
  automatedPost(url, csrf, {}).done(function(data) {
    make_message(data.message, data.status === 'success' ? 'success' : 'error');
    if (data.status === 'success') {
      clear_search_order_res();
      automatedRefreshBoard();
    }
  }).fail(function() {
    make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');
  });
}

function automatedBackToWork(url, csrf) {
  automatedPost(url, csrf, {}).done(function(data) {
    make_message(data.message, data.status === 'success' ? 'success' : 'error');
    if (data.status === 'success') {
      clear_search_order_res();
      automatedRefreshBoard();
    }
  }).fail(function() {
    make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');
  });
}

function automatedMoveStageDirect(url, csrf, orderIdn, targetStage) {
  if (String(targetStage) === String(AUTOMATED_STAGE_PROBLEM)) {
    automatedOpenStageCommentModal({
      modalTitle: `Комментарий к переводу заказа ${orderIdn} в проблему`,
      label: 'Комментарий проблемы',
      placeholder: 'Введите комментарий к проблеме',
      submitLabel: 'Перевести в проблему',
      submitClass: 'btn btn-sm bg-error mt-1',
      url: url,
      csrf: csrf,
      targetStage: targetStage,
      required: false,
      defaultValue: '',
    });
    return;
  }

  if (String(targetStage) === String(AUTOMATED_STAGE_CANCELLED)) {
    automatedOpenStageCommentModal({
      modalTitle: `Причина отмены заказа ${orderIdn}`,
      label: 'Причина отмены',
      placeholder: 'Введите причину отмены',
      submitLabel: 'Перевести в отменено',
      submitClass: 'btn btn-sm bg-danger text-white mt-1',
      url: url,
      csrf: csrf,
      targetStage: targetStage,
      required: true,
      defaultValue: 'Стадия изменена оператором automated CRM',
    });
    return;
  }

  automatedSubmitMoveStage(url, csrf, targetStage, '');
}

function automatedOpenStageCommentModal(config) {
  document.getElementById('automatedStageCommentModalLabel').innerHTML = config.modalTitle;
  document.getElementById('automated_stage_comment_block').innerHTML = `
    <div class="modal-body text-justify">
      <form id="automated_stage_comment_form">
        <input type="hidden" name="csrf_token" value="${config.csrf}">
        <label>${config.label}</label>
        <input type="text" ${config.required ? 'minlength="3" maxlength="150" required' : 'maxlength="150"'} id="automated_stage_comment_input" name="stage_comment" class="form-control" placeholder="${config.placeholder}" value="${config.defaultValue || ''}">
      </form>
      <div class="modal-footer">
        <button type="button" class="btn btn-sm btn-secondary" data-bs-dismiss="modal">Отмена</button>
        <button class="${config.submitClass}" type="button" onclick="automatedSubmitMoveStage('${config.url}', '${config.csrf}', '${config.targetStage}', document.getElementById('automated_stage_comment_input').value, ${config.required ? 'true' : 'false'})">${config.submitLabel}</button>
      </div>
    </div>`;
  $('#automated_stage_commentModal').modal('show');
}

function automatedSubmitMoveStage(url, csrf, targetStage, stageComment, requiredComment) {
  if (requiredComment && !document.getElementById('automated_stage_comment_form').reportValidity()) {
    return;
  }

  automatedPost(url, csrf, {
    target_stage: targetStage,
    stage_comment: stageComment || '',
  }).done(function(data) {
    make_message(data.message, data.status === 'success' ? 'success' : 'error');
    if (data.status === 'success') {
      $('#automated_stage_commentModal').modal('hide');
      document.getElementById('automated_stage_comment_block').innerHTML = '';
      clear_search_order_res();
      automatedRefreshBoard();
    }
  }).fail(function() {
    make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');
  });
}

function automatedCancelOrder(url, csrf, orderIdn) {
  document.getElementById('cancel_orderModalLabel').innerHTML = `Вы хотите отменить заказ номер ${orderIdn}!`;
  document.getElementById('order_cancel_block').innerHTML = `
    <div class="modal-body text-justify">
      <form id="cancel_order_form">
        <input type="hidden" name="csrf_token" value="${csrf}">
        <label>Причина отмены заказа</label>
        <input type="text" minlength="3" maxlength="150" id="cancel_order_comment" name="cancel_order_comment" class="form-control" placeholder="Введите причину отказа" required>
      </form>
    </div>
    <div class="modal-footer">
      <button type="button" class="btn btn-sm btn-secondary" data-bs-dismiss="modal">Отмена</button>
      <button class="btn btn-sm bg-danger text-white mt-1" type="button" onclick="automatedSubmitCancel('${url}', '${csrf}')">Отменить заказ</button>
    </div>`;
  $('#cancel_orderModal').modal('show');
}

function automatedSubmitCancel(url, csrf) {
  if (!document.getElementById('cancel_order_form').reportValidity()) {
    return;
  }
  automatedPost(url, csrf, {
    cancel_order_comment: document.getElementById('cancel_order_comment').value,
  }).done(function(data) {
    make_message(data.message, data.status === 'success' ? 'success' : 'error');
    if (data.status === 'success') {
      $('#cancel_orderModal').modal('hide');
      document.getElementById('order_cancel_block').innerHTML = '';
      clear_search_order_res();
      automatedRefreshBoard();
    }
  }).fail(function() {
    make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');
  });
}

function process_post_attach_file(file_input_id, file_url, csrf, o_id, manager_id) {
  if (!check_attach_file(file_input_id)) {
    return;
  }

  $('#modalFileLink').modal('hide');
  loadingCircle();
  let file_input = document.getElementById(file_input_id);
  let formData = new FormData();
  formData.append('order_file', file_input.files[0]);
  if (manager_id) {
    formData.append('manager_id', manager_id);
  }

  $.ajax({
    url: file_url,
    headers: {"X-CSRFToken": csrf},
    method: 'POST',
    data: formData,
    processData: false,
    contentType: false,
    success: function(data) {
      make_message(data.message, data.status === 'success' ? 'success' : 'error');
      if (data.status === 'success') {
        clear_search_order_res();
        automatedRefreshBoard();
      }
      document.getElementById('blockModalFileLinkAttach').innerHTML = '';
      close_Loading_circle();
    },
    error: function() {
      document.getElementById('blockModalFileLinkAttach').innerHTML = '';
      close_Loading_circle();
      make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');
    }
  });
}

function process_post_attach_link(link_input_id, link_url, csrf, o_id, manager_id) {
  let link_block = document.getElementById(link_input_id);
  let link_value = link_block.value;
  if (!check_link(link_value, link_block)) {
    $('#modalFileLink').modal('hide');
    return;
  }

  $('#modalFileLink').modal('hide');
  loadingCircle();
  $.ajax({
    url: link_url,
    headers: {"X-CSRFToken": csrf},
    method: 'POST',
    data: {of_link: link_value, manager_id: manager_id},
    success: function(data) {
      make_message(data.message, data.status === 'success' ? 'success' : 'error');
      if (data.status === 'success') {
        clear_search_order_res();
        automatedRefreshBoard();
      }
      document.getElementById('blockModalFileLinkAttach').innerHTML = '';
      close_Loading_circle();
    },
    error: function() {
      document.getElementById('blockModalFileLinkAttach').innerHTML = '';
      close_Loading_circle();
      make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');
    }
  });
}

function process_post_delete_file(url, csrf, o_id, manager_id) {
  loadingCircle();
  $.ajax({
    url: url,
    headers: {"X-CSRFToken": csrf},
    method: 'POST',
    data: {manager_id: manager_id},
    success: function(data) {
      make_message(data.message, data.status === 'success' ? 'success' : 'error');
      if (data.status === 'success') {
        clear_search_order_res();
        automatedRefreshBoard();
      }
      document.getElementById('blockModalFileLinkAttach').innerHTML = '';
      close_Loading_circle();
    },
    error: function() {
      document.getElementById('blockModalFileLinkAttach').innerHTML = '';
      close_Loading_circle();
      make_message('Ошибка CSRF. Обновите страницу и попробуйте снова', 'danger');
    }
  });
}