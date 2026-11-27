const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../app/static/main_v2/js/categories/socks.js'), 'utf8');
let quantities = [{value: '37.42'}];
const context = {document: {querySelectorAll: selector => selector === '[id=size_info]' ? [{}] : quantities}};
vm.createContext(context);
for (const [start, end] of [
    ['function socks_check_sizes_quantity_valid()', 'function socksSizeInputId('],
    ['function check_socks_quantity_input(', 'function create_size_blocks('],
]) {
    vm.runInContext(source.slice(source.indexOf(start), source.indexOf(end)), context);
}
for (const value of ['37.42', '37,42', '', '0', '-1', '50001', '1e2', 'NaN', ' 37 ']) {
    let message = '', reported = false;
    const input = {value, setCustomValidity: text => {message = text;}, reportValidity: () => {reported = true;}};
    assert.equal(context.check_socks_quantity_input(input), false, value);
    assert.ok(message.includes('целое количество'));
    assert.equal(reported, true);
    assert.equal(input.value, value, 'Do not silently round or replace quantities');
    quantities = [input];
    assert.equal(context.socks_check_sizes_quantity_valid(), false, 'Hidden quantity cannot bypass validation');
}
for (const value of ['1', '37', '50000']) {
    let message = 'old error';
    const input = {value, setCustomValidity: text => {message = text;}, reportValidity: () => assert.fail()};
    assert.equal(context.check_socks_quantity_input(input), true);
    assert.equal(message, '');
    quantities = [input];
    assert.equal(context.socks_check_sizes_quantity_valid(), true);
}
quantities = [];
assert.equal(context.socks_check_sizes_quantity_valid(), false);
console.log('Socks quantity validation: OK');
