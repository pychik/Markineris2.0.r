(function () {
    let uploadConfig = {
        requestPath: "",
        subcategories: [],
        subcategory: null,
    };

    function getUploadForm() {
        return document.getElementById("uploadForm");
    }

    function reloadUploadPageWithParams() {
        const companyType = document.getElementById("company_type").value;
        const companyName = document.getElementById("company_name").value;
        const companyIdn = document.getElementById("company_idn").value;
        const edoType = document.getElementById("edo_type").value;
        const markType = document.getElementById("mark_type").value;
        const markTypeHidden = document.getElementById("mark_type_hidden").value || markType;

        const urlParams = new URLSearchParams();
        urlParams.set("company_type", companyType);
        urlParams.set("company_name", companyName);
        urlParams.set("company_idn", companyIdn);
        urlParams.set("edo_type", edoType);
        urlParams.set("mark_type", markType);
        urlParams.set("mark_type_hidden", markTypeHidden);

        if (uploadConfig.subcategory) {
            urlParams.set("subcategory", uploadConfig.subcategory);
        }

        window.location = `${uploadConfig.requestPath}?${urlParams.toString()}`;
    }

    function ensureSubcategoryField(uploadForm) {
        const existingInput = uploadForm.querySelector('input[name="subcategory"]');
        if (existingInput) {
            existingInput.remove();
        }

        if (uploadConfig.subcategory && uploadConfig.subcategories.includes(uploadConfig.subcategory)) {
            const hiddenInput = document.createElement("input");
            hiddenInput.type = "hidden";
            hiddenInput.name = "subcategory";
            hiddenInput.value = uploadConfig.subcategory;
            uploadForm.appendChild(hiddenInput);
        }
    }

    function getResponseFilename(response) {
        const disposition = response.headers.get("Content-Disposition") || "";
        const utf8Match = disposition.match(/filename\*=UTF-8''([^;]+)/i);
        if (utf8Match && utf8Match[1]) {
            return decodeURIComponent(utf8Match[1]);
        }

        const simpleMatch = disposition.match(/filename="?([^"]+)"?/i);
        if (simpleMatch && simpleMatch[1]) {
            return simpleMatch[1];
        }

        return "upload_errors.txt";
    }

    async function submitUploadForm(uploadForm) {
        const response = await fetch(uploadForm.action, {
            method: "POST",
            body: new FormData(uploadForm),
            credentials: "same-origin",
            redirect: "follow",
            headers: {
                "X-Requested-With": "XMLHttpRequest",
                "Accept": "application/json, text/plain, */*",
            },
        });

        const disposition = response.headers.get("Content-Disposition") || "";
        const isAttachment = disposition.toLowerCase().includes("attachment");
        const contentType = response.headers.get("Content-Type") || "";

        if (isAttachment) {
            const blob = await response.blob();
            const downloadUrl = window.URL.createObjectURL(blob);
            const link = document.createElement("a");
            link.href = downloadUrl;
            link.download = getResponseFilename(response);
            document.body.appendChild(link);
            link.click();
            link.remove();
            window.URL.revokeObjectURL(downloadUrl);
            reloadUploadPageWithParams();
            return false;
        }

        if (contentType.includes("application/json")) {
            const payload = await response.json();
            if (payload && payload.redirect_url) {
                window.location = payload.redirect_url;
                return false;
            }
        }

        if (response.redirected && response.url) {
            window.location = response.url;
            return false;
        }

        window.location.reload();
        return false;
    }

    function collectFormErrors() {
        const allInputs = $("#uploadForm input, #uploadForm select");
        const errorsList = [];

        allInputs.each(function (index) {
            const errorFieldId = check_valid(allInputs[index]);
            if (errorFieldId !== true) {
                const labelText = jQuery(`#${errorFieldId}`).closest(".form-group").find("label").text();
                if (labelText) {
                    errorsList.push(labelText);
                }
            }
        });

        return errorsList;
    }

    function bindLoadingButtons() {
        ["btn_upload_1", "btn_upload_2"].forEach(function (buttonId) {
            const button = document.getElementById(buttonId);
            if (!button) {
                return;
            }

            button.addEventListener("click", function () {
                const uploadForm = getUploadForm();
                if (uploadForm && uploadForm.checkValidity() === true) {
                    loadingCircle();
                }
            });
        });
    }

    function initCommonExcelUpload(config) {
        uploadConfig = {
            requestPath: config.requestPath,
            subcategories: config.subcategories || [],
            subcategory: config.subcategory || null,
        };

        bindLoadingButtons();
    }

    window.upload_type_process = function (typeProcess) {
        document.getElementById("table_type").value = typeProcess;
        return window.check_upload_form();
    };

    window.check_upload_form = function () {
        const uploadForm = getUploadForm();

        if (!uploadForm.checkValidity || uploadForm.checkValidity()) {
            ensureSubcategoryField(uploadForm);
            submitUploadForm(uploadForm);
            return false;
        }

        show_form_errors(collectFormErrors());
        $("#form_errorModal").modal("show");
        return false;
    };

    window.initCommonExcelUpload = initCommonExcelUpload;
})();
