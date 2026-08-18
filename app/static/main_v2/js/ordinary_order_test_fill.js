const ORDINARY_ORDER_TEST_COMPANY = {
    inn: "7807256966",
    companyType: "НАО",
    companyName: "ЭВОЛЮЦИЯ ПИТАНИЯ",
    edoType: "ЭДО-ЛАЙТ",
    markType: "11 макет 58*40",
};

function ordinaryOrderSetValue(id, value) {
    const element = document.getElementById(id);
    if (!element) return;
    element.value = value;
    element.dispatchEvent(new Event("input", { bubbles: true }));
    element.dispatchEvent(new Event("change", { bubbles: true }));
}

function ordinaryOrderSetSelect(id, preferredValues = []) {
    const element = document.getElementById(id);
    if (!element) return "";

    const options = Array.from(element.options || []).filter((option) => option.value);
    if (!options.length) return "";

    const preferred = preferredValues.find((value) => options.some((option) => option.value === value));
    element.value = preferred || options[0].value;
    element.dispatchEvent(new Event("change", { bubbles: true }));
    return element.value;
}

function ordinaryOrderSetCheckbox(id, checked) {
    const element = document.getElementById(id);
    if (!element) return;
    if (element.checked !== checked) {
        element.checked = checked;
        element.dispatchEvent(new Event("change", { bubbles: true }));
    }
}

function ordinaryOrderGetRowCount() {
    const element = document.getElementById("orders_row_count");
    if (!element) return 0;

    const raw = String(element.textContent || "").trim();
    const parsed = parseInt(raw, 10);
    return Number.isFinite(parsed) ? parsed : 0;
}

function ordinaryOrderShouldPrefillMeta() {
    const rowCount = ordinaryOrderGetRowCount();
    if (rowCount !== 0) return false;

    const companyName = (document.getElementById("company_name")?.value || "").trim();
    const companyType = (document.getElementById("company_type")?.value || "").trim();
    const companyInn = (document.getElementById("company_idn")?.value || "").trim();
    const markType = (document.getElementById("mark_type_hidden")?.value || "").trim();

    return !companyName && !companyType && !companyInn && !markType;
}

function ordinaryOrderPrefillMetaIfNeeded() {
    if (!ordinaryOrderShouldPrefillMeta()) return false;

    ordinaryOrderSetValue("organization", ORDINARY_ORDER_TEST_COMPANY.inn);
    ordinaryOrderSetValue("company_idn", ORDINARY_ORDER_TEST_COMPANY.inn);
    ordinaryOrderSetValue("company_type", ORDINARY_ORDER_TEST_COMPANY.companyType);
    ordinaryOrderSetValue("company_name", ORDINARY_ORDER_TEST_COMPANY.companyName);
    ordinaryOrderSetSelect("edo_type", [ORDINARY_ORDER_TEST_COMPANY.edoType]);
    ordinaryOrderSetValue("mark_type", ORDINARY_ORDER_TEST_COMPANY.markType);
    ordinaryOrderSetValue("mark_type_hidden", ORDINARY_ORDER_TEST_COMPANY.markType);
    return true;
}

function ordinaryOrderRevealTextField(toggleId, fieldId) {
    const toggle = document.getElementById(toggleId);
    if (!toggle) return;
    if (toggle.checked && typeof toggleArticleTrademarkField === "function") {
        toggle.checked = false;
        toggleArticleTrademarkField(toggle, fieldId);
    }
}

function ordinaryOrderResetRd() {
    ordinaryOrderSetCheckbox("has-rd-switch", false);
    ["rd_type", "rd_name", "rd_date", "rd_date_from", "rd_date_to"].forEach((id) => ordinaryOrderSetValue(id, ""));
}

function ordinaryOrderSetPrice() {
    ordinaryOrderSetValue("article_price", "100");
    ordinaryOrderSetSelect("tax", ["20", "10", "0"]);
}

function ordinaryOrderFormatRuDate(date) {
    const day = String(date.getDate()).padStart(2, "0");
    const month = String(date.getMonth() + 1).padStart(2, "0");
    return `${day}.${month}.${date.getFullYear()}`;
}

function ordinaryOrderDateOneYearFromNow() {
    const date = new Date();
    date.setFullYear(date.getFullYear() + 1);
    return date;
}

