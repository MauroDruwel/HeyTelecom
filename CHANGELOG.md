# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.1] - 2026-07-30

### Changed
- **Breaking:** API methods (`get_products`, `get_latest_invoice`, `get_invoices`,
  `get_benefits`, `get_profile_products`) now raise `APIError` /
  `AuthenticationError` on failure instead of returning empty/`None` values.
  An empty product list or missing invoice still returns `[]` / `None`.
- Token lifetime now uses `expires_in` from the OIDC token response (with a
  safety margin). Full re-login still occurs on expiry (no refresh token in the
  public web client flow).
- Minimum Python version is now **3.9** (aligned with CI).
- User-Agent updated to a realistic Chrome 131 string.
- `get_account_data` fetches products and latest invoice in parallel.

### Fixed
- OIDC `state` and `nonce` are generated independently.
- Auth cookie clearing deletes matching cookies by name/path/domain instead of
  wiping entire domains.
- Re-authentication after `clear_credentials()` raises a clear
  `AuthenticationError` instead of failing obscurely.
- HTTP 401/403 map to `AuthenticationError`; other failures and network errors
  map to `APIError` (with optional `status_code`).
- Data usage parsing respects MB vs GB units and converts `LimitAmount` with
  the balance unit.
- Non-dict balance entries in usage responses are skipped safely.

### Added
- `APIError.status_code` attribute.
- README API reference covering auth, caching, credentials, and exceptions.
- Publish workflow runs lint + tests before uploading to PyPI.
- Expanded unit tests (cookie clear, token expiry, HTTP mapping, usage units).

## [0.2.0] - 2025

- Pure `requests` + OAuth2/PKCE client (no browser).
- Products, usage, invoices, benefits, profile endpoints.
- TTL cache, parallel usage fetch, token auto-renewal via re-login.
