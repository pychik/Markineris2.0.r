// order_aggr.js
var aggrBuffer = {};

document.addEventListener('DOMContentLoaded', () => {
    initAggrCheckboxes(); // при первом открытии
});

document.querySelectorAll('.aggr-size-checkbox').forEach(cb => {
    cb.addEventListener('change', () => {
        const sizeId = cb.value;
        const isChecked = cb.checked;
        const category = document.querySelector('#create_aggr_btn').dataset.category;
        const quantity = parseInt(cb.dataset.quantity);

        if (isChecked) {
            aggrBuffer[sizeId] = {
                quantity: quantity,
                category: category
            };
        } else {
            delete aggrBuffer[sizeId];
        }

        toggleCreateButton();
    });
});

function toggleCreateButton() {
    const btn = document.getElementById('create_aggr_btn');
    if (!btn) return;

    const hasValidSelections = Object.keys(aggrBuffer).some(id => {
        const cb = document.getElementById(`sizeCheckbox_${id}`);
        return cb && !cb.disabled;
    });

    btn.disabled = !hasValidSelections;
}

function saveBuffer() {
    sessionStorage.setItem('aggrBuffer', JSON.stringify(aggrBuffer));
}

function loadBuffer() {
    const saved = sessionStorage.getItem('aggrBuffer');
    if (saved) {
        aggrBuffer = JSON.parse(saved);
    }
}

function saveAggrCountToStorage() {
    const input = document.getElementById('aggr_count_input');
    if (input) {
        sessionStorage.setItem('aggrCount', input.value);
    }
}

function restoreAggrCountFromStorage() {
    const input = document.getElementById('aggr_count_input');
    const stored = sessionStorage.getItem('aggrCount');
    if (input && stored) {
        input.value = stored;
    }
}

function clearAggrCountOnLeave() {
    sessionStorage.removeItem('aggrCount');
    sessionStorage.removeItem('aggrBuffer');
}

function createAggrSet() {
    const $btn = $('#create_aggr_btn');
    const $countInput = $('#aggr_count_input');
    const createUrl = $btn.data('create-url');
    const updateUrl = $btn.data('update-url');
    const csrfToken = $btn.data('csrf-token');
    const category = $btn.data('category');
    const currentNum = parseInt($btn.data('aggr-num'));

    const aggrCount = parseInt($countInput.val()) || 1;

    sanitizeAggrBuffer();

    const items = Object.entries(aggrBuffer).map(([id, data]) => {
        return [parseInt(id), data.quantity * aggrCount];
    });

    $.ajax({
        type: 'POST',
        url: createUrl,
        contentType: 'application/json',
        headers: {
            'X-CSRFToken': csrfToken
        },
        data: JSON.stringify({
            category: category,
            items: items,
            count: aggrCount
        }),
        success: function (response) {
            if (response.status === 'success') {
                aggrBuffer = {};
                sessionStorage.removeItem('aggrBuffer');
                sessionStorage.removeItem('aggrCount');
                toggleCreateButton();
                $btn.text(`Создать набор ${currentNum + 1}`);
                $btn.data('aggr-num', currentNum + 1);
                $btn.prop('disabled', true);

                refreshFullOrderBlock(updateUrl);
            } else {
                alert(response.message);
            }
        },
        error: function () {
            alert('Ошибка при создании набора. Попробуйте ещё раз.');
        }
    });
}

function sanitizeAggrBuffer() {
    document.querySelectorAll('.aggr-size-checkbox:disabled').forEach(cb => {
        const id = cb.value;
        if (aggrBuffer[id]) {
            delete aggrBuffer[id];
        }
    });

    try {
        sessionStorage.setItem('aggrBuffer', JSON.stringify(aggrBuffer));
    } catch (e) {
        console.warn('Ошибка при сохранении очищенного буфера', e);
    }
}

function refreshFullOrderBlock(updateUrl) {
    fetch(`${updateUrl}?bck=1`)
        .then(res => res.json())
        .then(data => {
            if (data.status === 'success') {
                const wrapper = document.getElementById('step-3_update');
                if (wrapper) {
                    wrapper.innerHTML = data.htmlresponse;
                }

                if (typeof initAggrCheckboxes === 'function') {
                    initAggrCheckboxes();
                }

                const btn = document.getElementById('create_aggr_btn');
                if (btn) {
                    btn.textContent = `Добавить в набор ${btn.dataset.aggrNum}`;
                }
            } else {
                make_message(data.message || 'Ошибка обновления блока заказа', 'error');
            }
        })
        .catch(() => {
            make_message('Ошибка связи с сервером при обновлении таблицы', 'error');
        });
}

