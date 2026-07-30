"""Public client-side constants from the Hey Telecom web app."""

from __future__ import annotations

from enum import Enum

__all__ = [
    "API_BASE",
    "API_KEY_DATA",
    "API_KEY_LOGIN",
    "BFF_BASE_HEADERS",
    "BFF_ORIGIN",
    "BFF_REFERER",
    "CLIENT_ID",
    "DEFAULT_HEADERS",
    "OPENID_BASE",
    "PATH_BENEFITS",
    "PATH_INVOICES",
    "PATH_LATEST_INVOICE",
    "PATH_PRODUCT_INVENTORY",
    "PATH_PROFILE_PRODUCTS",
    "PATH_USAGE",
    "PRODUCT_TYPE_FIXED",
    "PRODUCT_TYPE_MOBILE",
    "REDIRECT_URI",
    "REQUEST_TIMEOUT",
    "SCOPE",
    "SEC_CH_UA",
    "TOKEN_LIFETIME",
    "USER_AGENT",
    "ProductType",
]


class ProductType(str, Enum):
    MOBILE = "M"
    FIXED = "F"


PRODUCT_TYPE_MOBILE = ProductType.MOBILE
PRODUCT_TYPE_FIXED = ProductType.FIXED

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
    "Chrome/131.0.0.0 Safari/537.36"
)
SEC_CH_UA = '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"'

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

# Fallback token lifetime used only when the token response omits expires_in.
# Actual expiry is typically 3600s; 300s safety margin for early renewal.
TOKEN_LIFETIME = 3300
REQUEST_TIMEOUT = 30
# API endpoint paths
PATH_PRODUCT_INVENTORY = "/api/bff/product-inventory/v1/productInventory"
PATH_LATEST_INVOICE = "/api/bff/latest-invoice-overview/v1/invoices/latest"
PATH_INVOICES = "/api/bff/invoices-details/v1/invoices"
PATH_BENEFITS = "/api/bff/my-benefits/v1/my-benefits"
PATH_PROFILE_PRODUCTS = "/api/bff/my-profile/v1/products"
PATH_USAGE = "/api/bff/info-consumption/v1/usage"
