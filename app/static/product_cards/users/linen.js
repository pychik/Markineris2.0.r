
function linen_check_sizes_quantity_valid(){
    var sizes = document.querySelectorAll('[id=sizeX_info]');
    console.log(sizes.length);
    return sizes.length >= 1;
}


function linen_clear_pos(){
    $('#article').val("");
    $('#trademark').val("");

    $('#type').val('').trigger("change");
    $('#color').val('').trigger("change");
    $('#customColor').val("");
    $('#gender').val('').trigger("change");
    $('#customer_age').val('').trigger("change");
    $('#textile_type').val('').trigger("change");
    $('#content').val("");
    $('#country').val('').trigger("change");
    $('#rd_type').val('').trigger("change");
    $('#tax').val('').trigger("change");

    $('#tnved_code').val("");
    // $('#article_price').val("");
    $('#rd_name').val("");
    $('#rd_date').val("");

    $('#sizes_quantity').empty();

    check_valid(document.getElementById('tax'));
    check_valid(document.getElementById('article_price'));
    // check_valid(document.getElementById('trademark'));
    // check_valid(document.getElementById('article'));
}

function countLinen(){
    var total = 0;
    document.querySelectorAll('[id=quantity_info]').forEach(el=>total+=+parseInt(el.innerText, 10));
    return total

}


function setLinen(){
    var total = 0;

    var wp = document.getElementById('with_packages');
    var q_box = 1;
    if (wp.value === "True"){
        let q_box_raw = document.getElementById('box_quantity')
        if(q_box_raw){q_box = document.getElementById('box_quantity').value;}

    }

    document.querySelectorAll('[id=quantity_info]').forEach(el=>total+=+parseInt(el.innerText, 10));
    document.getElementById('linen_in_box_info').innerHTML = '';
    document.getElementById('linen_in_box_info').innerText = total;
}


function addLinenCell(){

    var sizeX = document.getElementById('sizeX_order').value;
    var sizeY = document.getElementById('sizeY_order').value;
    var sizeUnit = document.getElementById('sizeUnitOrder').value;
    var quantity_val = document.getElementById('quantity_order').value;
    if(sizeX < 1 || sizeY < 1){
        show_form_errors(['некорректный размер белья',]);
        $('#form_errorModal').modal('show');
            return false
        }
    // if(check_linen_size(size)!==true){
    //     return false
    // }
    var quantity = parseInt(quantity_val,10);
    if(isNaN(quantity)){
        // alert('некорректное количество');
        show_form_errors(['некорректное количество единиц товара белья',]);
        $('#form_errorModal').modal('show');
        return false
    }

    if(!sizeUnit || sizeUnit === ''){
        // alert('некорректное количество');
        show_form_errors(['не выбраны единицы измерения для белья',]);
        $('#form_errorModal').modal('show');
        return false
    }
    if (check_add_same_size(sizeX, sizeY,sizeUnit, quantity)){
        return false
    }
    // if (size_val === '56.5' || size_val === '56' || size > 56){
    //     size = '56.5';
    // }
    // else if(isNaN(size)){
    //     size = '';

    var f = document.getElementById('sizes_quantity');
    var wp = document.getElementById('with_packages');
    var max_param = '';
    var placeholder_param = '';

    if (wp.value==="True"){
       max_param = "12";
       placeholder_param = 'Max. 12';

    }


    f.insertAdjacentHTML( 'beforeend', `<div class="important-card__item important-card__size ms-2"><div class="d-flex align-items-center g-3"><svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" onclick="$(this).closest('div').parent().remove();setLinen();" viewBox="0 0 20 20" fill="none"><path fill-rule="evenodd" clip-rule="evenodd" d="M4.34074 0.312213C8.07158 -0.104071 11.9285 -0.104071 15.6593 0.312213C17.7413 0.544517 19.4209 2.18214 19.6655 4.26889C20.1115 8.07671 20.1115 11.9234 19.6655 15.7312C19.4209 17.8179 17.7413 19.4555 15.6593 19.6878C11.9285 20.1041 8.07158 20.1041 4.34074 19.6878C2.25873 19.4555 0.579043 17.8179 0.33457 15.7312C-0.111523 11.9234 -0.111523 8.07671 0.33457 4.26889C0.579043 2.18214 2.25873 0.544517 4.34074 0.312213ZM10 9.08981H10.9117H15.1575C15.661 9.08981 16.0692 9.49734 16.0692 10C16.0692 10.5027 15.661 10.9102 15.1575 10.9102H10.9117C10.9117 10.9102 10.2506 10.9102 10 10.9102C9.74947 10.9102 9.46208 10.9102 9.46208 10.9102H9.08832H4.84265C4.33912 10.9102 3.93094 10.5027 3.93094 10C3.93094 9.49734 4.33912 9.08981 4.84265 9.08981H9.08832H10Z" fill="white" /></svg>
<!--                            <div class="ms-2" title="Нажать для изменения позиции. При нажатии, размер и количество перемещаются из накладной в форму!">-->
<!--                                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" onclick="linen_edit_size($(this).closest('div').parent());"-->
<!--                                     fill="none" class="bi bi-pencil" viewBox="0 0 20 20">-->
<!--                                  <path fill-rule="evenodd" clip-rule="evenodd" d="M12.146.146a.5.5 0 0 1 .708 0l3 3a.5.5 0 0 1 0 .708l-10 10a.5.5 0 0 1-.168.11l-5 2a.5.5 0 0 1-.65-.65l2-5a.5.5 0 0 1 .11-.168zM11.207 2.5 13.5 4.793 14.793 3.5 12.5 1.207zm1.586 3L10.5 3.207 4 9.707V10h.5a.5.5 0 0 1 .5.5v.5h.5a.5.5 0 0 1 .5.5v.5h.293zm-9.761 5.175-.106.106-1.528 3.821 3.821-1.528.106-.106A.5.5 0 0 1 5 12.5V12h-.5a.5.5 0 0 1-.5-.5V11h-.5a.5.5 0 0 1-.468-.325" fill="white"/>-->
<!--                                </svg>-->
<!--                            </div>-->
                            <div class="ms-2"><span id="sizeX_info">${sizeX}</span> * <span id="sizeY_info">${sizeY}</span>, <span id="sizeUnit_info">${sizeUnit}</span></div>
                        </div>
                        <div class="important-card__val">
                            <span id="quantity_info">${quantity}</span> <span>шт. </span>
                            <input type="number" id="quantity_input" name="quantity_input"
                                           value="${quantity}" style="display:none; width: 68px;"
                                           min="1" placeholder="0">
                        </div>
                        <input type="hidden" id="sizeX" name="sizeX" value="${sizeX}">
                        <input type="hidden" id="sizeY" name="sizeY" value="${sizeY}">
                        <input type="hidden" id="sizeUnit" name="sizeUnit" value="${sizeUnit}">
                        <input type="hidden" id="quantity" name="quantity" value="${quantity}">
                    </div>`);
        // `<div class="row mb-3" id="container_element"><div class="col-md-6 col-xs-12 mt-1"><input type="text" name="size" id="size" minlength="2" maxlength="5" class="form-control mb-1" placeholder="Размер 16 - 56.5" autocomplete="off" oninput="check_shoes_size(value)||(value='');" value="${size}" required></div><div class="col-md-6 col-xs-12 mt-1"><input type="number" name="quantity" id="quantity" class="form-control ms-1" value="1" min="1"  oninput="validity.valid||(value='');javascript:setShoes();" max="${max_param}" placeholder="${placeholder_param}" required></div></div>`);

    var total = countLinen();

    document.getElementById('linen_in_box_info').innerHTML = '';
    document.getElementById('linen_in_box_info').innerText = total;
    document.getElementById('sizeX_order').value = '';
    document.getElementById('sizeY_order').value = '';
    $('#sizeUnitOrder').val('').trigger("change");
    document.getElementById('quantity_order').value = '1';
}

