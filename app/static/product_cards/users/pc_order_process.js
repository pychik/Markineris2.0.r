(function () {
  function cfg() {
    const el = document.getElementById("config");
    if (!el) return null;
    return {
      csrf: el.getAttribute("data-csrf") || "",
      checkUrl: el.getAttribute("data-check-url") || "",
    };
  }
// ===============================
// CONTACT STEP (для этой ветки)
// Требования:
// - после проверки (и после подтверждения дублей) ОБЯЗАТЕЛЬНО выбрать тип связи
// - контакт уходит ВМЕСТЕ с финальным сабмитом (form_process.submit внутри performProcess)
// ===============================

  let __order_contact = { type: null, value: "" };

  function validate_contact_value(type, value) {
    value = (value || "").trim();

    if (!value) return { ok: false, msg: "Поле обязательно" };

    if (type === "telegram") {
      const re = /^@[A-Za-z0-9_]{5,32}$/;
      if (!re.test(value)) return { ok: false, msg: "Введите корректный username (@username)" };
    }

    if (type === "phone") {
      const digits = value.replace(/\D/g, "");
      if (digits.length < 10) return { ok: false, msg: "Введите корректный номер телефона" };
    }

    if (type === "max") {
      if (value.length < 3) return { ok: false, msg: "Слишком короткие данные" };
    }

    return { ok: true, msg: "" };
  }

  function show_contact_step() {
    __order_contact = { type: null, value: "" };

    setCheckMessage(`
      <div id="contact_block" class="contact-block faded">
        <div class="contact-title">Способ связи (обязательно)</div>
        <div class="contact-subtitle">Выберите способ связи по вопросам в заказе</div>
  
        <div class="d-grid gap-2 mt-3">
  
          <button type="button"
                  class="btn btn-outline-secondary text-start d-flex align-items-center gap-2"
                  id="btn_contact_tg">
            <svg width="28" height="28" viewBox="0 0 42 41" fill="none"
                 xmlns="http://www.w3.org/2000/svg">
                <g>
                    <path
                        d="M21.4053 40.9368C32.7097 40.9368 41.8737 31.7728 41.8737 20.4684C41.8737 9.16403 32.7097 0 21.4053 0C10.1009 0 0.93689 9.16403 0.93689 20.4684C0.93689 31.7728 10.1009 40.9368 21.4053 40.9368Z"
                        fill="#039BE5"/>
                    <path
                        d="M10.3029 20.025L30.0379 12.4159C30.9538 12.085 31.7538 12.6393 31.457 14.0244L28.0985 29.8533C27.8494 30.9756 27.1825 31.2485 26.2495 30.7198L21.1324 26.9485L18.6642 29.3262L17.9956 24.6219L27.4793 16.0541L15.1232 23.2266L10.0709 21.6506C8.97415 21.3026 8.95027 20.5538 10.3029 20.025Z"
                        fill="white"/>
                </g>
            </svg>
            Телеграм
          </button>
  
          <button type="button"
                  class="btn btn-outline-secondary text-start d-flex align-items-center gap-2"
                  id="btn_contact_max">
            <img
              src="/static/index_v3/images/max_bot.svg"
              width="28"
              height="28"
              alt="MAX messenger">
            Max
          </button>
  
          <button type="button"
                  class="btn btn-outline-secondary text-start d-flex align-items-center gap-2"
                  id="btn_contact_phone">
              <svg width="28" height="28" viewBox="0 0 41 41" fill="none"
                 xmlns="http://www.w3.org/2000/svg">

                <circle cx="20.5" cy="20.5" r="20.5" fill="#25D366"/>

                <g transform="translate(20.5 20.5) scale(2) translate(-20.5 -20.5)">
                    <path
                        d="M16.57 20.556C16.4419 20.3852 15.5253 19.1684 15.5253 17.9089C15.5253 16.6494 16.1863 16.0302 16.4208 15.774C16.6554 15.5179 16.9326 15.4541 17.1034 15.4541C17.2741 15.4541 17.4449 15.4559 17.5941 15.4631C17.7513 15.4712 17.9621 15.4033 18.1697 15.9025C18.3831 16.4148 18.8945 17.6748 18.9587 17.8028C19.023 17.9309 19.0652 18.0801 18.9803 18.2513C18.8949 18.422 18.8522 18.5285 18.7246 18.6782L18.3404 19.1266C18.2124 19.2542 18.0789 19.3926 18.2281 19.6487C18.3773 19.9049 18.8909 20.7429 19.6516 21.4219C20.6289 22.294 21.4535 22.5641 21.7096 22.6922C21.9653 22.8202 22.1149 22.7991 22.2641 22.6279L23.0747 21.6245C23.2455 21.3684 23.4158 21.4111 23.6503 21.4965C23.8849 21.5818 25.1431 22.201 25.3987 22.3291C25.6544 22.4572 25.8252 22.5214 25.8894 22.6279C25.9537 22.7349 25.9537 23.2471 25.7402 23.8447C25.5268 24.4424 24.5045 24.9883 24.013 25.0616C23.5722 25.1276 23.0141 25.155 22.4012 24.96C21.9056 24.8062 21.4186 24.6262 20.9421 24.4208C18.3746 23.3118 16.6985 20.7267 16.57 20.556Z"
                        fill="white"/>
                </g>

            </svg>
            Связаться по телефону
          </button>
  
        </div>
  
        <div id="contact_form_wrap" class="mt-3"></div>
        <div id="contact_error" class="mt-2 text-danger"></div>
      </div>
    `);

    const f = document.getElementById("process_modal_footer");
    if (f) {
      f.innerHTML = `
        <button type="button" class="btn btn-accent border-0" id="btn_contact_submit" disabled>
          Оформить заказ
        </button>
        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Назад</button>
      `;
    }

    const tg = document.getElementById("btn_contact_tg");
    const mx = document.getElementById("btn_contact_max");
    const ph = document.getElementById("btn_contact_phone");
    if (tg) tg.addEventListener("click", () => select_contact_method("telegram"));
    if (mx) mx.addEventListener("click", () => select_contact_method("max"));
    if (ph) ph.addEventListener("click", () => select_contact_method("phone"));

  const btn = document.getElementById("btn_contact_submit");
  if (btn) btn.addEventListener("click", submit_contact_and_form);
  }

  function select_contact_method(type) {
  __order_contact.type = type;
  __order_contact.value = "";

  let input_type = "text";
  let label = "";
  let placeholder = "";

  if (type === "telegram") {
  label = "Введите ваш username в Telegram (например: @username)";
  placeholder = "@username";
  } else if (type === "max") {
  label = "Введите ваши данные для связи через Max";
  placeholder = "Введите данные";
  } else if (type === "phone") {
  input_type = "tel";
  label = "Введите номер телефона";
  placeholder = "+7 (999) 123-45-67";
  }

    const wrap = document.getElementById("contact_form_wrap");
    if (!wrap) return;

    wrap.innerHTML = `
      <label class="mb-2">${label}</label>
      <input class="form-control" id="contact_value" type="${input_type}" placeholder="${placeholder}">
      <div id="contact_input_error" class="contact-error-text"></div>
    `;

    const input = document.getElementById("contact_value");
    const btn = document.getElementById("btn_contact_submit");
    const err = document.getElementById("contact_input_error");

    if (btn) btn.disabled = true;

    if (!input) return;

    input.addEventListener("input", () => {
      const value = (input.value || "").trim();
      __order_contact.value = value;

      const check = validate_contact_value(type, value);
      if (!check.ok) {
        input.classList.add("input-invalid");
        input.classList.remove("input-valid");
        if (err) err.innerText = check.msg;
        if (btn) btn.disabled = true;
      } else {
        input.classList.remove("input-invalid");
        input.classList.add("input-valid");
        if (err) err.innerText = "";
        if (btn) btn.disabled = false;
      }
    });
  }

  function submit_contact_and_form() {
    // const type = __order_contact.type;
    // const value = (__order_contact.value || "").trim();
    //
    // const errBox = document.getElementById("contact_error");
    // if (!type) {
    //   if (errBox) errBox.innerHTML = "Выберите способ связи";
    //   return;
    // }
    // if (!value) {
    //   if (errBox) errBox.innerHTML = "Заполните контактные данные";
    //   return;
    // }

    const form = document.getElementById("form_process");
    if (!form) {
      if (errBox) errBox.innerHTML = "Форма не найдена";
      return;
    }

    // hidden поля (если ещё нет)
    // let typeInput = document.getElementById("contact_type_input");
    // if (!typeInput) {
    //   typeInput = document.createElement("input");
    //   typeInput.type = "hidden";
    //   typeInput.name = "contact_type";
    //   typeInput.id = "contact_type_input";
    //   form.appendChild(typeInput);
    // }
    //
    // let valueInput = document.getElementById("contact_value_input");
    // if (!valueInput) {
    //   valueInput = document.createElement("input");
    //   valueInput.type = "hidden";
    //   valueInput.name = "contact_value";
    //   valueInput.id = "contact_value_input";
    //   form.appendChild(valueInput);
    // }
    //
    // typeInput.value = type;
    // valueInput.value = value;

    // дальше запускаем ТВОЙ штатный финальный сабмит (копирует коммент + показывает лоадер + submit)
    performProcess();
  }

  function setFooterLoading() {
    const f = document.getElementById("process_modal_footer");
    if (!f) return;
    f.innerHTML = `<div class="col text-center text-warning">
        <b>Производится проверка</b><br>
        <div class="spinner-border" role="status"></div>
      </div>`;
  }

  function setFooterOk(submitText = "Оформить накладную") {
    const f = document.getElementById("process_modal_footer");
    if (!f) return;
    f.innerHTML = `
      <button type="button" class="btn btn-accent border-0" id="btn_process">${submitText}</button>
      <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Назад</button>
    `;

    const btn = document.getElementById("btn_process");
    // if (btn) btn.addEventListener("click", show_contact_step);
    if (btn) btn.addEventListener("click", performProcess);
  }

  function setFooterForce() {
    const f = document.getElementById("process_modal_footer");
    if (!f) return;
    f.innerHTML = `
      <button type="button" class="btn btn-accent" id="btn_force">Все-равно оформить накладную!</button>
      <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Отмена</button>
    `;
    const btn = document.getElementById("btn_force");
    // if (btn) btn.addEventListener("click", show_contact_step);
    if (btn) btn.addEventListener("click", performProcess);
  }

  function setCheckMessage(html) {
    const box = document.getElementById("data_order_check_insert");
    if (box) box.innerHTML = html || "";
  }

  function performProcess() {
    const textarea = document.getElementById("order_comment_after");
    const hidden = document.getElementById("order_comment");
    if (hidden && textarea) hidden.value = textarea.value || "";

    const f = document.getElementById("process_modal_footer");
    if (f) {
      f.innerHTML = `<div class="col text-center">
        <b>Производится обработка</b><br>
        <div class="spinner-border text-warning" role="status">
          <span class="visually-hidden">Loading...</span>
        </div>
      </div>`;
    }

    setTimeout(() => {
      const form = document.getElementById("form_process");
      if (form) form.submit();
    }, 500);
  }
  function setFooterOkOnly() {
    const f = document.getElementById("process_modal_footer");
    if (!f) return;
    f.innerHTML = `
      <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Назад</button>
    `;
  }
  function resetProcessModal() {
    // 1) сброс состояния контакта
    __order_contact = { type: null, value: "" };

    // 2) очистить сообщение/контент в центре модалки
    setCheckMessage("");

    // 3) сбросить счетчик позиций в шапке модалки (если есть)
    const modalCnt = document.querySelector("#modal_orders_pos_count span");
    if (modalCnt) modalCnt.textContent = "0";

    // 4) сбросить футер (к начальному виду)
    // вариант А: просто "Назад"
    setFooterOkOnly();

    // 5) очистить поле комментария в модалке (если есть textarea)
    const textarea = document.getElementById("order_comment_after");
    if (textarea) textarea.value = "";

    // 6) удалить hidden поля контакта из формы, чтобы не тащились при новом открытии
    const t = document.getElementById("contact_type_input");
    const v = document.getElementById("contact_value_input");
    if (t) t.remove();
    if (v) v.remove();

    // 7) (опционально) сбросить hidden order_comment
    const hiddenComment = document.getElementById("order_comment");
    if (hiddenComment) hiddenComment.value = "";
  }
  async function runCheck() {
    const c = cfg();
    if (!c || !c.checkUrl) {
      setCheckMessage(`<span style="color:red"><b>Не задан URL проверки</b></span>`);
      setFooterOkOnly();
      return;
    }

    setCheckMessage("");
    setFooterLoading();


    let data = null;
    try {
      const r = await fetch(c.checkUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": c.csrf },
        body: JSON.stringify({}),
      });
      data = await r.json();
      const modalCnt = document.querySelector("#modal_orders_pos_count span");
      if (modalCnt) modalCnt.textContent = String(data.marks_count ?? 0);
    } catch (e) {
      setCheckMessage(`<span style="color:red"><b>Ошибка проверки</b></span>`);
      setFooterOkOnly();
      return;
    }

    if (!data || data.status !== "success") {
      setCheckMessage(`<span style="color:red"><b>${(data && data.message) ? data.message : "Ошибка проверки"}</b></span>`);
      setFooterOkOnly();
      return;
    }

    // логика как у тебя:
    // status_balance: 1 ok, иначе не ok
    // status_order: 0 no duplicate, 1 duplicate
    const status_balance = Number(data.status_balance || 0);
    const status_order = Number(data.status_order || 0);
    const agent_at2 = !!data.agent_at2;

    const agent_2_str = "Обратитесь к агенту, на данный момент активность невозможна";

    // ✅ всё ок
    if (status_balance === 1 && status_order === 0) {
      setCheckMessage(`<span style="color:green"><b>Проверки пройдены. Нажмите “Оформить накладную”.</b></span>`);
      setFooterOk("Оформить накладную");
      return;
    }

    // ❌ баланс не ок (без дубля)
    if (status_balance !== 1 && status_order === 0) {
      setFooterOkOnly();
      if (!agent_at2) {
        setCheckMessage(`<span style="color:red"><b>${data.answer_balance}</b></span><br>`);
      } else {
        setCheckMessage(`<span style="color:red"><b>${agent_2_str}</b></span><br>`);
      }
      return;
    }

    // ❌ баланс не ок + есть дубль
    if (status_balance !== 1 && status_order !== 0) {
      setFooterOkOnly();
      if (!agent_at2) {
        setCheckMessage(`<span style="color:red"><b>${data.answer_balance}</b></span><br>`);
      } else {
        setCheckMessage(`<span style="color:red"><b>${agent_2_str}</b></span><br>`);
      }
      return;
    }

    // ⚠️ баланс ок, но дубль найден → разрешаем “всё равно”
    if (status_balance === 1 && status_order !== 0) {
      setCheckMessage(`<span style="color:#ffc400"><b>${data.answer_orders}</b></span><br>`);
      setFooterForce();
      return;
    }

    setCheckMessage(`<span style="color:red"><b>Неизвестная ошибка</b></span><br>`);
    setFooterOkOnly();
  }

  document.addEventListener("DOMContentLoaded", () => {
    const modalEl = document.getElementById("processModal");
    if (!modalEl || !window.bootstrap) return;
    modalEl.addEventListener("hidden.bs.modal", () => {
      resetProcessModal();
    });
    // при каждом открытии модалки запускаем проверку
    modalEl.addEventListener("shown.bs.modal", () => {
      runCheck();
    });
  });
})();
