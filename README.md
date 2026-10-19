<p align="center">
  <img width="1280" height="668" alt="HeyTelecom Banner" src="https://github.com/user-attachments/assets/e6da23c6-5911-4223-8358-c6856e617e9f" />
</p>


<h1 align="center">📱 HeyTelecom Python Library</h1>
<p align="center"><b>"I just want my usage data" Edition 🚀</b></p>

<p align="center">
  <a href="#-quick-install">Quick Install</a> |
  <a href="#%EF%B8%8F-getting-started">Getting Started</a> |
  <a href="#-api-reference">API Reference</a> |
  <a href="#-features">Features</a> |
  <a href="#-contributing">Contributing</a>
</p>

<p align="center">
  <img alt="PyPI" src="https://img.shields.io/pypi/v/heytelecom"/>
  <img alt="Python Version" src="https://img.shields.io/pypi/pyversions/heytelecom"/>
  <img alt="License" src="https://img.shields.io/github/license/MauroDruwel/HeyTelecom"/>
</p>

---

> **Automate your Hey! Telecom account. Get usage, invoices, and more without lifting a finger.**

> ⚠️ **Project On Hold / Blocked by Upstream 2FA**
> Hey! Telecom (`auth.heytelecom.be` / `ecare.heytelecom.be`) recently made SMS two-factor authentication mandatory on login. Because access tokens expire in 1 hour and no refresh tokens are provided by their web portal, automated headless logins are currently blocked. This repository and the Home Assistant integration are paused until an alternative authentication flow or long-lived token mechanism is found.

> ⚠️ Unofficial library. Use against **your own** account only and respect Hey Telecom's terms of service. The portal sits behind Imperva/Incapsula; automated access may occasionally fail.

---

## 📦 Quick Install

Requires **Python 3.9+**.

```bash
pip install heytelecom
```

---

## 🏠 Home Assistant Integration

This whole project was basically an excuse to get my data into Home Assistant.

**How it works now:**
1. **The Library**: Pure Python — no browser, no heavy dependencies. Just `requests` + OAuth2.
2. **The Integration**: A lightweight HA component that talks to the library and creates sensors.
    *   👉 [Get the Integration here](https://github.com/maurodruwel/heytelecomha)

---

## 🛠️ Getting Started

```python
from heytelecom import HeyTelecomClient, APIError, AuthenticationError

with HeyTelecomClient(email="your@email.com", password="your_password") as client:
    client.login()

    account_data = client.get_account_data()

    print(f"You have {len(account_data.products)} products.")
    if account_data.latest_invoice:
        print(f"Latest invoice: €{account_data.latest_invoice.amount_eur}")
```

Credentials can also be supplied via environment variables in `example.py`
(`HEY_EMAIL` / `HEY_PASSWORD`).

---

## 📖 API Reference

### `HeyTelecomClient(email=None, password=None)`

| Method | Returns | Notes |
|--------|---------|--------|
| `login()` | `str` (access token) | Required before data calls unless you only construct the client after obtaining a token another way. |
| `get_account_data(use_cache=True)` | `AccountData` | Products + latest invoice (fetched in parallel). |
| `get_products(use_cache=True)` | `list[Product]` | Mobile usage fetched in parallel per line. |
| `get_latest_invoice(use_cache=True)` | `Invoice \| None` | `None` if the account has no invoices. |
| `get_invoices()` | `list[Invoice]` | Full invoice list (not cached). |
| `get_benefits()` | raw JSON | Passthrough of the benefits endpoint. |
| `get_profile_products()` | raw JSON | Passthrough of profile products. |
| `invalidate_cache()` | `None` | Drop TTL cache entries. |
| `clear_credentials()` | `None` | Wipe email/password from memory. Auto re-login on token expiry will then fail until `login()` is called again. |
| `close()` | `None` | Close the HTTP session (also via context manager). |

### Models

- **`AccountData`**: `provider`, `products`, `latest_invoice` — `.to_dict()` skips `None`/empty lists.
- **`Product`**: `product_id`, `product_type` (`mobile` / `internet` / …), `phone_number`, `easy_switch_number`, `tariff`, `contract`, `usage`.
- **`UsageData`**: `period`, `data` (`used`/`limit` in **GB**), `calls`, `sms_mms`.
- **`Invoice`**: `invoice_id`, `amount_eur`, `status`, `paid`, `date`, `due_date`.
- **`Contract`**: `price_per_month_eur`.

### Exceptions

| Exception | When |
|-----------|------|
| `HeyTelecomError` | Base class |
| `AuthenticationError` | Login failed, missing auth, 401/403, token expired without credentials |
| `APIError` | Network failure, non-2xx (with `.status_code`), non-JSON / Incapsula HTML, unexpected payload shape |

```python
from heytelecom import HeyTelecomClient, APIError, AuthenticationError

try:
    with HeyTelecomClient(email=..., password=...) as client:
        client.login()
        print(client.get_products())
except AuthenticationError as e:
    print("Auth problem:", e)
except APIError as e:
    print("API problem:", e, "status=", e.status_code)
```

### Caching & tokens

- Product inventory and latest invoice are cached for **60 seconds** (in-memory TTL).
- Access tokens expire after ~1 hour; the client renews **~5 minutes early** using
  `expires_in` from the token response, via a full email/password re-login
  (the public web client does not expose a refresh-token grant).
- After `clear_credentials()`, expired tokens raise `AuthenticationError` instead of re-login.

---

## 🤖 How it Works

1. **The Setup**: We use **requests** (plain HTTP) — no browser needed. Just OAuth2 with PKCE, exactly like the web app does.
2. **The Login**: Authenticates via the same OIDC flow the browser uses — email/password → BFF auth endpoint → authorization code → access token.
3. **The Grab**: Calls the same BFF JSON APIs the web app uses to get products, usage, and invoices.
4. **The Result**: You get nice, clean Python objects to play with. No more parsing HTML yourself!

See the [research folder](./research) for sanitized reverse-engineering notes.

---

## ✨ Features

- **Auto Login**: Handles the OAuth2/PKCE auth flow automatically.
- **Token Refresh**: Re-authenticates transparently when the access token expires (while credentials remain available).
- **Product Info**: Mobile, Internet, whatever you got.
- **Usage Stats**: Data (GB), Calls, SMS.
- **Invoices**: Latest + full list.
- **Typed errors**: `APIError` / `AuthenticationError` with optional HTTP status.

---

## 📖 The Story (or "Why?")

So, here's the tea. I wanted to integrate my mobile usage into my dashboard. I checked for an API. Crickets.

The official API is not public, but I reverse-engineered the web app's traffic using a HAR capture (see the [research folder](./research)). The e-care portal uses standard OAuth2/PKCE + a set of BFF JSON endpoints, so I rebuilt the whole flow with plain HTTP requests — no browser required.

Now I can graph my data usage and feel guilty about it in real-time.

---

## 🤝 Contributing

Found a bug? Want to add a feature? PRs are welcome.

```bash
pip install -e ".[dev]"
ruff check src/ tests/
ruff format src/ tests/
pytest
```

See [CHANGELOG.md](./CHANGELOG.md) for release notes.

---

*Made with ❤️ and a lot of debugging.*
