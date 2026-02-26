function socks_check_sizes_quantity_valid() {
    var sizes = document.querySelectorAll('[id=size_info]');
    return sizes.length >= 1;
}



function socks_clear_pos() {
    $('#article').val("");
    $('#trademark').val("");

    $('#type').val('').trigger("change");
    $('#color').val('').trigger("change");
    $('#customColor').val("");
    $('#gender').val('').trigger("change");
    $('#multi_content').val('').trigger("change");
    $('#country').val('').trigger("change");
    $('#rd_type').val('').trigger("change");
    $('#tax').val('').trigger("change");

    $('#content').val("");
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

function socks_content_add() {
    var multi_box = document.getElementById('multi_content');
    var content = multi_box.value;
    var content_box = document.getElementById("content");
    var add_content = ''
    if (content_box.value.length !== 0) {

        if (content_box.value.includes(content) !== true && content_box.value.length + content.length + 2 <= content_box.maxLength) {
            add_content += ', ' + content;

        }
    } else {
        add_content += content;

    }

    content_box.value += add_content;
    content_box.value = content_box.value.slice(0, 101);
}

function check_nat_content(content) {
    if (socks_nat_array.includes(content)) {
        var nmc = document.getElementById("nat_materials_check")
        nmc.checked = true;
        set_tnved();
    }
}

function manual_content_edit() {
    var mccb = document.getElementById('manual_content_checkbox')
    var nmc = document.getElementById("nat_materials_check")
    var ctb = document.getElementById("content")
    if (mccb.checked === true) {
        nmc.disabled = false;
        ctb.readOnly = false
        ctb.classList.remove('bg-light')
    } else {
        nmc.disabled = true;
        ctb.readOnly = true
        ctb.classList.add('bg-light')

    }

}

function check_content() {
    var ctb = document.getElementById("content")
    if (ctb.value.length > 100) {
        ctb.value = ctb.value.slice(0,100);
    }
}

function countSocks() {
    var total = 0;
    document.querySelectorAll('[id=quantity_info]').forEach(el => total += parseInt(el.innerText, 10));
    return total

}


function setSocks() {
    var total = 0;

    var wp = document.getElementById('with_packages');
    var q_box = 1;
    if (wp.value === "True") {
        let q_box_raw = document.getElementById('box_quantity')
        if (q_box_raw) {
            q_box = document.getElementById('box_quantity').value;
        }

    }

    document.querySelectorAll('[id=quantity_info]').forEach(el => total += parseInt(el.innerText, 10));
    document.getElementById('socks_in_box_info').innerHTML = '';
    if (isNaN(total)){total=0;}
    document.getElementById('socks_in_box_info').innerText = total;
}


function check_add_same_size(size, quantity) {
    var sizes = document.querySelectorAll('[id=size_info]');
    for (let i = 0; i < sizes.length; ++i) {
        // console.log(sizes[i].innerText, size);
        if (sizes[i].innerText === size) {
            // console.log(sizes[i].innerText, size);
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
            setsocks();
            // $('#size_order').val('').trigger("change");
            document.getElementById('size_order').value = '';
            document.getElementById('quantity_order').value = '1';
            return true
        }
    }

    return false
}

function validateInput(inputElement) {
    const value = inputElement.value;
    const errorMessage = document.getElementById("errorSocksSizeMessage");

    // Проверка на кириллицу
    if (/[а-яА-ЯёЁ]/.test(value)) {
        errorMessage.textContent = "Кириллица недопустима!";
        errorMessage.style.display = "block";
        inputElement.value = value.replace(/[а-яА-ЯёЁ]/g, ""); // Убираем кириллицу
        return;
    }

    // Проверка для допустимых символов
    const allowedPattern = /^[A-Z+\d-]*$/;
    if (!allowedPattern.test(value)) {
        errorMessage.textContent = "Недопустимые символы!";
        errorMessage.style.display = "block";
        inputElement.value = value.replace(/[^A-Z+\d-]/g, ""); // Убираем недопустимые символы
        return;
    }

    // Если ввод корректный, но неполный (например, "44-")
    if (/^\d+-$/.test(value)) {
        errorMessage.textContent = "Ожидается ввод числа после тире.";
        errorMessage.style.display = "block";
        return;
    }

    // Убираем сообщение об ошибке для других случаев
    errorMessage.style.display = "none";
}

function finalValidateInput(inputElement) {
    const value = inputElement.value;
    const errorMessage = document.getElementById("errorSocksSizeMessage");

    if (!check_socks_size(value)) {
        errorMessage.textContent = "Некорректный ввод!";
        errorMessage.style.display = "block";
        inputElement.value = ""; // Очищаем поле
    } else {
        errorMessage.style.display = "none";
    }
}

function check_socks_size(value) {
    if (value.length > 0) {
        // Проверка для буквенных размеров
        if (/^[A-Z]+\+?$/.test(value)) {
            return true; // Допустимые размеры: S, S+, L, L+ и т.д.
        }

        // Проверка для диапазона чисел (формат "число-число")
        if (/^\d+-\d+$/.test(value)) {
            const [first, second] = value.split('-').map(Number);

            // Первая цифра должна быть от 1 до 100
            if (first < 1 || first > 100) {
                console.log(`Ошибка: первое число в диапазоне (${first}) вне допустимого диапазона 1–100.`);
                return false;
            }

            // Вторая цифра должна быть одной из +1, +2, +3, +4 к первой
            const validSecondNumbers = [first + 1, first + 2, first + 3, first + 4];
            if (!validSecondNumbers.includes(second)) {
                console.log(
                    `Ошибка: второе число в диапазоне (${second}) не является допустимым значением для ${first} (+1, +2, +3, +4).`
                );
                return false;
            }

            return true; // Диапазон валиден
        }

        // Проверка для одиночных чисел
        if (/^\d+$/.test(value)) {
            const number = Number(value);

            // Допустимые одиночные числа: от 1 до 100
            if (number < 1 || number > 100) {
                console.log(`Ошибка: число (${number}) вне допустимого диапазона 1–100.`);
                return false;
            }

            return true; // Число валидно
        }

        // Если ничего не подошло, возвращаем false
        console.log("Ошибка: значение не соответствует ни одному допустимому формату.");
        return false;
    }

    // Поле пустое — ошибка
    console.log("Ошибка: поле пустое.");
    return false;
}

function check_socks_size_on_add(value) {

    // console.log(value);
    if (value.length > 0) {

        if (check_list.includes(value)) {
            // console.log(check_list[i]);
            return true
        }

        show_form_errors(["Введите корректный размер: от 12 до 74 с шагом 2, либо особый размер вида 12-14, OVERSIZE !",]);
        $('#form_errorModal').modal('show');
        return false
    } else {
        return false
    }
}

function chooseSizeSocks() {
    let divBlock = document.getElementById('sizesSocksDiv');
    let content = '';
    let gender_value = document.getElementById('gender').value;
    if (!gender_value){
        make_message('Необходимо выбрать пол перед тем, как указать размеры', 'warning');
        return
    }
    if (!socks_types_sizes_dict.hasOwnProperty(gender_value)){
        make_message('Указан некорректный пол', 'error');
    }
    let socks_operation_dict = socks_types_sizes_dict[gender_value];
    // Iterate over each clothing type and its sizes
    for (let clothingType in socks_operation_dict) {
        // console.log(socks_operation_dict);
        if (socks_operation_dict.hasOwnProperty(clothingType)) {
            let sizes = socks_operation_dict[clothingType];



            // Create HTML for sizes
           let sizesBlock = create_size_blocks(sizes, clothingType);

            // Create HTML for collapsible div
            content += `
                <div class="accordion-item">
                    <h2 class="accordion-header" id="heading_${clothingType}">
                        <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#collapse_${clothingType}" aria-expanded="false" aria-controls="collapse_${clothingType}">
                            ${clothingType}
                        </button>
                    </h2>
                    <div id="collapse_${clothingType}" class="accordion-collapse collapse" aria-labelledby="heading_${clothingType}">
                        <div class="accordion-body">
                            <div class="row">${sizesBlock}</div>
                        </div>
                    </div>
                </div>`;
        }
    }

    divBlock.innerHTML = `
        <div class="modal fade" id="sizesSocksModal" tabindex="-1" role="dialog" aria-labelledby="sizesSocksModalLabel" aria-hidden="true">
            <div class="modal-dialog modal-lg modal-dialog-scrollable" data-backdrop="static" role="document">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title" id="sizesSocksModalLabel">Выберите размеры чулочно-носочных изделий.</h5>
                        <button type="button" class="btn-close" onclick="clear_socksSizes_modal();" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body px-5">
                        <p> Для выбора размера, кликните по нему, справа от размера появится поле - введите количество. После ввода всех необходимых размеров нажмите кнопку <b>Добавить и закрыть</b></p>
                        <p> Если нужно убрать размер, кликните на него</p>
                        <div class="accordion" id="accordionSizes" style="background-color: #f0f0f0;">${content}</div>
                    </div>
                    <div class="modal-footer d-flex flex-column" >
                        <button type="button" class="btn btn-accent" data-bs-dismiss="modal" onclick="clear_socksSizes_modal();" >Добавить и закрыть</button>
                    </div>
                </div>
            </div>
        </div>`;

    $('#sizesSocksModal').modal('show');
    enableAllTooltips();
}

function setQuantitySize(size) {
 let quantityInput = document.getElementById(`size_${size}`);
 let check = document.getElementById(`check_${size}`);
     if (quantityInput.disabled) {
        // включили размер
        quantityInput.disabled = false;
        quantityInput.value = 1;

        check.classList.remove('d-none');
    } else {
        // выключили размер
        quantityInput.disabled = true;
        quantityInput.value = '';

        check.classList.add('d-none');
    }
    // quantityInput.disabled = !quantityInput.disabled;
        updateSizesQuantityBlock();
}

function updateSizesQuantityBlock() {
    // Get the sizes_quantity block
    let sizesQuantityBlock = document.getElementById('sizes_quantity');

    // Clear previous content
    sizesQuantityBlock.innerHTML = '';

    // Iterate over each selected size and quantity
    let selectedSizes = document.querySelectorAll('#sizesSocksModal .form-control:not([readonly]):not([disabled])');
    selectedSizes.forEach(input => {


        let size = input.getAttribute('id').replace('size_', '');
        let quantity = input.value;
        let sizeType = input.getAttribute('data-size-type'); // Get the size type}
        if (size==='ЕДИНЫЙ РАЗМЕР'){sizeType = 'РОССИЯ';}


        // Create HTML for the size, size type, and quantity
        let sizeQuantityHTML = `
            <div class="important-card__item important-card__size ms-2">
                <div class="d-flex align-items-center g-3">
                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" onclick="$(this).closest('div').parent().remove();setSocks();"
                        viewBox="0 0 20 20" fill="none">
                        <path fill-rule="evenodd" clip-rule="evenodd"
                            d="M4.34074 0.312213C8.07158 -0.104071 11.9285 -0.104071 15.6593 0.312213C17.7413 0.544517 19.4209 2.18214 19.6655 4.26889C20.1115 8.07671 20.1115 11.9234 19.6655 15.7312C19.4209 17.8179 17.7413 19.4555 15.6593 19.6878C11.9285 20.1041 8.07158 20.1041 4.34074 19.6878C2.25873 19.4555 0.579043 17.8179 0.33457 15.7312C-0.111523 11.9234 -0.111523 8.07671 0.33457 4.26889C0.579043 2.18214 2.25873 0.544517 4.34074 0.312213ZM10 9.08981H10.9117H15.1575C15.661 9.08981 16.0692 9.49734 16.0692 10C16.0692 10.5027 15.661 10.9102 15.1575 10.9102H10.9117C10.9117 10.9102 10.2506 10.9102 10 10.9102C9.74947 10.9102 9.46208 10.9102 9.46208 10.9102H9.08832H4.84265C4.33912 10.9102 3.93094 10.5027 3.93094 10C3.93094 9.49734 4.33912 9.08981 4.84265 9.08981H9.08832H10Z"
                            fill="white" />
                    </svg>
                    <div class="ms-2">
                        <span id="size_info">${size}</span>
                        <span id="size_type_info" style="font-size: 10px">${sizeType}</span>
                     </div>
                </div>
                <div class="important-card__val"><span id="quantity_info">${quantity}</span> <span>шт.</span></div>
                <input type="hidden" id="size" name="size" value="${size}"><input type="hidden" id="quantity" name="quantity" value="${quantity}"><input type="hidden" id="size_type" name="size_type" value="${sizeType}">
            </div>`;

        // Append the size, size type, and quantity HTML to the sizes_quantity block
        sizesQuantityBlock.innerHTML += sizeQuantityHTML;
    });
    setSocks();
    // selectedSizes.forEach(input => {
    // input.addEventListener('change', updateSizesQuantityBlock);
// });
}

function clear_socksSizes_modal() {
    document.getElementById('sizesSocksDiv').innerHTML = '';
}

function check_socks_quantity_input(block){
    var value = parseFloat(block.value);
    var min = parseFloat(block.min);
    var max = parseFloat(block.max);

    // Check if the input value falls outside the specified range
    if (value < min || value > max || isNaN(value)) {
        // If so, set the input value to 0
        block.value = 1;
    }
}


function create_size_blocks(sizes, clothingType){
    let sizesBlock = '';

    for (let i = 0; i < sizes.length; i++) {
        let size = sizes[i]; // [буквенный, обувной]
        let sizeAlreadyExists = false;
        let quantity = 0;

        document.querySelectorAll('#sizes_quantity .important-card__size').forEach(item => {
            let sizeTypeInCard = item.querySelector('#size_type_info').textContent;
            let sizeInCard = item.querySelector('#size_info').textContent;

            if (sizeTypeInCard === clothingType && sizeInCard === size[0]) {
                sizeAlreadyExists = true;
                quantity = parseInt(item.querySelector('#quantity_info').textContent, 10);
            }
        });

        const checkClass    = sizeAlreadyExists ? '' : 'd-none';
        const inputDisabled = sizeAlreadyExists ? '' : 'disabled';
        const inputValue    = sizeAlreadyExists ? `value="${quantity}"` : `value=""`;

        sizesBlock += `
            <div class="col-md-5 border-bottom border-0 border-warning text-center mt-1">
                <div class="row align-items-center">
                    <div class="col-4 my-2" onclick="setQuantitySize('${size[0]}');" style="cursor:pointer">
                        <span>${size[0]}</span>
                        <span id="check_${size[0]}" class="faded size-check ms-2 ${checkClass}">✓</span>
                    </div>

                    <div class="col-6">
                        <input type="number" class="form-control ms-1 input-light-grey"
                            min="1" max="50000"
                            id="size_${size[0]}" name="size_${size[0]}"
                            style="display:none;"
                            placeholder="0"
                            data-size-type="${clothingType}"
                            ${inputValue}
                            ${inputDisabled}
                            onchange="check_socks_quantity_input(this);updateSizesQuantityBlock()">
                    </div>

                    <div class="col-2">
                        <div data-bs-toggle="tooltip" data-bs-placement="top"
                             data-bs-title="Размер по &#34;обуви&#34; ${size[1]}">
                            <span style="color:#c49204" class="font-12">${size[1]}</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    return sizesBlock;
}


function enableAllTooltips()
            {
                let tooltipelements =
                    document.querySelectorAll("[data-bs-toggle='tooltip']");
                tooltipelements.forEach((el) => {
                    new bootstrap.Tooltip(el);
                });
            }
function disableAllTooltips()
            {
                let tooltipelements =
                    document.querySelectorAll("[data-bs-toggle='tooltip']");
                tooltipelements.forEach((el) => {
                    el.disable();
                });
            }
function deleteCell() {
    var cur = $(this).closest('div');
    cur.parent().remove();
    setSocks();
}

function addSocksCell(){

    var size = document.getElementById('size_order').value;
    var quantity_val = document.getElementById('quantity_order').value;
    if(size.length< 1){
            return false
        }
    if(check_socks_size(size)!==true){
        return false
    }
    var quantity = parseInt(quantity_val,10);
    if(isNaN(quantity)){
        // alert('некорректное количество');
        show_form_errors(['некорректное количество размеров обуви',]);
        $('#form_errorModal').modal('show');
        return false
    }
    if (check_add_same_size(size, quantity)){
        return false
    }


    var f = document.getElementById('sizes_quantity');
    var wp = document.getElementById('with_packages');
    var max_param = '';
    var placeholder_param = '';

    if (wp.value==="True"){
       max_param = "12";
       placeholder_param = 'Max. 12';

    }


    f.insertAdjacentHTML( 'beforeend', `<div class="important-card__item important-card__size ms-2"><div class="d-flex align-items-center g-3"><svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" onclick="$(this).closest('div').parent().remove();setSocks();" viewBox="0 0 20 20" fill="none"><path fill-rule="evenodd" clip-rule="evenodd" d="M4.34074 0.312213C8.07158 -0.104071 11.9285 -0.104071 15.6593 0.312213C17.7413 0.544517 19.4209 2.18214 19.6655 4.26889C20.1115 8.07671 20.1115 11.9234 19.6655 15.7312C19.4209 17.8179 17.7413 19.4555 15.6593 19.6878C11.9285 20.1041 8.07158 20.1041 4.34074 19.6878C2.25873 19.4555 0.579043 17.8179 0.33457 15.7312C-0.111523 11.9234 -0.111523 8.07671 0.33457 4.26889C0.579043 2.18214 2.25873 0.544517 4.34074 0.312213ZM10 9.08981H10.9117H15.1575C15.661 9.08981 16.0692 9.49734 16.0692 10C16.0692 10.5027 15.661 10.9102 15.1575 10.9102H10.9117C10.9117 10.9102 10.2506 10.9102 10 10.9102C9.74947 10.9102 9.46208 10.9102 9.46208 10.9102H9.08832H4.84265C4.33912 10.9102 3.93094 10.5027 3.93094 10C3.93094 9.49734 4.33912 9.08981 4.84265 9.08981H9.08832H10Z" fill="white" /></svg>
                            <div class="ms-2" title="Нажать для изменения позиции. При нажатии, размер и количество перемещаются из накладной в форму!">
                                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" onclick="socks_edit_size($(this).closest('div').parent());"
                                     fill="none" class="bi bi-pencil" viewBox="0 0 20 20">
                                  <path fill-rule="evenodd" clip-rule="evenodd" d="M12.146.146a.5.5 0 0 1 .708 0l3 3a.5.5 0 0 1 0 .708l-10 10a.5.5 0 0 1-.168.11l-5 2a.5.5 0 0 1-.65-.65l2-5a.5.5 0 0 1 .11-.168zM11.207 2.5 13.5 4.793 14.793 3.5 12.5 1.207zm1.586 3L10.5 3.207 4 9.707V10h.5a.5.5 0 0 1 .5.5v.5h.5a.5.5 0 0 1 .5.5v.5h.293zm-9.761 5.175-.106.106-1.528 3.821 3.821-1.528.106-.106A.5.5 0 0 1 5 12.5V12h-.5a.5.5 0 0 1-.5-.5V11h-.5a.5.5 0 0 1-.468-.325" fill="white"/>
                                </svg>
                            </div>
                            <div class="ms-2"><span id="size_info">${size}</span> размер</div>
                        </div>
                        <div class="important-card__val">
                            <span id="quantity_info">${quantity}</span> <span>шт.</span>
                            <!-- Input field to edit the quantity, hidden by default -->
                            <input type="number" id="quantity_input" name="quantity_input" value="${quantity}" style="display:none; width: 68px;" min="1">
                        </div>
                        <input type="hidden" id="size" name="size" value="${size}"><input type="hidden" id="quantity" name="quantity" value="${quantity}">
                    </div>`);

    var total = countSocks();
    document.getElementById('socks_in_box_info').innerHTML = '';
    document.getElementById('socks_in_box_info').innerText = total;
    document.getElementById('size_order').value = '';
    document.getElementById('quantity_order').value = '1';

}


function socks_edit_size(el) {
    // Find quantity display and input fields
    const quantitySpan = $(el).closest('.important-card__size').find('#quantity_info');
    const quantityInput = $(el).closest('.important-card__size').find('#quantity_input');
    const quantityHidden = $(el).closest('.important-card__size').find('#quantity');

    // If the span is visible, switch to input field
    if (quantitySpan.is(':visible')) {
        quantitySpan.hide();  // Hide quantity span
        $(el).closest('.important-card__size').find('span:contains("шт.")').hide(); // Hide 'шт.'
        quantityInput.show().focus();  // Show and focus on input field
    }

    // Input validation for quantity
    quantityInput.on('input', function() {
        let value = parseInt(quantityInput.val(), 10);
        if (isNaN(value) || value < 1) {
            quantityInput.attr('placeholder', '0');  // Placeholder for invalid input
        } else if (value > 50000) {
            quantityInput.val(50000);  // Limit the value to 50000
        }
    });

    // When the input loses focus or Enter is pressed, save the value and switch back to span
    quantityInput.on('blur keypress', function(e) {
        if (e.type === 'blur' || (e.type === 'keypress' && e.key === 'Enter')) {
            let newQuantity = quantityInput.val();

            // If the input is empty or invalid, set it to 1 (auto-correct)
            if (newQuantity === '' || parseInt(newQuantity) < 1) {
                newQuantity = 1;
                quantityInput.val(1);
            }

            // Update hidden input, visible span, and the quantity info
            quantityHidden.val(newQuantity);
            quantitySpan.text(newQuantity);

            // Hide input and show quantity span and 'шт.'
            quantityInput.hide();
            quantitySpan.show();
            $(el).closest('.important-card__size').find('span:contains("шт.")').show(); // Show 'шт.'

            setSocks();  // Update the total shoes count
        }
    });
}


function check_add_same_size(size, quantity){
    var sizes = document.querySelectorAll('[id=size_info]');
    for (let i = 0; i < sizes.length; ++i) {
      if (sizes[i].innerText === size){
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
          document.getElementById('size_order').value = '';
          document.getElementById('quantity_order').value = '1';
          setSocks();
          return true
      }
    }
    return false
}

function isTenDigits(code){ return /^\d{10}$/.test(code); }

// проверка по префиксам, если включён режим агрегирования
function isAllowedTnved(code){
  if (!window.HAS_AGGR) return isTenDigits(code); // без агрегатора — лишь формат
  return isTenDigits(code) && (window.HAS_AGGR_LIST || []).some(prefix => code.startsWith(prefix));
}

function check_tnved(submit){
  if (submit !== 'submit') return true;

  const code = (document.getElementById('tnved_code').value || '').trim();

  if (!isTenDigits(code)){
    show_form_errors(['Заполните ТНВЭД: 10 цифр']);
    $('#form_errorModal').modal('show');
    return false;
  }

  if (!isAllowedTnved(code)){
    // сообщение в общий модал ошибок
    show_form_errors(['Код ТНВЭД не разрешён для текущего режима заказа. Проверьте ваш тнвэд во втором окне или обратитесь к модератору']);
    $('#form_errorModal').modal('show');

    // и показываем модалку со списком разрешённых (таблица)
    if (typeof showNotAllowedModal === 'function') {
      showNotAllowedModal(code);

    }
    return false;
  }

  return true; // всё ок — отправляем форму
}

function get_tnveds(url, csrf){
    let socks_type = document.getElementById('type').value;
    if(!socks_type){

        show_form_errors(['Выберите тип одежды до выбора ТНВЕД',]);
        $('#form_errorModal').modal('show');
        return
    }
    $.ajax({
        url: url,
        headers:{"X-CSRFToken": csrf},
        method:"POST",
        data: {'socks_type': socks_type},

        success:function(data)
        {
            if(data.status == 'danger' || data.status == 'error'){
                 show_form_errors([data.message,]);
                 $('#form_errorModal').modal('show');

            }
            else if( data.status == 'success'){
                $('#manual_tnved_insert').html(data);
                $("#manual_tnved_insert").append(data.tnved_report);
                $('#manualTnvedModal').modal('show')

            }
            else{
                 show_form_errors(['Обновите страницу...',]);
                 $('#form_errorModal').modal('show');

            }
        },
        error: function() {
         show_form_errors(['Ошибка CSRF. Обновите страницу и попробуйте снова',]);
         $('#form_errorModal').modal('show');
     }
   });
  }

function socks_manual_tnved(){
    const m_tnved = (document.getElementById("manual_tnved_input").value || "").trim();

    // 1. Базовая валидация: должно быть 10 цифр
    if (m_tnved && !/^\d{10}$/.test(m_tnved)){
        document.getElementById('manual_tnved_message').textContent =
            'Введите 10-значный код или оставьте пустым';
        setTimeout(clear_socks_tnved_m, 5000);
        return;
    }

    // 2. Проверка: код есть в глобальном списке all_tnved (тот что бэкенд передаёт для выбранного типа одежды)
    if (m_tnved && !all_tnved.includes(m_tnved)){
        document.getElementById('manual_tnved_message').textContent =
            'Некорректный ТНВЭД, попробуйте другой или обратитесь к вашему менеджеру';
        setTimeout(clear_socks_tnved_m, 5000);
        return;
    }

    // // 3. Проверка на режим "аггрегатор"
    // if (window.HAS_AGGR && m_tnved){
    //     const ok = (window.HAS_AGGR_LIST || []).some(prefix => m_tnved.startsWith(prefix));
    //     if (!ok){
    //         document.getElementById('manual_tnved_message').textContent = 'Код не разрешён.';
    //         showNotAllowedModal(m_tnved);
    //         return;
    //     }
    // }

    // 4. Всё прошло → пишем в поле формы и закрываем
    document.getElementById('tnved_code').value = m_tnved;
    clear_manual_tnved();
    $('#manualTnvedModal').modal('hide');
}

function clear_manual_tnved(){
    document.getElementById('manual_tnved_insert').innerHTML='';
    $('#manual_tnved_input').val('');

}

function clear_socks_tnved_m(){
    document.getElementById('manual_tnved_message').innerHTML='';
}


function renderAllowedTable(){
  const body = document.getElementById('tnvedAllowedBody');
  if (!body) return;
  const rows = (window.HAS_AGGR_LIST || []).map(code => {
    const desc = (window.HAS_AGGR_DICT && window.HAS_AGGR_DICT[code]) ? window.HAS_AGGR_DICT[code] : '';
    return `<tr><td><code>${code}</code></td><td>${desc}</td></tr>`;
  }).join('');
  body.innerHTML = rows || '<tr><td colspan="2" class="text-muted">Список пуст</td></tr>';
}

function showNotAllowedModal(){
  renderAllowedTable();
  const el = document.getElementById('tnvedDeniedModal');
  const modal = bootstrap.Modal.getOrCreateInstance(el);
  modal.show();
}

function selectTnved(code){
    // если включён аггрегатор — проверим по префиксам
    // if (window.HAS_AGGR) {
    //     const ok = window.HAS_AGGR_LIST.some(prefix => code.startsWith(prefix));
    //     if (!ok) {
    //         showNotAllowedModal();
    //         return;
    //     }
    // }

    // иначе принимаем
    document.getElementById('tnved_code').value = code;
    clear_manual_tnved();
    $('#manualTnvedModal').modal('hide');
}


document.addEventListener('DOMContentLoaded', function () {
    const switchInput = document.getElementById('aggrModeSwitch');

    function updateSwitchStyle() {
        const label = document.getElementById('aggrModeLabel');
        if (!label) return;

        const switchInput = document.getElementById('aggrModeSwitch');
        if (switchInput.checked) {
            label.textContent = 'Режим заказа по наборам';
            // label.classList.add('text-warning');
            switchInput.classList.add('bg-warning', 'border-warning');
            window.HAS_AGGR = true;
        } else {
            label.textContent = 'Режим заказа по позициям';
            // label.classList.remove('text-warning');
            switchInput.classList.remove('bg-warning', 'border-warning');
            window.HAS_AGGR = false;
        }
    }

    switchInput.addEventListener('change', updateSwitchStyle);

    // при загрузке страницы
    updateSwitchStyle();
});

document.addEventListener("input", function (e) {
    if (e.target.name && e.target.name.startsWith("size_")) {
        e.preventDefault();
        e.target.value = e.target.getAttribute("value") || 1;
    }
});

document.addEventListener("keydown", function (e) {
    if (e.target.name && e.target.name.startsWith("size_")) {
        e.preventDefault();
    }
});

document.addEventListener("wheel", function (e) {
    if (e.target.name && e.target.name.startsWith("size_")) {
        if (document.activeElement === e.target) {
            e.preventDefault();
        }
    }
});