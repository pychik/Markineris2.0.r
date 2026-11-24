document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('price_filters');
    const result = document.getElementById('price_results');
    const chart = document.getElementById('price_chart');
    const errorBox = document.getElementById('price_error');
    const exportButton = document.getElementById('price_export');
    let controller = null;
    let requestId = 0;
    let exporting = false;
    let renderedChartKey = null;
    let chartMode = 'both';
    const calendarButtons = form.querySelectorAll('[data-calendar]');
    $('#price_date_from, #price_date_to').datepicker({
        ...$.datepicker.regional.ru, dateFormat: 'dd.mm.yy', changeMonth: true, changeYear: true, firstDay: 1,
        beforeShow: (input, instance) => {
            instance.dpDiv.addClass('eco-datepicker');
            calendarButtons.forEach(button => button.setAttribute('aria-expanded', String(button.dataset.calendar === input.id)));
        },
        onClose: (_, instance) => {
            instance.dpDiv.removeClass('eco-datepicker');
            calendarButtons.forEach(button => button.setAttribute('aria-expanded', 'false'));
        },
        onSelect: () => { updateDateLimits(); loadReport(1, true); }
    });
    function updateDateLimits() {
        const from = $('#price_date_from').datepicker('getDate');
        if (!from) return;
        const lastDay = new Date(from.getFullYear() + 1, from.getMonth() + 1, 0).getDate();
        const maxTo = new Date(from.getFullYear() + 1, from.getMonth(), Math.min(from.getDate(), lastDay));
        $('#price_date_to').datepicker('option', {minDate: from, maxDate: maxTo});
    }
    calendarButtons.forEach(button => button.addEventListener('click', () => {
        $(`#${button.dataset.calendar}`).datepicker(button.getAttribute('aria-expanded') === 'true' ? 'hide' : 'show');
    }));

    function showError(message) {
        errorBox.textContent = message;
        errorBox.hidden = !message;
    }

    function drawChart(points) {
        chart.replaceChildren();
        const header = document.createElement('div');
        header.className = 'price-chart-header';
        const title = document.createElement('h2');
        title.className = 'h5 mb-0';
        title.textContent = 'Средняя цена по дням';
        header.append(title);
        chart.append(header);
        if (!points.some(point => point.price !== null)) {
            chart.append(document.createTextNode('За выбранный период данных нет.'));
            return;
        }
        const modes = document.createElement('div');
        modes.className = 'price-chart-modes';
        modes.setAttribute('role', 'group');
        modes.setAttribute('aria-label', 'Вид графика');
        const modeButtons = [];
        for (const [mode, label] of [['points', 'Точки'], ['line', 'Линия'], ['both', 'Линия и точки']]) {
            const button = document.createElement('button');
            button.type = 'button';
            button.textContent = label;
            button.dataset.priceChartMode = mode;
            button.addEventListener('click', () => { chartMode = mode; renderViewport(); });
            modeButtons.push(button);
            modes.append(button);
        }
        header.append(modes);
        const ns = 'http://www.w3.org/2000/svg';
        function element(name, attrs, text) {
            const node = document.createElementNS(ns, name);
            Object.entries(attrs).forEach(([key, value]) => node.setAttribute(key, value));
            if (text !== undefined) node.textContent = text;
            return node;
        }
        const svg = element('svg', {id: 'price-chart-plot', viewBox: '0 0 1000 300', role: 'group', tabindex: 0,
            'aria-label': 'Средняя цена по дням. После увеличения перемещайте график мышью или стрелками влево и вправо.'});
        const defs = element('defs', {});
        const clip = element('clipPath', {id: 'price-chart-clip'});
        clip.append(element('rect', {x: 84, y: 20, width: 862, height: 230}));
        defs.append(clip);
        svg.append(defs);
        const min = points.reduce((value, point) => point.price === null ? value : Math.min(value, point.price), 0);
        const max = points.reduce((value, point) => point.price === null ? value : Math.max(value, point.price), 1);
        const y = price => 240 - (price - min) / (max - min) * 210;
        for (let index = 0; index <= 4; index++) {
            const value = min + (max - min) * index / 4;
            svg.append(element('line', {x1: 85, x2: 945, y1: y(value), y2: y(value), stroke: '#F1F3F5'}));
            svg.append(element('text', {x: 75, y: y(value) + 4, 'text-anchor': 'end'}, value.toFixed(2)));
        }
        const plot = element('g', {'clip-path': 'url(#price-chart-clip)'});
        const labels = element('g', {});
        svg.append(plot, labels);
        const tooltip = document.createElement('div');
        tooltip.className = 'price-chart-tooltip';
        tooltip.hidden = true;
        tooltip.setAttribute('role', 'tooltip');
        const footer = document.createElement('div');
        footer.className = 'price-chart-footer';
        const hint = document.createElement('span');
        hint.className = 'text-muted small';
        hint.textContent = 'Увеличьте график и перетаскивайте мышью вправо или влево';
        const controls = document.createElement('div');
        controls.className = 'price-chart-zoom';
        controls.setAttribute('role', 'group');
        controls.setAttribute('aria-label', 'Масштаб графика');
        function control(text, label, action) {
            const button = document.createElement('button');
            button.type = 'button';
            button.textContent = text;
            button.title = label;
            button.setAttribute('aria-label', label);
            button.addEventListener('click', action);
            controls.append(button);
            return button;
        }
        const extent = Math.max(0, points.length - 1);
        const minSpan = Math.min(2, extent);
        let start = 0;
        let span = extent;
        let dragging = null;
        let pinnedPoint = null;
        function setViewport(nextStart, nextSpan) {
            span = Math.max(minSpan, Math.min(extent, nextSpan));
            start = Math.max(0, Math.min(extent - span, nextStart));
            renderViewport();
        }
        function zoom(factor) {
            const nextSpan = Math.max(minSpan, Math.min(extent, span * factor));
            setViewport(start + (span - nextSpan) / 2, nextSpan);
        }
        const zoomOut = control('−', 'Уменьшить масштаб', () => zoom(2));
        const zoomIn = control('+', 'Увеличить масштаб', () => zoom(0.5));
        const reset = control('Сброс', 'Показать весь период', () => setViewport(0, extent));
        const scrollbar = document.createElement('div');
        scrollbar.className = 'price-chart-scrollbar';
        scrollbar.tabIndex = 0;
        scrollbar.setAttribute('role', 'scrollbar');
        scrollbar.setAttribute('aria-label', 'Прокрутка периода графика');
        scrollbar.setAttribute('aria-orientation', 'horizontal');
        scrollbar.setAttribute('aria-controls', 'price-chart-plot');
        scrollbar.setAttribute('aria-valuemin', '0');
        scrollbar.setAttribute('aria-valuemax', '100');
        const thumb = document.createElement('div');
        thumb.className = 'price-chart-scrollbar-thumb';
        scrollbar.append(thumb);
        let scrollDrag = null;
        scrollbar.addEventListener('pointerdown', event => {
            if (event.button !== 0 || !event.isPrimary || span >= extent) return;
            event.preventDefault();
            scrollbar.focus();
            const bounds = scrollbar.getBoundingClientRect();
            const travel = bounds.width - thumb.getBoundingClientRect().width;
            if (travel <= 0) return;
            if (event.target !== thumb) {
                const position = (event.clientX - bounds.left - thumb.getBoundingClientRect().width / 2) / travel;
                setViewport(position * (extent - span), span);
            }
            scrollDrag = {pointerId: event.pointerId, x: event.clientX, start, travel};
            scrollbar.setPointerCapture(event.pointerId);
            scrollbar.classList.add('price-chart-scrollbar-dragging');
        });
        scrollbar.addEventListener('pointermove', event => {
            if (!scrollDrag || scrollDrag.pointerId !== event.pointerId) return;
            setViewport(scrollDrag.start + (event.clientX - scrollDrag.x) / scrollDrag.travel * (extent - span), span);
        });
        function endScrollDrag(event) {
            if (!scrollDrag || scrollDrag.pointerId !== event.pointerId) return;
            scrollDrag = null;
            scrollbar.classList.remove('price-chart-scrollbar-dragging');
            if (scrollbar.hasPointerCapture(event.pointerId)) scrollbar.releasePointerCapture(event.pointerId);
        }
        scrollbar.addEventListener('pointerup', endScrollDrag);
        scrollbar.addEventListener('pointercancel', endScrollDrag);
        scrollbar.addEventListener('lostpointercapture', endScrollDrag);
        scrollbar.addEventListener('keydown', event => {
            const steps = {ArrowLeft: -span / 5, ArrowRight: span / 5, PageUp: -span, PageDown: span};
            if (event.key === 'Home' || event.key === 'End' || Object.hasOwn(steps, event.key)) {
                event.preventDefault();
                setViewport(event.key === 'Home' ? 0 : event.key === 'End' ? extent - span : start + steps[event.key], span);
            }
        });
        footer.append(hint, controls);
        chart.append(svg, scrollbar, footer, tooltip);

        function renderViewport() {
            plot.replaceChildren();
            labels.replaceChildren();
            tooltip.hidden = true;
            pinnedPoint = null;
            const x = index => span ? 85 + (index - start) / span * 860 : 515;
            let path = '';
            let gap = true;
            points.forEach((point, index) => {
                if (point.price === null) { gap = true; return; }
                path += `${gap ? 'M' : 'L'}${x(index)},${y(point.price)} `;
                gap = false;
            });
            if (chartMode !== 'points') {
                plot.append(element('path', {d: path, fill: 'none', stroke: '#E5B700', 'stroke-width': 1.75,
                    'stroke-linejoin': 'round', 'stroke-linecap': 'round'}));
            }
            points.forEach((point, index) => {
                if (point.price === null || index < start || index > start + span) return;
                const label = `${point.date}: ${point.price.toFixed(2)} руб. · Марок: ${point.marks.toLocaleString('ru-RU')}`;
                const dot = element('circle', {cx: x(index), cy: y(point.price), r: 3, tabindex: 0, 'aria-label': label});
                // Invisible targets keep price tooltips available in line mode.
                if (chartMode === 'line') dot.classList.add('price-chart-hit');
                const showTooltip = () => {
                    if (dragging || (pinnedPoint !== null && pinnedPoint !== index)) return;
                    tooltip.textContent = label;
                    tooltip.hidden = false;
                    const bounds = dot.getBoundingClientRect();
                    const container = chart.getBoundingClientRect();
                    const halfWidth = tooltip.offsetWidth / 2 + 8;
                    tooltip.style.left = `${Math.max(halfWidth, Math.min(container.width - halfWidth, bounds.left + bounds.width / 2 - container.left))}px`;
                    tooltip.style.top = `${bounds.top - container.top - 8}px`;
                };
                dot.addEventListener('mouseenter', showTooltip);
                dot.addEventListener('focus', showTooltip);
                const hideTooltip = () => { if (pinnedPoint === null) tooltip.hidden = true; };
                const selectPoint = () => {
                    const selected = pinnedPoint === index;
                    plot.querySelectorAll('.price-chart-selected').forEach(node => node.classList.remove('price-chart-selected'));
                    pinnedPoint = selected ? null : index;
                    dot.classList.toggle('price-chart-selected', !selected);
                    if (selected) tooltip.hidden = true;
                    else showTooltip();
                };
                dot.addEventListener('click', event => { event.stopPropagation(); selectPoint(); });
                dot.addEventListener('keydown', event => {
                    if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); selectPoint(); }
                });
                dot.addEventListener('mouseleave', hideTooltip);
                dot.addEventListener('blur', hideTooltip);
                plot.append(dot);
            });
            const ticks = new Set();
            for (let index = 0; index <= 4; index++) ticks.add(Math.round(start + span * index / 4));
            ticks.forEach(index => {
                if (index >= start && index <= start + span) {
                    labels.append(element('text', {x: x(index), y: 270, 'text-anchor': 'middle'}, points[index].date));
                }
            });
            modeButtons.forEach(button => button.setAttribute('aria-pressed', String(button.dataset.priceChartMode === chartMode)));
            zoomIn.disabled = span <= minSpan;
            zoomOut.disabled = span >= extent;
            reset.disabled = span >= extent;
            svg.classList.toggle('price-chart-pannable', span < extent);
            const position = extent > span ? start / (extent - span) : 0;
            thumb.style.width = `${extent ? span / extent * 100 : 100}%`;
            thumb.style.left = `${position * 100}%`;
            thumb.style.transform = `translateX(${-position * 100}%)`;
            scrollbar.setAttribute('aria-valuenow', String(Math.round(position * 100)));
            scrollbar.setAttribute('aria-valuetext', `${points[Math.round(start)].date} — ${points[Math.round(start + span)].date}`);
            scrollbar.setAttribute('aria-disabled', String(span >= extent));
            scrollbar.tabIndex = span < extent ? 0 : -1;
        }
        function pointerX(event) {
            const point = svg.createSVGPoint();
            point.x = event.clientX;
            point.y = event.clientY;
            return point.matrixTransform(svg.getScreenCTM().inverse()).x;
        }
        svg.addEventListener('pointerdown', event => {
            if (event.button !== 0 || span >= extent || !event.isPrimary) return;
            const x = pointerX(event);
            if (x < 85 || x > 945) return;
            dragging = {pointerId: event.pointerId, x, start};
            tooltip.hidden = true;

            event.preventDefault();
        });
        svg.addEventListener('pointermove', event => {
            if (!dragging || dragging.pointerId !== event.pointerId) return;
            if (!svg.hasPointerCapture(event.pointerId)) {
                if (Math.abs(pointerX(event) - dragging.x) < 4) return;
                svg.setPointerCapture(event.pointerId);
                svg.classList.add('price-chart-dragging');
            }
            setViewport(dragging.start - (pointerX(event) - dragging.x) / 860 * span, span);
        });
        function endDrag(event) {
            if (!dragging || dragging.pointerId !== event.pointerId) return;
            dragging = null;
            svg.classList.remove('price-chart-dragging');
            if (svg.hasPointerCapture(event.pointerId)) svg.releasePointerCapture(event.pointerId);
        }
        svg.addEventListener('pointerup', endDrag);
        svg.addEventListener('pointercancel', endDrag);
        svg.addEventListener('lostpointercapture', endDrag);
        svg.addEventListener('click', () => {
            pinnedPoint = null;
            tooltip.hidden = true;
            plot.querySelectorAll('.price-chart-selected').forEach(node => node.classList.remove('price-chart-selected'));
        });
        svg.addEventListener('keydown', event => {
            if (event.key === 'Escape') {
                pinnedPoint = null;
                tooltip.hidden = true;
                plot.querySelectorAll('.price-chart-selected').forEach(node => node.classList.remove('price-chart-selected'));
            }
            if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {
                event.preventDefault();
                setViewport(start + (event.key === 'ArrowLeft' ? -1 : 1) * span / 5, span);
            }
        });
        renderViewport();
    }

    async function loadReport(page = 1, refreshChart = false) {
        if (!form.reportValidity()) return;
        if (controller) controller.abort();
        controller = new AbortController();
        const active = controller;
        const id = ++requestId;
        const params = new URLSearchParams(new FormData(form));
        const chartKey = `${params.get('date_from')}/${params.get('date_to')}`;
        refreshChart = refreshChart || renderedChartKey !== chartKey;
        params.set('format', 'json');
        params.set('page', page);
        params.set('chart', refreshChart ? '1' : '0');
        result.setAttribute('aria-busy', 'true');
        if (refreshChart) chart.setAttribute('aria-busy', 'true');
        showError('');
        const timeout = setTimeout(() => active.abort(), 60000);
        try {
            const response = await fetch(`${location.pathname}?${params}`, {signal: active.signal, headers: {'Accept': 'application/json'}});
            const data = await response.json().catch(() => ({}));
            if (!response.ok) throw new Error(data.message || `Ошибка загрузки отчета (${response.status})`);
            if (id !== requestId) return;
            result.innerHTML = data.htmlresponse;
            if (data.chart !== null) { drawChart(data.chart); renderedChartKey = chartKey; }
            const urlParams = new URLSearchParams(new FormData(form));
            urlParams.set('page', page);
            history.replaceState(null, '', `${location.pathname}?${urlParams}`);
        } catch (error) {
            if (id === requestId) showError(error.name === 'AbortError' ? 'Превышено время ожидания. Уточните период и повторите запрос.' : error.message);
        } finally {
            clearTimeout(timeout);
            if (id === requestId) {
                controller = null;
                result.setAttribute('aria-busy', 'false');
                chart.setAttribute('aria-busy', 'false');
            }
        }
    }
    form.addEventListener('submit', event => { event.preventDefault(); loadReport(1, true); });
    result.addEventListener('click', event => {
        const page = event.target.closest('[data-price-page]');
        const sort = event.target.closest('[data-price-sort]');
        if (page) { event.preventDefault(); loadReport(Number(page.dataset.pricePage)); }
        if (sort) {
            form.elements.sort.value = form.elements.sort.value === 'asc' ? 'desc' : 'asc';
            loadReport();
        }
    });
    exportButton.addEventListener('click', async () => {
        if (exporting || !form.reportValidity()) return;
        exporting = true;
        exportButton.disabled = true;
        exportButton.textContent = 'Подготовка Excel…';
        showError('');
        const params = new URLSearchParams(new FormData(form));
        params.set('format', 'xlsx');
        const downloadController = new AbortController();
        const timeout = setTimeout(() => downloadController.abort(), 60000);
        try {
            const response = await fetch(`${location.pathname}?${params}`, {signal: downloadController.signal});
            if (!response.ok) {
                const error = await response.json().catch(() => ({}));
                throw new Error(error.message || `Ошибка выгрузки (${response.status})`);
            }
            const url = URL.createObjectURL(await response.blob());
            const link = document.createElement('a');
            link.href = url;
            link.download = `average_price_${params.get('date_from')}_${params.get('date_to')}.xlsx`;
            document.body.append(link);
            link.click();
            link.remove();
            setTimeout(() => URL.revokeObjectURL(url), 1000);
        } catch (error) {
            showError(error.name === 'AbortError' ? 'Превышено время ожидания выгрузки. Уточните период и повторите запрос.' : error.message);
        } finally {
            clearTimeout(timeout);
            exporting = false;
            exportButton.disabled = false;
            exportButton.textContent = 'Скачать в Excel';
        }
    });
    const initialPage = Number(new URLSearchParams(location.search).get('page')) || 1;
    updateDateLimits();
    loadReport(initialPage, true);
});
