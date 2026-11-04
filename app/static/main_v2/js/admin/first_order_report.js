(() => {
    const root = document.getElementById('firstOrderReport');
    if (!root) return;
    const form = document.getElementById('firstOrderReportFilters');
    const table = document.getElementById('firstOrderReportTable');
    const error = document.getElementById('firstOrderReportError');
    const loading = document.getElementById('firstOrderReportLoading');
    const excel = document.getElementById('firstOrderReportExcel');
    const months = [...root.querySelectorAll('[data-first-order-month]')];
    let controller;

    function updateMonthSelection() {
        months.forEach(button => {
            const selected = !button.disabled
                && form.elements.date_from.value === button.dataset.dateFrom
                && form.elements.date_to.value === button.dataset.dateTo;
            button.setAttribute('aria-pressed', String(selected));
        });
    }

    function parseDateTime(value) {
        const match = /^(\d{2})\.(\d{2})\.(\d{4}) (\d{2}):(\d{2})$/.exec(value);
        if (!match) return null;
        const [, day, month, year, hour, minute] = match.map(Number);
        if (hour > 23 || minute > 59 || month < 1 || month > 12 || day < 1 || year < 1) return null;
        const result = new Date(0);
        result.setFullYear(year, month - 1, day);
        result.setHours(hour, minute, 0, 0);
        return result.getFullYear() === year && result.getMonth() === month - 1 && result.getDate() === day
            ? result : null;
    }

    const pickers = [];
    root.querySelectorAll('[data-first-order-picker]').forEach(wrapper => {
        const input = wrapper.querySelector('.first-order-picker__input');
        const toggle = wrapper.querySelector('.first-order-picker__toggle');
        const panel = wrapper.querySelector('.first-order-picker__panel');
        const calendar = $(wrapper.querySelector('.first-order-picker__calendar'));
        const time = wrapper.querySelector('[type="time"]');
        const close = () => {
            panel.hidden = true;
            toggle.setAttribute('aria-expanded', 'false');
        };
        pickers.push({wrapper, close});

        function save() {
            const day = calendar.datepicker('getDate');
            if (!day || !time.value) return;
            input.value = `${$.datepicker.formatDate('dd.mm.yy', day)} ${time.value}`;
            input.dispatchEvent(new Event('input', {bubbles: true}));
        }

        calendar.datepicker({
            ...$.datepicker.regional.ru,
            dateFormat: 'dd.mm.yy',
            changeMonth: true,
            changeYear: true,
            yearRange: '2000:+5',
            onSelect: save
        });

        function open() {
            pickers.forEach(picker => picker.close());
            const value = parseDateTime(input.value) || new Date();
            calendar.datepicker('setDate', value);
            time.value = `${String(value.getHours()).padStart(2, '0')}:${String(value.getMinutes()).padStart(2, '0')}`;
            panel.hidden = false;
            toggle.setAttribute('aria-expanded', 'true');
        }
        toggle.addEventListener('click', () => panel.hidden ? open() : close());
        input.addEventListener('click', open);
        input.addEventListener('keydown', event => {
            if (event.key !== 'ArrowDown') return;
            event.preventDefault();
            open();
            panel.querySelector('.ui-state-active')?.focus();
        });
        wrapper.addEventListener('keydown', event => {
            if (event.key === 'Escape' && !panel.hidden) {
                event.preventDefault();
                close();
                toggle.focus();
            }
        });
        time.addEventListener('change', save);
        wrapper.querySelector('.first-order-picker__done').addEventListener('click', () => {
            save();
            close();
            input.focus();
        });
    });
    document.addEventListener('pointerdown', event => {
        pickers.forEach(picker => {
            if (!picker.wrapper.contains(event.target)) picker.close();
        });
    });
    months.forEach(button => button.addEventListener('click', () => {
        if (button.disabled) return;
        pickers.forEach(picker => picker.close());
        form.elements.date_from.value = button.dataset.dateFrom;
        form.elements.date_to.value = button.dataset.dateTo;
        form.elements.date_from.dispatchEvent(new Event('input', {bubbles: true}));
    }));
    updateMonthSelection();

    function filterUrl(base) {
        const url = new URL(base, location.origin);
        url.search = new URLSearchParams(new FormData(form)).toString();
        return url;
    }

    function validateDates() {
        const from = form.elements.date_from;
        const to = form.elements.date_to;
        const start = parseDateTime(from.value);
        const end = parseDateTime(to.value);
        from.setCustomValidity(start ? '' : 'Введите дату и время в формате ДД.ММ.ГГГГ ЧЧ:ММ');
        to.setCustomValidity(end ? '' : 'Введите дату и время в формате ДД.ММ.ГГГГ ЧЧ:ММ');
        if (start && end) to.setCustomValidity(start > end
            ? 'Дата начала не может быть позже даты окончания' : '');
        return form.reportValidity();
    }

    async function load(url) {
        controller?.abort();
        const active = new AbortController();
        controller = active;
        url.searchParams.set('bck', '1');
        error.classList.add('d-none');
        loading.classList.remove('d-none');
        table.setAttribute('aria-busy', 'true');
        try {
            const response = await fetch(url, {signal: active.signal, headers: {'Accept': 'application/json'}});
            if (response.redirected) throw new Error('Сессия завершена или доступ к отчёту закрыт. Обновите страницу.');
            const data = await response.json();
            if (!response.ok || data.status !== 'success') throw new Error(data.message || 'Не удалось обновить отчёт');
            if (controller !== active) return;
            table.innerHTML = data.htmlresponse;
            const result = table.querySelector('[data-sort]');
            form.elements.sort.value = result.dataset.sort;
            form.elements.direction.value = result.dataset.direction;
            url.searchParams.set('page', result.dataset.page);
            url.searchParams.delete('bck');
            history.replaceState(null, '', url);
            excel.href = filterUrl(root.dataset.excelUrl).href;
        } catch (reason) {
            if (reason.name === 'AbortError' || controller !== active) return;
            error.textContent = reason.message;
            error.classList.remove('d-none');
        } finally {
            if (controller === active) {
                loading.classList.add('d-none');
                table.setAttribute('aria-busy', 'false');
            }
        }
    }

    form.addEventListener('input', () => {
        form.elements.date_from.setCustomValidity('');
        form.elements.date_to.setCustomValidity('');
        updateMonthSelection();
    });
    form.addEventListener('submit', event => {
        event.preventDefault();
        if (validateDates()) load(filterUrl(root.dataset.reportUrl));
    });
    table.addEventListener('click', event => {
        const link = event.target.closest('[data-first-order-nav]');
        if (!link || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || event.button !== 0) return;
        event.preventDefault();
        if (!validateDates()) return;
        const url = filterUrl(root.dataset.reportUrl);
        url.searchParams.set('page', link.dataset.firstOrderPage || '1');
        if (link.dataset.firstOrderSort) {
            url.searchParams.set('sort', link.dataset.firstOrderSort);
            url.searchParams.set('direction', link.dataset.firstOrderDirection);
        }
        load(url);
    });
    excel.addEventListener('click', event => {
        if (!validateDates()) event.preventDefault();
        else excel.href = filterUrl(root.dataset.excelUrl).href;
    });
})();
