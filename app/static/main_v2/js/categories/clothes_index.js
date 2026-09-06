function initClothesCategorySearch() {
    const searchIndex = Array.isArray(window.CLOTHES_SEARCH_INDEX) ? window.CLOTHES_SEARCH_INDEX : [];
    const input = document.getElementById('clothes-category-search');
    const resultEl = document.getElementById('clothes-search-result');

    if (!input || !resultEl || !searchIndex.length) {
        return;
    }

    function normalizeText(value) {
        return String(value || '').trim().toUpperCase().replace(/\s+/g, ' ');
    }

    function extractDigits(value) {
        return String(value || '').replace(/\D/g, '');
    }

    function escapeHtml(value) {
        return String(value || '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    function findMatches(query) {
        const normalizedQuery = normalizeText(query);
        const digitQuery = extractDigits(query);
        const matches = [];
        const seen = new Set();

        if (!normalizedQuery) {
            return matches;
        }

        for (const item of searchIndex) {
            if (digitQuery) {
                for (const choice of (item.allowed_tnved_choices || [])) {
                    const key = `${item.slug}::tnved::${choice.code}`;
                    if (!String(choice.code || '').includes(digitQuery) || seen.has(key)) {
                        continue;
                    }
                    seen.add(key);
                    matches.push({
                        item,
                        reason: `ТН ВЭД: ${choice.code}`,
                        details: choice.label || 'Подкатегория определена по коду ТН ВЭД',
                    });
                }
            }

            for (const type of (item.product_types || [])) {
                const key = `${item.slug}::type::${type}`;
                if (!normalizeText(type).includes(normalizedQuery) || seen.has(key)) {
                    continue;
                }
                seen.add(key);
                matches.push({
                    item,
                    reason: `Вид товара: ${type}`,
                    details: 'Подкатегория определена по названию товара',
                });
            }
        }

        return matches;
    }

    function renderResult(matches, query) {
        if (!matches.length) {
            resultEl.classList.remove('is-empty');
            resultEl.innerHTML = `
                <p class="cosmetics-search-result__title">Совпадений не найдено</p>
                <div class="cosmetics-search-result__meta">Запрос: ${escapeHtml(query)}</div>
            `;
            return;
        }

        resultEl.classList.remove('is-empty');
        const itemsHtml = matches.slice(0, 15).map((match) => `
            <li class="cosmetics-search-result__item">
                <a class="cosmetics-search-result__link" href="${escapeHtml(match.item.url)}">
                    <div class="cosmetics-search-result__link-title">${escapeHtml(match.item.title)}</div>
                    <div class="cosmetics-search-result__meta">${escapeHtml(match.reason)}</div>
                    <div class="cosmetics-search-result__meta">${escapeHtml(match.details)}</div>
                </a>
            </li>
        `).join('');
        const moreHtml = matches.length > 15
            ? '<div class="cosmetics-search-result__more">Результатов поиска больше 15 ...</div>'
            : '';

        resultEl.innerHTML = `
            <p class="cosmetics-search-result__title">${matches.length === 1 ? 'Найдена подкатегория' : 'Найдено несколько совпадений'}</p>
            <ul class="cosmetics-search-result__list">${itemsHtml}</ul>
            ${moreHtml}
        `;
    }

    input.addEventListener('input', () => {
        const query = input.value.trim();
        if (query.length < 3) {
            resultEl.classList.add('is-empty');
            resultEl.innerHTML = '';
            return;
        }

        renderResult(findMatches(query), query);
    });
}

document.addEventListener('DOMContentLoaded', initClothesCategorySearch);

