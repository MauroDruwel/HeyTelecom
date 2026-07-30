from __future__ import annotations

import base64
import hashlib
import secrets
import time
from dataclasses import fields
from typing import Any


def _asdict(instance) -> dict[str, Any]:
    result = {}
    for f in fields(instance):
        value = getattr(instance, f.name)
        if value is not None:
            if isinstance(value, list):
                result[f.name] = [
                    item.to_dict() if hasattr(item, "to_dict") else item for item in value
                ]
            elif hasattr(value, "to_dict"):
                nested = value.to_dict()
                if nested:
                    result[f.name] = nested
            else:
                result[f.name] = value
    return result


def b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def generate_pkce() -> tuple[str, str]:
    code_verifier = b64url(secrets.token_bytes(48))
    code_challenge = b64url(hashlib.sha256(code_verifier.encode("ascii")).digest())
    return code_verifier, code_challenge


def normalize_msisdn(msisdn: str) -> str:
    msisdn = msisdn.strip()
    if msisdn.startswith("0") and not msisdn.startswith("00"):
        return "32" + msisdn[1:]
    return msisdn


def format_msisdn(msisdn: str) -> str:
    msisdn = msisdn.strip()
    if msisdn.startswith("32") and len(msisdn) > 2:
        return "0" + msisdn[2:]
    if msisdn.startswith("00") and len(msisdn) > 2:
        return "0" + msisdn[2:]
    return msisdn


def mbytes_to_gbytes(mb: float | None) -> float | None:
    if mb is None:
        return None
    return round(mb / 1024, 2)


class TTLCache:
    def __init__(self, ttl: float = 60):
        self._data: dict[str, tuple[float, Any]] = {}
        self._ttl = ttl

    def get(self, key: str) -> Any:
        entry = self._data.get(key)
        if entry is None:
            return None
        deadline, value = entry
        if time.monotonic() > deadline:
            del self._data[key]
            return None
        return value

    def set(self, key: str, value: Any) -> None:
        self._data[key] = (time.monotonic() + self._ttl, value)

    def invalidate(self) -> None:
        self._data.clear()
