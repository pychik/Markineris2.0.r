window.pc_check_rd_docs = function () {
  const sw = document.getElementById("has-rd-switch");
  const hasRd = !!(sw && sw.checked);
  if (!hasRd) return [];

  if (typeof window.pcNormalizeRdDates === "function") {
    window.pcNormalizeRdDates();
  }

  const rdType = (document.getElementById("rd_type")?.value || "").trim();
  const rdName = (document.getElementById("rd_name")?.value || "").trim();
  const rdDate = (document.getElementById("rd_date")?.value || "").trim();
  const rdDateTo = (document.getElementById("rd_date_to")?.value || "").trim();

  const errs = [];
  if (!rdType) errs.push("РД: выберите тип документа");
  if (!rdName) errs.push("РД: заполните код/название документа");
  if (!rdDate) errs.push("РД: выберите дату 'От'");
  if (!rdDateTo) errs.push("РД: выберите дату 'До'");
  return errs;
};


function product_card_submit(category = null) {

    // Читаем конфиг из шаблона
    const configEl = document.getElementById("pc-config");
    if (!configEl) {
        console.error("pc-config not found");
        return;
    }

    const SAVE_CARD_URL = configEl.dataset.saveCardUrl;   // backend POST URL
    const UPDATE_CARD_URL = configEl.dataset.updateCardUrl;
    const CARDS_URL     = configEl.dataset.cardsUrl;      // /cards
    const DEFAULT_CAT   = configEl.dataset.currentCategory || "";
    const CRM_REDIRECT_URL = configEl.dataset.crmRedirectUrl;
    const CRM_FLAG = (configEl.dataset.crmFlag === "1");

    const editMode = (configEl.dataset.editMode === "1");
    const cardId   = (configEl.dataset.cardId || "").trim();

    // если категория не передана — берём из конфигурации
    const cat = category || DEFAULT_CAT;

    const form = document.getElementById("pc-create-form");
    if (!form) {
        console.error("pc-create-form not found");
        return;
    }

    const formData = new FormData(form);
    formData.append("category", cat);

    // Передаём тумблер на бэк (чтобы validate_rd_block работал от has_rd)
    const hasRdSwitch = document.getElementById("has-rd-switch");
    formData.append("has_rd", (hasRdSwitch && hasRdSwitch.checked) ? "1" : "0");

    if (editMode) {
        if (!cardId) {
            console.error("edit_mode=1 but card_id missing");
            if (typeof make_message === "function") make_message("Не найден ID карточки для обновления", "error");
            return;
        }
        if (!formData.has("card_id")) formData.append("card_id", cardId);
    }

    let errors = [];

    // ===== 1) TNVED =====
    let tnvedOk = true;
    if (typeof check_tnved === "function") {
        tnvedOk = !!check_tnved("submit");
        if (!tnvedOk) {
            // В старых функциях отдельного текста не было, но оставим общее сообщение
            errors.push("Некорректный ТНВЭД");
        }
    }

    // ===== 2) RD =====
    if (typeof window.pc_check_rd_docs === "function") {
      const rdErrors = window.pc_check_rd_docs(); // массив строк
      if (Array.isArray(rdErrors) && rdErrors.length > 0) {
        errors.push(...rdErrors);
      }
    } else {
      console.warn("pc_check_rd_docs not found");
    }

    // ===== 3) content / состав =====
    const contentInput = document.getElementById("content");
    let contentOk = true;
    if (contentInput) {
        if (contentInput.value.trim().length < 3) {
            contentOk = false;
        }
    }

    // ===== 4) размеры по категориям =====
    let sizesOk = true;
    if (cat === "clothes" && typeof clothes_check_sizes_quantity_valid === "function") {
        sizesOk = !!clothes_check_sizes_quantity_valid();
    }
    if (cat === "linen" && typeof linen_check_sizes_quantity_valid === "function") {
        sizesOk = !!linen_check_sizes_quantity_valid();
    }
    if (cat === "shoes" && typeof shoe_check_sizes_quantity_valid === "function") {
        sizesOk = !!shoe_check_sizes_quantity_valid();
    }
    if (cat === "socks" && typeof socks_check_sizes_quantity_valid === "function") {
        sizesOk = !!socks_check_sizes_quantity_valid();
    }

    // ===== 5) HTML5-валидность формы =====
    const nativeValid = (typeof form.checkValidity === "function")
        ? form.checkValidity()
        : true; // если нет checkValidity, считаем валидной

    // Если форма не валидна по HTML5 — стандартно подсветим браузерные ошибки
    // (в старом коде этого не было, но это удобный бонус)
    if (!nativeValid && typeof form.reportValidity === "function") {
        form.reportValidity();
    }

    // ===== 6) Сбор ошибок по аналогии со старыми функциями =====
    // Если есть jQuery и check_valid — обойдём все инпуты и соберём подписи label'ов
    if (typeof check_valid === "function" && (window.$ || window.jQuery)) {
        const $ = window.$ || window.jQuery;
        const hasRd = !!(hasRdSwitch && hasRdSwitch.checked);

        const allInputs = $('#pc-create-form input, #pc-create-form select');
        const SKIP_IDS = new Set(["rd_type", "rd_name", "rd_date", "rd_date_to", "tnved_code"]);
        allInputs.each(function () {
            const el = this;
            if (SKIP_IDS.has(el.id)) return;
            // пропускаем РД поля, если тумблер выключен

            const error_field_id = check_valid(el);
            if (error_field_id !== true) {
                const label_text = $(`#${error_field_id}`)
                    .closest(".form-group")
                    .find("label")
                    .text();
                if (label_text) {
                    errors.push(label_text);
                }
            }
        });
    }

    // Категорийные сообщения (точно такие же по смыслу, как в старом коде)
    if (!contentOk) {
        if (cat === "clothes") {
            errors.push("Блок состав одежды! Заполните!");
        } else if (cat === "socks") {
            errors.push("Блок состав чулочно-носочных изделий! Заполните!");
        } else {
            // универсальное сообщение для остальных категорий
            errors.push("Состав изделия должен быть заполнен!");
        }
    }

    if (!sizesOk) {
        if (cat === "clothes") {
            errors.push("Размер одежды. Добавьте хотя бы один");
        } else if (cat === "linen") {
            errors.push("Размер белья. Добавьте хотя бы один");
        } else if (cat === "shoes") {
            errors.push("Размер обуви. Добавьте хотя бы один");
        } else if (cat === "socks") {
            errors.push("Размер чулочно-носочных изделий. Добавьте хотя бы один");
        }
    }

    // Для parfum: отдельной проверки размеров нет, только РД
    if (cat === "parfum") {
        // здесь уже добавлено сообщение про РД выше (rdOk)
        // при необходимости можно добавить ещё категорийные проверки
    }

    // Также учтём общий случай — если форма невалидна и нет jQuery,
    // но нам нужно что-то сообщить пользователю:
    if (!nativeValid && errors.length === 0) {
        errors.push("Проверьте корректность заполнения формы");
    }

    // ===== 7) Если есть ошибки — показываем и выходим =====
    if (errors.length > 0) {
        if (typeof show_form_errors === "function") {
            // Уникализируем, чтобы не сыпать дубликаты
            const uniq = Array.from(new Set(errors));
            show_form_errors(uniq);
        }
        if (window.$) {
            $("#form_errorModal").modal("show");
        }
        return;
    }
    loadingCircle();
    // ===== 8) Если всё ок — отправляем форму на бэкенд POST'ом =====
    const endpointUrl = editMode ? UPDATE_CARD_URL : SAVE_CARD_URL;
    fetch(endpointUrl, {
        method: "POST",
        body: formData
    })
        .then(r => r.json())
        .then(data => {
            if (data.status === "success") {

                if (typeof make_message === "function") {
                    make_message(data.message || "Карточка успешно создана", "success");
                }

                // Редирект на список карточек
                if (CRM_FLAG) {

                    // 1️⃣ Обновить CRM вкладку
                    if (window.opener) {
                        window.opener.location.reload();
                    }

                    // 2️⃣ Пытаемся закрыть текущую
                    setTimeout(() => {
                        window.close();
                    }, 800);

                    // 3️⃣ Fallback — если браузер не дал закрыть
                    setTimeout(() => {
                        window.location.href = CRM_REDIRECT_URL;
                    }, 1000);

                } else {

                    // обычный редирект пользователя
                    const url = new URL(CARDS_URL, window.location.origin);
                    url.searchParams.set("category", cat);

                    setTimeout(() => {
                        window.location.href = url.toString();
                    }, 900);
                }


            } else {
                if (typeof make_message === "function") {
                    make_message(data.message || "Ошибка сохранения", "error");
                }
            }
        })
        .catch(err => {
            console.error(err);
            if (typeof make_message === "function") {
                make_message("Ошибка сервера", "error");
            }
        })
        .finally(() => close_Loading_circle());
}

