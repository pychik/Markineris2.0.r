(function () {
    const config = document.getElementById('clothesTnvedContentRule');
    if (!config) return;
    const rule = JSON.parse(config.textContent);
    const materialPattern = new RegExp(rule.materialPattern, 'i');

    function getError(code, content) {
        return String(code || '').trim().startsWith(rule.prefix) &&
            !materialPattern.test(String(content || '')) ? rule.message : '';
    }

    function check(code) {
        const error = getError(code, document.getElementById('content').value);
        if (!error) return true;
        show_form_errors([error]);
        $('#form_errorModal').modal('show');
        return false;
    }

    function sync() {
        const content = document.getElementById('content');
        const tnved = document.getElementById('tnved_code');
        if (!content || !tnved) return;
        const error = getError(tnved.value, content.value);
        const feedback = document.getElementById('tnved_nv_feedback');
        if (!error) {
            if (feedback && feedback.textContent.startsWith(rule.message)) feedback.textContent = '';
            return;
        }
        tnved.value = '';
        const flag = document.getElementById('check_tnved_flag');
        if (flag) flag.value = 'false';
        const success = document.getElementById('tnved_valid_feedback');
        if (success) success.textContent = '';
        if (feedback) feedback.textContent = error + ' Выберите другой ТН ВЭД.';
    }

    window.ClothesTnvedContent = {getError, check, sync};
    ['input', 'change'].forEach(eventName => {
        document.addEventListener(eventName, event => {
            if (event.target.id === 'content' || event.target.id === 'tnved_code') sync();
        });
    });
    document.addEventListener('DOMContentLoaded', sync);
})();
