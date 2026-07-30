from __future__ import annotations

import logging
import threading
import time
import weakref
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from . import auth
from .constants import (
    API_BASE,
    BFF_BASE_HEADERS,
    DEFAULT_HEADERS,
    PATH_BENEFITS,
    PATH_INVOICES,
    PATH_LATEST_INVOICE,
    PATH_PRODUCT_INVENTORY,
    PATH_PROFILE_PRODUCTS,
    PATH_USAGE,
    PRODUCT_TYPE_FIXED,
    PRODUCT_TYPE_MOBILE,
    REQUEST_TIMEOUT,
)
from .exceptions import APIError, AuthenticationError, HeyTelecomError
from .models import AccountData, Contract, Invoice, Product, UsageData
from .usage import parse_usage_response
from .utils import TTLCache, format_msisdn, normalize_msisdn

__all__ = ["HeyTelecomClient"]

logger = logging.getLogger(__name__)


def _extract_amount(data: dict) -> float | None:
    """Extract a monetary amount from an API response dict, trying multiple keys."""
    candidates = (
        data.get("amount", {}).get("value") if isinstance(data.get("amount"), dict) else None,
        data.get("amountEur"),
        data.get("totalAmount"),
        data.get("invoiceAmount", {}).get("value")
        if isinstance(data.get("invoiceAmount"), dict)
        else None,
    )
    for c in candidates:
        if c is not None:
            return round(float(c), 2)
    return None


def _parse_invoice(data: dict) -> Invoice:
    amount = _extract_amount(data)
    status = data.get("status", "")
    paid = status.lower() in ("betaald", "paid") if isinstance(status, str) else False
    date = data.get("date") or data.get("referenceDate") or data.get("invoiceDate")
    payment_dates = data.get("paymentDates")
    due_date = (
        data.get("dueDate")
        or data.get("paymentDueDate")
        or (payment_dates.get("endDate") if isinstance(payment_dates, dict) else None)
    )
    invoice_id = data.get("invoiceId") or data.get("invoiceNumber") or data.get("id")
    if not invoice_id and date:
        invoice_id = f"INV-{str(date).replace('-', '')}"

    return Invoice(
        invoice_id=str(invoice_id) if invoice_id is not None else None,
        amount_eur=amount,
        status=status if status != "" else None,
        paid=paid,
        date=date,
        due_date=due_date,
    )