function ordinaryOrderAppendWearSize(size, quantity, sizeType) {
    const block = document.getElementById("sizes_quantity");
    if (!block) return;

    block.innerHTML = `
        <div class="important-card__item important-card__size ms-2">
            <div class="d-flex align-items-center g-3">
                <div class="ms-2">
                    <span id="size_info">${size}</span>
                    <span id="size_type_info" style="font-size: 10px">${sizeType || ""}</span>
                </div>
            </div>
            <div class="important-card__val"><span id="quantity_info">${quantity}</span> <span>шт.</span></div>
            <input type="hidden" id="size" name="size" value="${size}">
            <input type="hidden" id="quantity" name="quantity" value="${quantity}">
            <input type="hidden" id="size_type" name="size_type" value="${sizeType || ""}">
        </div>
    `;
}

function ordinaryOrderFillCommonStep2Fields() {
    ordinaryOrderRevealTextField("noTMSwitch", "trademark");
    ordinaryOrderRevealTextField("noArtSwitch", "article");

    ordinaryOrderSetValue("trademark", "AUTOBRAND");
    ordinaryOrderSetValue("article", `AUTO-${Date.now().toString().slice(-6)}`);
    ordinaryOrderSetSelect("color", ["ЧЕРНЫЙ", "БЕЛЫЙ"]);
    ordinaryOrderSetSelect("country", ["Россия", "Китай"]);
    ordinaryOrderSetPrice();
    ordinaryOrderResetRd();
}

function ordinaryOrderWaitFor(condition, timeout = 3000, interval = 50) {
    return new Promise((resolve) => {
        const startedAt = Date.now();
        const timer = window.setInterval(() => {
            if (condition()) {
                window.clearInterval(timer);
                resolve(true);
                return;
            }
            if (Date.now() - startedAt >= timeout) {
                window.clearInterval(timer);
                resolve(false);
            }
        }, interval);
    });
}

async function ordinaryOrderFillClothesStep2(subcategory) {
    ordinaryOrderFillCommonStep2Fields();

    const typeElement = document.getElementById("type");
    if (typeElement) {
        const firstType = ordinaryOrderSetSelect("type");
        if (firstType) {
            await ordinaryOrderWaitFor(() => {
                const gender = document.getElementById("gender");
                return gender && Array.from(gender.options || []).filter((option) => option.value).length > 0;
            });
        }
    }

    ordinaryOrderSetSelect("gender", ["Унисекс", "Без указания пола", "Жен.", "Муж."]);

    ordinaryOrderSetCheckbox("manual_content_checkbox", true);
    ordinaryOrderSetValue("content", "ХЛОПОК 100%");
    ordinaryOrderSetCheckbox("nat_materials_check", false);

    ordinaryOrderAppendWearSize("42", 10, "РОССИЯ");
    if (typeof setClothes === "function") {
        setClothes();
    }
}

function ordinaryOrderFillSocksStep2() {
    ordinaryOrderFillCommonStep2Fields();

    ordinaryOrderSetSelect("type");
    ordinaryOrderSetSelect("gender", ["Унисекс", "Без указания пола", "Жен.", "Муж."]);

    ordinaryOrderSetCheckbox("manual_content_checkbox", true);
    ordinaryOrderSetValue("content", "ХЛОПОК 100%");
    ordinaryOrderSetCheckbox("nat_materials_check", false);

    ordinaryOrderAppendWearSize("42", 10, "РОССИЯ");
    if (typeof setSocks === "function") {
        setSocks();
    }
}

function ordinaryOrderFillShoesStep2() {
    ordinaryOrderFillCommonStep2Fields();

    ordinaryOrderSetSelect("type");
    ordinaryOrderSetSelect("material_top");
    ordinaryOrderSetSelect("material_lining");
    ordinaryOrderSetSelect("material_bottom");
    ordinaryOrderSetSelect("gender", ["Унисекс", "Жен.", "Муж."]);

    ordinaryOrderSetValue("size_order", "36");
    ordinaryOrderSetValue("quantity_order", "10");
    if (typeof addShoeCell === "function") {
        addShoeCell();
    }
}

function ordinaryOrderFillLinenStep2() {
    ordinaryOrderFillCommonStep2Fields();

    ordinaryOrderSetSelect("type");
    ordinaryOrderSetSelect("customer_age");
    ordinaryOrderSetSelect("textile_type");
    ordinaryOrderSetValue("content", "ХЛОПОК 100%");

    ordinaryOrderSetValue("sizeX_order", "50");
    ordinaryOrderSetValue("sizeY_order", "70");
    ordinaryOrderSetSelect("sizeUnitOrder", ["см", "мм"]);
    ordinaryOrderSetValue("quantity_order", "10");
    if (typeof addLinenCell === "function") {
        addLinenCell();
    }
}

