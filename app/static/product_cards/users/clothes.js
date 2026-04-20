function clothes_check_sizes_quantity_valid() {
    var sizes = document.querySelectorAll('[id=size_info]');
    return sizes.length >= 1;
}



function clothes_clear_pos() {
    window.__silenceReset = true;
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
    window.__silenceReset = false;
}

function clothes_content_add() {
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
    if (clothes_nat_array.includes(content)) {
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

function countClothes() {
    var total = 0;
    document.querySelectorAll('[id=quantity_info]').forEach(el => total += parseInt(el.innerText, 10));
    return total

}


function setClothes() {
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
    document.getElementById('clothes_in_box_info').innerHTML = '';
    if (isNaN(total)){total=0;}
    document.getElementById('clothes_in_box_info').innerText = total;
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
            setClothes();
            // $('#size_order').val('').trigger("change");
            document.getElementById('size_order').value = '';
            document.getElementById('quantity_order').value = '1';
            return true
        }
    }

    return false
}

// function check_clothes_size(value) {
//
//
//     // console.log(value);
//     if (value.length > 0) {
//
//         for (let i = 0; i < check_list.length; i++) {
//
//             if (check_list[i].startsWith(value)) {
//                 // console.log(check_list[i]);
//                 return true
//             }
//         }
//         show_form_errors(["Введите корректный размер: от 12 до 74 с шагом 2, либо особый размер вида 12-14, OVERSIZE !",]);
//         $('#form_errorModal').modal('show');
//         return false
//     } else {
//         return false
//     }
// }

// function check_clothes_size_on_add(value) {
//
//     // console.log(value);
//     if (value.length > 0) {
//
//         if (check_list.includes(value)) {
//             // console.log(check_list[i]);
//             return true
//         }
//
//         show_form_errors(["Введите корректный размер: от 12 до 74 с шагом 2, либо особый размер вида 12-14, OVERSIZE !",]);
//         $('#form_errorModal').modal('show');
//         return false
//     } else {
//         return false
//     }
// }

function perform_free_size_input(clothingType){
    // let subcategoryInputBlock = '';

    // Если subcategory == 'underwear', добавляем input
    // if (subcategory === 'underwear') {
    let subcategoryInputBlock = `
        <button class="btn btn-outline-secondary mb-3" type="button" onclick="document.getElementById('freeInputBlock${clothingType}').classList.toggle('d-none')">Свободный ввод</button>
        <div id="freeInputBlock${clothingType}" class="d-none">
            <p>Поле свободного ввода размера типа ${clothingType} (введите размер, количество и нажмите добавить)</p>
            <div class="input-group mb-3">
                <input type="text" class="form-control" id="subcategorySizeInput${clothingType}" placeholder="Введите размер"
                       maxlength="8"  pattern="[A-Za-z0-9]([-,.;]?[A-Za-z0-9]){0,7}" title="Только латиница и цифры (до 8 символов)"
                       oninput="if(this.value.toUpperCase() === 'ЕДИНЫЙ'){ this.value = ''; }" 
                       required>
                <input type="hidden" class="form-control" id="subcategorySizeQuantity${clothingType}" placeholder="Кол-во" min="1" value="1" readonly required>
                <button class="btn btn-accent" type="button" onclick="subcategory_size_add('${clothingType}')">Добавить</button>
                <div class="invalid-feedback d-block" id="subcategorySizeError${clothingType}"></div>
            </div>
        </div>`;
    // }
    return subcategoryInputBlock
}

function clothesAccordionId(clothingType) {
    return String(clothingType).replace(/[^A-Za-zА-Яа-яЁё0-9_-]/g, '_');
}

function preventNegativeDimensionInput(event) {
    if (event.key === '-' || event.key === '+') {
        event.preventDefault();
    }
}

function normalizePositiveDimensionInput(input) {
    if (input.value && Number(input.value.replace(',', '.')) < 0) {
        input.value = '';
    }
}

