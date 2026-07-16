"""Hey Telecom client using requests + OAuth2/PKCE (no browser required)."""
from __future__ import annotations

import base64
import hashlib
import secrets
import time
from datetime import datetime
from typing import Optional, List
from urllib.parse import parse_qs, urlencode, urlparse

import requests

from .models import Product, Contract, UsageData, Invoice, AccountData


# --------------------------------------------------------------------------- #
# Constants (public client-side values from the web app)
# --------------------------------------------------------------------------- #
CLIENT_ID = "4x5cSOWeuG"
REDIRECT_URI = "https://ecare.heytelecom.be/index.html"
SCOPE = "openid ecare"

OPENID_BASE = "https://openid.heytelecom.be"
API_BASE = "https://api.heytelecom.be"

API_KEY_LOGIN = "ST70c4jIzkKpGTf0cIGbVZLRN7VMhGl0mzLp8D3vEe79oNaK"
API_KEY_DATA = "KEQRymGhNEonxo79zqM40tphE7zk5NxHOGxjbVsrzsbrkpIs"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36"
)
SEC_CH_UA = '"Google Chrome";v="149", "Chromium";v="149", "Not)A;Brand";v="24"'


# --------------------------------------------------------------------------- #
# PKCE helpers
# --------------------------------------------------------------------------- #
def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _generate_pkce() -> tuple[str, str]:
    """Return (code_verifier, code_challenge) using the S256 method."""
    code_verifier = _b64url(secrets.token_bytes(48))
    code_challenge = _b64url(hashlib.sha256(code_verifier.encode("ascii")).digest())
    return code_verifier, code_challenge


def _normalize_msisdn(msisdn: str) -> str:
    """04XXXXXXXX -> 324XXXXXXXX (drop leading 0, prefix country code 32)."""
    msisdn = msisdn.strip()
    if msisdn.startswith("0") and not msisdn.startswith("00"):
        return "32" + msisdn[1:]
    return msisdn


def _format_msisdn(msisdn: str) -> str:
    """324XXXXXXXX -> 04XXXXXXXX (prefix with 0, drop country code)."""
    msisdn = msisdn.strip()
    if msisdn.startswith("32") and len(msisdn) > 2:
        return "0" + msisdn[2:]
    return msisdn


