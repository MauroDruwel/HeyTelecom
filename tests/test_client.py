from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest
import requests

from heytelecom.client import HeyTelecomClient, _extract_amount, _parse_invoice
from heytelecom.exceptions import APIError, AuthenticationError


def test_extract_amount_from_amount_value():
    assert _extract_amount({"amount": {"value": 42.5}}) == 42.5


def test_extract_amount_from_amount_eur():
    assert _extract_amount({"amountEur": 15.99}) == 15.99


def test_extract_amount_from_total_amount():
    assert _extract_amount({"totalAmount": 99.0}) == 99.0


def test_extract_amount_from_invoice_amount():
    assert _extract_amount({"invoiceAmount": {"value": 25.0}}) == 25.0


def test_extract_amount_returns_none():
    assert _extract_amount({}) is None
    assert _extract_amount({"amount": {}}) is None


def test_extract_amount_rounds():
    assert _extract_amount({"amount": {"value": 10.456}}) == 10.46


def test_extract_amount_prefers_first_match():
    data = {"amount": {"value": 10.0}, "amountEur": 20.0}
    assert _extract_amount(data) == 10.0


def test_extract_amount_handles_non_dict_amount():
    assert _extract_amount({"amount": "bad"}) is None


def test_parse_invoice_basic():
    inv = _parse_invoice(
        {
            "invoiceId": "INV-001",
            "invoiceAmount": {"value": 45.5},
            "status": "paid",
            "date": "2025-01-15",
            "dueDate": "2025-02-14",
        }
    )
    assert inv.invoice_id == "INV-001"
    assert inv.amount_eur == 45.5
    assert inv.paid is True
    assert inv.due_date == "2025-02-14"


def test_parse_invoice_fallback_id_from_date():
    inv = _parse_invoice({"status": "open", "date": "2025-03-01"})
    assert inv.invoice_id == "INV-20250301"
    assert inv.paid is False