function createLengthWidthSizeBlock(clothingType) {
    const typeId = clothesAccordionId(clothingType);
    return `
        <div class="mb-3">
            <p>Введите длину и ширину изделия, затем нажмите +</p>
            <div class="d-flex align-items-start gap-2 flex-nowrap">
                <input type="number" class="form-control" id="lengthWidthLength${typeId}"
                       min="0.01" step="any" placeholder="Длина" style="width: 120px; flex: 0 0 120px;"
                       onkeydown="preventNegativeDimensionInput(event)"
                       oninput="normalizePositiveDimensionInput(this)">
                <span class="pt-2 fw-bold">*</span>
                <input type="number" class="form-control" id="lengthWidthWidth${typeId}"
                       min="0.01" step="any" placeholder="Ширина" style="width: 120px; flex: 0 0 120px;"
                       onkeydown="preventNegativeDimensionInput(event)"
                       oninput="normalizePositiveDimensionInput(this)">
                <select class="form-control" id="lengthWidthUnit${typeId}" style="width: 86px; flex: 0 0 86px;">
                    <option value="мм" selected>мм</option>
                    <option value="см">см</option>
                </select>
                <button class="btn btn-accent" type="button"
                        style="width: 44px; min-width: 44px; max-width: 44px; height: 38px; min-height: 38px; max-height: 38px; flex: 0 0 44px; padding: 0; line-height: 1; display: inline-flex; align-items: center; justify-content: center;"
                        onclick="addLengthWidthClothesSize('${clothingType}')">+</button>
            </div>
            <div class="invalid-feedback d-block" id="lengthWidthError${typeId}"></div>
        </div>`;
}

function addLengthWidthClothesSize(clothingType) {
    const typeId = clothesAccordionId(clothingType);
    const lengthInput = document.getElementById(`lengthWidthLength${typeId}`);
    const widthInput = document.getElementById(`lengthWidthWidth${typeId}`);
    const unitInput = document.getElementById(`lengthWidthUnit${typeId}`);
    const errorBlock = document.getElementById(`lengthWidthError${typeId}`);

    const lengthValue = lengthInput.value.trim();
    const widthValue = widthInput.value.trim();
    const dimensionPattern = /^\d+(?:[.,]\d+)?$/;

    if (
        !dimensionPattern.test(lengthValue) ||
        !dimensionPattern.test(widthValue) ||
        Number(lengthValue.replace(',', '.')) <= 0 ||
        Number(widthValue.replace(',', '.')) <= 0
    ) {
        errorBlock.textContent = "Введите длину и ширину числом больше 0.";
        return;
    }

    errorBlock.textContent = "";
    const unitValue = unitInput.value || 'мм';
    const size = `${lengthValue}*${widthValue} ${unitValue}`;
    const sizesQuantityBlock = document.getElementById('sizes_quantity');
    const existingSizeBlocks = sizesQuantityBlock.getElementsByClassName('important-card__item');

    for (let block of existingSizeBlocks) {
        let sizeSpan = block.querySelector('#size_info');
        let typeSpan = block.querySelector('#size_type_info');
        if (sizeSpan && typeSpan && sizeSpan.textContent.trim() === size && typeSpan.textContent.trim() === clothingType) {
            lengthInput.value = '';
            widthInput.value = '';
            setClothes();
            return;
        }
    }

    let sizeQuantityHTML = `
        <div class="important-card__item important-card__size ms-2">
            <div class="d-flex align-items-center g-3">
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" onclick="$(this).closest('div').parent().remove();setClothes();"
                    viewBox="0 0 20 20" fill="none">
                    <path fill-rule="evenodd" clip-rule="evenodd"
                        d="M4.34074 0.312213C8.07158 -0.104071 11.9285 -0.104071 15.6593 0.312213C17.7413 0.544517 19.4209 2.18214 19.6655 4.26889C20.1115 8.07671 20.1115 11.9234 19.6655 15.7312C19.4209 17.8179 17.7413 19.4555 15.6593 19.6878C11.9285 20.1041 8.07158 20.1041 4.34074 19.6878C2.25873 19.4555 0.579043 17.8179 0.33457 15.7312C-0.111523 11.9234 -0.111523 8.07671 0.33457 4.26889C0.579043 2.18214 2.25873 0.544517 4.34074 0.312213ZM10 9.08981H10.9117H15.1575C15.661 9.08981 16.0692 9.49734 16.0692 10C16.0692 10.5027 15.661 10.9102 15.1575 10.9102H10.9117C10.9117 10.9102 10.2506 10.9102 10 10.9102C9.74947 10.9102 9.46208 10.9102 9.46208 10.9102H9.08832H4.84265C4.33912 10.9102 3.93094 10.5027 3.93094 10C3.93094 9.49734 4.33912 9.08981 4.84265 9.08981H9.08832H10Z"
                        fill="white" />
                </svg>
                <div class="ms-2">
                    <span id="size_info">${size}</span>
                    <span id="size_type_info" style="font-size: 10px">${clothingType}</span>
                </div>
            </div>
            <div class="important-card__val"><span id="quantity_info">1</span> <span>шт.</span></div>
            <input type="hidden" name="size" value="${size}">
            <input type="hidden" name="quantity" value="1">
            <input type="hidden" id="size_type" name="size_type" value="${clothingType}">
        </div>`;

    sizesQuantityBlock.innerHTML += sizeQuantityHTML;
    lengthInput.value = '';
    widthInput.value = '';
    setClothes();
}

