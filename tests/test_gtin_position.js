const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const listeners = {};
const field = () => ({value: '', required: false, addEventListener(event, callback) { this[event] = callback; }});
const gtin = field();
const company = field();
const collapsePanel = {shown: false};
const block = {querySelector: id => id === '#gtin' ? gtin : id === '#gtin_company_key' ? company : collapsePanel};
let attached = false;
let ajaxSuccess;
const elements = {
    'step-2': {querySelector: () => ({before(element) { attached = element === block; }})},
    'gtin-position-template': {content: {firstElementChild: {cloneNode: () => block}}},
    'form_process_main': {addEventListener() {}},
};
const context = {
    document: {getElementById: id => elements[id], addEventListener: (event, callback) => { listeners[event] = callback; }},
    window: {jQuery: true, location: {href: 'https://example.test/shoes/1/'}},
    jQuery: () => ({ajaxSuccess: callback => { ajaxSuccess = callback; }}),
    bootstrap: {Collapse: {getOrCreateInstance(panel, options) {
        assert.equal(panel, collapsePanel);
        assert.equal(options.toggle, false);
        return {show() { panel.shown = true; }, hide() { panel.shown = false; }};
    }}},
    URL,
};
vm.runInNewContext(fs.readFileSync('app/static/main_v2/js/gtin_position.js', 'utf8'), context);
listeners.DOMContentLoaded();
assert.ok(attached);
assert.equal(gtin.required, false);
assert.equal(company.required, false);
gtin.value = '04640735105562';
gtin.input();
assert.equal(company.required, true);
assert.equal(collapsePanel.shown, true);
company.value = 'g:GRENADA';
company.change();
assert.equal(gtin.required, true);
gtin.value = '';
gtin.input();
assert.equal(gtin.required, true);
assert.equal(company.required, false);
ajaxSuccess(null, null, {url: '/shoes/preprocess_order/1'}, {status: 'error'});
assert.equal(company.value, 'g:GRENADA');
ajaxSuccess(null, null, {url: '/shoes/preprocess_order/1'}, {status: 'success'});
assert.equal(company.value, '');
assert.equal(gtin.required, false);
assert.equal(collapsePanel.shown, false);
console.log('GTIN form pairing and AJAX reset OK');
