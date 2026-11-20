(function () {
    'use strict';
    let loading = false;
    window.gtinCompanyOpen = async function (event, button) {
        event.preventDefault();
        event.stopPropagation();
        const operatorPath = button.dataset.operatorCrmPath;
        if (!operatorPath || window.location.pathname.replace(/\/$/, '') !== operatorPath.replace(/\/$/, '')) return;
        if (loading || document.getElementById('gtin-company-modal')) return;
        loading = true;
        loadingCircle();
        bootstrap.Tooltip.getInstance(button)?.hide();
        try {
            const response = await fetch(button.dataset.gtinCompanyUrl, {
                headers: {'Accept': 'application/json'}, cache: 'no-store',
            });
            const data = await response.json().catch(() => ({}));
            if (!response.ok || data.status !== 'success') throw new Error(data.message || 'Не удалось загрузить компании.');
            document.body.insertAdjacentHTML('beforeend', data.html);
            const element = document.getElementById('gtin-company-modal');
            const modal = bootstrap.Modal.getOrCreateInstance(element, {backdrop: 'static', keyboard: false});
            element.addEventListener('hidden.bs.modal', () => {modal.dispose(); element.remove();}, {once: true});
            element.querySelector('form').addEventListener('submit', event => saveCompany(event, element));
            modal.show();
        } catch (error) {
            make_message(error instanceof TypeError ? 'Не удалось загрузить компании. Проверьте подключение.' : (error.message || 'Не удалось загрузить компании.'), 'danger');
        } finally {
            loading = false;
            close_Loading_circle();
        }
    };

    function updateCompanyCard(card, result) {
        if (!card) return;
        const title = card.querySelector('[data-gtin-company-title]');
        if (title) {
            title.textContent = result.company_title;
            title.dataset.copyValue = result.company_title;
        }
        const inn = card.querySelector('[data-gtin-company-inn]');
        if (inn) {
            inn.textContent = result.company_inn || '';
            inn.dataset.copyValue = result.company_inn || '';
        }
        const innRow = card.querySelector('[data-gtin-company-inn-row]');
        if (innRow) innRow.hidden = !result.company_inn;
        const updIcon = card.querySelector('[data-role="upd-icon"]');
        if (updIcon) {
            const hasUpd = Boolean(result.upd_number || result.processing_info);
            const tooltip = result.processing_info || (result.upd_number ? 'УПД: ' + result.upd_number : 'УПД не указан');
            updIcon.classList.toggle('active', hasUpd);
            updIcon.classList.toggle('mred', !hasUpd);
            updIcon.setAttribute('data-bs-title', tooltip);
            bootstrap.Tooltip.getInstance(updIcon)?.setContent({'.tooltip-inner': tooltip});
        }
    }

    async function saveCompany(event, element) {
        event.preventDefault();
        if (element.dataset.saving === '1') return;
        const form = element.querySelector('form');
        if (!form.reportValidity()) return;
        const errorElement = element.querySelector('[data-gtin-company-error]');
        errorElement.classList.add('d-none');
        const data = new FormData(form);
        element.dataset.saving = '1';
        loadingCircle();
        try {
            const response = await fetch(form.action, {
                method: 'POST',
                headers: {'Content-Type': 'application/json', 'X-CSRFToken': data.get('csrf_token')},
                body: JSON.stringify({company: data.get('company'), expected_company: data.get('expected_company')}),
            });
            const result = await response.json().catch(() => ({}));
            if (!response.ok || result.status !== 'success') throw new Error(result.message || 'Не удалось сохранить компанию.');
            document.querySelectorAll('.order[data-order-id]').forEach(card => {
                if (String(card.dataset.orderId) === String(result.order_id)) updateCompanyCard(card, result);
            });
            bootstrap.Modal.getOrCreateInstance(element).hide();
            make_message(result.message || 'Компания GTIN-заказа сохранена.', 'success');
        } catch (error) {
            errorElement.textContent = error instanceof TypeError ? 'Не удалось сохранить компанию. Проверьте подключение.' : (error.message || 'Не удалось сохранить компанию.');
            errorElement.classList.remove('d-none');
        } finally {
            element.dataset.saving = '0';
            close_Loading_circle();
        }
    }
})();
