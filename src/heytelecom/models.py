from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .utils import _asdict


@dataclass
class UsageData:
    period: dict[str, str] | None = None
    data: dict[str, Any] | None = None
    calls: dict[str, Any] | None = None
    sms_mms: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return _asdict(self)


@dataclass
class Contract:
    price_per_month_eur: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return _asdict(self)


@dataclass
class Product:
    product_id: str
    product_type: str
    phone_number: str | None = None
    easy_switch_number: str | None = None
    tariff: str | None = None
    contract: Contract | None = None
    usage: UsageData | None = None

    def to_dict(self) -> dict[str, Any]:
        return _asdict(self)


@dataclass
class Invoice:
    invoice_id: str | None = None
    amount_eur: float | None = None
    status: str | None = None
    paid: bool = False
    date: str | None = None
    due_date: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return _asdict(self)


@dataclass
class AccountData:
    provider: str = "hey!"
    last_sync: str | None = None
    products: list[Product] = field(default_factory=list)
    latest_invoice: Invoice | None = None

    def to_dict(self) -> dict[str, Any]:
        return _asdict(self)
