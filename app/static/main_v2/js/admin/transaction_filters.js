document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('transaction_filters_form');
    if (!form) return;
    const from = $('#date_from');
    const to = $('#date_to');
    const buttons = form.querySelectorAll('[data-transaction-calendar]');
    const today = new Date();

    function readDate(input) {
        try { return $.datepicker.parseDate('dd.mm.yy', input.val()); }
        catch (_) { return null; }
    }

    function syncDateBounds() {
        from.datepicker('option', 'maxDate', readDate(to) || today);
        to.datepicker('option', 'minDate', readDate(from));
    }

    const calendarOptions = {
        ...$.datepicker.regional.ru,
        dateFormat: 'dd.mm.yy', changeMonth: true, changeYear: true, showAnim: '',
        numberOfMonths: 1, maxDate: today, firstDay: 1,
        beforeShow: (input, instance) => {
            instance.dpDiv.addClass('eco-datepicker');
            buttons.forEach(button => button.setAttribute('aria-expanded', String(button.dataset.transactionCalendar === input.id)));
        },
        onClose: (_, instance) => {
            instance.dpDiv.removeClass('eco-datepicker');
            buttons.forEach(button => button.setAttribute('aria-expanded', 'false'));
        },
        onSelect: function () { updateSelectedDateBound(this); }
    };
    function updateSelectedDateBound(input) {
        if (input.id === 'date_from') to.datepicker('option', 'minDate', readDate(from));
        else from.datepicker('option', 'maxDate', readDate(to) || today);
    }
    from.datepicker({...calendarOptions, defaultDate: '-1w', maxDate: today})
        .on('change', function () { updateSelectedDateBound(this); });
    to.datepicker({...calendarOptions, defaultDate: today})
        .on('change', function () { updateSelectedDateBound(this); });
    buttons.forEach(button => button.addEventListener('click', () => {
        $(`#${button.dataset.transactionCalendar}`).datepicker(button.getAttribute('aria-expanded') === 'true' ? 'hide' : 'show');
    }));
    form.querySelector('[data-transaction-today]').addEventListener('click', () => {
        // The existing shortcut sets the same text values; keep the widget's bounds in sync.
        from.datepicker('option', 'maxDate', today);
        to.datepicker('option', 'minDate', null);
        from.add(to).datepicker('setDate', today);
        syncDateBounds();
    });
});
