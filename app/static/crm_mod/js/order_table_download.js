(() => {
  let downloading = false;

  function downloadFilename(disposition) {
    const encoded = disposition.match(/filename\*=UTF-8''([^;]+)/i);
    if (encoded) {
      try {
        return decodeURIComponent(encoded[1].trim());
      } catch (_) {
        // Fall back to the ordinary filename if the encoded name is invalid.
      }
    }
    const plain = disposition.match(/filename="([^"]+)"|filename=([^;]+)/i);
    return plain ? (plain[1] || plain[2]).trim() : 'Таблица заказа.zip';
  }

  window.downloadCrmOrderTable = async function (event, form) {
    event.preventDefault();
    event.stopPropagation();
    if (downloading) return;

    downloading = true;
    form.setAttribute('aria-busy', 'true');
    form.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(icon => {
      bootstrap.Tooltip.getInstance(icon)?.hide();
    });
    loadingCircle();
    try {
      const response = await fetch(form.action, {
        method: 'POST',
        body: new FormData(form),
        credentials: 'same-origin'
      });
      const disposition = response.headers.get('Content-Disposition') || '';
      if (!response.ok || response.redirected || !/^attachment\b/i.test(disposition)) {
        throw new Error('Download failed');
      }
      const blob = await response.blob();
      const objectUrl = URL.createObjectURL(blob);
      const link = document.createElement('a');
      try {
        link.href = objectUrl;
        link.download = downloadFilename(disposition);
        document.body.appendChild(link);
        link.click();
      } finally {
        link.remove();
        setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
      }
      make_message('Файл скачан', 'success');
    } catch (_) {
      make_message('Не удалось скачать файл. Обновите страницу и попробуйте снова.', 'danger');
    } finally {
      downloading = false;
      form.removeAttribute('aria-busy');
      close_Loading_circle();
    }
  };
})();
