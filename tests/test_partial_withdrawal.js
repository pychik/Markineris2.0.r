const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

function setup(value = '20000', responses = [], sortType = '1') {
    const calls = [], messages = [], controls = [{disabled: false}, {disabled: true}];
    const input = {value, validity: '', setCustomValidity(text) { this.validity = text; }};
    const form = {
        dataset: {amount: '50000', url: '/partial_withdrawal/1/5?bck=1', csrf: 'test-token'},
        elements: {amount: input},
        reportValidity() { return !input.validity; },
        closest() { return {querySelectorAll: () => controls}; },
        querySelector() { return controls[0]; }
    };
    const list = {dataset: {refreshUrl: `/su_bck_control_ut?tr_status=1&operation_type=0&agent_id=42&page=3&sort_type=${sortType}`}};
    const table = {innerHTML: ''};
    let loading = 0, closed = 0;
    const context = {
        document: {getElementById: id => id === 'transactions_table_info' ? list : table, addEventListener() {}},
        make_message: (message, status) => messages.push({message, status}),
        loadingCircle: () => { loading++; }, close_Loading_circle: () => { closed++; },
        $: () => ({modal(action) { assert.equal(action, 'hide'); }})
    };
    context.$.ajax = options => {
        calls.push(options);
        const next = responses.shift();
        return next instanceof Error ? Promise.reject(next) : Promise.resolve(next);
    };
    vm.createContext(context);
    vm.runInContext(fs.readFileSync('app/static/main_v2/js/admin/partial_withdrawal.js', 'utf8'), context);
    return {form, input, calls, messages, controls, table, context,
        submit: () => context.submitPartialWithdrawal({preventDefault() {}}, form),
        loading: () => loading, closed: () => closed};
}

(async () => {
    for (const value of ['0', '-1', '50000', '50001', '1.5', '1e3', '']) {
        const state = setup(value);
        await state.submit();
        assert.equal(state.calls.length, 0);
        assert(state.input.validity);
    }
    const state = setup('20000', [{status: 'success', message: 'Одобрено 20000, остаток 30000'}, {htmlresponse: '<table>Updated</table>'}]);
    const pending = state.submit();
    assert.equal(state.form.dataset.busy, '1');
    assert(state.controls.every(node => node.disabled));
    await state.submit(); // A second click while the request is in progress must not submit again.
    await pending;
    assert.equal(state.calls.length, 2);
    assert.equal(state.calls[0].method, 'POST');
    assert.equal(state.calls[0].data.amount, '20000');
    assert.equal(state.calls[0].headers['X-CSRFToken'], 'test-token');
    assert.equal(state.calls[1].url, '/su_bck_control_ut?tr_status=1&operation_type=0&agent_id=42&page=3&sort_type=1');
    assert.equal(state.table.innerHTML, '<table>Updated</table>');
    assert.equal(state.messages[0].status, 'success');
    assert.equal(state.loading(), 1);
    assert.equal(state.closed(), 1);
    assert(state.controls[0].disabled);

    for (const sortType of ['0', '1']) {
        const sorted = setup('20000', [{status: 'success', message: 'Одобрено'}, {htmlresponse: '<table>Updated</table>'}], sortType);
        await sorted.submit();
        const query = new URLSearchParams(sorted.calls[1].url.split('?')[1]);
        assert.equal(query.get('sort_type'), sortType);
        assert.equal(query.get('page'), '3');
        assert.equal(query.get('agent_id'), '42');
    }

    const error = new Error('Bad request');
    error.responseJSON = {message: 'Заявка уже подтверждена'};
    const failed = setup('20000', [error]);
    await failed.submit();
    assert.equal(failed.calls.length, 1);
    assert.equal(failed.messages[0].message, 'Заявка уже подтверждена');
    assert.equal(failed.closed(), 1);
    assert(!failed.controls[0].disabled);
    assert(failed.controls[1].disabled);

    const refreshFailed = setup('20000', [{status: 'success', message: 'Операция выполнена'}, new Error('List unavailable')]);
    await refreshFailed.submit();
    assert(refreshFailed.messages[0].message.includes('Операция выполнена'));
    assert(refreshFailed.messages[0].message.includes('Не удалось обновить список'));
    assert(refreshFailed.controls[0].disabled);
    console.log('Partial withdrawal UI OK: validation, AJAX, loader, duplicate click, filtered-page refresh, errors');
})().catch(error => { console.error(error); process.exitCode = 1; });
