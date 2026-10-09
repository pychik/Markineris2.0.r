window.PcTableLoading = (() => {
  let pending = 0;
  const tablesToReveal = new Set();

  function prepareOverlay() {
    const overlay = document.getElementById('overlay_loading');
    if (!overlay || overlay.classList.contains('pc-loading')) return;
    overlay.classList.add('pc-loading');
    overlay.innerHTML = '<div class="pc-loading__panel" role="status" aria-live="polite"><span class="pc-loading__spinner" aria-hidden="true"></span><div><div class="pc-loading__title">Обновляем карточки</div><div class="pc-loading__hint">Пожалуйста, подождите</div></div></div>';
  }

  function start(table) {
    table?.classList.add('is-loading');
    pending += 1;
    if (pending === 1) {
      prepareOverlay();
      loadingCircle();
    }
  }

  function finish(table) {
    if (table) tablesToReveal.add(table);
    pending = Math.max(0, pending - 1);
    if (pending === 0) {
      close_Loading_circle();
      requestAnimationFrame(() => {
        if (pending) return;
        tablesToReveal.forEach(item => {
          item.classList.remove('is-loading');
          item.classList.add('is-visible');
        });
        tablesToReveal.clear();
      });
    }
  }

  return {start, finish};
})();