// function linen_edit_size(parent_block){
//     let sizeX = parent_block.find('#sizeX_info').html();
//     let sizeY = parent_block.find('#sizeY_info').html();
//     let quantity = parent_block.parent().find('#quantity_info').html();
//     // console.log(size, quantity);
//     $('#sizeX_order').val(sizeX);
//     $('#sizeY_order').val(sizeY);
//     $('#quantity_order').val(quantity);
//
//     parent_block.parent().remove();
//     setLinen();
// }
function linen_edit_size(el) {
    // Find quantity display and input fields
    const quantitySpan = $(el).closest('.important-card__size').find('#quantity_info');
    const quantityInput = $(el).closest('.important-card__size').find('#quantity_input');

    // If the span is visible, switch to input field
    if (quantitySpan.is(':visible')) {
        quantitySpan.hide();  // Hide quantity span
        $(el).closest('.important-card__size').find('span:contains("шт.")').hide();
        quantityInput.show().focus();  // Show and focus on input field
    }

    // Input validation for quantity
    quantityInput.on('input', function() {
        let value = parseInt(quantityInput.val(), 10);
        if (isNaN(value) || value < 1) {
            quantityInput.attr('placeholder', '0');
        } else if (value > 50000) {
            quantityInput.val(50000);  // Limit the value to 50000
        }
    });

    // When the input loses focus or Enter is pressed, save the value and switch back to span
    quantityInput.on('blur keypress', function(e) {
        if (e.type === 'blur' || (e.type === 'keypress' && e.key === 'Enter')) {
            let newQuantity = quantityInput.val();

            // If the input is empty, set it to 1 (auto-correct)
            if (newQuantity === '' || parseInt(newQuantity) < 1) {
                newQuantity = 1;
                quantityInput.val(1);
            }

            // Update the hidden input and quantity span
            $('#quantity').val(newQuantity);
            quantitySpan.text(newQuantity);

            // Hide input and show quantity span
            quantityInput.hide()
            $(el).closest('.important-card__size').find('span:contains("шт.")').show();;
            quantitySpan.show();
            setLinen();
        }
    });
}


