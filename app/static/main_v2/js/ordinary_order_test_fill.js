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
