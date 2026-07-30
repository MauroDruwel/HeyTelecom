"""OAuth2 Authorization Code + PKCE (S256) login flow for Hey Telecom.

All functions in this module are private — the single public entry point
is :func:`login`, which drives the full four-step flow:

1. ``_start_authorization`` — obtain a transaction ID from the OIDC endpoint.
2. ``_login`` — POST email/password to the login API.
3. ``_collect_code`` — follow the redirect to extract the authorization code.
4. ``_exchange_token`` — trade the code and PKCE verifier for an access token.
"""

from __future__ import annotations

import secrets
import time
from typing import TYPE_CHECKING
from urllib.parse import parse_qs, urlencode, urlparse

from .constants import (
    API_BASE,
    API_KEY_LOGIN,
    CLIENT_ID,
    OPENID_BASE,
    REDIRECT_URI,
    REQUEST_TIMEOUT,
    SCOPE,
)
from .exceptions import AuthenticationError
from .utils import _b64url, _generate_pkce

if TYPE_CHECKING:
    import requests

__all__ = ["login"]


def _authorize_params(
    state: str, nonce: str, code_challenge: str, transaction_id: str | None = None
) -> dict[str, str]:
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
    if transaction_id:
        params["transactionId"] = transaction_id
        params["redirectedToAuthForm"] = ""
    return params


def login(
    session: requests.Session,
    email: str,
    password: str,
) -> tuple[str, float]:
    _clear_auth_cookies(session)
    code_verifier, code_challenge = _generate_pkce()
    state = nonce = _b64url(secrets.token_bytes(33))

    transaction_id = _start_authorization(session, state, nonce, code_challenge)
    return_uri = _build_return_uri(state, nonce, code_challenge, transaction_id)
    authorize_url = _login(session, email, password, return_uri)
    code = _collect_code(session, authorize_url)
    access_token = _exchange_token(session, code, code_verifier)
    return access_token, time.time()


def _clear_auth_cookies(session: requests.Session) -> None:
    """Remove cookies for heytelecom domains before a fresh login attempt."""
    for cookie in list(session.cookies):
        if any(d in (cookie.domain or "") for d in ("heytelecom", "openid")):
            session.cookies.clear(domain=cookie.domain)


def _start_authorization(
    session: requests.Session, state: str, nonce: str, code_challenge: str
) -> str:
    """Step 1: initiate OIDC authorization and extract the transaction ID."""
    resp = session.get(
        f"{OPENID_BASE}/oidc/authorize",
        params=_authorize_params(state, nonce, code_challenge),
        allow_redirects=False,
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    location = resp.headers.get("Location", "")
    params = parse_qs(urlparse(location).query)
    return_uri = params.get("returnUri", [""])[0]
    transaction_id = parse_qs(urlparse(return_uri).query).get("transactionId", [""])[0]
    if not transaction_id:
        raise AuthenticationError(
            f"Could not obtain transactionId (status {resp.status_code}, location={location!r})"
        )
    return transaction_id


def _build_return_uri(state: str, nonce: str, code_challenge: str, transaction_id: str) -> str:
    query = urlencode(_authorize_params(state, nonce, code_challenge, transaction_id))
    return f"{OPENID_BASE}/oidc/authorize?{query}"


def _login(
    session: requests.Session,
    email: str,
    password: str,
    return_uri: str,
) -> str:
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
        "Origin": "https://auth.heytelecom.be",
        "Referer": "https://auth.heytelecom.be/",
        "x-api-key": API_KEY_LOGIN,
        "x-channel-id": "web",
        "x-usecase-id": "login-email-pwd",
        "x-usersession-id": secrets.token_hex(15),
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
    }
    resp = session.post(
        f"{API_BASE}/api/bff/auth/v1/login/email",
        data={
            "email": email,
            "password": password,
            "returnUri": return_uri,
        },
        headers=headers,
        allow_redirects=False,
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    location = resp.headers.get("Location")
    if not location:
        body_preview = resp.text[:500] if resp.text else "(empty)"
        raise AuthenticationError(
            f"Login failed (status {resp.status_code}). "
            f"Check credentials / Incapsula challenge. Response: {body_preview}"
        )
    return location


def _collect_code(session: requests.Session, authorize_url: str) -> str:
    resp = session.get(
        authorize_url,
        allow_redirects=False,
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    location = resp.headers.get("Location", "")
    code = parse_qs(urlparse(location).query).get("code", [""])[0]
    if not code:
        raise AuthenticationError(
            f"No authorization code returned (status {resp.status_code}, location={location!r})"
        )
    return code


def _exchange_token(session: requests.Session, code: str, code_verifier: str) -> str:
    resp = session.post(
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
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    token = resp.json().get("access_token")
    if not token:
        raise AuthenticationError(
            f"Token exchange succeeded but no access_token in response (status {resp.status_code})"
        )
    return token
