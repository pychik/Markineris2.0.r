
const PC_CATEGORY_GROUPS = {
    clothes: {
        mode: "clothes",
        modeClass: "pc-category-tabs--clothes",
        rootCategory: "clothes",
        childCategories: ["socks"],
        tabIds: [
            "pills-clothes-tab",
            "pills-underwear-tab",
            "pills-swimming_accessories-tab",
            "pills-hats-tab",
            "pills-gloves-tab",
            "pills-shawls-tab",
            "pills-socks-tab",
        ],
    },
};

const PC_MAIN_CATEGORY_TAB_IDS = [
    "pills-shoes-tab",
    "pills-clothes-tab",
    "pills-linen-tab",
    "pills-parfum-tab",
    "pills-cosmetics-tab",
    "pills-toys-tab",
];

const PC_CATEGORY_CREATE_LABELS = {
    shoes: "обувь",
    clothes: "одежду",
    linen: "белье",
    parfum: "духи",
    socks: "носки",
};

const PC_CLOTHES_CREATE_LABELS = {
    common: "одежду",
    underwear: "нижнее белье",
    swimming_accessories: "плавательные аксессуары",
    hats: "шляпы",
    gloves: "перчатки",
    shawls: "шали",
};

let pcCategoryTabsMode = "main";

function pc_category_tab_wrapper(tabId) {
    const tab = document.getElementById(tabId);
    if (!tab) return null;
    return tab.closest("[data-pc-category-tile]") || tab.closest("a") || tab;
}

function pc_order_category_tabs(tabIds) {
    const tabs = document.getElementById("pills-tab");
    if (!tabs) return;

    tabIds.forEach(tabId => {
        const wrapper = pc_category_tab_wrapper(tabId);
        if (wrapper) tabs.appendChild(wrapper);
    });
}

function pc_ensure_category_back_tab() {
    const tabs = document.getElementById("pills-tab");
    if (!tabs) return null;

    let back = document.getElementById("pc-category-back");
    if (back) return back.closest("a") || back;

    const wrapper = document.createElement("a");
    wrapper.href = "javascript:void(0)";
    wrapper.className = "pc-category-back d-none";
    wrapper.innerHTML = `
        <li class="nav-link" id="pc-category-back" type="button" role="tab">
            <button class="text-center border-0" type="button">
                <span class="pc-category-back__arrow" aria-hidden="true">&larr;</span>
                <div class="category-item__name text-center">Категории</div>
            </button>
        </li>
    `;
    wrapper.addEventListener("click", function (event) {
        event.preventDefault();
        pc_show_main_category_tabs();
    });

    tabs.appendChild(wrapper);
    return wrapper;
}

function pc_show_main_category_tabs() {
    pc_set_category_tabs_mode("main");
}

function pc_show_category_group(groupMode) {
    pc_set_category_tabs_mode(groupMode);
}

function pc_set_category_tabs_mode(mode) {
    const tabs = document.getElementById("pills-tab");
    const group = Object.values(PC_CATEGORY_GROUPS).find(item => item.mode === mode) || null;

    pcCategoryTabsMode = group ? group.mode : "main";
    if (tabs) {
        tabs.classList.toggle("pc-category-tabs--main", !group);
        Object.values(PC_CATEGORY_GROUPS).forEach(item => {
            tabs.classList.toggle(item.modeClass, Boolean(group && item.mode === group.mode));
        });
    }

    const back = pc_ensure_category_back_tab();
    if (back) back.classList.toggle("d-none", !group);

    pc_order_category_tabs(group ? group.tabIds : PC_MAIN_CATEGORY_TAB_IDS);
    if (tabs && back && group) tabs.appendChild(back);

}

function pc_get_category_group_for_click(category) {
    return Object.values(PC_CATEGORY_GROUPS).find(group => {
        return category === group.rootCategory || group.childCategories.includes(category);
    }) || null;
}

function pc_get_category_group_for_initial(category, subcategory) {
    return Object.values(PC_CATEGORY_GROUPS).find(group => {
        const isRootSubcategory = category === group.rootCategory && Boolean(subcategory);
        return isRootSubcategory || group.childCategories.includes(category);
    }) || null;
}

function pc_init_category_tabs_mode(category, subcategory) {
    const group = pc_get_category_group_for_initial(category, subcategory);
    pc_set_category_tabs_mode(group ? group.mode : "main");
}

