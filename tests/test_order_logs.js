const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function setup() {
  const events = {};
  const elements = {};
  for (const id of ['order-logs-modal', 'order-logs-modal-body', 'order-logs-modal-title', 'order-logs-spinner']) {
    const classes = new Set(['d-none']);
    elements[id] = {
      textContent: '',
      classList: { add: c => classes.add(c), remove: c => classes.delete(c), contains: c => classes.has(c) },
      addEventListener: (type, listener) => { events[type] = listener; },
    };
  }
  const requests = [];
  let shown = 0;
  const context = {
    window: {}, AbortController, SyntaxError,
    document: { getElementById: id => elements[id] },
    bootstrap: {
      Tooltip: { getInstance: () => null },
      Modal: { getOrCreateInstance: () => ({ show: () => { shown++; } }) },
    },
    fetch: (url, options) => new Promise((resolve, reject) => requests.push({ url, options, resolve, reject })),
  };
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../app/static/crm_mod/js/order_logs.js'), 'utf8'), context);
  const event = { preventDefault() {}, stopPropagation() {} };
  const open = id => context.window.orderLogsOpen(event, { dataset: { logsUrl: `/orders/${id}/logs`, orderIdn: `N${id}` } });
  return { elements, events, requests, open, shown: () => shown };
}

function respond(request, data, ok = true) {
  request.resolve({ ok, json: async () => data });
}

(async function () {
  {
    const env = setup();
    const pending = env.open(1);
    assert.equal(env.shown(), 1);
    assert.equal(env.elements['order-logs-modal-body'].textContent, 'Загрузка…');
    assert.equal(env.elements['order-logs-spinner'].classList.contains('d-none'), false);
    assert.equal(env.requests[0].options.cache, 'no-store');
    const log = '<script>unsafe()</script> operator: прикрепил файл;';
    respond(env.requests[0], { status: 'success', logs: log });
    await pending;
    assert.equal(env.elements['order-logs-modal-body'].textContent, log);
    assert.equal(env.elements['order-logs-spinner'].classList.contains('d-none'), true);
    assert.equal(env.elements['order-logs-modal-title'].textContent, 'Логи заказа № N1');
  }
  {
    const env = setup();
    const first = env.open(1);
    const second = env.open(2);
    assert.equal(env.requests[0].options.signal.aborted, true);
    respond(env.requests[1], { status: 'success', logs: 'second' });
    await second;
    // Simulate a response arriving despite cancellation.
    respond(env.requests[0], { status: 'success', logs: 'first' });
    await first;
    assert.equal(env.elements['order-logs-modal-body'].textContent, 'second');
    assert.equal(env.elements['order-logs-modal-title'].textContent, 'Логи заказа № N2');
  }
  {
    const env = setup();
    const pending = env.open(1);
    env.events['hide.bs.modal']();
    assert.equal(env.requests[0].options.signal.aborted, true);
    respond(env.requests[0], { status: 'success', logs: 'late' });
    await pending;
    assert.notEqual(env.elements['order-logs-modal-body'].textContent, 'late');
  }
  {
    const env = setup();
    const pending = env.open(1);
    respond(env.requests[0], { status: 'error', message: 'Нет доступа к заказу' }, false);
    await pending;
    assert.equal(env.elements['order-logs-modal-body'].textContent, 'Нет доступа к заказу');
    assert.equal(env.elements['order-logs-modal-body'].classList.contains('text-danger'), true);
    const retry = env.open(1);
    assert.equal(env.elements['order-logs-modal-body'].classList.contains('text-danger'), false);
    respond(env.requests[1], { status: 'success', logs: '' });
    await retry;
    assert.equal(env.elements['order-logs-modal-body'].textContent, 'Логи пустые');
  }
  console.log('Order log UI: loading, text rendering, races, close, errors and retry passed');
})().catch(error => { console.error(error); process.exitCode = 1; });