class TestHeyTelecomClient:
    def test_init(self):
        client = HeyTelecomClient(email="test@test.com", password="secret")
        assert client.email == "test@test.com"
        assert client.password == "secret"
        assert client.access_token is None
        client.close()

    def test_context_manager(self):
        with HeyTelecomClient(email="a@b.com", password="p") as client:
            assert client.email == "a@b.com"

    def test_login_requires_credentials(self):
        client = HeyTelecomClient()
        with pytest.raises(ValueError, match="Email and password required"):
            client.login()
        client.close()

    @patch("heytelecom.client.auth.login", return_value=("token123", time.time() + 3300))
    def test_login_success(self, _mock_login):
        client = HeyTelecomClient(email="test@test.com", password="secret")
        client.login()
        assert client.access_token == "token123"
        assert client._token_expires_at > time.time()
        client.close()

    def test_clear_credentials(self):
        client = HeyTelecomClient(email="a@b.com", password="secret")
        client.clear_credentials()
        assert client.email is None
        assert client.password is None
        client.close()

    def test_get_token_raises_when_not_authenticated(self):
        client = HeyTelecomClient()
        with pytest.raises(AuthenticationError, match="Not authenticated"):
            client._get_token()
        client.close()

    @patch("heytelecom.client.auth.login", return_value=("token123", time.time() + 3300))
    def test_get_token_reauthenticates_when_expired(self, mock_login):
        client = HeyTelecomClient(email="test@test.com", password="secret")
        client._token_expires_at = time.time() - 1
        client.access_token = "expired_token"
        token = client._get_token()
        assert token == "token123"
        assert mock_login.called
        client.close()

    def test_get_token_expired_without_credentials(self):
        client = HeyTelecomClient()
        client.access_token = "expired"
        client._token_expires_at = time.time() - 1
        with pytest.raises(AuthenticationError, match="credentials are not available"):
            client._get_token()
        client.close()

    def test_bff_headers_include_authorization(self):
        client = HeyTelecomClient(email="test@test.com", password="secret")
        client.access_token = "my_token"
        client._token_expires_at = time.time() + 1000
        headers = client._bff_headers()
        assert headers["Authorization"] == "Bearer my_token"
        assert "x-api-key" in headers
        client.close()

    def test_bff_headers_with_extra(self):
        client = HeyTelecomClient(email="test@test.com", password="secret")
        client.access_token = "my_token"
        client._token_expires_at = time.time() + 1000
        headers = client._bff_headers(extra={"x-custom": "yes"})
        assert headers["x-custom"] == "yes"
        client.close()

    @patch("heytelecom.client.HeyTelecomClient._get")
    def test_get_products_empty_inventory(self, mock_get):
        mock_get.return_value = []
        client = HeyTelecomClient()
        products = client.get_products(use_cache=False)
        assert products == []
        client.close()

    @patch("heytelecom.client.HeyTelecomClient._get")
    def test_get_products_raises_on_error(self, mock_get):
        mock_get.side_effect = APIError("boom", status_code=500)
        client = HeyTelecomClient()
        with pytest.raises(APIError, match="boom"):
            client.get_products(use_cache=False)
        client.close()

    @patch("heytelecom.client.HeyTelecomClient._get")
    def test_get_products_rejects_non_list(self, mock_get):
        mock_get.return_value = {"unexpected": True}
        client = HeyTelecomClient()
        with pytest.raises(APIError, match="Expected list"):
            client.get_products(use_cache=False)
        client.close()

    @patch("heytelecom.client.HeyTelecomClient._get")
    def test_get_products_with_mobile(self, mock_get):
        inventory = [
            {
                "MSISDN": "0478123456",
                "tariffName": "hey! mobile S",
                "productType": "M",
                "price": {"unit": "euro", "value": 5.0},
            },
        ]

        def side_effect(path, **_kw):
            return {"BalancePresentation": []} if "usage" in path else inventory

        mock_get.side_effect = side_effect
        client = HeyTelecomClient()
        products = client.get_products(use_cache=False)
        assert len(products) == 1
        assert products[0].product_type == "mobile"
        assert products[0].phone_number == "0478123456"
        assert products[0].tariff == "hey! mobile S"
        assert products[0].contract.price_per_month_eur == 5.0
        client.close()

    @patch("heytelecom.client.HeyTelecomClient._get")
    def test_get_products_with_internet(self, mock_get):
        mock_get.return_value = [
            {
                "MSISDN": "00XXXXXXX",
                "tariffName": "hey! Internet",
                "productType": "F",
                "price": {"unit": "euro", "value": 39.0},
            },
        ]
        client = HeyTelecomClient()
        products = client.get_products(use_cache=False)
        assert len(products) == 1
        assert products[0].product_type == "internet"
        assert products[0].phone_number is None
        assert products[0].easy_switch_number == "00XXXXXXX"
        client.close()

    @patch("heytelecom.client.HeyTelecomClient._get")
    def test_get_products_unknown_type(self, mock_get):
        mock_get.return_value = [
            {
                "MSISDN": "999",
                "tariffName": "mystery",
                "productType": "X",
                "price": {"value": 1.0},
            },
        ]
        client = HeyTelecomClient()
        products = client.get_products(use_cache=False)
        assert products[0].product_type == "X"
        assert products[0].product_id == "X_999"
        client.close()

    @patch("heytelecom.client.HeyTelecomClient._get")
    def test_get_products_caching(self, mock_get):
        inventory = [
            {
                "MSISDN": "0478123456",
                "tariffName": "hey! mobile S",
                "productType": "M",
                "price": {"unit": "euro", "value": 5.0},
            },
        ]

        def side_effect(path, **_kwargs):
            if "usage" in path:
                return {"BalancePresentation": []}
            return inventory

        mock_get.side_effect = side_effect
        client = HeyTelecomClient()
        products1 = client.get_products(use_cache=True)
        products2 = client.get_products(use_cache=True)
        assert len(products1) == 1
        assert len(products2) == 1
        # inventory + one usage call on first fetch only
        assert mock_get.call_count == 2
        client.close()

    @patch("heytelecom.client.HeyTelecomClient._get")
    def test_get_latest_invoice(self, mock_get):
        mock_get.return_value = {
            "invoiceId": "INV-001",
            "invoiceAmount": {"value": 45.50, "unit": "euro"},
            "status": "paid",
            "date": "2025-01-15",
            "dueDate": "2025-02-14",
        }
        client = HeyTelecomClient()
        invoice = client.get_latest_invoice(use_cache=False)
        assert invoice is not None
        assert invoice.invoice_id == "INV-001"
        assert invoice.amount_eur == 45.50
        assert invoice.paid is True
        assert invoice.date == "2025-01-15"
        assert invoice.due_date == "2025-02-14"
        client.close()

    @patch("heytelecom.client.HeyTelecomClient._get")
    def test_get_latest_invoice_raises_on_error(self, mock_get):
        mock_get.side_effect = APIError("Network error", status_code=None)
        client = HeyTelecomClient()
        with pytest.raises(APIError, match="Network error"):
            client.get_latest_invoice(use_cache=False)
        client.close()

    @patch("heytelecom.client.HeyTelecomClient._get")
    def test_get_latest_invoice_empty(self, mock_get):
        mock_get.return_value = {}
        client = HeyTelecomClient()
        assert client.get_latest_invoice(use_cache=False) is None
        client.close()

    @patch("heytelecom.client.HeyTelecomClient._get")
    def test_get_invoices(self, mock_get):
        mock_get.return_value = [
            {
                "invoiceNumber": "INV-001",
                "invoiceAmount": {"value": 45.50},
                "status": "paid",
                "referenceDate": "2025-01-15",
                "paymentDates": {"endDate": "2025-02-14"},
            },
        ]
        client = HeyTelecomClient()
        invoices = client.get_invoices()
        assert len(invoices) == 1
        assert invoices[0].invoice_id == "INV-001"
        assert invoices[0].paid is True
        assert invoices[0].due_date == "2025-02-14"
        client.close()

    @patch("heytelecom.client.HeyTelecomClient._get")
    def test_get_invoices_non_list_response(self, mock_get):
        mock_get.return_value = "not_a_list"
        client = HeyTelecomClient()
        with pytest.raises(APIError, match="Expected list"):
            client.get_invoices()
        client.close()

    @patch("heytelecom.client.HeyTelecomClient._get")
    def test_get_benefits(self, mock_get):
        mock_get.return_value = {"benefit": "yes"}
        client = HeyTelecomClient()
        result = client.get_benefits()
        assert result == {"benefit": "yes"}
        client.close()

    @patch("heytelecom.client.HeyTelecomClient._get")
    def test_get_benefits_error(self, mock_get):
        mock_get.side_effect = APIError("Something went wrong", status_code=500)
        client = HeyTelecomClient()
        with pytest.raises(APIError, match="Something went wrong"):
            client.get_benefits()
        client.close()

    @patch("heytelecom.client.HeyTelecomClient._get")
    def test_get_profile_products(self, mock_get):
        mock_get.return_value = {"products": []}
        client = HeyTelecomClient()
        assert client.get_profile_products() == {"products": []}
        client.close()

    @patch("heytelecom.client.HeyTelecomClient.get_products")
    @patch("heytelecom.client.HeyTelecomClient.get_latest_invoice")
    def test_get_account_data(self, mock_invoice, mock_products):
        mock_products.return_value = []
        mock_invoice.return_value = None
        client = HeyTelecomClient()
        data = client.get_account_data(use_cache=False)
        assert data.provider == "hey!"
        assert data.products == []
        assert data.latest_invoice is None
        client.close()

    def test_invalidate_cache(self):
        client = HeyTelecomClient()
        client._cache.set("test", "value")
        assert client._cache.get("test") == "value"
        client.invalidate_cache()
        assert client._cache.get("test") is None
        client.close()

    def test_close_is_idempotent(self):
        client = HeyTelecomClient()
        client.close()
        client.close()

    def test_session_has_retry(self):
        client = HeyTelecomClient()
        adapter = client.session.get_adapter("https://api.heytelecom.be")
        assert adapter.max_retries.total == 2
        assert adapter.max_retries.backoff_factor == 0.5
        assert adapter.max_retries.status_forcelist == {502, 503, 504}
        assert adapter.max_retries.allowed_methods == {"GET"}
        client.close()

    def test_get_maps_401_to_authentication_error(self):
        client = HeyTelecomClient()
        client.access_token = "tok"
        client._token_expires_at = time.time() + 1000
        resp = MagicMock(spec=requests.Response)
        resp.ok = False
        resp.status_code = 401
        resp.text = "unauthorized"
        resp.headers = {}
        with (
            patch.object(client.session, "get", return_value=resp),
            pytest.raises(AuthenticationError, match="Authentication failed"),
        ):
            client._get("/api/test")
        client.close()

    def test_get_maps_500_to_api_error(self):
        client = HeyTelecomClient()
        client.access_token = "tok"
        client._token_expires_at = time.time() + 1000
        resp = MagicMock(spec=requests.Response)
        resp.ok = False
        resp.status_code = 500
        resp.text = "server broke"
        resp.headers = {}
        with patch.object(client.session, "get", return_value=resp):
            with pytest.raises(APIError, match="HTTP 500") as exc_info:
                client._get("/api/test")
            assert exc_info.value.status_code == 500
        client.close()

    def test_get_maps_network_error(self):
        client = HeyTelecomClient()
        client.access_token = "tok"
        client._token_expires_at = time.time() + 1000
        with (
            patch.object(client.session, "get", side_effect=requests.ConnectionError("down")),
            pytest.raises(APIError, match="Network error"),
        ):
            client._get("/api/test")
        client.close()

    def test_get_maps_non_json_to_api_error(self):
        client = HeyTelecomClient()
        client.access_token = "tok"
        client._token_expires_at = time.time() + 1000
        resp = MagicMock(spec=requests.Response)
        resp.ok = True
        resp.status_code = 200
        resp.headers = {"content-type": "text/html"}
        resp.json.side_effect = requests.exceptions.JSONDecodeError("msg", "doc", 0)
        with (
            patch.object(client.session, "get", return_value=resp),
            pytest.raises(APIError, match="Incapsula"),
        ):
            client._get("/api/test")
        client.close()

    @patch("heytelecom.client.HeyTelecomClient._get")
    def test_fetch_usage_returns_none_on_error(self, mock_get):
        mock_get.side_effect = APIError("fail")
        client = HeyTelecomClient()
        assert client._fetch_usage("32478123456") is None
        client.close()

    @patch("heytelecom.client.HeyTelecomClient._get")
    def test_fetch_usage_returns_none_on_parse_error(self, mock_get):
        mock_get.return_value = {"BalancePresentation": [None]}
        client = HeyTelecomClient()
        assert client._fetch_usage("32478123456") is None
        client.close()