// обновляет активные табы категорий/подкатегорий
function pc_update_category(category, subcategory) {
    // снять active со всех табов
    document.querySelectorAll('.nav-pills--cat .nav-link').forEach(el => {
        el.classList.remove('active');
    });

    // основная категория
    const mainMap = {
        shoes:   'pills-shoes-tab',
        clothes: 'pills-clothes-tab',
        linen:   'pills-linen-tab',
        parfum:  'pills-parfum-tab',
        socks:   'pills-socks-tab',
    };

    const mainId = mainMap[category];
    if (mainId) {
        const mainEl = document.getElementById(mainId);
        if (category === 'clothes' && subcategory) {

            const subId = `pills-${subcategory}-tab`; // underwear / swimming_accessories / hats / gloves / shawls
            const subEl = document.getElementById(subId);
            if (subEl) subEl.classList.add('active');
        return}
        if (mainEl) mainEl.classList.add('active');
    }

    // подкатегории одежды

}


document.addEventListener("DOMContentLoaded", function () {
    const config = document.getElementById("pc-config");
    if (!config) {
        console.error("pc-config not found");
        return;
    }

    const tableWrapper = document.getElementById("pc-table-wrapper");
    if (!tableWrapper) {
        console.error("pc-table-wrapper not found");
        return;
    }

    const form = document.getElementById("pc-search-form");
    if (!form) {
        console.error("pc-search-form not found");
        return;
    }

    const CARDS_TABLE_URL   = config.dataset.cardsTableUrl;
    let   currentCategory   = config.dataset.currentCategory;
    let   currentSubcategory = config.dataset.currentSubcategory || "";
    const csrfToken         = config.dataset.csrf;
    const NEW_PRODUCT_CARD_URL  = config.dataset.newCardUrl;
    const createCurrentBtn = document.getElementById("pc-create-current-category");
    const createCurrentLabel = document.getElementById("pc-create-current-category-label");
    const createdCardsCount = document.getElementById("pc-created-cards-count");

    const searchInput  = form.querySelector('input[name="article_query"]');
    const catInput     = form.querySelector('input[name="category"]');
    let   subcatInput  = form.querySelector('input[name="subcategory"]');

    // если hidden для subcategory нет – создаём
    if (!subcatInput) {
        subcatInput = document.createElement('input');
        subcatInput.type = 'hidden';
        subcatInput.name = 'subcategory';
        form.appendChild(subcatInput);
    }

    function getCurrentCreateTitle() {
        if (currentCategory === "clothes") {
            return PC_CLOTHES_CREATE_LABELS[currentSubcategory || "common"] || PC_CATEGORY_CREATE_LABELS.clothes;
        }
        return PC_CATEGORY_CREATE_LABELS[currentCategory] || "товар";
    }

    function buildCurrentCreateUrl() {
        const params = new URLSearchParams();
        params.set("category", currentCategory || "shoes");
        if (currentCategory === "clothes" && currentSubcategory && currentSubcategory !== "common") {
            params.set("subcategory", currentSubcategory);
        }
        return NEW_PRODUCT_CARD_URL + "?" + params.toString();
    }

    function updateCreateCurrentButton() {
        if (!createCurrentBtn || !createCurrentLabel) return;
        createCurrentLabel.textContent = `Создать ${getCurrentCreateTitle()}`;
    }

    window.pcUpdateCreatedCardsCount = function (count) {
        if (!createdCardsCount) return;
        const value = Number.isFinite(Number(count)) ? Number(count) : 0;
        createdCardsCount.textContent = String(value);
        config.dataset.createdCardsCount = String(value);
    };

    if (createCurrentBtn) {
        createCurrentBtn.addEventListener("click", function () {
            if (!NEW_PRODUCT_CARD_URL) {
                make_message("Не удалось определить адрес создания карточки", "error");
                return;
            }
            window.location.href = buildCurrentCreateUrl();
        });
    }

    tableWrapper.addEventListener("click", function (e) {
        const btn = e.target.closest("[data-pc-action]");
        if (!btn) return;

        const action = btn.dataset.pcAction;
        const cardId = btn.dataset.cardId;

        if (!cardId) return;

        switch (action) {
            case "view":
                handleCardView(btn, cardId);
                break;
            case "copy":
                handleCardCopy(cardId);
                break;
            case "edit":
                handleCardEdit(btn, cardId);
                break;
            case "delete":
                handleCardDelete(btn, cardId);
                break;
            case "show-reject-reason":
                handleRejectReason(btn);
                break;
        }
    });

    function handleRejectReason(btn) {
        const textEl = document.getElementById("pcRejectReasonText");
        const modalEl = document.getElementById("pcRejectReasonModal");
        if (!textEl || !modalEl || !window.bootstrap?.Modal) {
            console.warn("Reject reason modal not available");
            return;
        }

        const reason = (btn.dataset.rejectReason || "").trim();
        textEl.textContent = reason || "Причина отклонения не указана.";

        const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
        modal.show();
    }

    async function handleCardView(btn) {
        if (!btn) return;

        const cardId = btn.dataset.cardId;
        let viewUrl = btn.dataset.viewUrl || "";

        // Если data-view-url нет, пробуем собрать URL из глобального шаблона
        if (!viewUrl && typeof PC_CARD_VIEW_URL_TEMPLATE !== "undefined" && cardId) {
            // например, если шаблон "/user/product-cards/cards/__ID__/view"
            viewUrl = PC_CARD_VIEW_URL_TEMPLATE.replace("__ID__", cardId);
        }

        if (!viewUrl) {
            console.warn("handleCardView: viewUrl не задан и шаблон недоступен");
            make_message("Не удалось определить адрес просмотра карточки", "error");
            return;
        }
        loadingCircle();
        try {
            const response = await fetch(viewUrl, {
                headers: { "X-Requested-With": "XMLHttpRequest" }
            });

            if (!response.ok) {
                throw new Error("HTTP " + response.status);
            }

            const data = await response.json();

            if (data.status === "success" && data.html) {
                const body = document.getElementById("pcCardViewModalBody");
                const modalEl = document.getElementById("pcCardViewModal");

                if (!body || !modalEl) {
                    console.error("Не найдены элементы модалки pcCardViewModal / pcCardViewModalBody");
                    make_message("Ошибка отображения модального окна", "error");
                    return;
                }

                body.innerHTML = data.html;

                // Bootstrap 5
                const modal = new bootstrap.Modal(modalEl);
                modal.show();
            } else {
                make_message(data.message || "Не удалось загрузить карточку", "error");
            }
        } catch (err) {
            console.error("handleCardView error:", err);
            make_message("Ошибка при загрузке карточки", "error");
        }
        close_Loading_circle();
    }

    // --- Копировать: создаём новую карточку, заполнив форму данными старой ---
    function handleCardCopy(cardId) {
        // Логика «На фронте, без автосохранения»:
        // просто перенаправляем на страницу создания с параметром copy_from
        const baseUrl = config.dataset.newCardUrl; // data-new-card-url="..."
        if (!baseUrl) {
            console.warn("NEW_PRODUCT_CARD_URL не задан");
            return;
        }
        const url = new URL(baseUrl, window.location.origin);
        // передаём текущую категорию и id карточки для копии
        url.searchParams.set("category", currentCategory);
        if (currentSubcategory) {
            url.searchParams.set("subcategory", currentSubcategory);
        }
        url.searchParams.set("copy_from", cardId);

        window.location.href = url.toString();
    }

    // --- Изменить: простое редактирование ---
    function handleCardEdit(btn, cardId) {
        const editUrl = btn.dataset.editUrl;
        if (!editUrl) {
            console.warn("editUrl не задан");
            return;
        }
        window.location.href = editUrl;
    }

    // --- Удалить: подтверждение + запрос ---
    async function handleCardDelete(btn) {
        const deleteUrl = btn.dataset.deleteUrl;
        if (!deleteUrl) {
            console.warn("deleteUrl не задан");
            return;
        }

        if (!confirm("Удалить карточку товара? Это действие нельзя отменить.")) {
            return;
        }

        const originalDisabled = btn.disabled;
        const originalText = btn.innerHTML;

        // блокируем кнопку, показываем процесс
        btn.disabled = true;
        btn.innerHTML = "Удаление...";

        try {
            const response = await fetch(deleteUrl, {
                method: "POST", // или "DELETE", если бэкенд поддерживает
                headers: {
                    "X-Requested-With": "XMLHttpRequest",
                    "X-CSRFToken": config.dataset.csrf || "",
                },
            });

            let data = {};
            try {
                data = await response.json();
            } catch (e) {
                // если бэкенд вернул не JSON
                console.warn("Не удалось распарсить JSON ответа", e);
            }

            const status = data.status;
            const message = data.message;

            if (!response.ok || status !== "success") {
                // можно более детализировать текст в зависимости от response.status
                const errorText =
                    message ||
                    (response.status === 404
                        ? "Карточка не найдена (возможно уже удалена)"
                        : "Ошибка при удалении карточки");
                make_message(errorText, "error");
                return;
            }

            make_message(message || "Карточка удалена", "success");
            loadTable(1);

        } catch (err) {
            console.error(err);
            make_message("Ошибка сервера при удалении", "error");
        } finally {
            // возвращаем кнопке исходное состояние
            btn.disabled = originalDisabled;
            btn.innerHTML = originalText;
        }
    }

function loadTable(page = 1) {
    const params = new URLSearchParams();
    params.append("csrf_token", csrfToken);
    params.append("category", currentCategory);
    params.append("subcategory", currentSubcategory);
    params.append("page", String(page));
    params.append("article_query", searchInput.value.trim());
    loadingCircle();
    fetch(CARDS_TABLE_URL, {
        method: "POST",
        headers: {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"
        },
        body: params.toString()
    })
    .then(r => r.json())
    .then(data => {
        if (data.status === "success") {
            if (data.html) {
                tableWrapper.innerHTML = data.html;
                pc_update_category(currentCategory, currentSubcategory);
            }
            if (data.message) {
                make_message(data.message, "success");
            }
        } else if (data.status === "error") {
            make_message(data.message || "Ошибка сервера", "error");
        } else {
            make_message("Неизвестный ответ сервера", "error");
        }
    })
    .catch(err => {
        console.error(err);
        make_message("Ошибка сети или сервера", "error");
    })
    .finally(() => close_Loading_circle());
}



    // сабмит поиска
    form.addEventListener("submit", function (e) {
        e.preventDefault();
        loadTable(1);
    });

    const clearBtn = document.getElementById("pc-btn-clear");

    // --- ENTER → выполнить поиск ---
    searchInput.addEventListener("keydown", function (e) {
        if (e.key === "Enter") {
            e.preventDefault();
            form.dispatchEvent(new Event("submit"));
        }
    });

    // --- ESC → очистить поле и выполнить очистку таблицы ---
    searchInput.addEventListener("keydown", function (e) {
        if (e.key === "Escape") {
            e.preventDefault();
            searchInput.value = "";
            loadTable(1);
        }
    });

    // --- Кнопка очистить ---
    clearBtn.addEventListener("click", function () {
        searchInput.value = "";
        loadTable(1);
    });

    // Пагинация (делегирование)
    tableWrapper.addEventListener("click", function (e) {
        const link = e.target.closest("[data-pc-page]");
        if (!link) return;
        e.preventDefault();
        const page = parseInt(link.dataset.pcPage, 10);
        loadTable(page);
    });

    // 🔥 НОВАЯ ЛОГИКА ВМЕСТО СТАРОГО get_category_history
    // Сигнатуру оставляем ту же, чтобы не трогать разметку:
    // href="javascript:get_category_history('...', 'clothes', 'underwear')"
    window.get_category_product_cards = function (_url, category, subcategory) {
        const group = pc_get_category_group_for_click(category);
        if (group) {
            pc_show_category_group(group.mode);
        } else if (pcCategoryTabsMode !== "main") {
            pc_show_main_category_tabs();
        }

        // обновляем текущие значения
        currentCategory    = category;
        currentSubcategory = subcategory || "";

        // обновляем hidden поля формы
        if (catInput)   catInput.value   = currentCategory;
        if (subcatInput) subcatInput.value = currentSubcategory;

        // очищаем поиск по артикулу
        if (searchInput) {
            searchInput.value = "";
        }

        // обновляем URL (чтобы можно было шарить/рефрешить)
        try {
            const url = new URL(window.location.href);
            url.searchParams.set("category", currentCategory);
            if (currentSubcategory) {
                url.searchParams.set("subcategory", currentSubcategory);
            } else {
                url.searchParams.delete("subcategory");
            }
            url.searchParams.delete("article_query");
            window.history.replaceState({}, "", url.toString());
        } catch (e) {
            console.warn("Не удалось обновить URL:", e);
        }

        // визуально переключаем активный таб
        pc_update_category(category, subcategory);
        updateCreateCurrentButton();

        // перезагружаем таблицу по новой категории
        loadTable(1);
    };
    const categorySelect   = document.getElementById("pc-create-category");
    const subcatWrapper    = document.getElementById("pc-create-subcat-wrapper");
    const subcategorySelect = document.getElementById("pc-create-subcategory");
    const createContinueBtn = document.getElementById("pc-create-continue");

    if (categorySelect) {
        // показать/скрыть подкатегории
        categorySelect.addEventListener("change", function () {
            if (this.value === "clothes") {
                subcatWrapper.classList.remove("d-none");
            } else {
                subcatWrapper.classList.add("d-none");
            }
        });
    }

    if (createContinueBtn) {
        createContinueBtn.addEventListener("click", function () {
            const cat = categorySelect.value;

            if (!cat) {
                make_message("Выберите категорию товара", "error");
                return;
            }

            let subcat = "";
            if (cat === "clothes" && subcategorySelect && !subcatWrapper.classList.contains("d-none")) {
                subcat = subcategorySelect.value || "";
            }

            const params = new URLSearchParams();
            params.set("category", cat);
            if (subcat && subcat !== "common") {
                params.set("subcategory", subcat);
            }

            const targetUrl = NEW_PRODUCT_CARD_URL + "?" + params.toString();
            window.location.href = targetUrl;
        });
    }
    pc_init_category_tabs_mode(currentCategory, currentSubcategory);
    updateCreateCurrentButton();
    window.pcUpdateCreatedCardsCount(config.dataset.createdCardsCount);

    // первый старт
    loadTable(1);
});


