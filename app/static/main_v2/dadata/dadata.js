
// Запрашиваем токен с сервера
$.ajax({
    url: getDadataTokenUrl,
    method: 'GET',
    dataType: 'json',
    success: function(data) {
        const token = data.token;

        // Используем полученный токен для работы с DaData
        $("#organization").suggestions({
            minChars: 10,
            token: token, // Токен, полученный с сервера
            type: "PARTY",
            onSelect: function(suggestion) {
                let company_idn = document.getElementById('company_idn');
                let company_type = document.getElementById('company_type');
                let company_name = document.getElementById('company_name');
                let modal_company_idn = document.getElementById('modal_company_idn');
                let modal_company_name = document.getElementById('modal_company_name');

                company_idn.value = suggestion.data.inn;
                company_type.value = suggestion.data.opf.short;
                company_name.value = suggestion.data.name.full;
                modal_company_idn.value = suggestion.data.inn;
                modal_company_name.value = suggestion.data.name.full;

                if (count_words(document.getElementById('organization').value) < 3 || document.getElementById('organization').value.length < 5) {
                    document.getElementById('organization').classList.remove('is-valid');
                    document.getElementById('organization').classList.add('is-invalid');
                } else {
                    document.getElementById('organization').classList.remove('is-invalid');
                    document.getElementById('organization').classList.add('is-valid');
                }
            }
        });
    },
    error: function(error) {
        console.error('Ошибка при получении токена:', error);
    }
});


function count_words(answer){
     answer = answer.replace(/(^\s*)|(\s*$)/gi,"");
     answer = answer.replace(/[ ]{2,}/gi," ");
     return answer.split(' ').length;
  }


// function check_blank_start (){
//     var company_name = document.getElementById("company_name");
//
//     if (company_name.value.startsWith(' ')){
//         company_name.value='';
//         alert("Наименование компании не может начинаться с пробела!");
//     }
// }

function manual_org_change(){
    document.getElementById('company_idn').value=document.getElementById('modal_company_idn').value;
    document.getElementById('company_type').value=document.getElementById('modal_company_type').value;
    document.getElementById('company_name').value=document.getElementById('modal_company_name').value;
}