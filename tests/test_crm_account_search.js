const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../app/static/crm_mod/js/account_search.js'), 'utf8');
const main = fs.readFileSync(path.join(__dirname, '../app/static/crm_mod/js/crm_main_v1_1.js'), 'utf8');

function setup(enabled = true) {
    const elements = {};
    for (const id of ['searchOrderAccountMode', 'searchOrdertext', 'searchOrderModeLabel', 'searchOrderHelp',
                      'accountOrdersModal', 'accountOrdersResults', 'accountOrdersModalLabel']) {
        elements[id] = {
            value: '', textContent: '', innerHTML: '', dataset: {}, listeners: {},
            setAttribute(name, value) { this[name] = value; },
            removeAttribute(name) { delete this[name]; },
            replaceChildren() { this.innerHTML = ''; this.textContent = ''; },
            querySelectorAll: () => [], focus() {},
            addEventListener(name, callback) { this.listeners[name] = callback; },
        };
    }
    elements.searchOrderAccountMode.dataset.searchUrl = '/search_orders_email';
    if (!enabled) delete elements.searchOrderAccountMode;
    const requests = [], numberRequests = [], messages = [];
    let shown = 0, hidden = 0;
    const modal = {show() { shown++; }, hide() { hidden++; }};
    const jquery = () => ({html() {}, append() {}});
    jquery.ajax = options => numberRequests.push(options);
    const context = {
        window: {}, document: {getElementById: id => elements[id]},
        bootstrap: {Modal: {getInstance: () => modal, getOrCreateInstance: () => modal},
                    Tooltip: {getInstance: () => null}},
        AbortController, URLSearchParams,
        fetch: (url, options) => new Promise(resolve => requests.push({url, options, resolve})),
        make_message: message => messages.push(message), init_tooltip() {},
        initializeJSPage(document) { document._crmClickHandler = () => {}; },
        clear_user_messages() {}, setTimeout() {}, $: jquery,
    };
    vm.createContext(context);
    vm.runInContext(main.slice(main.indexOf('function clear_search_order_res()'), main.indexOf('function get_current_category()')), context);
    vm.runInContext(source, context);
    context.CrmAccountSearch = context.window.CrmAccountSearch;
    return {context, elements, requests, numberRequests, messages, shown: () => shown, hidden: () => hidden};
}

async function respond(request, data, ok = true) {
    request.resolve({ok, json: async () => data});
    await new Promise(resolve => setImmediate(resolve));
}

(async () => {
    assert.equal(setup(false).context.window.CrmAccountSearch, undefined);
    const env = setup();
    const {elements: e, context: c} = env;
    const api = c.window.CrmAccountSearch;
    e.searchOrdertext.value = '12_34';
    c.search_crm_order('/number', 'csrf');
    assert.equal(env.numberRequests.length, 1);
    assert.equal(env.numberRequests[0].data.search_order_idn, '12_34');

    e.searchOrderAccountMode.checked = true;
    api.toggle();
    assert.equal(e.searchOrdertext.type, 'email');
    assert.equal(e.searchOrderModeLabel.textContent, 'Поиск по email пользователя');
    assert.equal(e.searchOrdertext.value, '');
    e.searchOrdertext.value = 'invalid';
    await api.search('csrf');
    assert.equal(env.requests.length, 0);
    assert.equal(env.messages.length, 1);
    e.searchOrdertext.value = ' Client@Example.org ';
    c.search_crm_order('/number', 'csrf');
    assert.equal(env.requests.length, 1);
    assert.equal(env.requests[0].options.body.get('account'), 'Client@Example.org');
    assert.equal(env.requests[0].options.headers['X-CSRFToken'], 'csrf');
    await respond(env.requests[0], {status: 'success', htmlresponse: '<section>results</section>'});
    assert.equal(e.accountOrdersResults.innerHTML, '<section>results</section>');

    const hiddenBefore = env.hidden();
    const second = api.search('csrf');
    assert.equal(env.hidden(), hiddenBefore, 'repeated search must not hide and re-open an existing modal');
    e.searchOrderAccountMode.checked = false;
    api.toggle();
    assert.equal(env.requests[1].options.signal.aborted, true);
    await respond(env.requests[1], {status: 'success', htmlresponse: 'stale'});
    await second;
    assert.equal(e.accountOrdersResults.innerHTML, '');
    assert.equal(e.searchOrderModeLabel.textContent, 'Поиск по номеру заказа');
    assert.equal(e.searchOrdertext.type, 'text');

    e.searchOrderAccountMode.checked = true;
    api.toggle();
    e.searchOrdertext.value = 'client@example.org';
    const denied = api.search('csrf');
    await respond(env.requests[2], {status: 'danger', message: 'Недостаточно прав'}, false);
    await denied;
    assert.equal(e.accountOrdersResults.textContent, 'Недостаточно прав');
    console.log('OK: mode switching, original number search, email requests, stale responses and access errors');
})().catch(error => { console.error(error); process.exitCode = 1; });
