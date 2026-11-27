(function () {
    const maximum = 100000000;
    function isValid(value, max = maximum) {
        return /^[0-9]+$/.test(value) && Number(value) >= 1 && Number(value) <= max;
    }
    function checkInput(input, max = maximum) {
        const valid = isValid(input.value, max);
        input.setCustomValidity(valid ? '' : `Укажите целое количество от 1 до ${max}.`);
        if (!valid) input.reportValidity();
        return valid;
    }
    function validateForm(form) {
        const fields = form.querySelectorAll('[name="quantity"], [name="box_quantity"], [name="kpb_quantity"], [name="linen_set_item_quantity"]');
        for (const input of fields) {
            if (input.disabled) continue;
            const max = input.name === 'linen_set_item_quantity' ? 5 : maximum;
            if (!isValid(input.value, max)) {
                make_message(`Укажите целое количество от 1 до ${max} для каждого размера и комплекта.`, 'warning');
                if (typeof window.clearPendingStep3TransitionAfterAsyncAdd === 'function') {
                    window.clearPendingStep3TransitionAfterAsyncAdd();
                }
                return false;
            }
        }
        return true;
    }
    window.OrderQuantity = {isValid, checkInput, validateForm};
})();
