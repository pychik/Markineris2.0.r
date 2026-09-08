function processingCompaniesEscapeHtml(value) {
    return String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function renderProcessingCompaniesResult(payload) {
    const requestPayload = payload.request || {};
    const responsePayload = payload.response || {};
    const company = responsePayload.company || {};
    const matchedText = responsePayload.matched === true ? "Да" : "Нет";
    const responseText = processingCompaniesEscapeHtml(JSON.stringify(responsePayload, null, 2));

    return `
        <h3 class="h5 mb-3">Результат</h3>
        <div class="mb-3">
            <div><b>Категория:</b> ${processingCompaniesEscapeHtml(requestPayload.category || "")}</div>
            <div><b>Происхождение:</b> ${processingCompaniesEscapeHtml(requestPayload.origin || "")}</div>
        </div>
        <div class="border rounded p-3 mb-3">
            <div><b>Найдена:</b> ${matchedText}</div>
            <div><b>Компания:</b> ${processingCompaniesEscapeHtml(company.title || "")}</div>
            <div><b>ИНН:</b> ${processingCompaniesEscapeHtml(company.inn || "")}</div>
        </div>
        <pre class="bg-white border rounded p-3 mb-0" style="white-space: pre-wrap; font-size: 12px;">${responseText}</pre>
    `;
}

function renderProcessingCompaniesError(message) {
    return `
        <h3 class="h5 mb-3">Ошибка</h3>
        <div class="alert alert-danger mb-0">
            ${processingCompaniesEscapeHtml(message || "Не удалось выполнить запрос.")}
        </div>
    `;
}

function setProcessingCompaniesLoading(isLoading) {
    const form = document.getElementById("processingCompaniesTestForm");
    if (!form) {
        return;
    }

    const button = form.querySelector('button[type="submit"]');
    if (!button) {
        return;
    }

    button.disabled = isLoading;
    button.textContent = isLoading ? "Запрос..." : "Отправить запрос";
}

function setResetProductCardsLoading(isLoading) {
    const form = document.getElementById("resetProductCardsForm");
    if (!form) {
        return;
    }

    const button = form.querySelector('button[type="submit"]');
    if (!button) {
        return;
    }

    button.disabled = isLoading;
    button.textContent = isLoading
        ? "Выполняется..."
        : "Перевести все карточки товаров в исходное положение";
}

function setDeleteProductCardsLoading(isLoading) {
    const form = document.getElementById("deleteProductCardsForm");
    const openButton = document.getElementById("deleteProductCardsOpenBtn");
    if (!form) {
        return;
    }

    const button = form.querySelector('button[type="submit"]');
    if (!button) {
        return;
    }

    button.disabled = isLoading;
    button.textContent = isLoading
        ? "Удаляется..."
        : "Да, удалить все старые карточки товаров";

    if (openButton) {
        openButton.disabled = isLoading;
    }
}

function renderProductCardsActionSuccess(message) {
    return `
        <h3 class="h5 mb-3">Готово</h3>
        <div class="alert alert-success mb-0">
            ${processingCompaniesEscapeHtml(message || "")}
        </div>
    `;
}

async function submitProcessingCompaniesTest(event) {
    event.preventDefault();

    const form = event.currentTarget;
    const result = document.getElementById("processingCompaniesResult");
    const csrf = form.querySelector('input[name="csrf_token"]')?.value || "";
    const category = form.querySelector('[name="category"]')?.value || "";
    const country = form.querySelector('[name="country"]')?.value || "";

    if (!form.reportValidity()) {
        return;
    }

    if (!result) {
        return;
    }

    setProcessingCompaniesLoading(true);
    result.classList.remove("d-none");
    result.innerHTML = '<div class="text-center text-warning"><b>Производится обработка</b><br><div class="spinner-border mt-2" role="status"></div></div>';

    try {
        const response = await fetch(form.dataset.action, {
            method: "POST",
            credentials: "same-origin",
            headers: {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "X-CSRFToken": csrf,
            },
            body: JSON.stringify({category, country}),
        });
        const payload = await response.json();

        if (!response.ok || payload.status !== "success") {
            throw new Error(payload.message || "Запрос не выполнен.");
        }

        result.innerHTML = renderProcessingCompaniesResult(payload);
    } catch (error) {
        result.innerHTML = renderProcessingCompaniesError(error.message);
    } finally {
        setProcessingCompaniesLoading(false);
    }
}

async function submitResetProductCards(event) {
    event.preventDefault();

    if (!confirm("Перевести все неотмененные карточки в этап создания, очистить компании, удалить старые привязки фирм и отмененные карточки?")) {
        return;
    }

    const form = event.currentTarget;
    const result = document.getElementById("resetProductCardsResult");
    const csrf = form.querySelector('input[name="csrf_token"]')?.value || "";

    if (!result) {
        return;
    }

    setResetProductCardsLoading(true);
    result.classList.remove("d-none");
    result.innerHTML = '<div class="text-center text-warning"><b>Производится обработка</b><br><div class="spinner-border mt-2" role="status"></div></div>';

    try {
        const response = await fetch(form.dataset.action, {
            method: "POST",
            credentials: "same-origin",
            headers: {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "X-CSRFToken": csrf,
            },
            body: JSON.stringify({}),
        });
        const payload = await response.json();

        if (!response.ok || payload.status !== "success") {
            throw new Error(payload.message || "Сброс не выполнен.");
        }

        result.innerHTML = renderProductCardsActionSuccess(payload.message);
    } catch (error) {
        result.innerHTML = renderProcessingCompaniesError(error.message);
    } finally {
        setResetProductCardsLoading(false);
    }
}

async function submitDeleteProductCards(event) {
    event.preventDefault();

    const form = event.currentTarget;
    const result = document.getElementById("resetProductCardsResult");
    const csrf = form.querySelector('input[name="csrf_token"]')?.value || "";
    const passwordInput = form.querySelector('[name="password"]');
    const password = passwordInput?.value || "";
    const modalError = document.getElementById("deleteProductCardsModalError");

    if (!result) {
        return;
    }

    if (!password.trim()) {
        if (modalError) {
            modalError.textContent = "Введите пароль учетной записи.";
            modalError.classList.remove("d-none");
        }
        passwordInput?.focus();
        return;
    }

    if (modalError) {
        modalError.textContent = "";
        modalError.classList.add("d-none");
    }

    setDeleteProductCardsLoading(true);
    result.classList.remove("d-none");
    result.innerHTML = '<div class="text-center text-danger"><b>Удаление карточек</b><br><div class="spinner-border mt-2" role="status"></div></div>';

    try {
        const response = await fetch(form.dataset.action, {
            method: "POST",
            credentials: "same-origin",
            headers: {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "X-CSRFToken": csrf,
            },
            body: JSON.stringify({password}),
        });
        const payload = await response.json();

        if (!response.ok || payload.status !== "success") {
            throw new Error(payload.message || "Удаление не выполнено.");
        }

        const modalEl = document.getElementById("deleteProductCardsModal");
        if (modalEl && window.bootstrap) {
            bootstrap.Modal.getOrCreateInstance(modalEl).hide();
        }
        form.reset();
        result.innerHTML = renderProductCardsActionSuccess(payload.message);
    } catch (error) {
        if (modalError) {
            modalError.textContent = error.message;
            modalError.classList.remove("d-none");
        }
        result.innerHTML = renderProcessingCompaniesError(error.message);
    } finally {
        setDeleteProductCardsLoading(false);
    }
}

function openDeleteProductCardsModal() {
    const modalEl = document.getElementById("deleteProductCardsModal");
    const form = document.getElementById("deleteProductCardsForm");
    const modalError = document.getElementById("deleteProductCardsModalError");

    if (!modalEl || !window.bootstrap) {
        return;
    }

    form?.reset();
    if (modalError) {
        modalError.textContent = "";
        modalError.classList.add("d-none");
    }

    bootstrap.Modal.getOrCreateInstance(modalEl).show();
    modalEl.addEventListener("shown.bs.modal", () => {
        document.getElementById("deleteProductCardsPassword")?.focus();
    }, {once: true});
}

document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("processingCompaniesTestForm");
    if (form) {
        form.addEventListener("submit", submitProcessingCompaniesTest);
    }

    const resetForm = document.getElementById("resetProductCardsForm");
    if (resetForm) {
        resetForm.addEventListener("submit", submitResetProductCards);
    }

    const deleteForm = document.getElementById("deleteProductCardsForm");
    if (deleteForm) {
        deleteForm.addEventListener("submit", submitDeleteProductCards);
    }

    const deleteOpenButton = document.getElementById("deleteProductCardsOpenBtn");
    if (deleteOpenButton) {
        deleteOpenButton.addEventListener("click", openDeleteProductCardsModal);
    }
});
