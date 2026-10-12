function crmApplyCategoryCounters(counters) {
  if (!counters) return;
  const ids = {
    all: "all_commonCounter",
    "одежда": "clothes_commonCounter",
    "обувь": "shoes_commonCounter",
    "белье": "linen_commonCounter",
    "парфюм": "parfum_commonCounter",
    "косметика": "cosmetics_commonCounter",
    "игрушки": "toys_commonCounter",
    "носки и прочее": "socks_commonCounter",
    clothes: "clothes_commonCounter",
    shoes: "shoes_commonCounter",
    linen: "linen_commonCounter",
    parfum: "parfum_commonCounter",
    cosmetics: "cosmetics_commonCounter",
    toys: "toys_commonCounter",
    socks: "socks_commonCounter"
  };
  Object.entries(counters).forEach(([category, count]) => {
    const element = document.getElementById(ids[category]);
    if (element) element.textContent = count;
  });
}

function crmApplyBoardSummary(data) {
  crmApplyCategoryCounters(data.categories_counter);
  const weeklySummary = document.getElementById("crm-weekly-order-summary");
  if (weeklySummary && data.weekly_order_summary) {
    weeklySummary.textContent = data.weekly_order_summary;
  }
}

async function crmLoadInitialBoard() {
  const host = document.getElementById("update_all_info");
  const url = host?.dataset.initialBoardUrl;
  if (!url) return;

  const sequence = Number(host.dataset.boardSequence || 0) + 1;
  host.dataset.boardSequence = String(sequence);
  try {
    const response = await fetch(url, {
      credentials: "same-origin",
      headers: { "X-Requested-With": "XMLHttpRequest" }
    });
    if (!response.ok) throw new Error("Не удалось загрузить карточки");
    const data = await response.json();
    if (data.status !== "success" || typeof data.htmlresponse !== "string") {
      throw new Error(data.message || "Не удалось загрузить карточки");
    }
    if (Number(host.dataset.boardSequence) !== sequence) return;
    $(host).html(data.htmlresponse);
    crmApplyBoardSummary(data);
    if (typeof initializeJSPage === "function") initializeJSPage(document);
  } catch (error) {
    if (Number(host.dataset.boardSequence) !== sequence) return;
    host.innerHTML = '<div class="text-center py-5"><div class="mb-3">Не удалось загрузить карточки.</div><button type="button" class="btn btn-warning" onclick="crmLoadInitialBoard()">Повторить</button></div>';
  }
}

document.addEventListener("DOMContentLoaded", crmLoadInitialBoard);
