// var toastTriggerError = document.getElementById('errorBtn')
// var toastTriggerSucces = document.getElementById('successBtn')
// var toastTriggerWarning = document.getElementById('warningBtn')
// var toastLiveError = document.getElementById('alert-message-error')
// var toastLiveSuccess = document.getElementById('alert-message-success')
// var toastLiveWarning = document.getElementById('alert-message-warning')
//
// if (toastTriggerError) {
//     toastTriggerError.addEventListener('click', function () {
//         var toast = new bootstrap.Toast(toastLiveError)
//         toast.show()
//
//     })
// }
// if (toastTriggerSucces) {
//     toastTriggerSucces.addEventListener('click', function () {
//         var toast = new bootstrap.Toast(toastLiveSuccess)
//         toast.show()
//     })
// }
// if (toastTriggerWarning) {
//     toastTriggerWarning.addEventListener('click', function () {
//         var toast = new bootstrap.Toast(toastLiveWarning)
//         toast.show()
//     })
// }

function show_user_messages() {
    var alert_error = document.getElementById('alert-message-error');
    if (alert_error) {
        var error_toast = new bootstrap.Toast(alert_error)
        error_toast.show()
    }
    var alert_warning = document.getElementById('alert-message-warning');
    if (alert_warning) {
        var warning_toast = new bootstrap.Toast(alert_warning)
        warning_toast.show()
    }
    var alert_success = document.getElementById('alert-message-success');
    if (alert_success) {
        var success_toast = new bootstrap.Toast(alert_success)
        success_toast.show()
    }
}

 function clear_user_messages() {
    // var allAlerts = document.querySelectorAll('.alert');
    // allAlerts.forEach(function (el) {
    //  });
    // $('#alert-message-error').alert('close');
    // $('#alert-message-warning').alert('close');
    // $('#alert-message-success').alert('close');
    var alert_error = document.getElementById('alert-message-error');
    var alert_errorToast = bootstrap.Toast.getInstance(alert_error);
    if (alert_errorToast){alert_errorToast.hide()}
    var alert_warning = document.getElementById('alert-message-warning');
    var alert_warningToast = bootstrap.Toast.getInstance(alert_warning);
    if (alert_warningToast) {alert_warningToast.hide()}
    var alert_success = document.getElementById('alert-message-success');
    var alert_successToast = bootstrap.Toast.getInstance(alert_success);
    if (alert_successToast){alert_successToast.hide()}
    document.getElementById('all_messages').innerHTML = '';
    }