# --------------------------------------------------------------------------- #
# Client
# --------------------------------------------------------------------------- #
class HeyTelecomClient:
    """Client for interacting with Hey Telecom accounts.

    Uses the same OAuth2/PKCE + BFF API flow as the web app, but without a
    browser.  Supports the context-manager protocol::

        with HeyTelecomClient(email="...", password="...") as client:
            client.login()
            data = client.get_account_data()
    """

    def __init__(
        self,
        email: Optional[str] = None,
        password: Optional[str] = None,
        **_kwargs,
    ):
        """Initialise the client.

        Args:
            email: Account email address.
            password: Account password.
            **_kwargs: Ignored (kept for backward compatibility with the old
                Playwright-based constructor which accepted ``user_data_dir``
                and ``auto_install``).
        """
        self.email = email
        self.password = password
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": USER_AGENT,
                "Accept-Language": "nl-BE,nl;q=0.9",
                "sec-ch-ua": SEC_CH_UA,
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Windows"',
            }
        )
        self.access_token: Optional[str] = None

    # -- context manager ---------------------------------------------------- #
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        """Close the underlying requests session."""
        self.session.close()

    # ====================================================================== #
    # OAuth2 / PKCE login flow (from test.py)
    # ====================================================================== #

    def login(self) -> None:
        """Run the full OAuth2/PKCE + credential login flow."""
        if not self.email or not self.password:
            raise ValueError("Email and password required for login")

        code_verifier, code_challenge = _generate_pkce()
        state = nonce = _b64url(secrets.token_bytes(33))

        transaction_id = self._start_authorization(state, nonce, code_challenge)
        return_uri = self._build_return_uri(
            state, nonce, code_challenge, transaction_id
        )
        authorize_url = self._login(return_uri)
        code = self._collect_code(authorize_url)
        self.access_token = self._exchange_token(code, code_verifier)

    def _start_authorization(self, state, nonce, code_challenge) -> str:
        params = {
            "response_type": "code",
            "client_id": CLIENT_ID,
            "state": state,
            "redirect_uri": REDIRECT_URI,
            "scope": SCOPE,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "nonce": nonce,
            "ui_locales": "nl",
        }
        resp = self.session.get(
            f"{OPENID_BASE}/oidc/authorize",
            params=params,
            allow_redirects=False,
        )
        location = resp.headers.get("Location", "")
        return_uri = parse_qs(urlparse(location).query).get("returnUri", [""])[0]
        transaction_id = parse_qs(urlparse(return_uri).query).get(
            "transactionId", [""]
        )[0]
        if not transaction_id:
            raise RuntimeError(
                f"Could not obtain transactionId (status {resp.status_code}, "
                f"location={location!r})"
            )
        return transaction_id

    @staticmethod
    def _build_return_uri(state, nonce, code_challenge, transaction_id) -> str:
        query = urlencode(
            {
                "response_type": "code",
                "client_id": CLIENT_ID,
                "state": state,
                "redirect_uri": REDIRECT_URI,
                "scope": SCOPE,
                "code_challenge": code_challenge,
                "code_challenge_method": "S256",
                "nonce": nonce,
                "ui_locales": "nl",
                "transactionId": transaction_id,
                "redirectedToAuthForm": "",
            }
        )
        return f"{OPENID_BASE}/oidc/authorize?{query}"

    def _login(self, return_uri: str) -> str:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
            "Origin": "https://auth.heytelecom.be",
            "Referer": "https://auth.heytelecom.be/",
            "x-api-key": API_KEY_LOGIN,
            "x-channel-id": "web",
            "x-usecase-id": "login-email-pwd",
            "x-usersession-id": "".join(
                secrets.choice("0123456789") for _ in range(30)
            ),
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site",
        }
        resp = self.session.post(
            f"{API_BASE}/api/bff/auth/v1/login/email",
            data={
                "email": self.email,
                "password": self.password,
                "returnUri": return_uri,
            },
            headers=headers,
            allow_redirects=False,
        )
        location = resp.headers.get("Location")
        if not location:
            raise RuntimeError(
                f"Login failed (status {resp.status_code}). "
                "Check credentials / Incapsula challenge."
            )
        return location

    def _collect_code(self, authorize_url: str) -> str:
        resp = self.session.get(authorize_url, allow_redirects=False)
        location = resp.headers.get("Location", "")
        code = parse_qs(urlparse(location).query).get("code", [""])[0]
        if not code:
            raise RuntimeError(
                f"No authorization code returned (status {resp.status_code}, "
                f"location={location!r})"
            )
        return code

    def _exchange_token(self, code: str, code_verifier: str) -> str:
        resp = self.session.post(
            f"{OPENID_BASE}/oidc/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": REDIRECT_URI,
                "code_verifier": code_verifier,
                "client_id": CLIENT_ID,
            },
            headers={
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
                "Origin": "https://ecare.heytelecom.be",
                "Referer": "https://ecare.heytelecom.be/",
            },
        )
        resp.raise_for_status()
        return resp.json()["access_token"]

    # ====================================================================== #
    # Authenticated BFF data calls
    # ====================================================================== #

    def _bff_headers(self, extra: Optional[dict] = None) -> dict:
        if not self.access_token:
            raise RuntimeError("Not authenticated - call login() first.")
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.access_token}",
            "Content-Language": "nl",
            "Origin": "https://ecare.heytelecom.be",
            "Referer": "https://ecare.heytelecom.be/",
            "x-api-key": API_KEY_DATA,
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site",
        }
        if extra:
            headers.update(extra)
        return headers

    def _get(self, path: str, params=None, extra_headers=None):
        resp = self.session.get(
            f"{API_BASE}{path}",
            params=params,
            headers=self._bff_headers(extra_headers),
        )
        resp.raise_for_status()
        return resp.json()

    # ====================================================================== #
    # Public API — same interface as the old Playwright client
    # ====================================================================== #

    def get_products(self) -> List[Product]:
        """Get all products from the account.

        Returns:
            List of Product objects (mobile lines, internet, ...).
        """
        inventory = self._get("/api/bff/product-inventory/v1/productInventory")
        products: List[Product] = []

        for item in inventory:
            msisdn_raw = item.get("MSISDN", "")
            tariff = item.get("tariffName", "")
            product_type_raw = item.get("productType", "")
            price_info = item.get("price", {})
            price_value = price_info.get("value")
            price_unit = price_info.get("unit", "EUR")

            # Map API productType to old library conventions
            if product_type_raw == "M":
                product_type = "mobile"
                phone_number = _format_msisdn(msisdn_raw)
                product_id = f"mobile_{msisdn_raw}"
                easy_switch_number = None
            elif product_type_raw == "F":
                product_type = "internet"
                phone_number = None
                easy_switch_number = msisdn_raw
                product_id = f"internet_{msisdn_raw}"
            else:
                product_type = product_type_raw or "unknown"
                phone_number = _format_msisdn(msisdn_raw) if msisdn_raw else None
                easy_switch_number = msisdn_raw if not phone_number else None
                product_id = f"{product_type}_{msisdn_raw}"

            # Build contract
            contract = None
            if price_value is not None:
                contract = Contract(price_per_month_eur=float(price_value))

            # Fetch usage for mobile lines
            usage = None
            if product_type_raw == "M":
                msisdn_intl = _normalize_msisdn(msisdn_raw)
                usage = self._fetch_usage(msisdn_intl)

            products.append(
                Product(
                    product_id=product_id,
                    product_type=product_type,
                    phone_number=phone_number,
                    easy_switch_number=easy_switch_number,
                    tariff=tariff,
                    contract=contract,
                    usage=usage,
                )
            )

        return products

    def get_latest_invoice(self) -> Optional[Invoice]:
        """Get the latest invoice.

        Returns:
            Invoice object or None if no invoice data is available.
        """
        try:
            data = self._get("/api/bff/invoice/v1/latest")
        except Exception:
            # Endpoint may not exist or may have a different path; return None
            # rather than crashing so the rest of the library still works.
            return None

        if not data:
            return None

        amount = data.get("amount", {}).get("value")
        if amount is None:
            amount = data.get("amountEur") or data.get("totalAmount")
        if amount is not None:
            amount = float(amount)

        status = data.get("status", "")
        paid = status.lower() in ("betaald", "paid") if isinstance(status, str) else False

        date = data.get("date") or data.get("invoiceDate")
        due_date = data.get("dueDate") or data.get("paymentDueDate")

        invoice_id = data.get("invoiceId") or data.get("id")
        if not invoice_id and date:
            invoice_id = f"INV-{date.replace('-', '')}"

        return Invoice(
            invoice_id=invoice_id,
            amount_eur=amount,
            status=status,
            paid=paid,
            date=date,
            due_date=due_date,
        )

    def get_account_data(self) -> AccountData:
        """Get all account data including products and latest invoice.

        Returns:
            AccountData object with all information.
        """
        products = self.get_products()
        invoice = self.get_latest_invoice()

        return AccountData(
            products=products,
            latest_invoice=invoice,
        )

    # ====================================================================== #
    # Usage (private)
    # ====================================================================== #

    def _fetch_usage(self, msisdn: str) -> Optional[UsageData]:
        """Fetch consumption/balance for a mobile line."""
        try:
            data = self._get(
                "/api/bff/info-consumption/v1/usage",
                params={"timestamp": int(time.time() * 1000)},
                extra_headers={"x-req-msisdn": msisdn},
            )
        except Exception:
            return None

        balances = data.get("BalancePresentation", [])
        if not balances:
            return None

        period = None
        date_range = data.get("dateRange") or data.get("period")
        if date_range:
            period = {
                "start": date_range.get("start"),
                "end": date_range.get("end"),
            }

        usage_data: Dict = {}
        calls_used = 0.0
        calls_unlimited = False
        sms_used = 0
        sms_unlimited = False
        data_used_gb: Optional[float] = None
        data_limit_gb: Optional[float] = None
        data_unlimited = False

        for bal in balances:
            name = (bal.get("Name") or "").lower()
            consumed = bal.get("ConsumedAmount", {})
            consumed_val = consumed.get("Amount")
            unit = (bal.get("Unit") or "").lower()
            category = (bal.get("Category") or "").lower()

            if consumed_val is not None:
                consumed_val = float(consumed_val)

            if "data" in name or "internet" in category:
                data_used_gb = consumed_val
                data_unlimited = "onbeperkt" in name or "unlimited" in name
                limit = bal.get("LimitAmount")
                if limit is not None:
                    data_limit_gb = float(limit)
            elif "minuut" in name or "call" in category or "bel" in name:
                calls_used = consumed_val or 0.0
                calls_unlimited = "onbeperkt" in name or "unlimited" in name
            elif "sms" in name or "mms" in name or "sms" in category:
                sms_used = int(consumed_val or 0)
                sms_unlimited = "onbeperkt" in name or "unlimited" in name

        usage_dict: Dict = {}
        if data_used_gb is not None or data_limit_gb is not None:
            usage_dict["data"] = {
                "used": data_used_gb,
                "limit": data_limit_gb,
                "unlimited": data_unlimited,
            }
        if calls_used or calls_unlimited:
            usage_dict["calls"] = {
                "used": calls_used,
                "unlimited": calls_unlimited,
            }
        if sms_used or sms_unlimited:
            usage_dict["sms_mms"] = {
                "used": sms_used,
                "unlimited": sms_unlimited,
            }

        if not usage_dict:
            return None

        return UsageData(period=period, **usage_dict)