function chooseSizeClothes(subcategory) {
    let divBlock = document.getElementById('sizesClothesDiv');
    let content = '';
    // let subcategoryInputBlock = '';

    // Перебираем типы одежды и их размеры
    for (let clothingType in clothes_types_sizes_dict) {
        if (clothes_types_sizes_dict.hasOwnProperty(clothingType)) {
            let sizes = clothes_types_sizes_dict[clothingType];
            let sizesBlock = clothingType === clothes_length_width_size_type
                ? createLengthWidthSizeBlock(clothingType)
                : create_size_blocks(sizes, clothingType);
            let free_size_input = '';
            if (!['ОСОБЫЕ_РАЗМЕРЫ', 'РОССИЯ', clothes_length_width_size_type].includes(clothingType)){
                free_size_input = perform_free_size_input(clothingType);
                }
            const typeId = clothesAccordionId(clothingType);

            content += `
                <div class="accordion-item">
                    <h2 class="accordion-header" id="heading_${typeId}">
                        <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#collapse_${typeId}" aria-expanded="false" aria-controls="collapse_${typeId}">
                            ${clothingType}
                        </button>
                    </h2>
                    <div id="collapse_${typeId}" class="accordion-collapse collapse" aria-labelledby="heading_${typeId}">
                        <div class="accordion-body">
                            <div>${free_size_input}</div>
                            <div class="row">${sizesBlock}</div>
                        </div>
                    </div>
                </div>`;
        }
    }

    divBlock.innerHTML = `
        <div class="modal fade" id="sizesClothesModal" tabindex="-1" role="dialog" aria-labelledby="sizesClothesModalLabel" aria-hidden="true"  data-bs-backdrop="static" data-bs-keyboard="false">
            <div class="modal-dialog modal-lg modal-dialog-scrollable" role="document">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title" id="sizesClothesModalLabel">Выберите размеры одежды.</h5>
                        <button type="button" class="btn-close" onclick="clear_clothesSizes_modal();" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body px-5">
                        
                        <p>Для выбора размера, кликните по нему, справа от размера появится поле - введите количество. После ввода всех необходимых размеров нажмите кнопку <b>Закрыть</b></p>
                        <p>Если нужно убрать размер, кликните на него</p>
                        
                        <div class="accordion" id="accordionSizes" style="background-color: #f0f0f0;">${content}</div>
                    </div>
                    <div class="modal-footer d-flex flex-column">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal" onclick="clear_clothesSizes_modal();">Закрыть</button>
                    </div>
                </div>
            </div>
        </div>`;

    $('#sizesClothesModal').modal('show');
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
    let sizesQuantityBlock = document.getElementById('sizes_quantity');

    // Создаем объект для хранения уже добавленных размеров
    let existingSizes = {};
    sizesQuantityBlock.querySelectorAll('.important-card__item').forEach(item => {
        let size = item.querySelector('#size_info').textContent.trim();
        let quantity = parseInt(item.querySelector('#quantity_info').textContent.trim(), 10);
        let sizeType = item.querySelector('#size_type_info').textContent.trim();
        existingSizes[size] = { quantity, sizeType, element: item };
    });

    // Обрабатываем выбранные размеры из формы
    let selectedSizes = document.querySelectorAll('#sizesClothesModal .form-control:not([readonly]):not([disabled])');
    let newSizes = {};
    selectedSizes.forEach(input => {
        let size = input.getAttribute('id').replace('size_', '').trim();
        let quantity = parseInt(input.value.trim(), 10);
        let sizeType = input.getAttribute('data-size-type') || "";

        if (size.startsWith('subcategorySize')) return;
        if (special_clothes_sizes.includes(size)) {
            sizeType = 'МЕЖДУНАРОДНЫЙ';
        }

        newSizes[size] = { quantity, sizeType };

        // Если размер уже есть, обновляем количество
        if (existingSizes[size]) {
            existingSizes[size].element.querySelector('#quantity_info').textContent = quantity;
            existingSizes[size].element.querySelector('input[name="quantity"]').value = quantity;
        } else {
            // Создаем новый элемент
            let sizeQuantityHTML = `
                <div class="important-card__item important-card__size ms-2">
                    <div class="d-flex align-items-center g-3">
                        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" onclick="$(this).closest('div').parent().remove();setClothes();"
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
                    <input type="hidden" id="size" name="size" value="${size}">
                    <input type="hidden" id="quantity" name="quantity" value="${quantity}">
                    <input type="hidden" id="size_type" name="size_type" value="${sizeType}">
                </div>`;

            sizesQuantityBlock.innerHTML += sizeQuantityHTML;
        }
    });

    Object.keys(existingSizes).forEach(size => {
        if (!newSizes[size] && !Object.values(clothes_types_sizes_dict).some(sizes => sizes.includes(size))) {
            return;
        }
        if (!newSizes[size]) {
            existingSizes[size].element.remove();
        }
    });
    setClothes();
}