function ordinaryOrderFillParfumStep2() {
    ordinaryOrderRevealTextField("noTMSwitch", "trademark");

    ordinaryOrderSetValue("trademark", "AUTOBRAND");
    ordinaryOrderSetValue("volume", "100");
    ordinaryOrderSetSelect("volume_type", ["мл", "л"]);
    ordinaryOrderSetSelect("package_type");
    ordinaryOrderSetSelect("material_package");
    ordinaryOrderSetSelect("type");
    ordinaryOrderSetSelect("country", ["Россия", "Китай"]);
    ordinaryOrderSetPrice();
    ordinaryOrderSetValue("quantity", "10");

    ordinaryOrderResetRd();
}

function ordinaryOrderFillCosmeticsStep2(subcategory) {
    ordinaryOrderRevealTextField("noTMSwitch", "trademark");

    ordinaryOrderSetValue("trademark", "AUTOBRAND");
    ordinaryOrderSetSelect("type");
    ordinaryOrderSetSelect("nominal_quantity_type", ["шт"]);
    ordinaryOrderSetValue("nominal_quantity", "1");
    ordinaryOrderSetSelect("for_children", ["no", "yes"]);
    ordinaryOrderSetSelect("country", ["РОССИЯ", "КИТАЙ"]);
    ordinaryOrderSetSelect("content_type");
    ordinaryOrderSetValue("content", "ВОДА, ГЛИЦЕРИН");
    ordinaryOrderSetSelect("usage_term_type");
    ordinaryOrderSetValue("service_life", "36");
    ordinaryOrderSetValue("sl_date_from", "01.01.2023");
    ordinaryOrderSetValue("sl_date_to", "01.01.2026");
    ordinaryOrderSetValue("quantity", "10");
    ordinaryOrderSetPrice();
    ordinaryOrderResetRd();

    if (subcategory === "cosmetics_toilet_paper") {
        ordinaryOrderSetSelect("layers_characteristic", ["ДВУХСЛОЙНОЕ"]);
    }
}

