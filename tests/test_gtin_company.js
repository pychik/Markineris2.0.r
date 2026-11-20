const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

function setup() {
    const requests = [];
    let inserted = false;
    let reloads = 0;
    let hides = 0;
    let spinner = false;
    let spinnerStarts = 0;
    let spinnerStops = 0;
    let message;
    const values = {csrf_token: 'csrf-test', expected_company: 'g:GRENADA', company: 'g:AVRORA'};
    const listeners = {};
    const error = {textContent: '', classList: {add() {}, remove() {}}};
    const controls = [{disabled: false}, {disabled: false}, {disabled: false}];
    const title = {textContent: 'Гренада', dataset: {copyValue: 'Гренада'}};
    const inn = {textContent: '1111111111', dataset: {copyValue: '1111111111'}};
    const innRow = {hidden: false};
    const updClasses = new Set(['active']);
    const updIcon = {attributes: {}, classList: {toggle(name, state) {if (state) updClasses.add(name); else updClasses.delete(name);}},
        setAttribute(name, value) {this.attributes[name] = value;}};
    const card = {dataset: {orderId: '42'}, querySelector(selector) {return {
        '[data-gtin-company-title]': title, '[data-gtin-company-inn]': inn,
        '[data-gtin-company-inn-row]': innRow, '[data-role="upd-icon"]': updIcon,
    }[selector];}};

    function extraCard(orderId) {
        const title = {textContent: 'Гренада', dataset: {copyValue: 'Гренада'}};
        const inn = {textContent: '1111111111', dataset: {copyValue: '1111111111'}};
        const innRow = {hidden: false};
        const classes = new Set(['active']);
        const upd = {attributes: {}, classList: {toggle(name, state) {if (state) classes.add(name); else classes.delete(name);}},
            setAttribute(name, value) {this.attributes[name] = value;}};
        const card = {dataset: {orderId}, querySelector(selector) {return {
            '[data-gtin-company-title]': title, '[data-gtin-company-inn]': inn,
            '[data-gtin-company-inn-row]': innRow, '[data-role="upd-icon"]': upd,
        }[selector];}};
        return {card, title, inn, innRow, upd, classes};
    }
    const search = extraCard('42');
    const other = extraCard('99');

    const form = {action: '/managers/orders/42/gtin-company', valid: true, reportValidity() {return this.valid;},
        addEventListener(type, callback) {listeners[type] = callback;}};
    const element = {dataset: {}, addEventListener(type, callback) {listeners[type] = callback;}, remove() {inserted = false;},
        querySelector(selector) {return selector === 'form' ? form : error;}, querySelectorAll() {return controls;}};
    const button = {closest: () => card, disabled: false, dataset: {gtinCompanyUrl: '/managers/orders/42/gtin-company', operatorCrmPath: '/managers'}};
    const context = {
        window: {location: {pathname: '/managers', reload() {reloads++;}}},
        document: {querySelectorAll(selector) {assert.equal(selector, '.order[data-order-id]'); return [card, search.card, other.card];}, getElementById() {return inserted ? element : null;}, body: {insertAdjacentHTML() {inserted = true;}}},
        bootstrap: {Tooltip: {getInstance: () => null}, Modal: {getOrCreateInstance: () => ({show() {}, hide() {hides++;}, dispose() {}})}},
        make_message(text) {message = text;},
        loadingCircle() {spinner = true; spinnerStarts++;},
        close_Loading_circle() {spinner = false; spinnerStops++;},
        FormData: class {constructor(received) {assert.equal(received, form);} get(name) {return values[name];}},
        fetch(url, options) {return new Promise((resolve, reject) => requests.push({url, options, resolve, reject}));},
    };
    vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../app/static/crm_mod/js/gtin_company.js'), 'utf8'), context);
    const event = {preventDefault() {}, stopPropagation() {}};
    return {requests, button, controls, form, error, element, listeners, values, title, inn, innRow, updIcon, updClasses, search, other, hides: () => hides, spinner: () => spinner, spinnerStarts: () => spinnerStarts, spinnerStops: () => spinnerStops, location: context.window.location,
        open: (fromSearch = false) => context.window.gtinCompanyOpen(event, fromSearch ? {...button, closest: () => search.card} : button), submit: () => listeners.submit(event),
        reloads: () => reloads, message: () => message};
}
function respond(request, data, ok = true) {request.resolve({ok, json: async () => data});}
async function opened(fromSearch = false) {
    const env = setup();
    const pending = env.open(fromSearch);
    respond(env.requests[0], {status: 'success', html: '<modal>'});
    await pending;
    return env;
}
(async function () {
    {
        const env = setup();
        env.location.pathname = '/agents';
        await env.open();
        assert.equal(env.requests.length, 0, 'admin board cannot open company assignment');
    }
    {
        const env = setup();
        const first = env.open();
        await env.open();
        assert.equal(env.requests.length, 1, 'double opening makes one request');
        assert.equal(env.spinner(), true);
        assert.equal(env.spinnerStarts(), 1);
        assert.equal(env.requests[0].options.cache, 'no-store');
        respond(env.requests[0], {status: 'error', message: 'Нет доступа'}, false);
        await first;
        assert.equal(env.message(), 'Нет доступа');
        assert.equal(env.button.disabled, false);
        assert.equal(env.spinner(), false);
        assert.equal(env.spinnerStops(), 1);
    }
    {
        const env = await opened();
        const save = env.submit();
        await env.submit();
        assert.equal(env.requests.length, 2, 'double submission makes one POST');
        assert.ok(env.controls.every(control => !control.disabled), 'modal controls are not disabled');
        assert.equal(env.spinner(), true);
        assert.equal(env.spinnerStarts(), 2);
        const post = env.requests[1];
        assert.equal(post.options.method, 'POST');
        assert.equal(post.options.headers['X-CSRFToken'], 'csrf-test');
        assert.deepEqual(JSON.parse(post.options.body), {company: 'g:AVRORA', expected_company: 'g:GRENADA'});
        assert.equal(env.title.textContent, 'Гренада', 'card stays unchanged until server confirms');
        respond(post, {status: 'success', order_id: 42, company_title: 'Аврора', company_inn: '2222222222', upd_number: '', processing_info: ''});
        await save;
        assert.equal(env.reloads(), 0, 'success never reloads the page');
        assert.equal(env.requests.length, 2, 'no column or card HTML is fetched');
        assert.equal(env.title.textContent, 'Аврора');
        assert.equal(env.title.dataset.copyValue, 'Аврора');
        assert.equal(env.inn.textContent, '2222222222');
        assert.equal(env.inn.dataset.copyValue, '2222222222');
        assert.equal(env.updIcon.attributes['data-bs-title'], 'УПД не указан');
        assert.ok(env.updClasses.has('mred'));
        assert.ok(!env.updClasses.has('active'));
        assert.equal(env.search.title.textContent, 'Аврора', 'search copy updates with the board card');
        assert.equal(env.search.title.dataset.copyValue, 'Аврора');
        assert.equal(env.search.inn.textContent, '2222222222');
        assert.equal(env.search.inn.dataset.copyValue, '2222222222');
        assert.ok(env.search.classes.has('mred'));
        assert.equal(env.search.upd.attributes['data-bs-title'], 'УПД не указан');
        assert.equal(env.other.title.textContent, 'Гренада', 'other orders stay unchanged');
        assert.equal(env.hides(), 1);
        assert.equal(env.spinner(), false);
        assert.equal(env.spinnerStops(), 2);
    }
    {
        const env = await opened(true);
        const save = env.submit();
        respond(env.requests[1], {status: 'success', order_id: 42, company_title: 'Другая компания', company_inn: '3333333333', upd_number: '', processing_info: ''});
        await save;
        assert.equal(env.title.textContent, 'Другая компания', 'saving from search also updates the board');
        assert.equal(env.search.title.textContent, 'Другая компания');
        assert.equal(env.other.title.textContent, 'Гренада');
        assert.equal(env.reloads(), 0);
        assert.equal(env.requests.length, 2);
    }
    {
        const env = await opened();
        const save = env.submit();
        respond(env.requests[1], {status: 'error', message: 'Компания уже изменилась'}, false);
        await save;
        assert.equal(env.reloads(), 0);
        assert.equal(env.error.textContent, 'Компания уже изменилась');
        assert.equal(env.title.textContent, 'Гренада', 'error leaves the card unchanged');
        assert.equal(env.search.title.textContent, 'Гренада', 'error leaves the search copy unchanged');
        assert.equal(env.hides(), 0);
        assert.equal(env.spinner(), false);
        assert.equal(env.spinnerStops(), 2);
        assert.equal(env.values.company, 'g:AVRORA');
        assert.ok(env.controls.every(control => !control.disabled));
    }
    {
        const env = await opened();
        const save = env.submit();
        assert.equal(env.spinner(), true);
        env.requests[1].reject(new Error('Сеть недоступна'));
        await save;
        assert.equal(env.spinner(), false, 'network error closes the spinner');
        assert.equal(env.hides(), 0, 'network error keeps the modal open');
        assert.equal(env.values.company, 'g:AVRORA');
        assert.equal(env.title.textContent, 'Гренада');
    }
    {
        const env = await opened();
        env.form.valid = false;
        await env.submit();
        assert.equal(env.requests.length, 1, 'invalid selection is not submitted');
    }
    console.log('GTIN company modal: spinner lifecycle, card update, CSRF and errors OK');
})().catch(error => {console.error(error); process.exitCode = 1;});
