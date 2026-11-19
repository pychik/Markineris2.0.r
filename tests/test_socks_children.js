const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

for (const file of ['main_v2/js/categories/socks.js', 'product_cards/users/socks.js']) {
    const source = fs.readFileSync(path.join(__dirname, '../app/static', file), 'utf8');
    const elements = {};
    const callbacks = {};
    const messages = [];
    function element(id, value = '') {
        return elements[id] = {
            value, checked: false, disabled: false, textContent: '', innerHTML: '',
            querySelector: () => null,
            classList: {toggle() {}},
        };
    }
    const toggle = element('is_children');
    const gender = element('gender', 'Унисекс');
    const sizes = element('sizes_quantity');
    const modal = element('sizesSocksDiv');
    const savedPositions = element('order_table_body_info');
    savedPositions.innerHTML = 'existing adult and child order rows';
    const context = {
        document: {
            getElementById: id => elements[id],
            addEventListener: (event, callback) => { callbacks[event] = callback; },
            querySelectorAll: () => [],
        },
        make_message: text => messages.push(text),
        setSocks() {}, enableAllTooltips() {},
        socks_types_sizes_dict: {
            'Унисекс': {'РОССИЯ': [['25', '']], 'МЕЖДУНАРОДНЫЙ': [['S', '']]},
            'Детск.': {'МЕЖДУНАРОДНЫЙ': [['6', ''], ['12', '']], 'РОССИЯ': [['12', '']],
                       month: [['0-3', '']], years: [['1,5', '']]},
        },
    };
    context.$ = selector => ({
        val(value) { if (elements[selector.slice(1)]) elements[selector.slice(1)].value = value; return this; },
        trigger() { return this; }, modal() {}, on(event, callback) { callbacks[event] = callback; return this; },
    });
    vm.createContext(context);
    const preamble = source.slice(0, source.indexOf('function socks_check_sizes_quantity_valid'));
    vm.runInContext(preamble, context);
    function loadFunction(name) {
        const start = source.indexOf(`function ${name}(`);
        assert.ok(start >= 0, name);
        const end = source.indexOf('\nfunction ', start + 1);
        vm.runInContext(source.slice(start, end < 0 ? source.length : end), context);
    }
    for (const name of ['socksSizeInputId', 'normalizeSocksSizeType', 'chooseSizeSocks', 'create_size_blocks']) {
        loadFunction(name);
    }
    if (file.includes('product_cards')) loadFunction('socksSizeCheckId');
    callbacks.DOMContentLoaded();
    sizes.innerHTML = 'selected adult sizes';
    sizes.querySelector = () => ({});
    toggle.checked = true;
    context.socksChildrenChanged();
    assert.equal(sizes.innerHTML, '');
    assert.equal(savedPositions.innerHTML, 'existing adult and child order rows');
    assert.equal(messages.length, 1);

    context.chooseSizeSocks();
    assert.match(modal.innerHTML, /ВОЗРАСТ — МЕСЯЦЫ/);
    assert.match(modal.innerHTML, /ВОЗРАСТ — ГОДЫ/);
    assert.match(modal.innerHTML, /data-size-value="0-3" data-size-type="month"|data-size-value="0-3"\s+data-size-type="month"/);
    assert.match(modal.innerHTML, /1,5/);
    assert.doesNotMatch(modal.innerHTML, /data-size-value="S"/);
    assert.notEqual(context.socksSizeInputId('12', 'РОССИЯ'), context.socksSizeInputId('12', 'МЕЖДУНАРОДНЫЙ'));
    assert.match(modal.innerHTML, /setQuantitySize\('12', 'РОССИЯ'\)/);
    assert.match(modal.innerHTML, /setQuantitySize\('12', 'МЕЖДУНАРОДНЫЙ'\)/);

    toggle.checked = false;
    context.socksChildrenChanged();
    context.chooseSizeSocks();
    assert.match(modal.innerHTML, /data-size-value="S"/);
    assert.doesNotMatch(modal.innerHTML, /data-size-type="month"/);
    gender.value = 'Детск.';
    callbacks['change.socksChildren'].call(gender);
    assert.equal(toggle.checked, true);

    toggle.disabled = true;
    sizes.innerHTML = 'frozen child sizes';
    context.socksChildrenChanged();
    assert.equal(sizes.innerHTML, 'frozen child sizes');
    console.log(`${file}: child/adult grids, labels, draft reset, saved positions and distinct size IDs OK`);
}
