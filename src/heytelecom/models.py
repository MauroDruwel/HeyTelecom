"""Data models for Hey Telecom."""
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from datetime import datetime


@dataclass
class UsageData:
    """Represents usage data for a product."""
    period: Optional[Dict[str, str]] = None
    data: Optional[Dict[str, Any]] = None
    calls: Optional[Dict[str, Any]] = None
    sms_mms: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        result = {}
        if self.period:
            result["period"] = self.period
        if self.data:
            result["data"] = self.data
        if self.calls:
            result["calls"] = self.calls
        if self.sms_mms:
            result["sms_mms"] = self.sms_mms
        return result


@dataclass
class Contract:
    """Represents contract information."""
    start_date: Optional[str] = None
    price_per_month_eur: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        result = {}
        if self.start_date:
            result["start_date"] = self.start_date
        if self.price_per_month_eur is not None:
            result["price_per_month_eur"] = self.price_per_month_eur
        return result


@dataclass
class Product:
    """Represents a telecom product (mobile or internet)."""
    product_id: str
    product_type: str
    phone_number: Optional[str] = None
    easy_switch_number: Optional[str] = None
    tariff: Optional[str] = None
    contract: Optional[Contract] = None
    usage: Optional[UsageData] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        result = {
            "id": self.product_id,
            "type": self.product_type
        }
        if self.phone_number:
            result["phone_number"] = self.phone_number
        if self.easy_switch_number:
            result["easy_switch_number"] = self.easy_switch_number
        if self.tariff:
            result["tariff"] = self.tariff
        if self.contract:
            contract_dict = self.contract.to_dict()
            if contract_dict:
                result["contract"] = contract_dict
        if self.usage:
            usage_dict = self.usage.to_dict()
            if usage_dict:
                result["usage"] = usage_dict
        return result


@dataclass
class Invoice:
    """Represents an invoice."""
    invoice_id: Optional[str] = None
    amount_eur: Optional[float] = None
    status: Optional[str] = None
    paid: bool = False
    date: Optional[str] = None
    due_date: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        result = {}
        if self.invoice_id:
            result["invoice_id"] = self.invoice_id
        if self.amount_eur is not None:
            result["amount_eur"] = self.amount_eur
        if self.status:
            result["status"] = self.status.lower()
        if self.paid is not None:
            result["paid"] = self.paid
        if self.date:
            result["date"] = self.date
        if self.due_date:
            result["due_date"] = self.due_date
        return result


@dataclass
class AccountData:
    """Represents account-level data."""
    provider: str = "hey!"
    last_sync: Optional[str] = None
    products: list[Product] = field(default_factory=list)
    latest_invoice: Optional[Invoice] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        result = {
            "provider": self.provider,
            "account": {
                "last_sync": self.last_sync or datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
            },
            "products": [product.to_dict() for product in self.products]
        }
        
        if self.latest_invoice:
            invoice_dict = self.latest_invoice.to_dict()
            if invoice_dict:
                result["billing"] = {
                    "latest_invoice": invoice_dict
                }
        
        return result
