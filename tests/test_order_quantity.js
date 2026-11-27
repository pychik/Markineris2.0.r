const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.join(__dirname, '../app/static/main_v2/js');
function loadFunction(context, category, name) {
    const source = fs.readFileSync(path.join(root, 'categories', category + '.js'), 'utf8');
    const start = source.search(new RegExp('^function ' + name + '\\(', 'm'));
    assert.ok(start >= 0, name);
    const next = source.slice(start + 1).search(/^function /m);
    vm.runInContext(source.slice(start, next < 0 ? undefined : start + 1 + next), context);
}
function setup(extra = {}) {
    const context = {window: {}, make_message() {}, ...extra};
    vm.createContext(context);
    vm.runInContext(fs.readFileSync(path.join(root, 'order_quantity.js'), 'utf8'), context);
    return context;
}
const invalid = ['37.42', '37,42', '', '0', '-1', '+1', '1e2', 'NaN', ' 37 ', '100000001'];
const basic = setup();
for (const value of invalid) assert.equal(basic.window.OrderQuantity.isValid(value), false, value);
for (const value of ['1', '0002', '100000000']) assert.equal(basic.window.OrderQuantity.isValid(value), true, value);
assert.equal(basic.window.OrderQuantity.isValid('6', 5), false);
for (const name of ['quantity', 'box_quantity', 'kpb_quantity', 'linen_set_item_quantity']) {
    for (const value of invalid) {
        assert.equal(basic.window.OrderQuantity.validateForm({querySelectorAll: () => [{name, value}]}), false, name + value);
    }
}
// An invalid hidden count must stop every submission handler before other checks or requests.
for (const [category, fn] of [['clothes', 'clothes_perform_pos_add'], ['socks', 'socks_perform_pos_add'], ['shoes', 'shoe_perform_pos_add'], ['linen', 'linen_perform_pos_add'], ['parfum', 'parfum_perform_pos_add'], ['cosmetics', 'cosmetics_perform_pos_add'], ['toys', 'toys_perform_pos_add']]) {
    const context = setup({document: {getElementById: () => ({querySelectorAll: () => [{name: 'quantity', value: '37.42', type: 'hidden'}]})}});
    loadFunction(context, category, fn);
    context[fn](0, '/must-not-submit');
    context[fn](1, '/must-not-request');
}
// Inline edits must preserve the old count on invalid input, then accept correction.
for (const [category, fn, total] of [['shoes', 'shoes_edit_size', 'setShoes'], ['linen', 'linen_edit_size', 'setLinen'], ['socks', 'socks_edit_size', 'setSocks']]) {
    const handlers = {}, fields = {};
    let recalculated = 0;
    const field = key => fields[key] ||= {
        value: key === '#quantity_input' ? '37.42' : '5', message: '',
        val(value) {if (value === undefined) return this.value; this.value = value; return this;},
        text(value) {this.value = value; return this;},
        on(event, fn) {handlers[event] = fn; return this;}, is() {return true;},
        hide() {return this;}, show() {return this;}, focus() {return this;},
        setCustomValidity(value) {this.message = value;}, reportValidity() {},
        get 0() {return this;},
    };
    const context = setup({$: selector => typeof selector === 'string' ? field(selector) : {closest: () => ({find: field})}, [total]: () => {recalculated++;}});
    if (category === 'socks') loadFunction(context, category, 'isValidSocksQuantity');
    loadFunction(context, category, fn);
    context[fn]({});
    const hidden = field(category === 'linen' ? 'input[name="quantity"]' : '#quantity');
    for (const value of invalid.concat('50001')) {
        field('#quantity_input').value = value;
        handlers.input.call(field('#quantity_input'));
        handlers['blur keypress']({type: 'blur'});
        assert.equal(hidden.value, '5', category + ' preserves prior count');
        assert.equal(recalculated, 0);
    }
    field('#quantity_input').value = '3';
    handlers.input.call(field('#quantity_input'));
    handlers['blur keypress']({type: 'blur'});
    assert.equal(hidden.value, '3');
    assert.equal(recalculated, 1);
}
// Clothing modal must carry raw invalid counts to the guard, never truncate them.
{
    const card = {innerHTML: '', querySelectorAll: () => []};
    const input = {value: '37.42', getAttribute: key => key === 'id' ? 'size_L' : 'МЕЖДУНАРОДНЫЙ'};
    const context = setup({special_clothes_sizes: [], document: {getElementById: () => card, querySelectorAll: () => [input]}, setClothes() {}});
    loadFunction(context, 'clothes', 'updateSizesQuantityBlock');
    context.updateSizesQuantityBlock();
    assert.match(card.innerHTML, /name="quantity" value="37\.42"/);
}
// Free clothing size and length/width entry must reject decimal counts before adding a row.
for (const fn of ['subcategory_size_add', 'addLengthWidthClothesSize']) {
    const fields = {};
    const context = setup({clothes_types_sizes_dict: {}, document: {getElementById: id => fields[id] ||= {value: id.includes('Quantity') ? '37.42' : '50', textContent: '', addEventListener() {}}}});
    if (fn === 'addLengthWidthClothesSize') loadFunction(context, 'clothes', 'clothesAccordionId');
    loadFunction(context, 'clothes', fn);
    context[fn]('TEST');
    assert.match(fields[fn === 'subcategory_size_add' ? 'subcategorySizeErrorTEST' : 'lengthWidthErrorTEST'].textContent, /количество/);
}
// A decimal set-item count must never become an integer before validation.
{
    let error = '';
    const values = {linen_set_item_type: 'НАВОЛОЧКА', linen_set_sizeX_order: '50', linen_set_sizeY_order: '70', linen_set_sizeUnit_order: 'см', linen_set_quantity_order: '2.5'};
    const context = setup({linenIsKpbMode: () => true, LINEN_SET_ITEM_TYPES: ['НАВОЛОЧКА'], linenShowFormErrors: errors => {error = errors[0];}, document: {getElementById: id => ({value: values[id]})}});
    loadFunction(context, 'linen', 'addLinenSetItem');
    assert.equal(context.addLinenSetItem(), false);
    assert.match(error, /Количество/);
}
console.log('Order quantities: all category handlers, hidden counts, inline edits, clothing and bedding sets OK');
