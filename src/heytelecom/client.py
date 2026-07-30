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
    TOKEN_LIFETIME,
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
        data.get("amount", {}).get("value"),
        data.get("amountEur"),
        data.get("totalAmount"),
        data.get("invoiceAmount", {}).get("value"),
    )
    for c in candidates:
        if c is not None:
            return round(float(c), 2)
    return None


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
        self._token_obtained_at: float = 0.0
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

    def __enter__(self) -> HeyTelecomClient:
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

        token, obtained_at = auth.login(self.session, self.email, self.password)
        with self._token_lock:
            self.access_token = token
            self._token_obtained_at = obtained_at
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
            if time.time() - self._token_obtained_at <= TOKEN_LIFETIME:
                return self.access_token
            logger.warning("Access token expired, re-authenticating")
            token, obtained_at = auth.login(self.session, self.email, self.password)
            self.access_token = token
            self._token_obtained_at = obtained_at
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

    def _get(self, path: str, params=None, extra_headers=None) -> Any:
        resp = self.session.get(
            f"{API_BASE}{path}",
            params=params,
            headers=self._bff_headers(extra_headers),
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        try:
            return resp.json()
        except requests.exceptions.JSONDecodeError:
            raise APIError(
                f"Expected JSON from {path} but got content-type "
                f"{resp.headers.get('content-type', '?')!r} — possible "
                "Incapsula/Imperva challenge page."
            )

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
        price_value = item.get("price", {}).get("value")

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
            tariff=tariff,
            contract=contract,
            usage=usage,
        )

    def get_products(self, use_cache: bool = True) -> list[Product]:
        """Fetch all products and their usage data.

        Usage for each mobile line is fetched in parallel via a thread pool.
        """
        if use_cache:
            cached = self._cache.get("products")
            if cached is not None:
                return cached

        try:
            inventory = self._get(PATH_PRODUCT_INVENTORY)
        except (requests.RequestException, HeyTelecomError) as exc:
            logger.warning("Failed to fetch products: %s", exc)
            return []

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
        if use_cache:
            cached = self._cache.get("latest_invoice")
            if cached is not None:
                return cached

        try:
            data = self._get(PATH_LATEST_INVOICE)
        except (requests.RequestException, HeyTelecomError) as exc:
            logger.warning("Failed to fetch latest invoice: %s", exc)
            return None

        if not data:
            return None

        amount = _extract_amount(data)
        status = data.get("status", "")
        paid = status.lower() in ("betaald", "paid") if isinstance(status, str) else False
        date = data.get("date") or data.get("referenceDate") or data.get("invoiceDate")
        due_date = data.get("dueDate") or data.get("paymentDueDate")

        invoice_id = data.get("invoiceId") or data.get("id") or data.get("invoiceNumber")
        if not invoice_id and date:
            invoice_id = f"INV-{date.replace('-', '')}"

        invoice = Invoice(
            invoice_id=str(invoice_id) if invoice_id is not None else None,
            amount_eur=amount,
            status=status,
            paid=paid,
            date=date,
            due_date=due_date,
        )
        self._cache.set("latest_invoice", invoice)
        return invoice

    def get_invoices(self) -> list[Invoice]:
        data = self._get(PATH_INVOICES)
        invoices: list[Invoice] = []
        for item in data if isinstance(data, list) else []:
            amount = _extract_amount(item)
            status = item.get("status", "")
            paid = status.lower() in ("betaald", "paid") if isinstance(status, str) else False
            inv_id = item.get("invoiceNumber") or item.get("id")
            date = item.get("referenceDate") or item.get("date")
            payment_dates = item.get("paymentDates")
            due_date = payment_dates.get("endDate") if isinstance(payment_dates, dict) else None

            invoices.append(
                Invoice(
                    invoice_id=str(inv_id) if inv_id is not None else None,
                    amount_eur=amount,
                    status=status,
                    paid=paid,
                    date=date,
                    due_date=due_date,
                )
            )
        return invoices

    def get_benefits(self) -> dict | None:
        try:
            return self._get(PATH_BENEFITS)
        except (requests.RequestException, HeyTelecomError) as exc:
            logger.warning("Failed to fetch benefits: %s", exc)
            return None

    def get_profile_products(self) -> dict | None:
        try:
            return self._get(PATH_PROFILE_PRODUCTS)
        except (requests.RequestException, HeyTelecomError) as exc:
            logger.warning("Failed to fetch profile products: %s", exc)
            return None

    def get_account_data(self, use_cache: bool = True) -> AccountData:
        products = self.get_products(use_cache=use_cache)
        invoice = self.get_latest_invoice(use_cache=use_cache)
        return AccountData(products=products, latest_invoice=invoice)

    def invalidate_cache(self) -> None:
        self._cache.invalidate()

    def _fetch_usage(self, msisdn: str) -> UsageData | None:
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
        except (ValueError, TypeError, KeyError) as exc:
            logger.warning("Failed to parse usage for %s: %s", msisdn, exc)
            return None
