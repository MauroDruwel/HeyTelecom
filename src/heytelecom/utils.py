"""Internal utility helpers for the heytelecom library.

Provides PKCE generation, MSISDN formatting, a TTL-based cache, and a
custom dataclass serializer that skips None values.
"""

from __future__ import annotations

import base64
import hashlib
import secrets
import threading
import time
from collections import OrderedDict
from dataclasses import fields
from typing import Any

__all__ = [
    "TTLCache",
    "format_msisdn",
    "normalize_msisdn",
]


def _asdict(instance) -> dict[str, Any]:
    """Convert a dataclass instance to a dict, skipping None fields.

    Nested objects with a ``to_dict()`` method are converted recursively.
    Empty lists and None values are omitted from the result.
    """
    result = {}
    for f in fields(instance):
        value = getattr(instance, f.name)
        if value is None:
            continue
        if isinstance(value, list):
            converted = [item.to_dict() if hasattr(item, "to_dict") else item for item in value]
            if converted:
                result[f.name] = converted
        elif hasattr(value, "to_dict"):
            nested = value.to_dict()
            if nested:
                result[f.name] = nested
        else:
            result[f.name] = value
    return result


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _generate_pkce() -> tuple[str, str]:
    code_verifier = _b64url(secrets.token_bytes(48))
    code_challenge = _b64url(hashlib.sha256(code_verifier.encode("ascii")).digest())
    return code_verifier, code_challenge


def normalize_msisdn(msisdn: str) -> str:
    msisdn = msisdn.strip()
    if msisdn.startswith("0") and not msisdn.startswith("00"):
        return "32" + msisdn[1:]
    return msisdn


def format_msisdn(msisdn: str) -> str:
    msisdn = msisdn.strip()
    if msisdn.startswith("+") and len(msisdn) > 1:
        msisdn = msisdn[1:]
    if msisdn.startswith("00"):
        msisdn = msisdn[2:]
    if msisdn.startswith("32") and len(msisdn) > 2:
        return "0" + msisdn[2:]
    return msisdn


def _mbytes_to_gbytes(mb: float | None) -> float | None:
    if mb is None:
        return None
    return round(mb / 1024, 2)


class TTLCache:
    def __init__(self, ttl: float = 60, maxsize: int = 128):
        self._data: OrderedDict[str, tuple[float, Any]] = OrderedDict()
        self._ttl = ttl
        self._maxsize = maxsize
        self._lock = threading.Lock()

    def get(self, key: str) -> Any:
        with self._lock:
            entry = self._data.get(key)
            if entry is None:
                return None
            deadline, value = entry
            if time.monotonic() > deadline:
                del self._data[key]
                return None
            self._data.move_to_end(key)
            return value

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._data[key] = (time.monotonic() + self._ttl, value)
            self._data.move_to_end(key)
            while len(self._data) > self._maxsize:
                self._data.popitem(last=False)

    def invalidate(self) -> None:
        with self._lock:
            self._data.clear()
