const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '../app/static/main_v2/js/categories/clothes.js'), 'utf8');
const elements = {};
function field(id, value = '') {
    const classes = new Set(['is-valid']);
    return elements[id] = {
        id, value,
        classList: {
            add: (...names) => names.forEach(name => classes.add(name)),
            remove: (...names) => names.forEach(name => classes.delete(name)),
            contains: name => classes.has(name),
            toggle: (name, enabled) => enabled ? classes.add(name) : classes.delete(name),
        },
    };
}
const tnved = field('tnved_code');
field('article_price', '100');
field('tax', '22');
const context = {
    window: {validateTrademarkProductType: () => true, OrderQuantity: {validateForm: () => true}},
    document: {getElementById: id => elements[id]},
    show_form_errors: () => {}, close_Loading_circle: () => {},
    check_rd_docs: () => true, clothes_check_sizes_quantity_valid: () => false,
    check_valid: input => assert.notEqual(input.id, 'tnved_code', 'native validation must not override TN VED'),
};
context.$ = selector => {
    if (selector === '#form_process_main input, #form_process_main select ') {
        const inputs = [tnved];
        inputs.each = callback => inputs.forEach((input, index) => callback(index));
        return inputs;
    }
    const targets = selector.split(',').map(s => elements[s.trim().slice(1)]).filter(Boolean);
    return {
        val(value) { targets.forEach(input => { input.value = value; }); return this; },
        prop() { return this; }, trigger() { return this; }, empty() { return this; }, modal() {},
        removeClass(names) { targets.forEach(input => input.classList.remove(...names.split(' '))); return this; },
    };
};
vm.createContext(context);
for (const [start, end] of [
    ['function clothes_perform_pos_add(', 'function show_clothes_pos('],
    ['function clothes_clear_pos()', 'function clothes_content_add()'],
    ['function check_tnved(', 'function get_tnveds('],
    ['function clear_tnved_input()', 'function renderAllowedTable()'],
]) {
    vm.runInContext(source.slice(source.indexOf(start), source.indexOf(end, source.indexOf(start))), context);
}

for (const value of ['', '123', 'abcdefghij', '6201900000']) {
    tnved.value = value;
    const valid = value === '6201900000';
    assert.equal(context.check_tnved('submit'), valid);
    assert.equal(tnved.classList.contains('is-valid'), valid);
    assert.equal(tnved.classList.contains('is-invalid'), !valid);
}
context.window.ClothesTnvedContent = {check: () => false};
assert.equal(context.check_tnved('submit'), false);
assert.equal(tnved.classList.contains('is-valid'), false);
delete context.window.ClothesTnvedContent;

field('form_process_main').checkValidity = () => false;
field('content', 'ХЛОПОК');
tnved.value = '';
context.clothes_perform_pos_add(1, '/unused');
assert.equal(tnved.classList.contains('is-invalid'), true);

tnved.value = '6201900000';
context.check_tnved('submit');
elements.tax.classList.add('is-invalid');
context.clothes_clear_pos();
assert.equal(elements.article_price.value, '0');
assert.equal(elements.tax.value, '0');
assert.equal(tnved.value, '');
for (const input of [tnved, elements.article_price, elements.tax]) {
    assert.equal(input.classList.contains('is-valid'), false, input.id);
    assert.equal(input.classList.contains('is-invalid'), false, input.id);
}
assert.equal(context.window.__silenceReset, false);
console.log('OK: TN VED validation and neutral price/VAT reset after adding a position');
