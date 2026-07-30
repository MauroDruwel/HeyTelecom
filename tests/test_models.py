from __future__ import annotations

from heytelecom.models import AccountData, Contract, Invoice, Product, UsageData


def test_usage_data_to_dict():
    usage = UsageData(
        period={"start": "2025-01-01", "end": "2025-01-31"},
        data={"used": 5.0, "limit": 10.0, "unlimited": False},
    )
    d = usage.to_dict()
    assert d["period"] == {"start": "2025-01-01", "end": "2025-01-31"}
    assert d["data"]["used"] == 5.0


def test_usage_data_empty():
    usage = UsageData()
    assert usage.to_dict() == {}


def test_contract_to_dict():
    contract = Contract(price_per_month_eur=29.99)
    d = contract.to_dict()
    assert d["price_per_month_eur"] == 29.99


def test_contract_empty():
    contract = Contract()
    assert contract.to_dict() == {}


def test_product_to_dict():
    product = Product(
        product_id="mobile_32478123456",
        product_type="mobile",
        phone_number="0478123456",
        tariff="hey! mobile S",
        contract=Contract(price_per_month_eur=5.0),
    )
    d = product.to_dict()
    assert d["product_id"] == "mobile_32478123456"
    assert d["contract"]["price_per_month_eur"] == 5.0


def test_product_minimal():
    product = Product(product_id="x", product_type="mobile")
    d = product.to_dict()
    assert d == {"product_id": "x", "product_type": "mobile"}


def test_invoice_to_dict():
    inv = Invoice(
        invoice_id="INV-001",
        amount_eur=45.50,
        status="paid",
        paid=True,
        date="2025-01-15",
        due_date="2025-02-14",
    )
    d = inv.to_dict()
    assert d["invoice_id"] == "INV-001"
    assert d["amount_eur"] == 45.50
    assert d["paid"] is True


def test_invoice_default_paid_false():
    inv = Invoice()
    assert inv.paid is False


def test_account_data_to_dict():
    account = AccountData(
        products=[
            Product(product_id="mobile_1", product_type="mobile"),
            Product(product_id="internet_1", product_type="internet"),
        ],
        latest_invoice=Invoice(invoice_id="INV-001", amount_eur=50.0),
    )
    d = account.to_dict()
    assert len(d["products"]) == 2
    assert d["latest_invoice"]["invoice_id"] == "INV-001"
    assert d["provider"] == "hey!"


def test_account_data_empty():
    account = AccountData()
    d = account.to_dict()
    assert d["provider"] == "hey!"
    assert "products" not in d or d["products"] == []
    assert "latest_invoice" not in d
