(function () {
  const MIN_LEN = 5;
  const DEBOUNCE_MS = 250;
  const HOMOGLYPHS = {"А": "A", "В": "B", "Е": "E", "К": "K", "М": "M", "Н": "H", "О": "O", "Р": "P", "С": "C", "Т": "T", "У": "Y", "Х": "X"};

  // Тот же алгоритм, что rd_registry/normalize.py::rd_key - менять синхронно.
  function rdKey(value) {
    return (value || "").toUpperCase()
      .replace(/[АВЕКМНОРСТУХ]/g, ch => HOMOGLYPHS[ch])
      .replace(/[^0-9A-ZА-ЯЁ]/g, "");
  }

  const modal = document.getElementById("rdRegistryModal");
  if (!modal) return;

  const searchUrl = modal.dataset.searchUrl;
  const recommendedUrl = modal.dataset.recommendedUrl;
  const recStatus = document.getElementById("rdRecommendedStatus");
  const recTable = document.getElementById("rdRecommendedTable");
  const recBody = recTable.querySelector("tbody");
  const input = document.getElementById("rdRegistryQuery");
  const applyBtn = document.getElementById("rdRegistryApply");
  const statusEl = document.getElementById("rdRegistryStatus");
  const table = document.getElementById("rdRegistryTable");
  const tbody = table.querySelector("tbody");

  let tnved = "";      // ТНВЭД карточки на момент открытия модалки
  let country = "";    // страна карточки - сужает и рекомендации, и реестр
  let productType = "";  // вид товара - только поднимает подходящие рекомендации выше
  let openId = 0;      // ответ рекомендаций от прошлого открытия модалки не рисуем
  let preload = null;  // {items, has_more}: РД с ТНВЭД карточки, грузим один раз за открытие
  let deadKey = null;  // по этому куску сервер ничего не нашёл - строки, которые его содержат, не ищем
  let fullSet = null;  // {key, items}: сервер отдал все совпадения (has_more=false) - дальше фильтруем сами
  let lastKey = null;
  let timer = null;
  let controller = null;

  // Строка обеих таблиц: колонки одинаковые, первая - категория реестра или вид товара из Tezaurus.
  function buildRow(item, first, firstClass) {
    const tr = document.createElement("tr");
    tr.style.cursor = "pointer";
    tr.title = "Подставить в карточку";
    [first, item.tnved_code, item.rd_type, item.rd_name, item.rd_date, item.rd_date_to, item.country || "—", item.days_left]
      .forEach((value, i) => {
        const td = document.createElement("td");
        td.textContent = value;
        if (i === 0 && firstClass) {
          td.className = firstClass;
          td.title = value;
        }
        if (i === 1 && value && value === tnved) td.className = "fw-semibold";  // ТНВЭД как в карточке
        if (i === 7) td.className = "text-end";
        tr.appendChild(td);
      });
    tr.addEventListener("click", () => applyRd(item));
    return tr;
  }

  function render(items, message) {
    tbody.innerHTML = "";
    table.classList.toggle("d-none", !items || !items.length);
    statusEl.textContent = message || (items && !items.length ? "Ничего не найдено" : "");
    (items || []).forEach(item => tbody.appendChild(buildRow(item, item.category)));
  }

  // Проверенные РД из Tezaurus: один запрос на открытие, поиск по реестру их не трогает.
  function renderRecommended(items, message) {
    recBody.innerHTML = "";
    recTable.classList.toggle("d-none", !items || !items.length);
    recStatus.textContent = message || "";
    (items || []).forEach(item => recBody.appendChild(
      buildRow(item, item.description, "rd-recommended-desc" + (item.type_match ? " fw-semibold" : ""))));
  }

  function loadRecommended() {
    if (!tnved || !country) return renderRecommended(null, "Укажите в карточке ТНВЭД и страну - подберём проверенные РД");
    const current = ++openId;
    renderRecommended(null, "Подбираем…");
    fetch(`${recommendedUrl}?${new URLSearchParams({tnved, country, type: productType})}`,
          {headers: {"X-Requested-With": "XMLHttpRequest"}})
      .then(r => r.json())
      .then(data => {
        if (current !== openId) return;
        if (data.status !== "success") throw new Error(data.message || "recommended failed");
        renderRecommended(data.items, data.items.length ? "" : `Под ТНВЭД ${tnved} и страну ${country} проверенных РД нет`);
      })
      .catch(() => {
        if (current === openId) renderRecommended(null, "Не удалось подобрать проверенные РД");
      });
  }

  function scope() {
    return `ТНВЭД ${tnved}` + (country ? ` и страной ${country}` : "");
  }

  function request(params) {
    if (controller) controller.abort();  // ответ на устаревший запрос не должен перерисовать список
    controller = new AbortController();
    statusEl.textContent = "Поиск…";
    return fetch(`${searchUrl}?${new URLSearchParams(params)}`, {
      signal: controller.signal,
      headers: {"X-Requested-With": "XMLHttpRequest"},
    })
      .then(r => r.json())
      .then(data => {
        if (data.status !== "success") throw new Error(data.message || "search failed");
        return data;
      });
  }

  function onError(err) {
    if (err.name === "AbortError") return;
    lastKey = null;
    render(null, "Не удалось выполнить поиск, попробуйте ещё раз");
  }

  // Ключ короче 5 символов: показываем РД с ТНВЭД карточки, отфильтрованные по введённому.
  function drawPreload() {
    const key = rdKey(input.value);
    if (!preload.items.length) return render(null, `С ${scope()} в реестре РД нет - найдите РД по номеру`);
    const items = preload.items.filter(item => item.search_key.includes(key));
    const more = preload.has_more ? `, показаны первые ${preload.items.length}` : "";
    render(items, items.length
      ? `РД с ${scope()}${more}`
      : `Среди РД с ${scope()} такого нет - от ${MIN_LEN} символов ищем по всему реестру`);
  }

  function showPreload(key) {
    if (!tnved) return render(null, key ? `Введите ещё ${MIN_LEN - key.length} симв.` : `Поиск с ${MIN_LEN} символов номера`);
    if (preload) return drawPreload();
    request({tnved, country})
      .then(data => {
        preload = data;
        if (rdKey(input.value).length < MIN_LEN) drawPreload();
      })
      .catch(onError);
  }

  function lookup() {
    const key = rdKey(input.value);
    if (key === lastKey) return;
    lastKey = key;
    if (controller) controller.abort();

    if (key.length < MIN_LEN) return showPreload(key);
    if (deadKey && key.includes(deadKey)) return render([]);
    if (fullSet && key.includes(fullSet.key)) {
      return render(fullSet.items.filter(item => item.search_key.includes(key)));
    }

    // поиск по всему реестру страны карточки, РД с ТНВЭД карточки сервер ставит первыми
    request({q: key, tnved, country})
      .then(data => {
        if (!data.items.length) deadKey = key;
        else if (!data.has_more) fullSet = {key, items: data.items};
        render(data.items, data.has_more ? `Показаны первые ${data.items.length} — уточните запрос` : "");
      })
      .catch(onError);
  }

  function setRdInput(id, value) {
    // input-событие нужно обработчикам rd.html (ручной ввод даты, кнопки календаря)
    $("#" + id).val(value).trigger("input");
  }

  function enableRd() {
    const rdSwitch = document.getElementById("has-rd-switch");
    if (rdSwitch && !rdSwitch.checked) {
      rdSwitch.checked = true;
      rdSwitch.dispatchEvent(new Event("change"));  // показывает блок РД и переключает список стран
    }
  }

  // РД нет в реестре: подставляем только введённый номер, тип и даты оператор заполнит сам
  function applyTyped() {
    const name = input.value.replace(/№/g, "").trim();
    if (!name) return input.focus();  // кнопка всегда активна, как основные кнопки карточки
    enableRd();
    setRdInput("rd_name", name);
    bootstrap.Modal.getOrCreateInstance(modal).hide();
  }

  function applyRd(item) {
    enableRd();
    $("#rd_type").val(item.rd_type).trigger("change");  // select2
    setRdInput("rd_name", item.rd_name);
    setRdInput("rd_date", item.rd_date);
    setRdInput("rd_date_to", item.rd_date_to);
    if (typeof window.pcNormalizeRdDates === "function") window.pcNormalizeRdDates();

    bootstrap.Modal.getOrCreateInstance(modal).hide();
  }

  applyBtn.addEventListener("click", applyTyped);

  input.addEventListener("input", () => {
    clearTimeout(timer);
    timer = setTimeout(lookup, DEBOUNCE_MS);
  });

  modal.addEventListener("show.bs.modal", () => {
    // реестр мог пополниться, а ТНВЭД карточки - измениться, пока страница открыта
    const tnvedInput = document.getElementById("tnved_code");
    tnved = tnvedInput ? tnvedInput.value.trim() : "";
    country = ($("#country").val() || "").trim();
    productType = ($("#type").val() || "").trim();
    loadRecommended();
    preload = null;
    deadKey = null;
    fullSet = null;
    lastKey = null;
  });

  modal.addEventListener("shown.bs.modal", () => {
    input.focus();
    lookup();
  });
})();
