document.addEventListener("DOMContentLoaded", function () {
    // console.log("DOM fully loaded and ready!");

    // Store the correct jQuery version in a variable
    var myJQuery = window.jQuery;

    function waitForDadata(retries = 5) {
        if (typeof myJQuery.fn.suggestions !== "undefined") {
            console.log("✅ Dadata suggestions plugin is loaded.");
            fetchDadataToken();
        } else {
            if (retries > 0) {
                console.warn(`⏳ Waiting for Dadata plugin... (${retries} retries left)`);
                setTimeout(() => waitForDadata(retries - 1), 1000); // Retry in 1 sec
            } else {
                console.error("❌ Dadata suggestions plugin failed to load.");
            }
        }
    }

    function fetchDadataToken() {
        myJQuery.ajax({
            url: getDadataTokenUrl,
            method: 'GET',
            dataType: 'json',
            success: function (data) {
                if (data.token) {
                    console.log("✅ Received token");
                    initializeDadataSuggestions(data.token);
                } else {
                    console.error("❌ Token missing in response:", data);
                }
            },
            error: function (error) {
                console.error("❌ Error fetching DaData token:", error);
            }
        });
    }

    function initializeDadataSuggestions(token) {
        if (!token) {
            console.error("❌ Cannot initialize suggestions: Token is missing!");
            return;
        }

        console.log("🚀 Initializing Dadata Suggestions...");
        myJQuery("#organization").suggestions({
            minChars: 10,
            token: token,
            type: "PARTY",
            onSelect: function (suggestion) {
                console.log("✅ Organization selected:", suggestion);
                myJQuery("#company_idn").val(suggestion.data.inn);
                myJQuery("#company_type").val(suggestion.data.opf.short);
                myJQuery("#company_name").val(suggestion.data.name.full);
                myJQuery("#modal_company_idn").val(suggestion.data.inn);
                myJQuery("#modal_company_name").val(suggestion.data.name.full);
            }
        });
    }

    // Start checking for Dadata plugin
    waitForDadata();
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