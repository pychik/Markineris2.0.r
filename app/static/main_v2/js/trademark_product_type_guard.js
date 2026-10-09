(function () {
    const trademarkSelector = '[name="trademark"]';
    const typeSelector = '[name="type"]';
    const emptyTrademarks = new Set(['без товарного знака', 'без бренда', 'нет']);
    const genderWords = new Set([
        'жен', 'женский', 'женская', 'женское', 'женские',
        'муж', 'мужской', 'мужская', 'мужское', 'мужские',
        'дет', 'детский', 'детская', 'детское', 'детские'
    ]);

    function normalize(value) {
        return String(value || '')
            .toLocaleLowerCase('ru-RU')
            .replace(/ё/g, 'е')
            .replace(/[^\p{L}\p{N}]+/gu, ' ')
            .trim()
            .replace(/\s+/g, ' ');
    }

    function withoutGenderWords(value) {
        const words = value.split(' ');
        const hasGender = words.some(word => genderWords.has(word));
        return words.filter(word => !genderWords.has(word) && !(hasGender && word === 'пол')).join(' ');
    }

    function oneEditApart(left, right) {
        if (Math.abs(left.length - right.length) > 1) return false;
        if (left.length === right.length) {
            let differences = 0;
            for (let index = 0; index < left.length; index++) {
                if (left[index] !== right[index]) differences++;
            }
            return differences === 1;
        }
        const short = left.length < right.length ? left : right;
        const long = left.length < right.length ? right : left;
        let shortIndex = 0;
        let longIndex = 0;
        let differences = 0;
        while (shortIndex < short.length) {
            if (short[shortIndex] !== long[longIndex]) {
                if (++differences > 1) return false;
                longIndex++;
            } else {
                shortIndex++;
                longIndex++;
            }
        }
        return true;
    }

    function hasProductType(trademark, productType) {
        const mark = normalize(trademark);
        const type = normalize(productType);
        if (!mark || !type || emptyTrademarks.has(mark)) return false;

        // Complete words from any part of a multiword type cannot be a brand.
        // A number or a Latin brand after the type makes it distinct.
        const baseType = withoutGenderWords(type);
        const baseMark = withoutGenderWords(mark);
        if (!baseType || !baseMark) return false;
        if ((` ${baseType} `).includes(` ${baseMark} `)) return true;
        return /^[а-я]{4,}$/.test(baseMark) && baseType.split(' ').some(word =>
            /^[а-я]{5,}$/.test(word) && oneEditApart(baseMark, word)
        );
    }

    function checkForm(form) {
        const trademark = form.querySelector(trademarkSelector);
        const productType = form.querySelector(typeSelector);
        if (!trademark || !productType || !hasProductType(trademark.value, productType.value)) return false;

        trademark.value = '';
        trademark.dispatchEvent(new Event('input', { bubbles: true }));
        if (typeof make_message === 'function') {
            make_message('Укажите товарный знак, отличный от вида товара, его части и обозначения пола. Поле «Товарный знак» очищено.', 'warning');
        }
        return true;
    }

    window.validateTrademarkProductType = function (form) {
        if (!checkForm(form)) return true;
        if (typeof window.clearPendingStep3TransitionAfterAsyncAdd === 'function') {
            window.clearPendingStep3TransitionAfterAsyncAdd();
        }
        return false;
    };

    document.addEventListener('change', function (event) {
        if (event.target.matches(`${trademarkSelector}, ${typeSelector}`) && event.target.form) {
            checkForm(event.target.form);
        }
    });

    document.addEventListener('submit', function (event) {
        if (!window.validateTrademarkProductType(event.target)) event.preventDefault();
    }, true);
})();
