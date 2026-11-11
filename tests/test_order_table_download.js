const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function setup() {
  const requests = [];
  const messages = [];
  const downloads = [];
  const revoked = [];
  const timers = [];
  let loading = false;
  const form = {
    action: '/crm/download_order/42?flag_046=1',
    attributes: {},
    setAttribute(key, value) { this.attributes[key] = value; },
    removeAttribute(key) { delete this.attributes[key]; },
    querySelectorAll: () => [{}]
  };
  const event = {preventDefault() {}, stopPropagation() {}};
  const context = {
    window: {},
    FormData: function (value) { this.form = value; },
    bootstrap: {Tooltip: {getInstance: () => ({hide() {}})}},
    loadingCircle: () => { loading = true; },
    close_Loading_circle: () => { loading = false; },
    make_message: (...args) => messages.push(args),
    fetch: (url, options) => new Promise((resolve, reject) => requests.push({url, options, resolve, reject})),
    URL: {createObjectURL: () => 'blob:table', revokeObjectURL: url => revoked.push(url)},
    setTimeout: callback => timers.push(callback),
    document: {
      body: {appendChild() {}},
      createElement: () => ({click() { downloads.push({href: this.href, name: this.download}); }, remove() {}})
    }
  };
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../app/static/crm_mod/js/order_table_download.js'), 'utf8'), context);
  return {requests, messages, downloads, revoked, timers, form,
    loading: () => loading, start: () => context.window.downloadCrmOrderTable(event, form)};
}

function response(overrides = {}) {
  return {ok: true, redirected: false,
    headers: {get: () => 'attachment; filename="order.zip"'},
    blob: async () => ({}), ...overrides};
}

(async () => {
  const env = setup();
  const pending = env.start();
  assert.equal(env.loading(), true);
  assert.equal(env.form.attributes['aria-busy'], 'true');
  await env.start();
  assert.equal(env.requests.length, 1, 'ignore repeat clicks during a download');
  assert.equal(env.requests[0].url, env.form.action, 'preserve format 046 query');
  assert.equal(env.requests[0].options.method, 'POST');
  assert.equal(env.requests[0].options.body.form, env.form, 'include the form and CSRF token');

  let finishBlob;
  env.requests[0].resolve(response({
    headers: {get: () => "attachment; filename=order.zip; filename*=UTF-8''%D0%97%D0%B0%D0%BA%D0%B0%D0%B7.zip"},
    blob: () => new Promise(resolve => { finishBlob = resolve; })
  }));
  await new Promise(setImmediate);
  assert.equal(env.loading(), true, 'wait for the complete response body');
  assert.equal(env.messages.length, 0, 'do not report success before receiving the file');
  finishBlob({});
  await pending;
  assert.deepEqual(env.downloads, [{href: 'blob:table', name: 'Заказ.zip'}]);
  assert.deepEqual(env.messages, [['Файл скачан', 'success']]);
  assert.equal(env.loading(), false);
  assert.equal(env.form.attributes['aria-busy'], undefined);
  env.timers.forEach(callback => callback());
  assert.deepEqual(env.revoked, ['blob:table']);

  for (const result of [response({ok: false}), response({redirected: true}),
    response({headers: {get: () => null}}), response({blob: async () => { throw Error('body failed'); }}), null]) {
    const failed = setup();
    const attempt = failed.start();
    if (result) failed.requests[0].resolve(result);
    else failed.requests[0].reject(Error('network failed'));
    await attempt;
    assert.equal(failed.loading(), false);
    assert.equal(failed.form.attributes['aria-busy'], undefined);
    assert.equal(failed.downloads.length, 0);
    assert.equal(failed.messages[0][1], 'danger');
    const retry = failed.start();
    assert.equal(failed.requests.length, 2, 'allow retry after failure');
    failed.requests[1].resolve(response());
    await retry;
    assert.equal(failed.messages[1][1], 'success');
  }
  console.log('Order table download: spinner, repeat clicks, filename, notifications, failures and retries passed');
})().catch(error => { console.error(error); process.exitCode = 1; });
