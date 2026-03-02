
function parfum_check_sizes_quantity_valid(){
    var sizes = document.querySelectorAll('[id=size_info]');
    return sizes.length >= 1;
}



function parfum_clear_pos(){
    $('#trademark').val("");
    $('#volume').val("");

    $('#type').val('').trigger("change");
    $('#volume_type').val('').trigger("change");
    $('#package_type').val('').trigger("change");
    $('#material_package').val('').trigger("change");
    $('#country').val('').trigger("change");
    $('#rd_type').val('').trigger("change");
    $('#tax').val('').trigger("change");

    $('#tnved_code').val("");
    // $('#article_price').val("");
    $('#rd_name').val("");
    $('#rd_date').val("");

    $('#quantity').val('1');
    check_valid(document.getElementById('tax'));
    check_valid(document.getElementById('article_price'));

}

// function countParfum(){
//     var total = 1;
//     document.querySelectorAll('[id=quantity_info]').forEach(el=>total+=+parseInt(el.innerText, 10));
//     return total
//
// }


function setParfum(){
    var total = 0;

    var wp = document.getElementById('with_packages');
    var q_box = 1;
    if (wp.value === "True"){
        let q_box_raw = document.getElementById('box_quantity')
        if(q_box_raw){q_box = document.getElementById('box_quantity').value;}

    }

    document.getElementById('quantity').value;
    // document.getElementById('parfum_in_pos_info').innerHTML = '';
    // document.getElementById('parfum_in_pos_info').innerText= q_box*total;
    document.getElementById('parfum_in_box_info').innerHTML = '';
    document.getElementById('parfum_in_box_info').innerText = total;
}

function updateVolumeParams() {
        let volumeType = document.getElementById('volume_type').value;
        let volumeInput = document.getElementById('volume');


        if (volumeType === 'мл') {
            volumeInput.min = 5;
            volumeInput.step = 5;
            volumeInput.max = 5000;
        } else if (volumeType === 'л') {
            volumeInput.min = 1;
            volumeInput.step = 1;
            volumeInput.max = 100;
        } else {
            volumeInput.min = 1;
            volumeInput.step = 1;
            volumeInput.max = 10000;
        }
        volumeInput.value = volumeInput.min;
    }

function check_volume_input(field){
    if (!field.checkValidity()){
        if (parseInt(field.value, 10) > 10 || parseInt(field.value, 10) < 1){
            field.value= field.min;
            make_message('Проверьте корретность заполняемого значения Объема. в соответсвии с выбранными единицами измерения', 'error')}
        }

}

document.addEventListener("input", function (e) {
    if (e.target.name && e.target.name.startsWith("quantity")) {
        e.preventDefault();
        e.target.value = e.target.getAttribute("value") || 1;
    }
});

document.addEventListener("keydown", function (e) {
    if (e.target.name && e.target.name.startsWith("quantity")) {
        e.preventDefault();
    }
});

document.addEventListener("wheel", function (e) {
    if (e.target.name && e.target.name.startsWith("quantity")) {
        if (document.activeElement === e.target) {
            e.preventDefault();
        }
    }
});