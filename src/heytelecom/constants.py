"""Public client-side constants from the Hey Telecom web app."""

CLIENT_ID = "4x5cSOWeuG"
REDIRECT_URI = "https://ecare.heytelecom.be/index.html"
SCOPE = "openid ecare"

OPENID_BASE = "https://openid.heytelecom.be"
API_BASE = "https://api.heytelecom.be"

# These are public client-side keys extracted from the web app's JS bundle.
# They are not secrets — they're equivalent to a public API client ID used
# by the browser to identify itself to the backend.
API_KEY_LOGIN = "ST70c4jIzkKpGTf0cIGbVZLRN7VMhGl0mzLp8D3vEe79oNaK"
API_KEY_DATA = "KEQRymGhNEonxo79zqM40tphE7zk5NxHOGxjbVsrzsbrkpIs"

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/150.0.0.0 Safari/537.36"
)
SEC_CH_UA = '"Not;A=Brand";v="8", "Chromium";v="150", "Google Chrome";v="150"'

DEFAULT_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept-Language": "nl-BE,nl;q=0.9",
    "sec-ch-ua": SEC_CH_UA,
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
}

BFF_ORIGIN = "https://ecare.heytelecom.be"
BFF_REFERER = "https://ecare.heytelecom.be/"

BFF_BASE_HEADERS = {
    "Accept": "application/json",
    "Content-Language": "nl",
    "Origin": BFF_ORIGIN,
    "Referer": BFF_REFERER,
    "x-api-key": API_KEY_DATA,
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-site",
}

TOKEN_LIFETIME = 3300
REQUEST_TIMEOUT = 30
CACHE_TTL = 60

PRODUCT_TYPE_MOBILE = "M"
PRODUCT_TYPE_FIXED = "F"

# API endpoint paths
PATH_PRODUCT_INVENTORY = "/api/bff/product-inventory/v1/productInventory"
PATH_LATEST_INVOICE = "/api/bff/latest-invoice-overview/v1/invoices/latest"
PATH_INVOICES = "/api/bff/invoices-details/v1/invoices"
PATH_BENEFITS = "/api/bff/my-benefits/v1/my-benefits"
PATH_PROFILE_PRODUCTS = "/api/bff/my-profile/v1/products"
PATH_USAGE = "/api/bff/info-consumption/v1/usage"
