/* GTIN metadata is keyed by size identity, never by row number or quantity. */
(function () {
    'use strict';
    const identity = row => JSON.stringify([row.size, row.size_type || '', row.unit || '']);
    function validateRows(rows) {
        const seen = new Set();
        return rows.map(row => {
            const gtin = row.gtin.trim();
            if (Boolean(gtin) !== Boolean(row.company)) return 'Заполните GTIN и компанию вместе или оставьте оба поля пустыми.';
            if (gtin && !/^046[0-9]{11}$/.test(gtin)) return 'GTIN должен состоять из 14 цифр и начинаться с 046.';
            if (gtin && seen.has(gtin)) return 'У разных размеров одной позиции должны быть разные GTIN.';
            if (gtin) seen.add(gtin);
            return '';
        });
    }
    if (typeof module !== 'undefined' && module.exports) module.exports = {identity, validateRows};
    if (typeof document === 'undefined') return;
    document.addEventListener('DOMContentLoaded', function () {
        const step = document.getElementById('step-2');
        const template = document.getElementById('gtin-position-template');
        if (!step || !template || document.getElementById('gtin')) return;
        const form = document.getElementById('form_process_main');
        const block = template.content.firstElementChild.cloneNode(true);
        const totals = step.querySelector('.important-card.text-light');
        if (totals) {
            totals.appendChild(block);
            const addControls = totals.querySelector('.step-btns');
            if (addControls) totals.appendChild(addControls);
        } else (step.querySelector('.step-btns') || step).before(block);
        const modalElement = document.getElementById('gtin-modal-template').content.firstElementChild.cloneNode(true);
        document.body.appendChild(modalElement);
        const modal = bootstrap.Modal.getOrCreateInstance(modalElement);
        const rowsElement = modalElement.querySelector('#gtin-modal-rows');
        const summary = block.querySelector('#gtin-position-summary');
        const gtin = block.querySelector('#gtin');
        const company = block.querySelector('#gtin_company_key');
        const payload = block.querySelector('#size_gtins');
        const sizeContainer = step.querySelector('#sizes_quantity');
        let stored = new Map(JSON.parse(document.getElementById('gtin-initial-data').textContent).map(row => [identity(row), row]));
        let rows = [];
        let signature = '';
        let sized = false;
        const value = (name, root = form) => root.querySelector('[name="' + name + '"]')?.value || '';
        function currentSizes() {
            if (!sizeContainer || value('type') === 'КОМПЛЕКТ ПОСТЕЛЬНОГО БЕЛЬЯ') return null;
            const inputs = name => Array.from(sizeContainer.querySelectorAll('input[name="' + name + '"]'));
            const dimensions = inputs('sizeX');
            const sizes = dimensions.length ? dimensions : inputs('size');
            return sizes.map((input, index) => ({
                size: dimensions.length ? input.value + '*' + inputs('sizeY')[index].value : input.value,
                size_type: inputs('size_type')[index]?.value || '',
                unit: inputs('sizeUnit')[index]?.value || '',
                quantity: inputs('quantity')[index]?.value || '',
            }));
        }
        function sync() {
            rows.forEach(row => {
                row.data.gtin = row.input.value.trim();
                row.data.company = row.select.value;
                row.input.required = Boolean(row.data.company);
                row.select.required = Boolean(row.data.gtin);
            });
            const errors = validateRows(rows.map(row => row.data));
            rows.forEach((row, index) => {
                row.input.setCustomValidity(errors[index]);
                row.input.classList.toggle('is-invalid', Boolean(errors[index]));
                row.input.nextElementSibling.textContent = errors[index];
            });
            if (sized) {
                gtin.value = '';
                company.value = '';
                payload.disabled = false;
                payload.value = JSON.stringify(rows.map(row => row.data));
            } else {
                payload.disabled = true;
                gtin.value = rows[0]?.data.gtin || '';
                company.value = rows[0]?.data.company || '';
            }
            summary.replaceChildren();
            rows.forEach(row => {
                if (!row.data.gtin && !row.data.company) return;
                const line = document.createElement('div');
                line.className = 'gtin-summary-row';
                const title = document.createElement('strong');
                title.textContent = (sized ? row.label + ' · ' : '') + (row.data.gtin || 'GTIN не указан');
                const companyLine = document.createElement('div');
                companyLine.className = 'small';
                companyLine.textContent = row.data.company ? row.select.selectedOptions[0].textContent : 'Компания не выбрана';
                line.append(title, companyLine);
                summary.appendChild(line);
            });
        }
        function rebuild(force = false) {
            const sizes = currentSizes();
            const nextSignature = JSON.stringify({sizes, trademark: sizes === null ? value('trademark') : ''});
            if (!force && nextSignature === signature) return;
            signature = nextSignature;
            sized = sizes !== null;
            modalElement.querySelector('#gtin-modal-help').textContent = sized
                ? 'У каждого размера — свой GTIN. Заполните GTIN и компанию вместе или оставьте оба поля пустыми. Разные компании будут оформлены отдельными заказами.'
                : 'Заполните GTIN и проводящую компанию вместе или оставьте оба поля пустыми. Позиции разных компаний будут оформлены отдельными заказами.';
            rowsElement.replaceChildren();
            rows = [];
            const nextStored = new Map();
            (sizes || [{size: '', size_type: '', unit: '', gtin: gtin.value, company: company.value}]).forEach((size, index) => {
                const key = identity(size);
                const data = {...size, ...(stored.get(key) || {}), quantity: size.quantity};
                data.gtin = data.gtin || '';
                data.company = data.company || '';
                nextStored.set(key, data);
                const node = document.getElementById('gtin-row-template').content.firstElementChild.cloneNode(true);
                const label = sized ? [size.size, size.size_type, size.unit].filter(Boolean).join(' · ') : (value('trademark').trim() || 'Товарный знак не указан');
                node.querySelector('.gtin-size-label').textContent = label + (size.quantity ? ' — ' + size.quantity + ' шт.' : '');
                const input = node.querySelector('.gtin-value');
                const select = node.querySelector('.gtin-company');
                input.value = data.gtin;
                select.value = data.company;
                input.id = 'gtin-size-' + index;
                select.id = 'gtin-company-' + index;
                input.addEventListener('input', sync);
                select.addEventListener('change', sync);
                rows.push({data, input, select, label});
                rowsElement.appendChild(node);
            });
            stored = nextStored;
            modalElement.querySelector('#gtin-modal-empty').hidden = rows.length > 0;
            sync();
        }
        block.querySelector('.gtin-toggle').addEventListener('click', () => {rebuild(); modal.show();});
        window.validatePositionGTIN = function () {
            rebuild();
            sync();
            const invalid = rows.flatMap(row => [row.input, row.select]).find(input => !input.validity.valid);
            if (!invalid) return true;
            const focus = () => {invalid.focus(); invalid.reportValidity();};
            if (modalElement.classList.contains('show')) focus();
            else {
                modalElement.addEventListener('shown.bs.modal', focus, {once: true});
                modal.show();
            }
            if (typeof window.clearPendingStep3TransitionAfterAsyncAdd === 'function') window.clearPendingStep3TransitionAfterAsyncAdd();
            return false;
        };
        modalElement.querySelector('#gtin-modal-save').addEventListener('click', () => {
            if (window.validatePositionGTIN()) modal.hide();
        });
        form.addEventListener('submit', event => {
            if (!window.validatePositionGTIN()) {event.preventDefault(); event.stopImmediatePropagation();}
        }, true);
        // Form-associated modal controls live outside the form; invalid does not bubble to it.
        modalElement.addEventListener('invalid', () => modal.show(), true);
        if (sizeContainer) new MutationObserver(() => rebuild()).observe(sizeContainer, {childList: true, subtree: true, attributes: true, attributeFilter: ['value']});
        step.addEventListener('change', () => rebuild());
        step.addEventListener('input', event => {if (sizeContainer?.contains(event.target) || event.target.name === 'trademark') rebuild();});
        if (window.jQuery) {
            jQuery(document).ajaxSuccess(function (_event, _xhr, options, data) {
                const path = new URL(options.url, window.location.href).pathname;
                if (!path.includes('/preprocess_order/') || !data || data.status !== 'success') return;
                stored.clear();
                gtin.value = '';
                company.value = '';
                rebuild(true);
                modal.hide();
            });
        }
        rebuild(true);
        document.addEventListener('click', function (event) {
            const button = event.target.closest('[data-gtin]');
            if (!button) return;
            const sizeRows = JSON.parse(button.dataset.sizeGtins || '[]');
            const values = sizeRows.length ? sizeRows : (button.dataset.gtin ? [{gtin: button.dataset.gtin, company: button.dataset.gtinCompany}] : []);
            setTimeout(function () {
                const card = document.querySelector('#ShowModalTable #showElementTable .important-card');
                if (!card) return;
                const options = document.getElementById('gtin-row-template').content.querySelector('.gtin-company').options;
                const sizeElements = card.querySelectorAll('.important-card__size');
                values.forEach((row, index) => {
                    const sizeElement = row.size ? sizeElements[index] : null;
                    if (!sizeElement && !row.gtin) return;
                    const line = document.createElement('div');
                    line.className = sizeElement ? 'gtin-size-details' : 'important-card__item';
                    const option = Array.from(options).find(item => item.value === row.company);
                    const gtinLine = document.createElement('div');
                    gtinLine.textContent = row.gtin ? 'GTIN: ' + row.gtin : 'Без GTIN';
                    line.appendChild(gtinLine);
                    if (row.company) {
                        const companyLine = document.createElement('div');
                        companyLine.textContent = 'Компания: ' + (option?.textContent || row.company);
                        line.appendChild(companyLine);
                    }
                    if (sizeElement) {
                        sizeElement.classList.add('flex-wrap');
                        sizeElement.appendChild(line);
                    } else {
                        card.appendChild(line);
                    }
                });
            }, 0);
        }, true);
    });
})();
