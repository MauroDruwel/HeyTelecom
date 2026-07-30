from __future__ import annotations

from typing import Any

from .models import UsageData
from .utils import mbytes_to_gbytes


def _is_data_unit(unit: str) -> bool:
    return unit in ("mbyte", "mb", "megabyte", "gbyte", "gb", "gigabyte")


def _is_cost_entry(unit: str) -> bool:
    return unit in ("euro", "eur", "€")


def _is_unlimited(name: str) -> bool:
    return "onbeperkt" in name or "unlimited" in name


def parse_usage_response(data: dict) -> UsageData | None:
    balances = data.get("BalancePresentation", [])
    if not isinstance(balances, list) or not balances:
        return None

    period = None
    date_range = data.get("dateRange") or data.get("period")
    if date_range:
        period = {
            "start": date_range.get("start"),
            "end": date_range.get("end"),
        }

    calls_used = 0.0
    calls_unlimited = False
    sms_used = 0
    sms_unlimited = False
    sms_limit: int | None = None
    data_used_gb: float | None = None
    data_limit_gb: float | None = None
    data_unlimited = False

    for bal in balances:
        name = (bal.get("Name") or "").lower()
        consumed = bal.get("ConsumedAmount", {})
        consumed_val = consumed.get("Amount")
        category = (bal.get("Category") or "").lower()
        unit = (bal.get("Unit") or "").lower()

        if consumed_val is not None:
            consumed_val = float(consumed_val)

        if _is_data_unit(unit) and ("data" in name or "data" in category or "internet" in category):
            data_unlimited = _is_unlimited(name)
            data_used_gb = mbytes_to_gbytes(consumed_val) if consumed_val is not None else None

            forfeit = bal.get("AmountOfForfeit", {})
            if forfeit:
                limit_val = forfeit.get("Amount")
                limit_unit = (forfeit.get("Unit") or "").lower()
                if limit_val is not None and _is_data_unit(limit_unit):
                    data_limit_gb = mbytes_to_gbytes(float(limit_val))

            if data_limit_gb is None:
                limit_raw = bal.get("LimitAmount")
                if limit_raw is not None:
                    data_limit_gb = float(limit_raw)

        elif "sms" in name or "mms" in name:
            sms_used = int(consumed_val) if consumed_val is not None else 0
            sms_unlimited = _is_unlimited(name)
            forfeit = bal.get("AmountOfForfeit", {})
            if forfeit and not _is_cost_entry(unit):
                sms_limit_val = forfeit.get("Amount")
                if sms_limit_val is not None:
                    sms_limit = int(float(sms_limit_val))

        elif not _is_cost_entry(unit) and (
            "minuut" in name or "bel" in name or "call" in name or "voice" in category
        ):
            calls_used = consumed_val if consumed_val is not None else 0.0
            calls_unlimited = _is_unlimited(name)

    usage_dict: dict[str, Any] = {}
    if data_used_gb is not None or data_limit_gb is not None or data_unlimited:
        usage_dict["data"] = {
            "used": data_used_gb,
            "limit": data_limit_gb,
            "unlimited": data_unlimited,
        }
    if calls_used or calls_unlimited:
        usage_dict["calls"] = {
            "used": calls_used,
            "unlimited": calls_unlimited,
        }
    if sms_used or sms_unlimited or sms_limit is not None:
        entry: dict[str, Any] = {
            "used": sms_used,
            "unlimited": sms_unlimited,
        }
        if sms_limit is not None:
            entry["limit"] = sms_limit
        usage_dict["sms_mms"] = entry

    if not usage_dict:
        return None

    return UsageData(period=period, **usage_dict)