class HeyTelecomClient:
    def __init__(
        self,
        email: str | None = None,
        password: str | None = None,
    ):
        self.email = email
        self.password = password
        self.session = self._make_session()
        self.access_token: str | None = None
        self._token_expires_at: float = 0.0
        self._token_lock = threading.Lock()
        self._cache = TTLCache()
        weakref.finalize(self, self.session.close)

    @staticmethod
    def _make_session() -> requests.Session:
        """Create a requests session with retry support and default headers."""
        session = requests.Session()
        retry = Retry(
            total=2,
            backoff_factor=0.5,
            status_forcelist={502, 503, 504},
            allowed_methods={"GET"},
        )
        session.mount("https://", HTTPAdapter(max_retries=retry))
        session.headers.update(DEFAULT_HEADERS)
        return session

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def close(self) -> None:
        """Close the underlying HTTP session."""
        self.session.close()

    def clear_credentials(self) -> None:
        """Remove stored email and password from memory.

        After calling this method, automatic re-authentication on token
        expiry will no longer be possible — call :meth:`login` again first.
        """
        self.email = None
        self.password = None

    def login(self) -> str:
        """Authenticate and obtain an access token.

        Raises ``ValueError`` when email or password were not provided.
        """
        if not self.email or not self.password:
            raise ValueError("Email and password required for login")

        token, expires_at = auth.login(self.session, self.email, self.password)
        with self._token_lock:
            self.access_token = token
            self._token_expires_at = expires_at
            self._cache.invalidate()
        return token

    def _get_token(self) -> str:
        """Return a valid access token, re-authenticating if expired.

        Uses double-checked locking to prevent concurrent re-login.
        """
        with self._token_lock:
            if not self.access_token:
                raise AuthenticationError(
                    "Not authenticated — call login() or pass email/password first."
                )
            if time.time() < self._token_expires_at:
                return self.access_token

            if not self.email or not self.password:
                raise AuthenticationError(
                    "Access token expired and credentials are not available for "
                    "re-authentication. Call login() again."
                )

            logger.info("Access token expired, re-authenticating")
            token, expires_at = auth.login(self.session, self.email, self.password)
            self.access_token = token
            self._token_expires_at = expires_at
            self._cache.invalidate()
            return self.access_token

    def _bff_headers(self, extra: dict | None = None) -> dict[str, str]:
        headers: dict[str, str] = {
            **BFF_BASE_HEADERS,
            "Authorization": f"Bearer {self._get_token()}",
        }
        if extra:
            headers.update(extra)
        return headers

    def _raise_for_response(self, resp: requests.Response, path: str) -> None:
        """Map HTTP failures to library exceptions."""
        if resp.ok:
            return
        status = resp.status_code
        if status in (401, 403):
            raise AuthenticationError(
                f"Authentication failed for {path} (HTTP {status}). "
                "Token may be invalid — try login() again."
            )
        body_preview = (resp.text or "")[:300]
        raise APIError(
            f"API request failed for {path} (HTTP {status}): {body_preview}",
            status_code=status,
        )

    def _get(self, path: str, params=None, extra_headers=None) -> Any:
        try:
            resp = self.session.get(
                f"{API_BASE}{path}",
                params=params,
                headers=self._bff_headers(extra_headers),
                timeout=REQUEST_TIMEOUT,
            )
        except requests.RequestException as exc:
            raise APIError(f"Network error requesting {path}: {exc}") from exc

        self._raise_for_response(resp, path)

        try:
            return resp.json()
        except requests.exceptions.JSONDecodeError as exc:
            raise APIError(
                f"Expected JSON from {path} but got content-type "
                f"{resp.headers.get('content-type', '?')!r} — possible "
                "Incapsula/Imperva challenge page."
            ) from exc

    def _classify_product(
        self, product_type_raw: str, msisdn_raw: str
    ) -> tuple[str, str | None, str | None, str]:
        """Map raw product type to a friendly type and derived identifiers."""
        if product_type_raw == PRODUCT_TYPE_MOBILE:
            return (
                "mobile",
                format_msisdn(msisdn_raw),
                None,
                f"mobile_{normalize_msisdn(msisdn_raw)}",
            )
        if product_type_raw == PRODUCT_TYPE_FIXED:
            return "internet", None, msisdn_raw, f"internet_{msisdn_raw}"
        product_type = product_type_raw or "unknown"
        phone = format_msisdn(msisdn_raw) if msisdn_raw else None
        easy_switch = msisdn_raw if not phone else None
        return product_type, phone, easy_switch, f"{product_type}_{msisdn_raw}"

    def _build_product(self, item: dict, usage_results: dict[str, UsageData | None]) -> Product:
        msisdn_raw = item.get("MSISDN", "")
        tariff = item.get("tariffName", "")
        product_type_raw = item.get("productType", "")
        price = item.get("price")
        price_value = price.get("value") if isinstance(price, dict) else None

        product_type, phone_number, easy_switch_number, product_id = self._classify_product(
            product_type_raw, msisdn_raw
        )

        contract = None
        if price_value is not None:
            contract = Contract(price_per_month_eur=round(float(price_value), 2))

        usage = None
        if product_type_raw == PRODUCT_TYPE_MOBILE:
            usage = usage_results.get(normalize_msisdn(msisdn_raw))

        return Product(
            product_id=product_id,
            product_type=product_type,
            phone_number=phone_number,
            easy_switch_number=easy_switch_number,
            tariff=tariff or None,
            contract=contract,
            usage=usage,
        )

    def get_products(self, use_cache: bool = True) -> list[Product]:
        """Fetch all products and their usage data.

        Usage for each mobile line is fetched in parallel via a thread pool.

        Raises:
            APIError: When the product inventory request fails.
            AuthenticationError: When authentication is missing or rejected.
        """
        if use_cache:
            cached = self._cache.get("products")
            if cached is not None:
                return cached

        inventory = self._get(PATH_PRODUCT_INVENTORY)
        if not isinstance(inventory, list):
            raise APIError(f"Expected list from product inventory, got {type(inventory).__name__}")

        mobile_msisdns = [
            normalize_msisdn(item["MSISDN"])
            for item in inventory
            if item.get("productType") == PRODUCT_TYPE_MOBILE and item.get("MSISDN")
        ]

        usage_results: dict[str, UsageData | None] = {}
        with ThreadPoolExecutor(max_workers=4) as pool:
            future_map = {
                pool.submit(self._fetch_usage, msisdn): msisdn for msisdn in mobile_msisdns
            }
            for future in as_completed(future_map):
                msisdn = future_map[future]
                usage_results[msisdn] = future.result()

        products = [self._build_product(item, usage_results) for item in inventory]

        self._cache.set("products", products)
        return products

    def get_latest_invoice(self, use_cache: bool = True) -> Invoice | None:
        """Fetch the latest invoice.

        Returns ``None`` when the account has no invoices.
        Raises ``APIError`` / ``AuthenticationError`` on request failure.
        """
        if use_cache:
            cached = self._cache.get("latest_invoice")
            if cached is not None:
                return cached

        data = self._get(PATH_LATEST_INVOICE)
        if not data:
            return None

        if not isinstance(data, dict):
            raise APIError(f"Expected object from latest invoice, got {type(data).__name__}")

        invoice = _parse_invoice(data)
        self._cache.set("latest_invoice", invoice)
        return invoice

    def get_invoices(self) -> list[Invoice]:
        """Fetch all invoices.

        Raises ``APIError`` / ``AuthenticationError`` on request failure.
        """
        data = self._get(PATH_INVOICES)
        if not isinstance(data, list):
            raise APIError(f"Expected list from invoices, got {type(data).__name__}")

        return [_parse_invoice(item) for item in data if isinstance(item, dict)]

    def get_benefits(self) -> Any:
        """Fetch account benefits.

        Raises ``APIError`` / ``AuthenticationError`` on request failure.
        """
        return self._get(PATH_BENEFITS)

    def get_profile_products(self) -> Any:
        """Fetch profile products.

        Raises ``APIError`` / ``AuthenticationError`` on request failure.
        """
        return self._get(PATH_PROFILE_PRODUCTS)

    def get_account_data(self, use_cache: bool = True) -> AccountData:
        """Fetch products and latest invoice (in parallel when uncached)."""
        if use_cache:
            cached_products = self._cache.get("products")
            cached_invoice = self._cache.get("latest_invoice")
            if cached_products is not None and cached_invoice is not None:
                return AccountData(products=cached_products, latest_invoice=cached_invoice)

        with ThreadPoolExecutor(max_workers=2) as pool:
            products_future = pool.submit(self.get_products, use_cache)
            invoice_future = pool.submit(self.get_latest_invoice, use_cache)
            products = products_future.result()
            invoice = invoice_future.result()

        return AccountData(products=products, latest_invoice=invoice)

    def invalidate_cache(self) -> None:
        self._cache.invalidate()

    def _fetch_usage(self, msisdn: str) -> UsageData | None:
        """Fetch usage for one MSISDN. Failures are logged and return None."""
        try:
            data = self._get(
                PATH_USAGE,
                params={"timestamp": int(time.time() * 1000)},
                extra_headers={"x-req-msisdn": msisdn},
            )
        except (requests.RequestException, HeyTelecomError) as exc:
            logger.warning("Failed to fetch usage for %s: %s", msisdn, exc)
            return None

        try:
            return parse_usage_response(data)
        except (ValueError, TypeError, KeyError, AttributeError) as exc:
            logger.warning("Failed to parse usage for %s: %s", msisdn, exc)
            return None