function subcategory_size_add(clothingType) {
    let sizeInput = document.getElementById(`subcategorySizeInput${clothingType}`);
    let quantityInput = document.getElementById(`subcategorySizeQuantity${clothingType}`);
    let errorBlock = document.getElementById(`subcategorySizeError${clothingType}`);

    let size = sizeInput.value.trim();
    let quantity = parseInt(quantityInput.value.trim(), 10);

    let sizePattern = /^[A-Za-z0-9]([-]?[A-Za-z0-9]|[.,]?[0-9]){0,7}$/;

    // Очистка ошибок при вводе
    sizeInput.addEventListener('input', () => errorBlock.textContent = "");
    quantityInput.addEventListener('input', () => errorBlock.textContent = "");

    // Проверка, есть ли размер в словаре
    let foundType = null;
    for (let type in clothes_types_sizes_dict) {
        if (clothes_types_sizes_dict[type].includes(size)) {
            foundType = type;
            break;
        }
    }

    if (foundType) {
        errorBlock.textContent = `Размер '${size}' уже существует в категории '${foundType}'.`;
        return;
    }

    // Проверка на корректность ввода
    if (!sizePattern.test(size)) {
        errorBlock.textContent = "Размер должен содержать только латиницу, цифры и знак дефиса между ними (1-8 символов). Допускаются дробные размеры";
        return;
    }
    if (isNaN(quantity) || quantity < 1) {
        errorBlock.textContent = "Введите корректное количество (минимум 1).";
        return;
    }

    // Очистка ошибок
    errorBlock.textContent = "";

    let sizesQuantityBlock = document.getElementById('sizes_quantity');

    // Проверяем, есть ли уже такой размер в карточке
    let existingSizeBlocks = sizesQuantityBlock.getElementsByClassName('important-card__item');
    let sizeFound = false;

    for (let block of existingSizeBlocks) {
        let sizeSpan = block.querySelector('#size_info');
        if (sizeSpan && sizeSpan.textContent === size) {
            let quantitySpan = block.querySelector('#quantity_info');
            let newQuantity = quantity;
            quantitySpan.textContent = newQuantity; // Обновляем количество
            block.querySelector('input[name="quantity"]').value = newQuantity;
            sizeFound = true;
            break;
        }
    }

    // Если размер не найден, создаем новый блок
    if (!sizeFound) {
        let sizeQuantityHTML = `
            <div class="important-card__item important-card__size ms-2">
                <div class="d-flex align-items-center g-3">
                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" onclick="$(this).closest('div').parent().remove();setClothes();"
                        viewBox="0 0 20 20" fill="none">
                        <path fill-rule="evenodd" clip-rule="evenodd"
                            d="M4.34074 0.312213C8.07158 -0.104071 11.9285 -0.104071 15.6593 0.312213C17.7413 0.544517 19.4209 2.18214 19.6655 4.26889C20.1115 8.07671 20.1115 11.9234 19.6655 15.7312C19.4209 17.8179 17.7413 19.4555 15.6593 19.6878C11.9285 20.1041 8.07158 20.1041 4.34074 19.6878C2.25873 19.4555 0.579043 17.8179 0.33457 15.7312C-0.111523 11.9234 -0.111523 8.07671 0.33457 4.26889C0.579043 2.18214 2.25873 0.544517 4.34074 0.312213ZM10 9.08981H10.9117H15.1575C15.661 9.08981 16.0692 9.49734 16.0692 10C16.0692 10.5027 15.661 10.9102 15.1575 10.9102H10.9117C10.9117 10.9102 10.2506 10.9102 10 10.9102C9.74947 10.9102 9.46208 10.9102 9.46208 10.9102H9.08832H4.84265C4.33912 10.9102 3.93094 10.5027 3.93094 10C3.93094 9.49734 4.33912 9.08981 4.84265 9.08981H9.08832H10Z"
                            fill="white" />
                    </svg>
                    <div class="ms-2">
                        <span id="size_info">${size}</span>
                        <span id="size_type_info" style="font-size: 10px">${clothingType}</span>
                    </div>
                </div>
                <div class="important-card__val"><span id="quantity_info">${quantity}</span> <span>шт.</span></div>
                <input type="hidden" name="size" value="${size}">
                <input type="hidden" name="quantity" value="${quantity}">
                <input type="hidden" id="size_type" name="size_type" value="${clothingType}">
            </div>`;

        sizesQuantityBlock.innerHTML += sizeQuantityHTML;
    }

    // Очистка полей ввода
    sizeInput.value = '';
    // quantityInput.value = '1';
    setClothes();
}


