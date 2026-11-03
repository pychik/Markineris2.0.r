(function () {
  'use strict';

  let controller = null;
  let requestId = 0;
  const modal = document.getElementById('order-logs-modal');
  if (!modal) return;

  modal.addEventListener('hide.bs.modal', function () {
    requestId += 1;
    if (controller) controller.abort();
  });

  window.orderLogsOpen = async function (event, button) {
    event.preventDefault();
    event.stopPropagation();

    const body = document.getElementById('order-logs-modal-body');
    const title = document.getElementById('order-logs-modal-title');
    const spinner = document.getElementById('order-logs-spinner');
    const url = button.dataset.logsUrl;
    if (!url || !body || !title || !spinner) return;

    if (controller) controller.abort();
    controller = new AbortController();
    const currentRequest = ++requestId;
    body.textContent = 'Загрузка…';
    body.classList.remove('text-danger');
    title.textContent = button.dataset.orderIdn ? `Логи заказа № ${button.dataset.orderIdn}` : 'Логи заказа';
    spinner.classList.remove('d-none');
    bootstrap.Tooltip.getInstance(button)?.hide();
    bootstrap.Modal.getOrCreateInstance(modal).show();

    try {
      const response = await fetch(url, {
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
        cache: 'no-store',
        signal: controller.signal,
      });
      const data = await response.json();
      if (!response.ok || data.status !== 'success') {
        throw new Error(data.message || 'Не удалось загрузить логи заказа');
      }
      if (currentRequest !== requestId) return;
      body.textContent = data.logs || 'Логи пустые';
    } catch (error) {
      if (currentRequest !== requestId || error.name === 'AbortError') return;
      body.textContent = error instanceof SyntaxError ? 'Не удалось загрузить логи заказа' : error.message;
      body.classList.add('text-danger');
    } finally {
      if (currentRequest === requestId) spinner.classList.add('d-none');
    }
  };
})();
