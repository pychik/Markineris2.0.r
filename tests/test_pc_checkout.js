const fs = require('fs');
const vm = require('vm');
const assert = require('assert');

async function testCart(mode) {
  const source = fs.readFileSync('app/static/product_cards/users/pc_cart.js', 'utf8');
  const code = source.slice(source.indexOf('let oBCartSubmitting = false;'), source.indexOf('function oBIsCompanyFilled'));
  const button = {disabled: false};
  let visible = false, requests = 0, release, restore;
  const pending = new Promise(resolve => release = resolve);
  const context = {
    document: {getElementById: () => button},
    window: {addEventListener: (_, fn) => restore = fn, location: {}},
    oBCartGetSingleOrder: () => ({}), oBCartValidateOrderSettings: () => '',
    oBCartBuildPayloadOrError: () => ({payload: {}}), make_cart_message() {},
    oBCartClearAll() {}, oBCartRemoveMissingCardIds: () => mode === 'missing',
    loadingCircle: () => visible = true, close_Loading_circle: () => visible = false,
    console: {error() {}}, setTimeout() {},
    fetch: async () => {
      requests++;
      await pending;
      if (mode === 'network') throw Error('network');
      return {json: async () => mode === 'redirect'
        ? {status: 'success', redirect_url: '/orders'} : {status: 'error', missing_card_ids: [1]}};
    },
  };
  vm.createContext(context);
  vm.runInContext(code, context);
  const result = context.oBCartSubmitToBackend('/order', 'csrf');
  assert(visible && button.disabled);
  await context.oBCartSubmitToBackend('/order', 'csrf');
  assert.equal(requests, 1);
  release();
  await result;
  assert.equal(visible, mode === 'redirect');
  assert.equal(button.disabled, mode === 'redirect');
  restore({persisted: true});
  assert(!visible && !button.disabled);
}

function testFinalSubmit(fails, buttonId) {
  const source = fs.readFileSync('app/static/product_cards/users/pc_order_process.js', 'utf8');
  const code = source.slice(source.indexOf('  function performProcess()'), source.indexOf('  function setFooterOkOnly()'));
  let visible = false, submits = 0, restore, error = '';
  const button = {disabled: false}, hidden = {}, textarea = {value: 'Комментарий'};
  const form = {submit() {submits++; if (fails) throw Error('submit');}};
  const elements = {form_process: form, [buttonId]: button, order_comment: hidden, order_comment_after: textarea};
  const context = {
    document: {getElementById: id => elements[id]}, window: {addEventListener: (_, fn) => restore = fn},
    loadingCircle: () => visible = true, close_Loading_circle: () => visible = false,
    setCheckError: message => error = message,
  };
  vm.createContext(context);
  vm.runInContext('let processing = false;\n' + code, context);
  context.performProcess();
  assert.equal(hidden.value, 'Комментарий');
  assert.equal(visible, !fails);
  assert.equal(button.disabled, !fails);
  if (!fails) {context.performProcess(); assert.equal(submits, 1);}
  else assert(error);
  restore({persisted: true});
  assert(!visible && !button.disabled);
}

(async () => {
  for (const mode of ['error', 'missing', 'network', 'redirect']) await testCart(mode);
  for (const buttonId of ['btn_process', 'btn_force']) {
    for (const fails of [false, true]) testFinalSubmit(fails, buttonId);
  }
  console.log('Checkout loading, duplicate prevention, errors, comments and browser-back reset OK');
})().catch(error => {console.error(error); process.exitCode = 1;});
