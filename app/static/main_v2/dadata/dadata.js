document.addEventListener("DOMContentLoaded", () => {
  const input = document.getElementById("organization");
  const box = document.getElementById("org_suggest");

  const companyInn = document.getElementById("company_idn");
  const companyType = document.getElementById("company_type");
  const companyName = document.getElementById("company_name");

  const MIN_LEN = 7;
  const DEBOUNCE_MS = 450;
  let timer = null;
  let activeController = null;
  let lastRequestedQuery = "";

  function normalize(v) {
    return v.replace(/\D/g, "");
  }

  function hide() {
    box.style.display = "none";
    box.innerHTML = "";
  }

  function showError(message) {
    hide();
    if (typeof make_message === "function") {
      make_message(message, "danger");
    }
  }

  function render(items) {
    if (!items.length) return hide();

    box.innerHTML = "";
    items.forEach(item => {
      const el = document.createElement("button");
      el.type = "button";
      el.className = "list-group-item list-group-item-action"; // фиксированный класс, без text-muted

      const inactive = isInactive(item.status);

      el.innerHTML = `
        <div class="${inactive ? "text-decoration-line-through text-danger" : ""}">
          <strong>${item.inn}</strong> — ${item.name}
        </div>
        <div class="small ${inactive ? "text-danger" : "text-muted"}">
          ${item.opf || ""}${item.address ? " · " + item.address : ""}
          ${inactive ? " · НЕ ДЕЙСТВУЕТ" : ""}
        </div>
      `;

      el.onclick = () => {
        input.value = item.inn;
        companyInn.value = item.inn || "";
        companyType.value = item.opf || "";
        companyName.value = item.name || "";
        hide();
      };

      box.appendChild(el);
      });


    box.style.display = "block";

    // автозаполнение, если ровно 1 вариант и ИНН полный
    if (items.length === 1 && /^\d{10}$|^\d{12}$/.test(items[0].inn)) {
      const i = items[0];
      input.value = i.inn;
      companyInn.value = i.inn;
      companyType.value = i.opf || "";
      companyName.value = i.name || "";
      hide();
    }
  }
  function isInactive(status) {
    // “не действует” обычно = ликвидировано/в процессе ликвидации
    return status && status !== "ACTIVE";
  }
  async function fetchSuggest(q) {
    const url = new URL(dadataByInnUrl, location.origin);
    url.searchParams.set("q", q);
    activeController?.abort();
    activeController = new AbortController();
    const r = await fetch(url, { signal: activeController.signal });
    const j = await r.json();
    if (j.ok) return { items: j.items, error: null };

    return { items: [], error: "Ошибка получения ответа от сервиса информации по юр лицам" };
  }

  input.addEventListener("input", () => {
    clearTimeout(timer);

    const raw = input.value;
    const q = normalize(raw);
    if (raw !== q) input.value = q;

    if (q.length < MIN_LEN) {
      lastRequestedQuery = "";
      activeController?.abort();
      hide();
      return;
    }

    timer = setTimeout(async () => {
      if (q === lastRequestedQuery) return;
      lastRequestedQuery = q;

      try {
        const result = await fetchSuggest(q);
        if (result.error) {
          showError(result.error);
          return;
        }
        render(result.items);
      } catch (error) {
        if (error.name === "AbortError") return;
        showError("Ошибка получения ответа от сервиса информации по юр лицам");
      }
    }, DEBOUNCE_MS);
  });

  document.addEventListener("click", e => {
    if (!box.contains(e.target) && e.target !== input) hide();
  });
});




// document.addEventListener("DOMContentLoaded", function () {
//     // console.log("DOM fully loaded and ready!");
//
//     // Store the correct jQuery version in a variable
//     var myJQuery = window.jQuery;
//
//     function waitForDadata(retries = 5) {
//         if (typeof myJQuery.fn.suggestions !== "undefined") {
//             console.log("✅ Dadata suggestions plugin is loaded.");
//             fetchDadataToken();
//         } else {
//             if (retries > 0) {
//                 console.warn(`⏳ Waiting for Dadata plugin... (${retries} retries left)`);
//                 setTimeout(() => waitForDadata(retries - 1), 1000); // Retry in 1 sec
//             } else {
//                 console.error("❌ Dadata suggestions plugin failed to load.");
//             }
//         }
//     }
//
//     function fetchDadataToken() {
//         myJQuery.ajax({
//             url: getDadataTokenUrl,
//             method: 'GET',
//             dataType: 'json',
//             success: function (data) {
//                 if (data.token) {
//                     console.log("✅ Received token");
//                     initializeDadataSuggestions(data.token);
//                 } else {
//                     console.error("❌ Token missing in response:", data);
//                 }
//             },
//             error: function (error) {
//                 console.error("❌ Error fetching DaData token:", error);
//             }
//         });
//     }
//
//     function initializeDadataSuggestions(token) {
//         if (!token) {
//             console.error("❌ Cannot initialize suggestions: Token is missing!");
//             return;
//         }
//
//         console.log("🚀 Initializing Dadata Suggestions...");
//         myJQuery("#organization").suggestions({
//             minChars: 10,
//             token: token,
//             type: "PARTY",
//             onSelect: function (suggestion) {
//                 console.log("✅ Organization selected:", suggestion);
//                 myJQuery("#company_idn").val(suggestion.data.inn);
//                 myJQuery("#company_type").val(suggestion.data.opf.short);
//                 myJQuery("#company_name").val(suggestion.data.name.full);
//                 myJQuery("#modal_company_idn").val(suggestion.data.inn);
//                 myJQuery("#modal_company_name").val(suggestion.data.name.full);
//             }
//         });
//     }
//
//     // Start checking for Dadata plugin
//     waitForDadata();
// });
// function count_words(answer){
//      answer = answer.replace(/(^\s*)|(\s*$)/gi,"");
//      answer = answer.replace(/[ ]{2,}/gi," ");
//      return answer.split(' ').length;
//   }
//
//
// function check_blank_start (){
//     var company_name = document.getElementById("company_name");
//
//     if (company_name.value.startsWith(' ')){
//         company_name.value='';
//         alert("Наименование компании не может начинаться с пробела!");
//     }
// }
//
function manual_org_change(){
    document.getElementById('company_idn').value=document.getElementById('modal_company_idn').value;
    document.getElementById('company_type').value=document.getElementById('modal_company_type').value;
    document.getElementById('company_name').value=document.getElementById('modal_company_name').value;
}
