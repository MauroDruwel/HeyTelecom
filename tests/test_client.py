from __future__ import annotations

import time
from unittest.mock import patch

import pytest
import requests

from heytelecom.client import HeyTelecomClient, _extract_amount
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

    @patch("heytelecom.client.auth.login", return_value=("token123", 1000.0))
    def test_login_success(self, _mock_login):
        client = HeyTelecomClient(email="test@test.com", password="secret")
        client.login()
        assert client.access_token == "token123"
        client.close()

    def test_get_token_raises_when_not_authenticated(self):
        client = HeyTelecomClient()
        with pytest.raises(AuthenticationError, match="Not authenticated"):
            client._get_token()
        client.close()

    @patch("heytelecom.client.auth.login", return_value=("token123", time.time()))
    def test_get_token_reauthenticates_when_expired(self, mock_login):
        client = HeyTelecomClient(email="test@test.com", password="secret")
        client._token_obtained_at = time.time() - 99999
        client.access_token = "expired_token"
        token = client._get_token()
        assert token == "token123"
        assert mock_login.called
        client.close()

    def test_bff_headers_include_authorization(self):
        client = HeyTelecomClient(email="test@test.com", password="secret")
        client.access_token = "my_token"
        client._token_obtained_at = time.time()
        headers = client._bff_headers()
        assert headers["Authorization"] == "Bearer my_token"
        assert "x-api-key" in headers
        client.close()

    def test_bff_headers_with_extra(self):
        client = HeyTelecomClient(email="test@test.com", password="secret")
        client.access_token = "my_token"
        client._token_obtained_at = time.time()
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
    def test_get_latest_invoice_returns_none_on_error(self, mock_get):
        mock_get.side_effect = requests.RequestException("Network error")
        client = HeyTelecomClient()
        invoice = client.get_latest_invoice(use_cache=False)
        assert invoice is None
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
        client.close()

    @patch("heytelecom.client.HeyTelecomClient._get")
    def test_get_invoices_non_list_response(self, mock_get):
        mock_get.return_value = "not_a_list"
        client = HeyTelecomClient()
        invoices = client.get_invoices()
        assert invoices == []
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
        mock_get.side_effect = APIError("Something went wrong")
        client = HeyTelecomClient()
        result = client.get_benefits()
        assert result is None
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
