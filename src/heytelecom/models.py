"""Dataclass models representing Hey Telecom account data.

All models inherit from ``_ToDictMixin`` which provides a ``to_dict()``
method for serialization (skipping None values via ``_asdict``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .utils import _asdict

__all__ = [
    "AccountData",
    "Contract",
    "Invoice",
    "Product",
    "UsageData",
]


class _ToDictMixin:
    def to_dict(self) -> dict[str, Any]:
        return _asdict(self)


@dataclass
class UsageData(_ToDictMixin):
    period: dict[str, str] | None = None
    data: dict[str, Any] | None = None
    calls: dict[str, Any] | None = None
    sms_mms: dict[str, Any] | None = None


@dataclass
class Contract(_ToDictMixin):
    price_per_month_eur: float | None = None


@dataclass
class Product(_ToDictMixin):
    product_id: str
    product_type: str
    phone_number: str | None = None
    easy_switch_number: str | None = None
    tariff: str | None = None
    contract: Contract | None = None
    usage: UsageData | None = None


@dataclass
class Invoice(_ToDictMixin):
    invoice_id: str | None = None
    amount_eur: float | None = None
    status: str | None = None
    paid: bool = False
    date: str | None = None
    due_date: str | None = None


@dataclass
class AccountData(_ToDictMixin):
    provider: str = "hey!"
    products: list[Product] = field(default_factory=list)
    latest_invoice: Invoice | None = None
