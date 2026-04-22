window.__pendingStep3AfterAsyncAdd = null;

function navigate_to_step3() {
    const btn = document.getElementById("btn-step-3");
    if (btn) {
        btn.click();
    }
}

function ensure_after_add_step3_flag(enabled) {
    const form = document.getElementById("form_process_main");
    if (!form) {
        return;
    }

    let input = document.getElementById("after_add_go_to_step3");
    if (!input && enabled) {
        input = document.createElement("input");
        input.type = "hidden";
        input.name = "after_add_go_to_step3";
        input.id = "after_add_go_to_step3";
        form.appendChild(input);
    }

    if (input) {
        if (enabled) {
            input.value = "1";
        } else {
            input.remove();
        }
    }
}

function get_filled_value_count(ids) {
    return ids.reduce((count, id) => {
        const element = document.getElementById(id);
        if (!element) {
            return count;
        }

        const value = (element.value || "").trim();
        return value ? count + 1 : count;
    }, 0);
}

function has_sizes_quantity_draft() {
    const block = document.getElementById("sizes_quantity");
    if (!block) {
        return false;
    }

    return block.querySelectorAll('input[name="quantity"]').length > 0;
}

function should_warn_about_unsaved_position(category) {
    const sharedIds = ["article", "trademark", "type", "color", "gender", "country", "tnved_code", "article_price"];

    if (category === "clothes" || category === "socks") {
        return has_sizes_quantity_draft()
            && get_filled_value_count([...sharedIds, "content"]) >= 3;
    }

    if (category === "shoes") {
        return has_sizes_quantity_draft()
            && get_filled_value_count(sharedIds) >= 3;
    }

    if (category === "linen") {
        return has_sizes_quantity_draft()
            && get_filled_value_count([...sharedIds, "content"]) >= 3;
    }

    if (category === "parfum") {
        const strongCount = get_filled_value_count(["trademark", "volume", "type"]);
        const softCount = get_filled_value_count(["trademark", "volume", "type", "country", "tnved_code", "article_price"]);
        return strongCount === 3 && softCount >= 4;
    }

    return false;
}

function ensure_unsaved_position_modal() {
    let modal = document.getElementById("unsavedPositionModal");
    if (modal) {
        return modal;
    }

    document.body.insertAdjacentHTML("beforeend", `
        <div class="modal fade" id="unsavedPositionModal" tabindex="-1" aria-hidden="true" data-bs-backdrop="static" data-bs-keyboard="false">
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Недобавленная заполненная позиция</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Закрыть"></button>
                    </div>
                    <div class="modal-body">
                        У вас осталась недобавленная заполненная позиция. Добавить ее в накладную перед переходом к оформлению?
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-accent border-0 text-dark" id="unsavedPositionAddBtn">Да, добавить</button>
                        <button type="button" class="btn btn-outline-secondary" id="unsavedPositionSkipBtn">Нет</button>
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Отмена</button>
                    </div>
                </div>
            </div>
        </div>
    `);

    return document.getElementById("unsavedPositionModal");
}

function open_unsaved_position_modal(onAdd, onSkip) {
    const modalEl = ensure_unsaved_position_modal();
    const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
    const addBtn = document.getElementById("unsavedPositionAddBtn");
    const skipBtn = document.getElementById("unsavedPositionSkipBtn");

    addBtn.onclick = () => {
        modal.hide();
        onAdd();
    };

    skipBtn.onclick = () => {
        modal.hide();
        onSkip();
    };

    modal.show();
}

window.runPendingStep3TransitionAfterAsyncAdd = function () {
    if (typeof window.__pendingStep3AfterAsyncAdd === "function") {
        const callback = window.__pendingStep3AfterAsyncAdd;
        window.__pendingStep3AfterAsyncAdd = null;
        callback();
    }
};

window.clearPendingStep3TransitionAfterAsyncAdd = function () {
    window.__pendingStep3AfterAsyncAdd = null;
    ensure_after_add_step3_flag(false);
};

window.goToStep3WithDraftCheck = function (category, addFnName, asyncFlag, url) {
    ensure_after_add_step3_flag(false);

    if (!should_warn_about_unsaved_position(category)) {
        navigate_to_step3();
        return;
    }

    open_unsaved_position_modal(
        () => {
            const addFn = window[addFnName];
            if (typeof addFn !== "function") {
                navigate_to_step3();
                return;
            }

            if (Number(asyncFlag) === 1) {
                window.__pendingStep3AfterAsyncAdd = navigate_to_step3;
            } else {
                ensure_after_add_step3_flag(true);
            }

            addFn(asyncFlag, url);
        },
        () => {
            navigate_to_step3();
        }
    );
};