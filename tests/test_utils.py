from __future__ import annotations

import time
from threading import Thread

from heytelecom.utils import (
    TTLCache,
    _asdict,
    _b64url,
    _generate_pkce,
    _mbytes_to_gbytes,
    format_msisdn,
    normalize_msisdn,
)


def test_b64url_encodes_correctly():
    assert _b64url(b"test") == "dGVzdA"
    assert _b64url(b"f") == "Zg"
    assert _b64url(b"") == ""


def test_generate_pkce_returns_verifier_and_challenge():
    verifier, challenge = _generate_pkce()
    assert isinstance(verifier, str)
    assert isinstance(challenge, str)
    assert len(verifier) > 0
    assert len(challenge) > 0
    assert verifier != challenge


def test_normalize_msisdn_converts_national_to_international():
    assert normalize_msisdn("0478123456") == "32478123456"


def test_normalize_msisdn_strips_whitespace():
    assert normalize_msisdn(" 0478123456 ") == "32478123456"


def test_normalize_msisdn_passthrough_international():
    assert normalize_msisdn("32478123456") == "32478123456"


def test_normalize_msisdn_passthrough_00():
    assert normalize_msisdn("0032478123456") == "0032478123456"


def test_format_msisdn_converts_international_to_national():
    assert format_msisdn("32478123456") == "0478123456"


def test_format_msisdn_handles_plus_prefix():
    assert format_msisdn("+32478123456") == "0478123456"


def test_format_msisdn_handles_00_prefix():
    assert format_msisdn("0032478123456") == "0478123456"


def test_format_msisdn_passthrough_national():
    assert format_msisdn("0478123456") == "0478123456"


def test_format_msisdn_strips_whitespace():
    assert format_msisdn(" 32478123456 ") == "0478123456"


def test_normalize_and_format_are_inverses():
    national = "0478123456"
    international = normalize_msisdn(national)
    assert international == "32478123456"
    assert format_msisdn(international) == national


def test_mbytes_to_gbytes_converts():
    assert _mbytes_to_gbytes(1024) == 1.0
    assert _mbytes_to_gbytes(2048) == 2.0
    assert _mbytes_to_gbytes(500) == 0.49


def test_mbytes_to_gbytes_handles_none():
    assert _mbytes_to_gbytes(None) is None


def test_mbytes_to_gbytes_rounds_correctly():
    assert _mbytes_to_gbytes(100) == 0.1


def test_ttlcache_get_set():
    cache = TTLCache(ttl=60)
    cache.set("key", "value")
    assert cache.get("key") == "value"


def test_ttlcache_expires():
    cache = TTLCache(ttl=0.05)
    cache.set("key", "value")
    time.sleep(0.1)
    assert cache.get("key") is None


def test_ttlcache_missing_key():
    cache = TTLCache()
    assert cache.get("nonexistent") is None


def test_ttlcache_invalidate():
    cache = TTLCache()
    cache.set("a", 1)
    cache.set("b", 2)
    cache.invalidate()
    assert cache.get("a") is None
    assert cache.get("b") is None


def test_ttlcache_overwrite():
    cache = TTLCache()
    cache.set("key", "old")
    cache.set("key", "new")
    assert cache.get("key") == "new"


def test_ttlcache_thread_safety():
    cache = TTLCache(ttl=60)
    errors = []

    def worker():
        for i in range(100):
            try:
                cache.set(f"k{i}", i)
                cache.get(f"k{i}")
                cache.get("nonexistent")
            except Exception as e:
                errors.append(e)

    threads = [Thread(target=worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(errors) == 0


def test_ttlcache_invalidate_thread_safety():
    cache = TTLCache(ttl=60)
    errors = []

    def writer():
        for i in range(50):
            try:
                cache.set(f"k{i}", i)
            except Exception as e:
                errors.append(e)

    def invalidator():
        for _ in range(20):
            try:
                cache.invalidate()
            except Exception as e:
                errors.append(e)

    threads = [Thread(target=writer) for _ in range(5)]
    threads += [Thread(target=invalidator) for _ in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(errors) == 0


def test_asdict_basic():
    from dataclasses import dataclass

    @dataclass
    class Sample:
        a: str
        b: int | None = None

    instance = Sample(a="hello", b=42)
    result = _asdict(instance)
    assert result == {"a": "hello", "b": 42}


def test_asdict_skips_none():
    from dataclasses import dataclass

    @dataclass
    class Sample:
        a: str
        b: int | None = None

    instance = Sample(a="hello", b=None)
    result = _asdict(instance)
    assert result == {"a": "hello"}
    assert "b" not in result


def test_asdict_nested_with_to_dict():
    from dataclasses import dataclass

    @dataclass
    class Inner:
        val: str

        def to_dict(self):
            return {"val": self.val}

    @dataclass
    class Outer:
        inner: Inner | None = None

    instance = Outer(inner=Inner(val="test"))
    result = _asdict(instance)
    assert result == {"inner": {"val": "test"}}


def test_asdict_list_with_to_dict():
    from dataclasses import dataclass

    @dataclass
    class Item:
        name: str

        def to_dict(self):
            return {"name": self.name}

    @dataclass
    class Container:
        items: list = None

    instance = Container(items=[Item(name="a"), Item(name="b")])
    result = _asdict(instance)
    assert result == {"items": [{"name": "a"}, {"name": "b"}]}


def test_generate_pkce_different_each_call():
    v1, c1 = _generate_pkce()
    v2, c2 = _generate_pkce()
    assert v1 != v2
    assert c1 != c2