// document.addEventListener("DOMContentLoaded", function () {
//     const configEl = document.getElementById("pc-config");
//     if (!configEl) {
//         console.error("pc-config not found");
//         return;
//     }
//
//     const SAVE_CARD_URL = configEl.dataset.saveCardUrl;   // /save_product_card
//     const CARDS_URL     = configEl.dataset.cardsUrl;      // /cards
//     const DEFAULT_CAT   = configEl.dataset.currentCategory || "";
//
//     // Делаем функцию глобальной, чтобы вызывать из onClick
//     window.product_card_submit = function (category) {
//         const form = document.getElementById("form_process_main");
//         if (!form) {
//             console.error("form_process_main not found");
//             return;
//         }
//
//         // если category не передали явно — берём из конфига
//         const cat = category || DEFAULT_CAT;
//
//         const formData = new FormData(form);
//         formData.append("category", cat);
//
//         let errors = [];
//
//         // 1) TNVED
//         if (typeof check_tnved === "function" && !check_tnved("submit")) {
//             errors.push("Некорректный ТНВЭД");
//         }
//
//         // 2) РД
//         if (typeof check_rd_docs === "function" && !check_rd_docs()) {
//             errors.push("Разрешительная документация заполнена неверно");
//         }
//
//         // 3) content / состав
//         const contentInput = document.getElementById("content");
//         if (contentInput && contentInput.value.trim().length < 3) {
//             errors.push("Состав изделия должен быть заполнен!");
//         }
//
//         // 4) размеры только для одежды
//         if (cat === "clothes" && typeof clothes_check_sizes_quantity_valid === "function") {
//             if (!clothes_check_sizes_quantity_valid()) {
//                 errors.push("Добавьте хотя бы один размер одежды");
//             }
//         }
//
//         // 5) HTML5-валидность
//         if (!form.checkValidity()) {
//             form.reportValidity();
//             return;
//         }
//
//         if (errors.length > 0) {
//             if (typeof show_form_errors === "function") {
//                 show_form_errors(errors);
//             }
//             if (window.$) {
//                 $("#form_errorModal").modal("show");
//             }
//             return;
//         }
//
//         // отправка на бек
//         fetch(SAVE_CARD_URL, {
//             method: "POST",
//             body: formData
//         })
//             .then(r => r.json())
//             .then(data => {
//                 if (data.status === "success") {
//                     // просто сообщение и переход к списку карточек
//                     if (typeof make_message === "function") {
//                         make_message(data.message || "Карточка сохранена", "success");
//                     }
//
//                     const url = new URL(CARDS_URL, window.location.origin);
//                     url.searchParams.set("category", cat);
//                     // subcategory не тащим – ты как раз этого не хочешь
//                     window.location.href = url.toString();
//                 } else {
//                     if (typeof make_message === "function") {
//                         make_message(data.message || "Ошибка сохранения", "error");
//                     }
//                 }
//             })
//             .catch(err => {
//                 console.error(err);
//                 if (typeof make_message === "function") {
//                     make_message("Ошибка сервера", "error");
//                 }
//             });
//     };
// });

document.addEventListener('shown.bs.offcanvas', function () {
document.documentElement.classList.add('offcanvas-open');
});

document.addEventListener('hidden.bs.offcanvas', function () {
document.documentElement.classList.remove('offcanvas-open');
});
