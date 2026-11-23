function togglePartialWithdrawal(button) {
    const form = document.getElementById('partial_withdrawal_form');
    form.hidden = !form.hidden;
    button.setAttribute('aria-expanded', String(!form.hidden));
    if (!form.hidden) form.elements.amount.focus();
}

async function submitPartialWithdrawal(event, form) {
    event.preventDefault();
    if (form.dataset.busy === '1') return;
    const input = form.elements.amount;
    input.setCustomValidity('');
    const value = input.value.trim();
    if (!/^[0-9]+$/.test(value) || !Number.isSafeInteger(Number(value)) || Number(value) <= 0 || Number(value) >= Number(form.dataset.amount)) {
        input.setCustomValidity('Введите целую сумму больше нуля и меньше суммы заявки.');
    }
    if (!form.reportValidity()) return;
    const refreshUrl = document.getElementById('transactions_table_info')?.dataset.refreshUrl;
    if (!refreshUrl) {
        make_message('Не удалось определить открытый список транзакций. Обновите страницу.', 'warning');
        return;
    }
    form.dataset.busy = '1';
    const modal = form.closest('.modal');
    const controls = Array.from(modal.querySelectorAll('button, input')).map(node => [node, node.disabled]);
    controls.forEach(([node]) => { node.disabled = true; });
    loadingCircle();
    let approved = false;
    try {
        const data = await $.ajax({
            url: form.dataset.url,
            method: 'POST',
            timeout: 60000,
            headers: {'X-CSRFToken': form.dataset.csrf},
            data: {amount: value}
        });
        if (data.status !== 'success') {
            make_message(data.message || 'Не удалось одобрить вывод.', 'warning');
            return;
        }
        approved = true;
        $('#su_transactionDetailModal').modal('hide');
        try {
            const refreshed = await $.ajax({url: refreshUrl, method: 'GET', dataType: 'json', timeout: 60000});
            if (typeof refreshed.htmlresponse !== 'string') throw new Error('Некорректный ответ обновления');
            document.getElementById('transactions_table').innerHTML = refreshed.htmlresponse;
            make_message(data.message, 'success');
        } catch (_) {
            make_message(`${data.message} Не удалось обновить список транзакций. Нажмите «Обновить».`, 'warning');
        }
    } catch (xhr) {
        make_message(xhr.responseJSON?.message || 'Не удалось получить результат операции. Обновите список транзакций перед повторной попыткой.', 'warning');
    } finally {
        close_Loading_circle();
        controls.forEach(([node, disabled]) => { node.disabled = disabled; });
        form.dataset.busy = '0';
        // Do not allow resubmitting a completed approval from stale modal contents.
        if (approved) form.querySelector('button[type="submit"]').disabled = true;
    }
}

document.addEventListener('input', event => {
    if (event.target.id === 'partial_withdrawal_amount') event.target.setCustomValidity('');
});
