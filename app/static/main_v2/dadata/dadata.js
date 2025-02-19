
$("#organization").suggestions({
                    minChars: 10,
                    token: "eae07ba0f72cc349e91500f5a949eacf49a63051",
                    type: "PARTY",
                    /* Вызывается, когда пользователь выбирает одну из подсказок */
                    onSelect: function(suggestion) {

                        // console.log(suggestion);
                        // console.log(suggestion.data.name.full);
                        // console.log(suggestion.data.opf.short);
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
                        // document.getElementById('organization').value='';
                        if (count_words(document.getElementById('organization').value) < 3 || document.getElementById('organization').value.length<5){
                           document.getElementById('organization').classList.remove('is-valid');
                            document.getElementById('organization').classList.add('is-invalid')
                        }
                        else{
                           document.getElementById('organization').classList.remove('is-invalid')
                           document.getElementById('organization').classList.add('is-valid');

                        }

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