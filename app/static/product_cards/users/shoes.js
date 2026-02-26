
function shoe_check_sizes_quantity_valid(){
    var sizes = document.querySelectorAll('[id=size_info]');
    return sizes.length >= 1;
}


function shoe_clear_pos(){
    $('#article').val("");
    $('#trademark').val("");
    $('#type').val('').trigger("change");
    $('#color').val('').trigger("change");
    $('#customColor').val("");
    $('#gender').val('').trigger("change");
    $('#material_top').val('').trigger("change");
    $('#material_lining').val('').trigger("change");
    $('#material_bottom').val('').trigger("change");
    $('#country').val('').trigger("change");
    $('#rd_type').val('').trigger("change");
    $('#tax').val('').trigger("change");

    $('#content').val("");
    $('#tnved_code').val("");
    // $('#article_price').val("0");
    $('#rd_name').val("");
    $('#rd_date').val("");

    $('#sizes_quantity').empty();
    check_valid(document.getElementById('tax'));
    check_valid(document.getElementById('article_price'));
    // check_valid(document.getElementById('trademark'));
    // check_valid(document.getElementById('article'));
}

function countShoes(){
    var total = 0;
    document.querySelectorAll('[id=quantity_info]').forEach(el=>total+=+parseInt(el.innerText, 10));
    return total

}


function setShoes(){
    var total = 0;

    var wp = document.getElementById('with_packages');
    var q_box = 1;
    if (wp.value === "True"){
        let q_box_raw = document.getElementById('box_quantity')
        if(q_box_raw){q_box = document.getElementById('box_quantity').value;}

    }

    document.querySelectorAll('[id=quantity_info]').forEach(el=>total+=+parseInt(el.innerText, 10));
    // document.getElementById('shoes_in_pos_info').innerHTML = '';
    // document.getElementById('shoes_in_pos_info').innerText= q_box*total;
    document.getElementById('shoes_in_box_info').innerHTML = '';
    document.getElementById('shoes_in_box_info').innerText = total;
}


function addShoeCell(){

    var size = document.getElementById('size_order').value;
    var quantity_val = document.getElementById('quantity_order').value;
    if(size.length< 2){
            return false
        }
    if(check_shoes_size(size)!==true){
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


    f.insertAdjacentHTML( 'beforeend', `<div class="important-card__item important-card__size ms-2"><div class="d-flex align-items-center g-3"><svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" onclick="$(this).closest('div').parent().remove();setShoes();" viewBox="0 0 20 20" fill="none"><path fill-rule="evenodd" clip-rule="evenodd" d="M4.34074 0.312213C8.07158 -0.104071 11.9285 -0.104071 15.6593 0.312213C17.7413 0.544517 19.4209 2.18214 19.6655 4.26889C20.1115 8.07671 20.1115 11.9234 19.6655 15.7312C19.4209 17.8179 17.7413 19.4555 15.6593 19.6878C11.9285 20.1041 8.07158 20.1041 4.34074 19.6878C2.25873 19.4555 0.579043 17.8179 0.33457 15.7312C-0.111523 11.9234 -0.111523 8.07671 0.33457 4.26889C0.579043 2.18214 2.25873 0.544517 4.34074 0.312213ZM10 9.08981H10.9117H15.1575C15.661 9.08981 16.0692 9.49734 16.0692 10C16.0692 10.5027 15.661 10.9102 15.1575 10.9102H10.9117C10.9117 10.9102 10.2506 10.9102 10 10.9102C9.74947 10.9102 9.46208 10.9102 9.46208 10.9102H9.08832H4.84265C4.33912 10.9102 3.93094 10.5027 3.93094 10C3.93094 9.49734 4.33912 9.08981 4.84265 9.08981H9.08832H10Z" fill="white" /></svg>
<!--                            <div class="ms-2" title="Нажать для изменения позиции. При нажатии, размер и количество перемещаются из накладной в форму!">-->
<!--                                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" onclick="shoes_edit_size($(this).closest('div').parent());"-->
<!--                                     fill="none" class="bi bi-pencil" viewBox="0 0 20 20">-->
<!--                                  <path fill-rule="evenodd" clip-rule="evenodd" d="M12.146.146a.5.5 0 0 1 .708 0l3 3a.5.5 0 0 1 0 .708l-10 10a.5.5 0 0 1-.168.11l-5 2a.5.5 0 0 1-.65-.65l2-5a.5.5 0 0 1 .11-.168zM11.207 2.5 13.5 4.793 14.793 3.5 12.5 1.207zm1.586 3L10.5 3.207 4 9.707V10h.5a.5.5 0 0 1 .5.5v.5h.5a.5.5 0 0 1 .5.5v.5h.293zm-9.761 5.175-.106.106-1.528 3.821 3.821-1.528.106-.106A.5.5 0 0 1 5 12.5V12h-.5a.5.5 0 0 1-.5-.5V11h-.5a.5.5 0 0 1-.468-.325" fill="white"/>-->
<!--                                </svg>-->
<!--                            </div>-->
                            <div class="ms-2"><span id="size_info">${size}</span> размер</div>
                        </div>
                        <div class="important-card__val">
                            <span id="quantity_info">${quantity}</span> <span>шт.</span>
                            <!-- Input field to edit the quantity, hidden by default -->
                            <input type="number" id="quantity_input" name="quantity_input" value="${quantity}" style="display:none; width: 68px;" min="1">
                        </div>
                        <input type="hidden" id="size" name="size" value="${size}"><input type="hidden" id="quantity" name="quantity" value="${quantity}">
                    </div>`);
        // `<div class="row mb-3" id="container_element"><div class="col-md-6 col-xs-12 mt-1"><input type="text" name="size" id="size" minlength="2" maxlength="5" class="form-control mb-1" placeholder="Размер 16 - 56.5" autocomplete="off" oninput="check_shoes_size(value)||(value='');" value="${size}" required></div><div class="col-md-6 col-xs-12 mt-1"><input type="number" name="quantity" id="quantity" class="form-control ms-1" value="1" min="1"  oninput="validity.valid||(value='');javascript:setShoes();" max="${max_param}" placeholder="${placeholder_param}" required></div></div>`);

    var total = countShoes();
    document.getElementById('shoes_in_box_info').innerHTML = '';
    document.getElementById('shoes_in_box_info').innerText = total;
    document.getElementById('size_order').value = '';
    document.getElementById('quantity_order').value = '1';

}

// function shoes_edit_size(parent_block){
    // let size = parent_block.find('#size_info').html();
    // let quantity = parent_block.parent().find('#quantity_info').html();
    // // console.log(size, quantity);
    // $('#size_order').val(size);
    // $('#quantity_order').val(quantity);
    //
    // parent_block.parent().remove();
function shoes_edit_size(el) {
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

            setShoes();  // Update the total shoes count
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
          setShoes();
          return true
      }
    }
    return false
}

function deleteCell(){
    var cur = $(this).closest('div');
    cur.parent().remove();
    setShoes();
}

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