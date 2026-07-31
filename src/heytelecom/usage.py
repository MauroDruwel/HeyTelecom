"""Parse the raw usage JSON from the Hey Telecom BFF /usage endpoint.

The single public entry point :func:`parse_usage_response` converts the
API response into a :class:`UsageData` model, normalising data volumes
to GB and categorising entries as data / calls / SMS-MMS.
"""

from __future__ import annotations

from typing import Any

from .models import UsageData
from .utils import _to_gbytes

__all__ = ["parse_usage_response"]


_DATA_UNITS_MB = frozenset({"mbyte", "mb", "megabyte"})
_DATA_UNITS_GB = frozenset({"gbyte", "gb", "gigabyte"})
_DATA_UNITS = _DATA_UNITS_MB | _DATA_UNITS_GB
_COST_UNITS = frozenset({"euro", "eur", "€"})
_CALL_KEYWORDS = frozenset({"minuut", "bellen", "bel", "call", "calls"})


def _is_data_unit(unit: str) -> bool:
    return unit.lower() in _DATA_UNITS


def _is_cost_entry(unit: str) -> bool:
    return unit.lower() in _COST_UNITS


def _is_unlimited(name: str) -> bool:
    return "onbeperkt" in name or "unlimited" in name


def _is_call_entry(name: str, category: str) -> bool:
    return any(kw in name for kw in _CALL_KEYWORDS) or "voice" in category


def _to_gb(amount: float | None, unit: str) -> float | None:
    """Convert a data amount to GB based on the declared unit."""
    if amount is None:
        return None
    unit_l = (unit or "").lower()
    if unit_l in _DATA_UNITS_GB:
        return round(float(amount), 2)
    # Default / MB units
    return _to_gbytes(float(amount), from_unit="mb")


def _parse_data_balance(bal: dict) -> dict[str, Any] | None:
    consumed = bal.get("ConsumedAmount", {})
    consumed_val = consumed.get("Amount")
    if consumed_val is not None:
        consumed_val = float(consumed_val)

    unlimited = _is_unlimited((bal.get("Name") or "").lower())
    unit = (bal.get("Unit") or consumed.get("Unit") or "").lower()
    used_gb = _to_gb(consumed_val, unit) if consumed_val is not None else None

    limit_gb: float | None = None
    forfeit = bal.get("AmountOfForfeit", {})
    if forfeit:
        limit_val = forfeit.get("Amount")
        limit_unit = (forfeit.get("Unit") or unit or "").lower()
        if limit_val is not None and _is_data_unit(limit_unit):
            limit_gb = _to_gb(float(limit_val), limit_unit)

    if limit_gb is None:
        limit_raw = bal.get("LimitAmount")
        if limit_raw is not None:
            # LimitAmount has no separate unit field in observed responses;
            # prefer forfeit unit, then balance unit, defaulting to MB.
            limit_unit = unit if _is_data_unit(unit) else "mbyte"
            limit_gb = _to_gb(float(limit_raw), limit_unit)

    if used_gb is None and limit_gb is None and not unlimited:
        return None

    return {
        "used": used_gb,
        "limit": limit_gb,
        "unlimited": unlimited,
    }


def _parse_sms_balance(bal: dict) -> dict[str, Any] | None:
    consumed = bal.get("ConsumedAmount", {})
    consumed_val = consumed.get("Amount")

    used = int(float(consumed_val)) if consumed_val is not None else 0
    unlimited = _is_unlimited((bal.get("Name") or "").lower())
    unit = (bal.get("Unit") or "").lower()

    limit: int | None = None
    forfeit = bal.get("AmountOfForfeit", {})
    if forfeit and not _is_cost_entry(unit):
        limit_val = forfeit.get("Amount")
        if limit_val is not None:
            limit = int(float(limit_val))

    entry: dict[str, Any] = {
        "used": used,
        "unlimited": unlimited,
    }
    if limit is not None:
        entry["limit"] = limit
    return entry


def _parse_calls_balance(bal: dict) -> dict[str, Any] | None:
    consumed = bal.get("ConsumedAmount", {})
    consumed_val = consumed.get("Amount")

    used = float(consumed_val) if consumed_val is not None else 0.0
    unlimited = _is_unlimited((bal.get("Name") or "").lower())

    return {
        "used": used,
        "unlimited": unlimited,
    }


def parse_usage_response(data: dict) -> UsageData | None:
    """Parse a raw usage API response into a ``UsageData`` model.

    Returns ``None`` when no usable balance entries are found.
    """
    balances = data.get("BalancePresentation", [])
    if not isinstance(balances, list) or not balances:
        return None

    period = None
    # Try top-level dateRange/period first
    date_range = data.get("dateRange") or data.get("period")
    if date_range and isinstance(date_range, dict):
        period = {
            "start": date_range.get("start"),
            "end": date_range.get("end"),
        }
    else:
        # Extract from first data balance entry (PreviousInvoiceClosing/NextInvoiceClosing)
        for bal in balances:
            if not isinstance(bal, dict):
                continue
            if bal.get("PreviousInvoiceClosing") or bal.get("NextInvoiceClosing"):
                start = bal.get("PreviousInvoiceClosing")
                end = bal.get("NextInvoiceClosing")
                # Parse dates if they're in ISO format
                if start:
                    start = start.split("T")[0] if "T" in start else start
                if end:
                    end = end.split("T")[0] if "T" in end else end
                period = {"start": start, "end": end}
                break

    usage_dict: dict[str, Any] = {}

    for bal in balances:
        if not isinstance(bal, dict):
            continue
        name = (bal.get("Name") or "").lower()
        unit = (bal.get("Unit") or "").lower()
        category = (bal.get("Category") or "").lower()

        if _is_data_unit(unit) and ("data" in name or "data" in category or "internet" in category):
            parsed = _parse_data_balance(bal)
            if parsed:
                usage_dict["data"] = parsed

        elif "sms" in name or "mms" in name:
            parsed = _parse_sms_balance(bal)
            if parsed:
                usage_dict["sms_mms"] = parsed

        elif not _is_cost_entry(unit) and _is_call_entry(name, category):
            parsed = _parse_calls_balance(bal)
            if parsed:
                usage_dict["calls"] = parsed

    if not usage_dict:
        return None

    return UsageData(period=period, **usage_dict)