function check_add_same_size(sizeX, sizeY, sizeUnit, quantity){
    var sizesX = document.querySelectorAll('[id=sizeX_info]');
    var sizesY = document.querySelectorAll('[id=sizeY_info]');
    var sizesUnit = document.querySelectorAll('[id=sizeUnit_info]');
    for (let i = 0; i < sizesX.length; ++i) {
      if (sizesX[i].innerText === sizeX && sizesY[i].innerText === sizeY && sizesUnit[i].innerText === sizeUnit){
          let quantities = document.querySelectorAll('[id=quantity_info]');
          let quantities_hidden = document.querySelectorAll('[id=quantity]');
          let quantity_block = quantities[i];
          let quantity_block_hidden = quantities_hidden[i];
          // console.log(`обнаружен похожий размер ${size}`);
          let quantity_pre = parseInt(quantity_block.innerText, 10);
          let quantity_val = quantity_pre + quantity;
          quantity_block.innerHTML = '';
          quantity_block.innerText = quantity_val;
          quantity_block_hidden.value = quantity_val
          setLinen();
          document.getElementById('sizeX_order').value = '';
          document.getElementById('sizeY_order').value = '';
          $('#sizeUnitOrder').val('').trigger("change");
          document.getElementById('quantity_order').value = '1';
          return true
      }
    }
    return false
}

function deleteCell(){
    var cur = $(this).closest('div');
    cur.parent().remove();
    setLinen();
}

(function initCottonTnvedLock(){
    const contentEl = document.getElementById('content');      // состав
    const tnvedEl   = document.getElementById('tnved_code');   // ТНВЭД
    const msgEl     = document.getElementById('tnved_co_supressor');
    const flagEl    = document.getElementById('check_tnved_flag');
    const typeEl    = document.getElementById('type');         // select2 select

    if (!contentEl || !tnvedEl || !msgEl || !typeEl) return;

    const WORD = 'ХЛОПОК';

    const TNVED_TOWEL_COTTON  = '6302910000'; // ПОЛОТЕНЦЕ + ХЛОПОК
    const TNVED_BEDSET_COTTON = '6302100001'; // КОМПЛЕКТ ПОСТЕЛЬНОГО БЕЛЬЯ + ХЛОПОК
    const DEFAULT_TNVED       = '6302999000'; // дефолт

    function normStr(v){
        return (v ?? '').toString().trim().toUpperCase();
    }

    function hasCotton(){
        return normStr(contentEl.value).includes(WORD);
    }

    function getTypeText(){
        return normStr(typeEl.value);
    }

    function lockTnved(code, message){
        tnvedEl.value = code;

        tnvedEl.readOnly = true;
        tnvedEl.style.pointerEvents = 'none';
        tnvedEl.onchange = null;
        tnvedEl.removeAttribute('onchange');

        if (flagEl) flagEl.value = "true";

        msgEl.style.color = '#f13131';
        msgEl.textContent = message;
    }

    function applyDefault(){
        tnvedEl.value = DEFAULT_TNVED;

        tnvedEl.readOnly = false;
        tnvedEl.style.pointerEvents = '';

        if (flagEl) flagEl.value = "false";

        msgEl.style.color = '#ffffff';
        msgEl.innerHTML = '&nbsp;';
    }

    function sync(){
        const typeText = getTypeText();
        const cotton   = hasCotton();

        if (cotton && typeText.includes('ПОЛОТЕНЦЕ')) {
            lockTnved(
                TNVED_TOWEL_COTTON,
                'Тип содержит "ПОЛОТЕНЦЕ" и в составе хлопок — ТНВЭД: 6302910000'
            );
            return;
        }

        if (cotton && typeText === 'КОМПЛЕКТ ПОСТЕЛЬНОГО БЕЛЬЯ') {
            lockTnved(
                TNVED_BEDSET_COTTON,
                'КОМПЛЕКТ ПОСТЕЛЬНОГО БЕЛЬЯ и хлопок — ТНВЭД: 6302100001'
            );
            return;
        }

        applyDefault();
    }

    // --- Состав (нативно) ---
    contentEl.addEventListener('input', sync);
    contentEl.addEventListener('change', sync);

    // --- Тип (нативно) ---
    typeEl.addEventListener('change', sync);
    typeEl.addEventListener('input', sync);

    // --- Тип (Select2/jQuery) ---
    if (window.jQuery) {
        const $type = window.jQuery(typeEl);

        // jQuery change (когда .trigger('change') делается через jQuery)
        $type.on('change', sync);

        // события select2 (самый надежный вариант)
        $type.on('select2:select select2:unselect select2:clear', sync);
    }

    sync();
    window.__syncCottonTnved = sync;
})();

document.addEventListener("input", function (e) {
    if (e.target.name && e.target.name.startsWith("quantity_order")) {
        e.preventDefault();
        e.target.value = e.target.getAttribute("value") || 1;
    }
});

document.addEventListener("keydown", function (e) {
    if (e.target.name && e.target.name.startsWith("quantity_order")) {
        e.preventDefault();
    }
});

document.addEventListener("wheel", function (e) {
    if (e.target.name && e.target.name.startsWith("quantity_order")) {
        if (document.activeElement === e.target) {
            e.preventDefault();
        }
    }
});