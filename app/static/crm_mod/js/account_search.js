(function () {
    const toggle = document.getElementById('searchOrderAccountMode');
    if (!toggle) return;
    const input = document.getElementById('searchOrdertext');
    const label = document.getElementById('searchOrderModeLabel');
    const help = document.getElementById('searchOrderHelp');
    const modalElement = document.getElementById('accountOrdersModal');
    const body = document.getElementById('accountOrdersResults');
    const title = document.getElementById('accountOrdersModalLabel');
    const fieldName = 'email';
    let controller = null;
    let revision = 0;

    function cancel() {
        revision += 1;
        controller?.abort();
        controller = null;
        body.removeAttribute('aria-busy');
    }

    function clear(hide = true) {
        cancel();
        if (hide) bootstrap.Modal.getInstance(modalElement)?.hide();
        body.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(element => {
            bootstrap.Tooltip.getInstance(element)?.dispose();
        });
        body.replaceChildren();
    }

    function changeMode() {
        clear_search_order_res();
        input.value = '';
        input.type = toggle.checked ? 'email' : 'text';
        input.placeholder = toggle.checked ? `Введите ${fieldName} пользователя` : 'Введите номер заказа';
        input.setAttribute('aria-label', input.placeholder);
        label.textContent = toggle.checked ? `Поиск по ${fieldName} пользователя` : 'Поиск по номеру заказа';
        const hint = `Введите ${toggle.checked ? fieldName + ' пользователя' : 'номер заказа'} и нажмите кнопку поиск. Для очистки результата нажмите Очистить`;
        help.setAttribute('data-bs-title', hint);
        bootstrap.Tooltip.getInstance(help)?.setContent({'.tooltip-inner': hint});
        input.focus();
    }

    async function search(csrf) {
        const account = input.value.trim();
        if (!account || account.length > 254 || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(account)) {
            make_message(`Введите полный ${fieldName} пользователя.`, 'warning');
            return;
        }
        clear(false);
        const currentRevision = revision;
        controller = new AbortController();
        title.textContent = `Заказы по ${fieldName} пользователя`;
        body.textContent = 'Загрузка заказов…';
        body.setAttribute('aria-busy', 'true');
        bootstrap.Modal.getOrCreateInstance(modalElement).show();
        try {
            const response = await fetch(toggle.dataset.searchUrl, {
                method: 'POST',
                headers: {'X-CSRFToken': csrf, 'X-Requested-With': 'XMLHttpRequest'},
                body: new URLSearchParams({account}),
                signal: controller.signal,
            });
            if (currentRevision !== revision) return;
            const data = await response.json();
            if (currentRevision !== revision) return;
            if (!response.ok || data.status !== 'success') {
                body.textContent = data.message || 'Не удалось выполнить поиск.';
                return;
            }
            body.innerHTML = data.htmlresponse;
            // Общий обработчик обслуживает и карточки в модальном окне,
            // даже если основная доска ещё не загрузилась.
            if (!document._crmClickHandler) initializeJSPage(document);
            else init_tooltip(body);
        } catch (error) {
            if (currentRevision === revision && error.name !== 'AbortError') {
                body.textContent = 'Не удалось загрузить заказы. Повторите поиск.';
            }
        } finally {
            if (currentRevision === revision) {
                controller = null;
                body.removeAttribute('aria-busy');
            }
        }
    }

    modalElement.addEventListener('hidden.bs.modal', cancel);
    window.CrmAccountSearch = {toggle: changeMode, clear, search, isAccountMode: () => toggle.checked};
})();
