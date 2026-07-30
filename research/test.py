"""
[HISTORICAL — frozen snapshot]

HeyTelecom e-care API client (reverse-engineered from a browser HAR capture).

This script was used during development to reverse-engineer the OAuth2/PKCE
flow.  The production implementation lives in ``src/heytelecom/client.py``.
Do not modify this file — it is kept as a reference only.

    Usage:
        1. OAuth2 Authorization-Code + PKCE (S256) against openid.heytelecom.be
        2. Email/password login via the BFF auth endpoint (sets the `wassup` cookie)
        3. Exchange the returned `code` for a Bearer access_token
        4. Call the BFF data endpoints (product inventory, profile, usage, ...)

    All requests reuse a single requests.Session so Incapsula/Imperva cookies and
    the auth session cookie are carried automatically, and the browser headers
    (User-Agent, sec-ch-ua, origin/referer, x-api-key) are replicated closely.

    Usage:
        set HEY_EMAIL / HEY_PASSWORD environment variables (or edit the constants),
        then:  python test.py
"""

from __future__ import annotations

import base64
import hashlib
import os
import secrets
import time
from urllib.parse import parse_qs, urlencode, urlparse

import requests

# --------------------------------------------------------------------------- #
# Constants captured from the HAR (these are the public web-app values)
# --------------------------------------------------------------------------- #
CLIENT_ID = "4x5cSOWeuG"
REDIRECT_URI = "https://ecare.heytelecom.be/index.html"
SCOPE = "openid ecare"

OPENID_BASE = "https://openid.heytelecom.be"
API_BASE = "https://api.heytelecom.be"

# Two different public API keys are used by the web app:
API_KEY_LOGIN = "ST70c4jIzkKpGTf0cIGbVZLRN7VMhGl0mzLp8D3vEe79oNaK"  # auth endpoints
API_KEY_DATA = "KEQRymGhNEonxo79zqM40tphE7zk5NxHOGxjbVsrzsbrkpIs"   # BFF data endpoints

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36"
)
SEC_CH_UA = '"Google Chrome";v="149", "Chromium";v="149", "Not)A;Brand";v="24"'

# Credentials - prefer environment variables, never commit real ones.
EMAIL = os.environ.get("HEY_EMAIL", "your-email@example.com")
PASSWORD = os.environ.get("HEY_PASSWORD")


# --------------------------------------------------------------------------- #
# PKCE helpers
# --------------------------------------------------------------------------- #
def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def generate_pkce() -> tuple[str, str]:
    """Return (code_verifier, code_challenge) using the S256 method."""
    code_verifier = _b64url(secrets.token_bytes(48))
    code_challenge = _b64url(hashlib.sha256(code_verifier.encode("ascii")).digest())
    return code_verifier, code_challenge


# --------------------------------------------------------------------------- #
# Client
# --------------------------------------------------------------------------- #
class HeyTelecomClient:
    def __init__(self, email: str, password: str):
        self.email = email
        self.password = password
        self.session = requests.Session()
        # Headers every request shares (a real Chrome session sends these).
        self.session.headers.update(
            {
                "User-Agent": USER_AGENT,
                "Accept-Language": "nl-BE,nl;q=0.9",
                "sec-ch-ua": SEC_CH_UA,
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Windows"',
            }
        )
        self.access_token: str | None = None

    # -- step 1: kick off the PKCE authorize request to obtain a transactionId
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
        # Not logged in yet -> server 302s to the login flow with a fresh
        # transactionId embedded in the returnUri query parameter.
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

    # -- step 2: build the returnUri that the login form posts back
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

    # -- step 3: post the credentials; this sets the `wassup` auth cookie
    def _login(self, return_uri: str) -> str:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
            "Origin": "https://auth.heytelecom.be",
            "Referer": "https://auth.heytelecom.be/",
            "x-api-key": API_KEY_LOGIN,
            "x-channel-id": "web",
            "x-usecase-id": "login-email-pwd",
            "x-usersession-id": "".join(secrets.choice("0123456789") for _ in range(30)),
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

    # -- step 4: follow the authorize redirect to collect the `code`
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

    # -- step 5: exchange the code for an access token
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

    def login(self) -> None:
        """Run the full OAuth2/PKCE + credential login flow."""
        code_verifier, code_challenge = generate_pkce()
        # The web app uses the same random value for state and nonce.
        state = nonce = _b64url(secrets.token_bytes(33))

        transaction_id = self._start_authorization(state, nonce, code_challenge)
        return_uri = self._build_return_uri(
            state, nonce, code_challenge, transaction_id
        )
        authorize_url = self._login(return_uri)
        code = self._collect_code(authorize_url)
        self.access_token = self._exchange_token(code, code_verifier)

    # ------------------------------------------------------------------ #
    # Authenticated data calls
    # ------------------------------------------------------------------ #
    def _bff_headers(self, extra: dict | None = None) -> dict:
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

    def get_product_inventory(self):
        """List of subscriptions / lines (MSISDN, tariff, product type, price)."""
        return self._get("/api/bff/product-inventory/v1/productInventory")

    def get_profile(self):
        """Account holder profile + invoice address."""
        return self._get("/api/bff/my-profile/v1/customer")

    def get_usage(self, msisdn: str):
        """Consumption / balance for a mobile line.

        `msisdn` must be in international form without '+', e.g. 324XXXXXXXX.
        """
        return self._get(
            "/api/bff/info-consumption/v1/usage",
            params={"timestamp": int(time.time() * 1000)},
            extra_headers={"x-req-msisdn": msisdn},
        )


def _normalize_msisdn(msisdn: str) -> str:
    """04XXXXXXXX -> 324XXXXXXXX (drop leading 0, prefix country code 32)."""
    msisdn = msisdn.strip()
    if msisdn.startswith("0") and not msisdn.startswith("00"):
        return "32" + msisdn[1:]
    return msisdn


def main() -> None:
    client = HeyTelecomClient(EMAIL, PASSWORD)
    print("Logging in...")
    client.login()
    print("Access token acquired.\n")

    print("=== Profile ===")
    profile = client.get_profile()
    print(f"{profile.get('firstName')} {profile.get('lastName')} "
          f"<{profile.get('emailAddress')}>\n")

    print("=== Product inventory (your lines) ===")
    inventory = client.get_product_inventory()
    for item in inventory:
        print(f"  {item['MSISDN']:<14} {item['tariffName']:<16} "
              f"type={item['productType']} "
              f"{item['price']['value']:.2f} {item['price']['unit']}")
    print()

    # Usage is only available for mobile lines (productType == 'M').
    for item in inventory:
        if item.get("productType") == "M":
            msisdn = _normalize_msisdn(item["MSISDN"])
            print(f"=== Usage for {msisdn} ===")
            usage = client.get_usage(msisdn)
            for bal in usage.get("BalancePresentation", [])[:5]:
                print(f"  {bal.get('Name')}: "
                      f"{bal.get('ConsumedAmount', {}).get('Amount')} "
                      f"{bal.get('Unit')} ({bal.get('Category')})")
            print()


if __name__ == "__main__":
    main()
