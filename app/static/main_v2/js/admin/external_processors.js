(function () {
  const root = document.getElementById('external-processors-page');
  if (!root) {
    return;
  }

  const collectionUrl = root.dataset.collectionUrl;
  const csrfToken = root.dataset.csrfToken;
  const tableHolder = document.getElementById('external_processors_table');
  const createForm = document.getElementById('external-processor-create-form');
  const editForm = document.getElementById('external-processor-edit-form');
  const editModalElement = document.getElementById('externalProcessorEditModal');
  const editModal = editModalElement ? new bootstrap.Modal(editModalElement) : null;
  const totalCounter = document.getElementById('external-processors-total');
  const activeCounter = document.getElementById('external-processors-active');

  function notify(message, level) {
    if (window.make_message) {
      window.make_message(message, level);
      return;
    }
    window.alert(message);
  }

  function buildPayload(formElement) {
    const payload = {};
    const fields = new FormData(formElement);

    fields.forEach((value, key) => {
      if (key === 'id') {
        return;
      }

      const trimmedValue = typeof value === 'string' ? value.trim() : value;
      if (key === 'allowed_ips') {
        payload[key] = trimmedValue;
        return;
      }

      if (trimmedValue === '') {
        return;
      }

      if (['ttl_seconds', 'nonce_ttl_seconds', 'batch_size', 'confirmation_timeout_seconds'].includes(key)) {
        payload[key] = Number.parseInt(trimmedValue, 10);
        return;
      }

      payload[key] = trimmedValue;
    });

    payload.is_active = formElement.querySelector('[name="is_active"]').checked;
    return payload;
  }

  function formatError(data, fallbackMessage) {
    if (Array.isArray(data?.errors) && data.errors.length > 0) {
      return data.errors.map((item) => {
        const location = Array.isArray(item.loc) ? item.loc.join('.') : 'field';
        return `${location}: ${item.msg}`;
      }).join('\n');
    }
    return data?.message || fallbackMessage;
  }

  async function copyTextToClipboard(text) {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text);
      return;
    }

    const textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.setAttribute('readonly', 'readonly');
    textarea.style.position = 'absolute';
    textarea.style.left = '-9999px';
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand('copy');
    document.body.removeChild(textarea);
  }

  async function request(url, options) {
    const response = await fetch(url, {
      credentials: 'include',
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
        'X-CSRFTOKEN': csrfToken,
      },
      ...options,
    });

    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(formatError(data, 'Ошибка запроса'));
    }
    return data;
  }

  function bindTableActions() {
    document.querySelectorAll('.js-copy-external-processor').forEach(function (button) {
      button.addEventListener('click', async function () {
        const processorId = button.dataset.id;
        if (!processorId) {
          return;
        }

        try {
          const data = await request(`${collectionUrl}/${processorId}`, { method: 'GET' });
          const processor = data.data || {};
          const payload = [
            `key ID: ${processor.key_id || ''}`,
            `Shared secret: ${processor.shared_secret || ''}`,
            `MinIO bucket: ${processor.minio_bucket_name || ''}`,
            `Префикс MinIO: ${processor.minio_prefix || ''}`,
          ].join('\n');

          await copyTextToClipboard(payload);
          notify('Креды и настройки скопированы', 'success');
        } catch (error) {
          notify(error.message || 'Не удалось скопировать данные обработчика', 'danger');
        }
      });
    });

    document.querySelectorAll('.js-edit-external-processor').forEach(function (button) {
      button.addEventListener('click', async function () {
        const processorId = button.dataset.id;
        if (!processorId || !editForm || !editModal) {
          return;
        }

        try {
          const data = await request(`${collectionUrl}/${processorId}`, { method: 'GET' });
          const processor = data.data || {};

          editForm.elements.id.value = processor.id || '';
          editForm.elements.name.value = processor.name || '';
          editForm.elements.source_label.value = processor.source_label || '';
          editForm.elements.key_id.value = processor.key_id || '';
          editForm.elements.shared_secret.value = processor.shared_secret || '';
          editForm.elements.minio_bucket_name.value = processor.minio_bucket_name || '';
          editForm.elements.minio_prefix.value = processor.minio_prefix || '';
          editForm.elements.allowed_ips.value = Array.isArray(processor.allowed_ips) ? processor.allowed_ips.join(', ') : '';
          editForm.elements.ttl_seconds.value = processor.ttl_seconds || '';
          editForm.elements.nonce_ttl_seconds.value = processor.nonce_ttl_seconds || '';
          editForm.elements.batch_size.value = processor.batch_size || '';
          editForm.elements.confirmation_timeout_seconds.value = processor.confirmation_timeout_seconds || '';
          editForm.elements.is_active.checked = Boolean(processor.is_active);

          editModal.show();
        } catch (error) {
          notify(error.message || 'Не удалось загрузить обработчика', 'danger');
        }
      });
    });

    document.querySelectorAll('.js-delete-external-processor').forEach(function (button) {
      button.addEventListener('click', async function () {
        const processorId = button.dataset.id;
        const processorName = button.dataset.name || 'обработчик';
        if (!processorId) {
          return;
        }

        if (!window.confirm(`Удалить обработчик "${processorName}"?`)) {
          return;
        }

        try {
          await request(`${collectionUrl}/${processorId}`, { method: 'DELETE' });
          await refreshTable(getExternalProcessorsUpdateUrlForPage(1));
          notify('Внешний обработчик удален', 'success');
        } catch (error) {
          notify(error.message || 'Не удалось удалить обработчика', 'danger');
        }
      });
    });
  }

  async function bck_get_external_processors(url) {
    if (!tableHolder) {
      return;
    }

    try {
      const response = await fetch(url, { credentials: 'include' });
      const data = await response.json();
      if (!response.ok || data.status !== 'success') {
        notify(data.message || 'Ошибка загрузки списка', 'danger');
        return;
      }

      tableHolder.innerHTML = data.html || '';

      if (totalCounter) {
        totalCounter.textContent = String(data?.data?.total || 0);
      }

      if (activeCounter) {
        activeCounter.textContent = String(data?.data?.active || 0);
      }

      bindTableActions();
    } catch (error) {
      notify(error.message || 'Network error', 'danger');
    }
  }

  function getExternalProcessorsUpdateUrl() {
    if (!tableHolder) {
      return null;
    }

    const base = tableHolder.getAttribute('data-update-url-base') || '';
    const pageHolder = tableHolder.querySelector('[data-current-page]');
    let page = pageHolder ? pageHolder.getAttribute('data-current-page') : null;

    if (!page) {
      const active = tableHolder.querySelector('.pagination_section .active [data-page], .pagination_section .page-item.active a, .pagination_section .active a');
      if (active) {
        const dataPage = active.getAttribute('data-page');
        if (dataPage) {
          page = dataPage;
        } else {
          const href = active.getAttribute('href') || '';
          const match = href.match(/[?&]page=(\d+)/);
          if (match) {
            page = match[1];
          }
        }
      }
    }

    if (!page) {
      page = '1';
    }

    return base + page;
  }

  function getExternalProcessorsUpdateUrlForPage(targetPage) {
    if (!tableHolder) {
      return null;
    }

    const base = tableHolder.getAttribute('data-update-url-base') || '';
    return base + String(targetPage || '1');
  }

  async function refreshTable(updateUrl = null) {
    const url = updateUrl || getExternalProcessorsUpdateUrl();
    if (!url) {
      return;
    }
    await bck_get_external_processors(url);
  }

  if (createForm) {
    createForm.addEventListener('submit', async function (event) {
      event.preventDefault();
      const payload = buildPayload(createForm);

      try {
        await request(collectionUrl, {
          method: 'POST',
          body: JSON.stringify(payload),
        });
        createForm.reset();
        const createIsActiveCheckbox = createForm.elements.is_active;
        if (createIsActiveCheckbox) {
          createIsActiveCheckbox.checked = true;
        }
        await refreshTable(getExternalProcessorsUpdateUrlForPage(1));
        notify('Внешний обработчик создан', 'success');
      } catch (error) {
        notify(error.message || 'Не удалось создать обработчика', 'danger');
      }
    });
  }

  if (editForm) {
    editForm.addEventListener('submit', async function (event) {
      event.preventDefault();
      const processorId = editForm.elements.id.value;
      if (!processorId) {
        notify('Не найден идентификатор обработчика', 'danger');
        return;
      }

      const payload = buildPayload(editForm);
      if (!payload.shared_secret) {
        delete payload.shared_secret;
      }

      try {
        await request(`${collectionUrl}/${processorId}`, {
          method: 'PUT',
          body: JSON.stringify(payload),
        });
        await refreshTable();
        notify('Изменения сохранены', 'success');
        editModal.hide();
      } catch (error) {
        notify(error.message || 'Не удалось обновить обработчика', 'danger');
      }
    });
  }

  window.bck_get_external_processors = bck_get_external_processors;
  bindTableActions();
})();