function ordinaryOrderFillToysStep2(subcategory) {
    ordinaryOrderRevealTextField("noTMSwitch", "trademark");
    ordinaryOrderSetCheckbox("noModelArticleSwitch", false);
    if (typeof toggleToysModelArticleField === "function") {
        toggleToysModelArticleField(document.getElementById("noModelArticleSwitch"));
    }

    ordinaryOrderSetValue("trademark", "AUTOBRAND");
    ordinaryOrderSetSelect("model_article_type", ["Артикул"]);
    ordinaryOrderSetValue("model_article", `TOY-${Date.now().toString().slice(-6)}`);
    const toysTestProfiles = {
        puzzles: {
            type: ["ГОЛОВОЛОМКА"],
            material: ["ДЕРЕВО"],
            content: "ДЕРЕВО",
        },
        competition_cars: {
            type: ["НАБОР ЭЛЕКТРИЧЕСКИХ ГОНОЧНЫХ АВТОМОБИЛЕЙ ДЛЯ СОРЕВНОВАТЕЛЬНЫХ ИГР"],
            material: ["ПЛАСТМАССА"],
            content: "ПЛАСТМАССА",
        },
        sets_kits: {
            type: ["НАБОР ИГРУШЕК"],
            material: ["ПЛАСТМАССА"],
            content: "ПЛАСТМАССА",
        },
        motorized_toys: {
            type: ["ИГРУШКА ТРАНСПОРТНАЯ"],
            drive_type: ["МИКРОЭЛЕКТРОДВИГАТЕЛЬ"],
            material: ["ПЛАСТМАССА"],
            content: "ПЛАСТМАССА",
        },
        animal_creature: {
            type: ["ФИГУРКА"],
            drive_type: ["БЕЗ МЕХАНИЗМА"],
            material: ["ПЛАСТМАССА"],
            content: "ПЛАСТМАССА",
        },
        scale_models_other: {
            tnved: "9503009500",
            type: ["ТРАНСПОРТ ЛЕГКОВОЙ"],
            material: ["ПЛАСТМАССА"],
            content: "ПЛАСТМАССА",
        },
        musical_toy_instruments: {
            tnved: "9503005500",
            type: ["ИГРУШКА МУЗЫКАЛЬНАЯ"],
            drive_type: ["ЭЛЕКТРОННЫЙ"],
            material: ["ПЛАСТМАССА"],
            content: "ПЛАСТМАССА",
        },
        dolls_human_figures: {
            tnved: "9503002100",
            type: ["КУКЛА"],
            drive_type: ["БЕЗ МЕХАНИЗМА"],
            material: ["ПЛАСТМАССА"],
            content: "ПЛАСТМАССА",
        },
        construction_sets: {
            tnved: "9503003500",
            type: ["КОНСТРУКТОР"],
            material: ["ПЛАСТМАССА"],
            content: "ПЛАСТМАССА",
        },
        card_games: {
            tnved: "9504400000",
            type: ["ИГРА КАРТОЧНАЯ"],
            material: ["КАРТОН"],
            content: "КАРТОН",
        },
    };
    const toysTestProfile = toysTestProfiles[subcategory] || {
        type: ["ОДЕЖДА ДЛЯ КУКОЛ"],
        material: ["ПЛАСТМАССА", "ТКАНЬ"],
        content: "ПЛАСТМАССА, ТКАНЬ",
    };

    ordinaryOrderSetSelect("type", toysTestProfile.type);
    if (toysTestProfile.tnved_group) {
        ordinaryOrderSetSelect("tnved_group", toysTestProfile.tnved_group);
    }
    if (toysTestProfile.drive_type) {
        ordinaryOrderSetSelect("drive_type", toysTestProfile.drive_type);
    } else {
        ordinaryOrderSetValue("drive_type", "");
    }
    ordinaryOrderSetSelect("material", toysTestProfile.material);
    ordinaryOrderSetSelect("min_child_age", ["ОТ 3 ЛЕТ"]);
    ordinaryOrderSetSelect("usage_term_type", ["СРОК СЛУЖБЫ"]);
    ordinaryOrderSetValue("content", toysTestProfile.content);
    ordinaryOrderSetSelect("service_life_type", ["мес"]);
    ordinaryOrderSetValue("service_life", "36");
    ordinaryOrderSetValue("sl_date_from", ordinaryOrderFormatRuDate(new Date()));
    ordinaryOrderSetValue("sl_date_to", ordinaryOrderFormatRuDate(ordinaryOrderDateOneYearFromNow()));
    ordinaryOrderSetValue("quantity", "10");
    ordinaryOrderSetPrice();
    ordinaryOrderResetRd();
    ordinaryOrderSetSelect("country", ["РОССИЯ", "КИТАЙ"]);

    const tnved = toysTestProfile.tnved || window.TOYS_DEFAULT_TNVED_CODE || (window.TOYS_ALLOWED_TNVED_CODES || [])[0] || "";
    if (tnved && typeof selectToysTnved === "function") {
        selectToysTnved(tnved);
    } else {
        ordinaryOrderSetValue("tnved_code", tnved);
    }

    const choicesByTnved = window.TOYS_OKPD2_CHOICES_BY_TNVED || {};
    const okpd2Choices = Array.isArray(choicesByTnved[tnved]) ? choicesByTnved[tnved] : [];
    if (okpd2Choices.length && typeof selectToysOkpd2 === "function") {
        selectToysOkpd2(okpd2Choices[0][0], okpd2Choices[0][1]);
    }
}

window.ordinaryOrderTestFillStep2 = async function ordinaryOrderTestFillStep2(button) {
    const category = button?.dataset?.category || "";
    const subcategory = button?.dataset?.subcategory || "";

    if (!category) return;

    const metaPrefilled = ordinaryOrderPrefillMetaIfNeeded();

    if (category === "clothes") {
        await ordinaryOrderFillClothesStep2(subcategory);
    } else if (category === "socks") {
        ordinaryOrderFillSocksStep2();
    } else if (category === "shoes") {
        ordinaryOrderFillShoesStep2();
    } else if (category === "linen") {
        ordinaryOrderFillLinenStep2();
    } else if (category === "parfum") {
        ordinaryOrderFillParfumStep2();
    } else if (category === "cosmetics") {
        ordinaryOrderFillCosmeticsStep2(subcategory);
    } else if (category === "toys") {
        ordinaryOrderFillToysStep2(subcategory);
    }

    if (typeof make_message === "function") {
        make_message(
            metaPrefilled
                ? "Тестовые данные второго шага заполнены, организация и этикетка подставлены для первого товара."
                : "Тестовые данные второго шага заполнены.",
            "success"
        );
    }
};