function clear_clothesSizes_modal() {
    document.getElementById('sizesClothesDiv').innerHTML = '';
}

function check_clothes_quantity_input(block){
    var value = parseFloat(block.value);
    var min = parseFloat(block.min);
    var max = parseFloat(block.max);

    // Check if the input value falls outside the specified range
    if (value < min || value > max || isNaN(value)) {
        // If so, set the input value to 0
        block.value = 1;
    }
}


function create_size_blocks(sizes, clothingType) {
    let sizesBlock = '';
    const special_clothes_sizes = ["ЕДИНЫЙ РАЗМЕР", "ONE SIZE"];
    let quantityMap = {};

    // собираем выбранные размеры из карточки
    document.querySelectorAll('#sizes_quantity .important-card__size').forEach(item => {
        let sizeTypeInCard = item.querySelector('#size_type_info').textContent;
        let sizeInCard = item.querySelector('#size_info').textContent;
        let quantity = parseInt(item.querySelector('#quantity_info').textContent, 10);

        if (
            clothingType === 'ОСОБЫЕ_РАЗМЕРЫ' &&
            sizeTypeInCard === 'МЕЖДУНАРОДНЫЙ' &&
            special_clothes_sizes.includes(sizeInCard)
        ) {
            quantityMap[sizeInCard] = quantity;
        } else if (sizeTypeInCard === clothingType) {
            quantityMap[sizeInCard] = quantity;
        }
    });

    // строим блоки
    for (let i = 0; i < sizes.length; i++) {
        let size = sizes[i];

        let sizeAlreadyExists = quantityMap.hasOwnProperty(size);
        let quantity = sizeAlreadyExists ? quantityMap[size] : 0;

        const checkClass    = sizeAlreadyExists ? '' : 'd-none';
        const inputDisabled = sizeAlreadyExists ? '' : 'disabled';
        const inputValue    = sizeAlreadyExists ? `value="${quantity}"` : `value=""`;

        sizesBlock += `
            <div class="col-md-4 border-bottom border-0 border-warning text-center mt-1">
                <div class="row align-items-center">
                    <div class="col-5 my-2" onclick="setQuantitySize('${size}');" style="cursor:pointer">
                        <span>${size}</span>
                        <span id="check_${size}" class="faded size-check ms-2 ${checkClass}">✓</span>
                    </div>

                    <div class="col-7">
                        <input type="number" class="form-control ms-1 input-light-grey"
                            min="1" max="50000"
                            id="size_${size}" name="size_${size}"
                            style="display:none;"
                            placeholder="0"
                            data-size-type="${clothingType}"
                            ${inputValue}
                            ${inputDisabled}
                            onchange="check_clothes_quantity_input(this);updateSizesQuantityBlock()">
                    </div>
                </div>
            </div>`;
    }

    return sizesBlock;
}