function initAggrCheckboxes() {
    try {
        const stored = sessionStorage.getItem('aggrBuffer');
        if (stored) {
            aggrBuffer = JSON.parse(stored);
        } else {
            aggrBuffer = {};
        }
    } catch (e) {
        aggrBuffer = {};
    }

    document.querySelectorAll('.aggr-size-checkbox').forEach(cb => {
        const sizeId = cb.value;

        if (aggrBuffer[sizeId]) {
            cb.checked = true;
        }

        cb.addEventListener('change', () => {
            const isChecked = cb.checked;
            const category = document.querySelector('#create_aggr_btn')?.dataset.category;
            const quantity = parseInt(cb.dataset.quantity);

            if (isChecked) {
                aggrBuffer[sizeId] = {
                    quantity: quantity,
                    category: category
                };
            } else {
                delete aggrBuffer[sizeId];
            }

            toggleCreateButton();
            saveBuffer();
        });
    });

    sanitizeAggrBuffer();
    saveBuffer();
    toggleCreateButton();
    checkAggrCompletionAndToggleButton();
}

function openAggrModal(url) {
    fetch(url)
        .then(res => res.json())
        .then(data => {
            if (data.status === 'success') {
                const container = document.getElementById('aggrModalContainer');
                container.innerHTML = `
                    <div class="modal fade" id="aggrModal" tabindex="-1" aria-hidden="true">
                        <div class="modal-dialog modal-xl modal-dialog-scrollable">
                            <div class="modal-content">
                                <div class="modal-header">
                                    <h5 class="modal-title">Наборы</h5>
                                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                                </div>
                                <div class="modal-body" id="aggrModalBody">
                                    ${data.html}
                                </div>
                            </div>
                        </div>
                    </div>
                `;
                const modal = new bootstrap.Modal(document.getElementById('aggrModal'));
                modal.show();

                document.getElementById('aggrModal').addEventListener('hidden.bs.modal', function () {
                    container.innerHTML = '';
                });
            } else {
                alert(data.message || 'Ошибка загрузки наборов');
            }
        });
}

function updateAggrTable(url) {
    fetch(url)
        .then(res => res.json())
        .then(data => {
            if (data.status === 'success') {
                const body = document.getElementById('aggrModalBody');
                if (body) {
                    body.innerHTML = data.html;
                }
            } else {
                alert(data.message || 'Ошибка обновления таблицы наборов');
            }
        });
}

function deleteAggrOrder(el) {
    const url = el.dataset.deleteUrl;
    const csrf = el.dataset.csrfToken;
    const updateUrl = el.dataset.updateUrl;
    const updateMainUrl = el.dataset.updateMainUrl;
    const name = el.dataset.aggrName;

    if (!confirm(`Удалить набор "${name}"?`)) return;

    fetch(url, {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrf
        }
    }).then(res => res.json())
      .then(data => {
          if (data.status === 'success') {
               updateAggrTable(updateUrl);
               refreshFullOrderBlock(updateMainUrl);
          } else {
              alert(data.message || 'Ошибка при удалении набора');
          }
      }).catch(() => {
          alert('Ошибка связи с сервером');
      });
}

function checkAggrCompletionAndToggleButton() {
    const finalizeBtn = document.getElementById('finalizeOrderBtn');
    if (!finalizeBtn) return;

    const checkboxes = document.querySelectorAll('.aggr-size-checkbox');

    const allAssigned = Array.from(checkboxes).every(cb => cb.disabled || cb.checked);

    finalizeBtn.disabled = !allAssigned;
    finalizeBtn.classList.toggle('btn-success', allAssigned);
    finalizeBtn.classList.toggle('btn-secondary', !allAssigned);
}

window.addEventListener('beforeunload', clearAggrCountOnLeave);
window.addEventListener('pagehide', clearAggrCountOnLeave);
