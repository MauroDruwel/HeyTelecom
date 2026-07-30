from __future__ import annotations

from heytelecom.usage import parse_usage_response


def _make_balance(
    name,
    unit,
    consumed_amount,
    category,
    unlimited=False,
    forfeit_amount=None,
    forfeit_unit=None,
):
    entry = {
        "Name": name,
        "Unit": unit,
        "ConsumedAmount": {"Amount": consumed_amount},
        "Category": category,
        "Unlimited": unlimited,
    }
    if forfeit_amount is not None:
        entry["AmountOfForfeit"] = {"Amount": forfeit_amount, "Unit": forfeit_unit or unit}
    return entry


def test_parse_data_usage():
    data = {
        "BalancePresentation": [
            _make_balance(
                "Surfvolume",
                "MByte",
                500,
                "Data",
                forfeit_amount=20480,
                forfeit_unit="MByte",
            ),
        ],
        "dateRange": {"start": "2025-01-01", "end": "2025-01-31"},
    }
    result = parse_usage_response(data)
    assert result is not None
    assert result.period == {"start": "2025-01-01", "end": "2025-01-31"}
    assert result.data["used"] == 0.49  # 500 MB = 0.49 GB (rounded)
    assert result.data["limit"] == 20.0  # 20480 MB = 20 GB
    assert result.data["unlimited"] is False


def test_parse_unlimited_data():
    data = {
        "BalancePresentation": [
            _make_balance("onbeperkt data", "MByte", 100, "Data", unlimited=True),
        ],
    }
    result = parse_usage_response(data)
    assert result is not None
    assert result.data["unlimited"] is True
    assert result.data["limit"] is None


def test_parse_calls():
    data = {
        "BalancePresentation": [
            _make_balance("onbeperkt bellen", "HH:MI", 45, "Voice", unlimited=True),
        ],
    }
    result = parse_usage_response(data)
    assert result is not None
    assert result.calls["used"] == 45
    assert result.calls["unlimited"] is True


def test_parse_sms():
    data = {
        "BalancePresentation": [
            _make_balance("onbeperkt sms/mms", "Message", 10, "Voice", unlimited=True),
        ],
    }
    result = parse_usage_response(data)
    assert result is not None
    assert result.sms_mms["used"] == 10
    assert result.sms_mms["unlimited"] is True


def test_parse_sms_with_limit():
    data = {
        "BalancePresentation": [
            _make_balance("sms", "Message", 5, "Voice", forfeit_amount=200, forfeit_unit="Message"),
        ],
    }
    result = parse_usage_response(data)
    assert result is not None
    assert result.sms_mms["used"] == 5
    assert result.sms_mms["limit"] == 200


def test_parse_empty_balances():
    data = {"BalancePresentation": []}
    assert parse_usage_response(data) is None


def test_parse_missing_balances():
    data = {}
    assert parse_usage_response(data) is None


def test_parse_non_list_balances():
    data = {"BalancePresentation": "not_a_list"}
    assert parse_usage_response(data) is None


def test_parse_only_cost_entries():
    data = {
        "BalancePresentation": [
            _make_balance("Buiten abonnement", "Euro", 0, "Voice"),
        ],
    }
    result = parse_usage_response(data)
    assert result is None  # no useful data


def test_parse_data_with_amount_of_forfeit_as_limit():
    data = {
        "BalancePresentation": [
            _make_balance(
                "Surfvolume",
                "MByte",
                1024,
                "Data",
                forfeit_amount=10240,
                forfeit_unit="MByte",
            ),
        ],
    }
    result = parse_usage_response(data)
    assert result is not None
    assert result.data["used"] == 1.0
    assert result.data["limit"] == 10.0


def test_parse_data_used_none():
    entry = {
        "Name": "Surfvolume",
        "Unit": "MByte",
        "ConsumedAmount": {},
        "Category": "Data",
        "Unlimited": False,
    }
    data = {"BalancePresentation": [entry]}
    result = parse_usage_response(data)
    assert result is None


def test_parse_data_unit_normalization():
    data = {
        "BalancePresentation": [
            _make_balance(
                "Internet GB",
                "MByte",
                2048,
                "Data",
                forfeit_amount=10240,
                forfeit_unit="MByte",
            ),
        ],
    }
    result = parse_usage_response(data)
    assert result is not None
    assert result.data["used"] == 2.0
    assert result.data["limit"] == 10.0
    assert result.data["limit"] == 10.0


def test_parse_mixed_usage():
    data = {
        "BalancePresentation": [
            _make_balance(
                "Surfvolume",
                "MByte",
                2048,
                "Data",
                forfeit_amount=10240,
                forfeit_unit="MByte",
            ),
            _make_balance("onbeperkt bellen", "HH:MI", 60, "Voice", unlimited=True),
            _make_balance("onbeperkt sms/mms", "Message", 25, "Voice", unlimited=True),
        ],
    }
    result = parse_usage_response(data)
    assert result is not None
    assert result.data["used"] == 2.0
    assert result.data["limit"] == 10.0
    assert result.calls["used"] == 60
    assert result.calls["unlimited"] is True
    assert result.sms_mms["used"] == 25
    assert result.sms_mms["unlimited"] is True


def test_parse_english_names():
    data = {
        "BalancePresentation": [
            _make_balance(
                "Data volume",
                "MB",
                500,
                "Data",
                forfeit_amount=10000,
                forfeit_unit="MB",
            ),
            _make_balance("Calls", "min", 30, "Voice"),
            _make_balance("unlimited sms", "Message", 0, "Voice", unlimited=True),
        ],
    }
    result = parse_usage_response(data)
    assert result is not None
    assert result.data["used"] == 0.49  # 500 MB = 0.49 GB (rounded)
    assert result.calls["used"] == 30
    assert result.sms_mms["unlimited"] is True