function deleteCell() {
    var cur = $(this).closest('div');
    cur.parent().remove();
    setClothes();
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

function get_tnveds(url, csrf, subcategory) {
    const typeEl   = document.getElementById('type');
    const genderEl = document.getElementById('gender');
    const cl_type = typeEl ? (typeEl.value || '') : '';
    const gender  = genderEl ? (genderEl.value || '') : '';

    // Проверяем, если subcategory пустая, 'common' или None
    const needsGenderCheck =
        subcategory === '' ||
        subcategory === 'common' ||
        subcategory === 'underwear' ||
        subcategory === null ||
        subcategory === 'None'; // Jinja может отрендерить None как строку

    if (!cl_type || (needsGenderCheck && !gender)) {
        const msg =
            !cl_type && (needsGenderCheck && !gender)
                ? 'Выберите тип одежды и пол до выбора ТНВЭД'
                : !cl_type
                    ? 'Выберите тип одежды до выбора ТНВЭД'
                    : 'Выберите пол до выбора ТНВЭД';

        show_form_errors([msg]);
        $('#form_errorModal').modal('show');
        return;
    }

    $.ajax({
        url: url,
        headers: { "X-CSRFToken": csrf },
        method: "POST",
        data: Object.assign(
            { cl_type: cl_type, subcategory: subcategory },
            needsGenderCheck ? { gender: gender } : {}
        ),
        success: function (data) {
            if (data.status === 'danger' || data.status === 'error') {
                show_form_errors([data.message]);
                $('#form_errorModal').modal('show');
            } else if (data.status === 'success') {
                $('#manual_tnved_insert').html(data);
                $("#manual_tnved_insert").append(data.tnved_report);
                $('#manualTnvedModal').modal('show');
            } else {
                show_form_errors(['Обновите страницу...']);
                $('#form_errorModal').modal('show');
            }
        },
        error: function () {
            show_form_errors(['Ошибка CSRF. Обновите страницу и попробуйте снова']);
            $('#form_errorModal').modal('show');
        }
    });
}

function getTypeValue() {
    const el = document.getElementById('type');
    return el ? (el.value || '').trim() : '';
  }

  // простой гард только для gender и только на onclick
  function genderClickGuard(e) {
    if (getTypeValue()) return true; // тип выбран — всё ок

    // тип не выбран — блокируем и показываем ошибку
    if (e && e.preventDefault) e.preventDefault();
    show_form_errors(['Сначала выберите вид одежды']);
    $('#form_errorModal').modal('show');

    // если это select2 — закрыть выпадашку на всякий случай
    var $g = $('#gender');
    if ($.fn.select2 && $g.data('select2')) {
      $g.select2('close');
    }


    return false;
  }


function get_genders(url, csrf, subcategory, preferGender) {
    const typeEl   = document.getElementById('type');
    const genderEl = document.getElementById('gender');
    if (!typeEl || !genderEl) return;

    const cl_type = (typeEl.value || '').trim();

    // если подкатегория не требует пола — сразу выключаем селект и выходим
    if (!['', 'common', 'underwear', null, 'None'].includes(subcategory)) {
        return;
    }

    // тип не выбран — ошибка
    if (!cl_type) {
        show_form_errors(['Выберите тип одежды до выбора пола']);
        $('#form_errorModal').modal('show');
        try { typeEl.classList.add('is-invalid'); typeEl.focus(); } catch(e){}
        return;
    }

    // если уже подгружали для этого типа — всё равно попробуем применить preferGender (если пришёл)
    const loadedFor = genderEl.getAttribute('data-loaded-for-type');
    if (loadedFor === cl_type && genderEl.options.length > 1 && !genderEl.disabled) {
        if (preferGender) {
            applyPreferredGender(preferGender);
        }
        return;
    }

    fillGenderSelect([], { keepValue:false, enabled:false, placeholder:'Загрузка…' });

    $.ajax({
        url: url,
        headers: { "X-CSRFToken": csrf },
        method: "POST",
        data: { cl_type: cl_type, subcategory: subcategory },
        success: function (data) {
            if (data.status === 'danger' || data.status === 'error') {
                fillGenderSelect([], { keepValue:false, enabled:false, placeholder:'Ошибка загрузки' });
                show_form_errors([data.message || 'Ошибка при получении полов']);
                $('#form_errorModal').modal('show');
                return;
            }

            const options = Array.isArray(data.genders) ? data.genders : [];

            if (!options.length) {
                fillGenderSelect([], { keepValue:false, enabled:false, placeholder:'Список полов не найден' });
                show_form_errors(['Для выбранного типа не найден список полов']);
                $('#form_errorModal').modal('show');
                return;
            }

            // успех — наполняем и включаем
            fillGenderSelect(options, { keepValue:true, enabled:true, placeholder:'Выберите пол...' });
            $('#gender').attr('required', true);
            genderEl.setAttribute('data-loaded-for-type', cl_type);

            // ✅ применяем пол из copied_order, если передали
            if (preferGender) {
                applyPreferredGender(preferGender, options);
            }

            // если используете select2 — открыть дропдаун только если пол не проставили
            if ($ && $.fn && $.fn.select2) {
                if (!genderEl.value) $('#gender').select2('open');
            } else {
                if (!genderEl.value) genderEl.focus();
            }
        },
        error: function () {
            fillGenderSelect([], { keepValue:false, enabled:false, placeholder:'Ошибка сети/CSRF' });
            show_form_errors(['Ошибка CSRF. Обновите страницу и попробуйте снова']);
            $('#form_errorModal').modal('show');
        }
    });
}

function applyPreferredGender(preferGender, options) {
    const genderEl = document.getElementById('gender');
    if (!genderEl) return;

    const wanted = (preferGender || '').toString().trim();
    if (!wanted) return;

    const exists = Array.isArray(options)
        ? options.includes(wanted)
        : Array.from(genderEl.options).some(o => o.value === wanted);

    if (!exists) return;

    window.__gender_autofill = true;   // ✅ start
    genderEl.value = wanted;

    if (window.$) {
        $('#gender').trigger('change.select2');
        $('#gender').trigger('change'); // не почистит tnved, потому что флаг true
    }

    // сброс флага в микротаске/тик — чтобы следующие ручные изменения чистили tnved
    setTimeout(() => { window.__gender_autofill = false; }, 0); // ✅ end
}

function fillGenderSelect(genders, { keepValue = true, enabled = true, placeholder = 'Выберите пол...' } = {}) {
    const select = document.getElementById('gender');
    if (!select) return;

    const prev = select.value;

    // очистка
    select.innerHTML = '';

    // плейсхолдер
    const ph = document.createElement('option');
    ph.disabled = true;
    ph.selected = true;
    ph.value = '';
    ph.textContent = placeholder;
    select.appendChild(ph);

    // опции
    (genders || []).forEach(el => {
        const opt = document.createElement('option');
        opt.value = el;
        opt.textContent = el;
        select.appendChild(opt);
    });

    // восстановление выбранного значения
    if (keepValue && prev && genders && genders.includes(prev)) {
        select.value = prev;
        ph.selected = false;
    }

    // (де)активируем
    select.disabled = !enabled;

    // если есть UI-плагины
    if (window.$) {
        $('#gender').trigger('change.select2');
        $('#gender').trigger('change');
    }
}


function clothes_manual_tnved(){
    const m_tnved = (document.getElementById("manual_tnved_input").value || "").trim();

    // 1. Базовая валидация: должно быть 10 цифр
    if (m_tnved && !/^\d{10}$/.test(m_tnved)){
        document.getElementById('manual_tnved_message').textContent =
            'Введите 10-значный код или оставьте пустым';
        setTimeout(clear_clothes_tnved_m, 5000);
        return;
    }

    // 2. Проверка: код есть в глобальном списке all_tnved (тот что бэкенд передаёт для выбранного типа одежды)
    if (m_tnved && !all_tnved.includes(m_tnved)){
        document.getElementById('manual_tnved_message').textContent =
            'Некорректный ТНВЭД, попробуйте другой или обратитесь к вашему менеджеру';
        setTimeout(clear_clothes_tnved_m, 5000);
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
    // $('#manual_tnved_input').val('');

}

function clear_clothes_tnved_m(){
    document.getElementById('manual_tnved_message').innerHTML='';
}


function clear_gender_select(){
    $('#gender').val('').trigger("change");
}

function clear_tnved_input(){
    document.getElementById('tnved_code').value='';
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

function showNotAllowedModal(code){
    // вставляем введённый код внутрь <span id="tnvedCodeOrderAggrModalValue">
  const span = document.getElementById('tnvedCodeOrderAggrModalValue');
  if (span) {
    span.textContent = code || '';
  }

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


// document.addEventListener('DOMContentLoaded', function () {
//     const switchInput = document.getElementById('aggrModeSwitch');
//
//     function updateSwitchStyle() {
//         const label = document.getElementById('aggrModeLabel');
//         if (!label) return;
//
//         const switchInput = document.getElementById('aggrModeSwitch');
//         if (switchInput.checked) {
//             label.textContent = 'Режим заказа по наборам';
//             // label.classList.add('text-warning');
//             switchInput.classList.add('bg-warning', 'border-warning');
//             window.HAS_AGGR = true;
//         } else {
//             label.textContent = 'Режим заказа по позициям';
//             // label.classList.remove('text-warning');
//             switchInput.classList.remove('bg-warning', 'border-warning');
//             window.HAS_AGGR = false;
//         }
//     }
//
//     switchInput.addEventListener('change', updateSwitchStyle);
//
//     // при загрузке страницы
//     updateSwitchStyle();
// });

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
