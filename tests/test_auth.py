from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import requests

from heytelecom import auth
from heytelecom.exceptions import AuthenticationError


def _mock_response(status=200, headers=None, json_data=None, text=""):
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status
    resp.headers = headers or {}
    resp.json.return_value = json_data or {}
    resp.text = text
    resp.raise_for_status = MagicMock()
    if status >= 400:
        resp.raise_for_status.side_effect = requests.HTTPError(f"HTTP {status}")
    return resp


@patch.object(auth, "_start_authorization", return_value="txn_abc")
@patch.object(auth, "_login", return_value="https://openid.heytelecom.be/oidc/authorize?code=xyz")
@patch.object(auth, "_collect_code", return_value="auth_code_123")
@patch.object(auth, "_exchange_token", return_value="access_token_xyz")
def test_login_full_flow(mock_exchange, mock_collect, mock_login, mock_txn):
    session = requests.Session()
    token, obtained_at = auth.login(session, "test@example.com", "secret123")

    assert token == "access_token_xyz"
    assert obtained_at > 0

    mock_txn.assert_called_once()
    mock_login.assert_called_once()
    mock_collect.assert_called_once()
    mock_exchange.assert_called_once()


def test_start_authorization_happy_path():
    session = requests.Session()
    location = (
        "https://partners-enrichment.heytelecom.be/authlogicimplicit/login"
        "?returnUri=https%3A%2F%2Fopenid.heytelecom.be%2Foidc%2Fauthorize%3FtransactionId%3Dtxn_123"
    )
    with patch.object(session, "get", return_value=_mock_response(headers={"Location": location})):
        txn = auth._start_authorization(session, "state", "nonce", "challenge")
        assert txn == "txn_123"


def test_start_authorization_missing_transaction_id():
    session = requests.Session()
    resp = _mock_response(headers={"Location": "https://example.com"})
    with patch.object(session, "get", return_value=resp), pytest.raises(
        AuthenticationError, match="Could not obtain transactionId"
    ):
        auth._start_authorization(session, "state", "nonce", "challenge")


def test_start_authorization_http_error():
    session = requests.Session()
    resp = _mock_response(status=500)
    with patch.object(session, "get", return_value=resp), pytest.raises(requests.HTTPError):
        auth._start_authorization(session, "state", "nonce", "challenge")


def test_login_success():
    session = requests.Session()
    with patch.object(
        session,
        "post",
        return_value=_mock_response(
            headers={"Location": "https://openid.heytelecom.be/oidc/authorize?code=abc"}
        ),
    ):
        location = auth._login(session, "user@test.com", "pwd", "https://example.com/return")
        assert "code=abc" in location


def test_login_missing_location():
    session = requests.Session()
    resp = _mock_response()
    msg = "Login failed"
    with patch.object(session, "post", return_value=resp), pytest.raises(
        AuthenticationError,
        match=msg,
    ):
        auth._login(session, "user@test.com", "pwd", "https://example.com/return")


def test_collect_code_success():
    session = requests.Session()
    with patch.object(
        session,
        "get",
        return_value=_mock_response(
            headers={
                "Location": "https://ecare.heytelecom.be/index.html?code=secret_code&state=xyz"
            }
        ),
    ):
        code = auth._collect_code(session, "https://example.com/auth")
        assert code == "secret_code"


def test_collect_code_missing():
    session = requests.Session()
    resp = _mock_response(headers={"Location": "https://ecare.heytelecom.be/index.html"})
    msg = "No authorization code returned"
    with patch.object(session, "get", return_value=resp), pytest.raises(
        AuthenticationError,
        match=msg,
    ):
        auth._collect_code(session, "https://example.com/auth")


def test_exchange_token_success():
    session = requests.Session()
    with patch.object(
        session,
        "post",
        return_value=_mock_response(json_data={"access_token": "token_abc", "expires_in": 3600}),
    ):
        token = auth._exchange_token(session, "code", "verifier")
        assert token == "token_abc"


def test_exchange_token_missing_token():
    session = requests.Session()
    resp = _mock_response(json_data={"expires_in": 3600})
    msg = "no access_token"
    with patch.object(session, "post", return_value=resp), pytest.raises(
        AuthenticationError,
        match=msg,
    ):
        auth._exchange_token(session, "code", "verifier")


def test_exchange_token_http_error():
    session = requests.Session()
    resp = _mock_response(status=400)
    with patch.object(session, "post", return_value=resp), pytest.raises(requests.HTTPError):
        auth._exchange_token(session, "code", "verifier")
