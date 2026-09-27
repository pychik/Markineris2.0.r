DICTIONARY_COLORS = "colors"
DICTIONARY_COUNTRIES = "countries"
DICTIONARY_TNVED = "tnved"
DICTIONARY_PROCESSING_COMPANIES = "processing_companies"

DICTIONARIES = (
    DICTIONARY_COLORS,
    DICTIONARY_COUNTRIES,
    DICTIONARY_TNVED,
    DICTIONARY_PROCESSING_COMPANIES,
)

API_PATH_DICTIONARIES_STATE = "/api/v1/meta/dictionaries-state"
API_PATH_EXPORT_COLORS = "/api/v1/export/colors"
API_PATH_EXPORT_COUNTRIES = "/api/v1/export/countries"
API_PATH_EXPORT_TNVED_TEMPLATE = "/api/v1/export/tnved/{category_slug}"
API_PATH_EXPORT_PROCESSING_COMPANIES = "/api/v1/export/processing-companies"
API_PATH_PROCESSING_COMPANIES_SELECT = "/api/v1/processing-companies/select"
API_PATH_PROCESSING_COMPANIES_SELECT_BATCH = "/api/v1/processing-companies/select-batch"

DEFAULT_TNVED_CATEGORY_SLUG = "clothes"
