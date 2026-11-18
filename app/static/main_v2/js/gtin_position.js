document.addEventListener('DOMContentLoaded', function () {
    const step = document.getElementById('step-2');
    const template = document.getElementById('gtin-position-template');
    if (!step || !template || document.getElementById('gtin')) return;
    const block = template.content.firstElementChild.cloneNode(true);
    const controls = step.querySelector('.step-btns');
    if (controls) controls.before(block);
    else step.appendChild(block);
    const gtin = block.querySelector('#gtin');
    const company = block.querySelector('#gtin_company_key');
    const collapse = bootstrap.Collapse.getOrCreateInstance(block.querySelector('#gtin-position-fields'), {toggle: false});
    const sync = () => {
        gtin.required = Boolean(company.value);
        company.required = Boolean(gtin.value.trim());
        if (gtin.required || company.required) collapse.show();
    };
    gtin.addEventListener('input', sync);
    company.addEventListener('change', sync);
    sync();
    // Ordinary position forms use both native submissions and jQuery AJAX.
    document.getElementById('form_process_main').addEventListener('invalid', event => {
        if (block.contains(event.target)) collapse.show();
    }, true);
    if (window.jQuery) {
        jQuery(document).ajaxSuccess(function (_event, _xhr, options, data) {
            const path = new URL(options.url, window.location.href).pathname;
            if (!path.includes('/preprocess_order/') || !data || data.status !== 'success') return;
            gtin.value = '';
            company.value = '';
            sync();
            collapse.hide();
        });
    }
    document.addEventListener('click', function (event) {
        const button = event.target.closest('[data-gtin]');
        if (!button || !button.dataset.gtin) return;
        setTimeout(function () {
            const card = document.querySelector('#ShowModalTable #showElementTable .important-card');
            if (!card) return;
            const line = document.createElement('div');
            line.className = 'important-card__item';
            const option = Array.from(company.options).find(item => item.value === button.dataset.gtinCompany);
            line.textContent = 'GTIN: ' + button.dataset.gtin + '; ' + (option ? option.textContent : button.dataset.gtinCompany);
            card.appendChild(line);
        }, 0);
    }, true);
});
