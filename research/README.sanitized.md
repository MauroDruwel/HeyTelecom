# HeyTelecom (`ecare.heytelecom.be`) API — Reverse Engineering Notes

> **Disclaimer:** This document is for research/educational purposes against your
> **own** account only. It documents the network traffic of a normal login +
> dashboard session on the HeyTelecom customer portal, reconstructed from a Chrome
> HAR export. Do not use against accounts you do not own or in violation of
> HeyTelecom's ToS.
>
> ℹ️ **All personal data, credentials, tokens and account identifiers in this
> document have been replaced with sample/placeholder values.** Anything that
> looks like a real value (`john.doe@example.com`, `04XXXXXXXX`, `<REDACTED_...>`)
> is a stand-in — substitute your own when running the client.

---

## Table of Contents

- [Overview](#overview)
- [Hosts & Infrastructure](#hosts--infrastructure)
- [Public App Constants](#public-app-constants)
- [Session Secrets (per login)](#session-secrets-per-login)
- [Data Model (sample shapes)](#data-model-sample-shapes)
  - [Account holder / profile](#account-holder--profile)
  - [Address](#address)
  - [Login credentials](#login-credentials)
  - [Products / lines](#products--lines)
  - [Billing account](#billing-account)
  - [Invoices](#invoices)
  - [Usage / consumption](#usage--consumption)
- [Authentication Flow (step by step)](#authentication-flow-step-by-step)
- [API Endpoints Reference](#api-endpoints-reference)
- [Headers Reference](#headers-reference)
- [Cookies Reference](#cookies-reference)
- [Telemetry / Anti-bot](#telemetry--anti-bot)
- [Notes & Gotchas](#notes--gotchas)

---

## Overview

The `ecare.heytelecom.be` customer portal is an Angular SPA that talks to a
**BFF (Backend-For-Frontend)** at `api.heytelecom.be`. Authentication is
**OAuth2 Authorization Code + PKCE (S256)** handled by an Orange/IRIS OpenID
provider at `openid.heytelecom.be` (issuer `SGIDF_obe_iris`, i.e. Orange Belgium
infrastructure). After login the SPA holds a short-lived **Bearer access token**
(1 hour) and sends a fixed public **`x-api-key`** with every BFF call.

All hosts sit behind **Imperva/Incapsula** (the `visid_incap_*` / `incap_ses_*`
cookies and `_Incapsula_Resource` requests).

---

## Hosts & Infrastructure

| Host | Role |
|------|------|
| `ecare.heytelecom.be` | Angular SPA (static assets, `index.html`) |
| `api.heytelecom.be` | BFF REST API (auth + data endpoints) |
| `openid.heytelecom.be` | OpenID Connect provider (authorize/token/jwks) |
| `auth.heytelecom.be` | Hosted login UI (email/password form) |
| `partners-enrichment.heytelecom.be` | Redirect shim into the login UI |
| `www.heytelecom.be` | CMS / marketing (Drupal — `SSESS*` cookie) |
| `ialerting.heytelecom.be` | Alerting script |
| `bam.nr-data.net` | New Relic browser telemetry (3rd party) |

**OIDC discovery** (`GET https://openid.heytelecom.be/.well-known/openid-configuration`):

```json
{
  "issuer": "https://openid.heytelecom.be",
  "authorization_endpoint": "https://openid.heytelecom.be/oidc/authorize",
  "token_endpoint": "https://openid.heytelecom.be/oidc/token",
  "jwks_uri": "https://openid.heytelecom.be/oidc/jwks",
  "response_types_supported": ["code"],
  "subject_types_supported": ["public", "pairwise"],
  "id_token_signing_alg_values_supported": ["RS256", "HS256"],
  "ui_locales_supported": ["en", "fr", "nl"]
}
```

The signing keys are exposed at `GET /oidc/jwks` (one EC P-384 key + one RSA key).

---

## Public App Constants

These are baked into the SPA's JavaScript and are the same for every user (not
personal data — they identify the public web client):

| Name | Value |
|------|-------|
| `client_id` | `4x5cSOWeuG` |
| `redirect_uri` | `https://ecare.heytelecom.be/index.html` |
| `scope` | `openid ecare` |
| `code_challenge_method` | `S256` |
| `x-api-key` (auth endpoints) | `ST70c4jIzkKpGTf0cIGbVZLRN7VMhGl0mzLp8D3vEe79oNaK` |
| `x-api-key` (data/BFF endpoints) | `KEQRymGhNEonxo79zqM40tphE7zk5NxHOGxjbVsrzsbrkpIs` |
| `x-channel-id` | `web` |
| `x-usecase-id` (login) | `login-email-pwd` |

---

## Session Secrets (per login)

These are regenerated on every login and are unique to a session. Values below
are **placeholders** — the client generates real ones at runtime:

| Name | Example / how derived |
|------|-----------------------|
| `state` / `nonce` (identical in this app) | `<REDACTED_STATE>` — random base64url (33 bytes) |
| `code_verifier` | `<REDACTED_CODE_VERIFIER>` — random base64url (48 bytes) |
| `code_challenge` | `base64url(sha256(code_verifier))` |
| `transactionId` | `<REDACTED_TRANSACTION_ID>` — minted by the server on first `/oidc/authorize` |
| authorization `code` | `<REDACTED_CODE>` — returned to `redirect_uri` after login |
| `access_token` | `<REDACTED_ACCESS_TOKEN>` — opaque, `expires_in: 3600` |
| `x-usersession-id` | `<RANDOM_30_DIGITS>` — random per session |

> Verified: `base64url(sha256(code_verifier)) == code_challenge` ✅ (standard PKCE S256).

**Token response** (`POST /oidc/token`):

```json
{
  "token_type": "Bearer",
  "access_token": "<REDACTED_ACCESS_TOKEN>",
  "expires_in": 3600,
  "scope": "ecare"
}
```

The access token is **opaque** (not a JWT) and must be validated server-side via
introspection. There is **no refresh token** — the SPA re-runs the whole authorize
flow when the 1-hour token expires.

---

## Data Model (sample shapes)

> The JSON shapes below are real (field names/types), but **all values are
> samples**.

### Account holder / profile

`GET /api/bff/my-profile/v1/customer`:

```json
{
  "accountHolder": true,
  "title": "M.",
  "firstName": "JOHN",
  "lastName": "DOE",
  "birthDate": "1990-01-01",
  "nationalRegisterNumber": "<BASE64_ENCRYPTED_RRN>",
  "customerType": "M",
  "invoiceAddress": {
    "number": "1",
    "postbox": "",
    "street": "SAMPLE STREET",
    "postCode": "1000",
    "city": "SAMPLE CITY"
  },
  "id": "1.XXXXXXX",
  "emailAddress": "john.doe@example.com",
  "paymentType": "transfer"
}
```

| Field | Notes |
|-------|-------|
| `title` | salutation, e.g. `M.` |
| `firstName` / `lastName` | account holder name |
| `birthDate` | `YYYY-MM-DD` |
| `nationalRegisterNumber` | **encrypted** server-side (base64, ~16 bytes) — *not* the raw rijksregisternummer |
| `id` | customer id, form `1.XXXXXXX` (same as billing account id) |
| `paymentType` | e.g. `transfer` (bank transfer) |

### Address

`invoiceAddress` object: `street`, `number`, `postbox`, `postCode`, `city`.

### Login credentials

Submitted (form-urlencoded over HTTPS) to `/api/bff/auth/v1/login/email`:

| Field | Value |
|-------|-------|
| `email` | `john.doe@example.com` |
| `password` | `<YOUR_PASSWORD>` |
| `returnUri` | the `/oidc/authorize?...&transactionId=...` URL |

> ⚠️ A HAR capture records the login POST body in cleartext. If you export a HAR,
> treat it as a secret and rotate your password afterwards.

### Products / lines

`GET /api/bff/product-inventory/v1/productInventory`:

```json
[
  {"MSISDN":"00XXXXXXX","partyRole":"Customer","tariffName":"hey! Internet","productType":"F","contractStartDate":null,"price":{"unit":"euro","value":39.0},"promotion":[]},
  {"MSISDN":"04XXXXXXXX","partyRole":"Customer","tariffName":"hey! mobile S","productType":"M","contractStartDate":"2025-04-04T00:00:00.000Z","price":{"unit":"euro","value":5.0},"promotion":[]}
]
```

| Field | Notes |
|-------|-------|
| `MSISDN` | line identifier. Fixed/internet line uses an internal id; mobile uses the phone number in national form `04XXXXXXXX` |
| `productType` | `F` = fixed internet, `M` = mobile |
| `tariffName` | e.g. `hey! Internet`, `hey! mobile S` |
| `price` | `{unit: "euro", value: <float>}` (values come back with float rounding noise) |

Mobile numbers are returned in **national** form (`04XXXXXXXX`) but the usage
endpoint expects **international** form (`324XXXXXXXX`).

### Billing account

`GET /api/bff/billing-account-overview/v1/billingAccounts`:

```json
{"id":"1.XXXXXXX","accountHolder":true,"paymentType":"transfer"}
```

### Invoices

`GET /api/bff/invoices-details/v1/invoices` → array of invoices:

```json
[
  {
    "id": 5XXXXXXXX,
    "invoiceNumber": "0XXXXXXXXXX",
    "referenceDate": "2026-05-19",
    "paymentDates": {"startDate": "2026-05-19", "endDate": "2026-05-29"},
    "invoiceAmount": {"value": 10.0, "unit": "euro"},
    "msisdn": "324XXXXXXXX",
    "status": "paid",
    "hasPepol": false
  }
]
```

**Latest invoice** (`GET /api/bff/latest-invoice-overview/v1/invoices/latest`):

```json
{"msisdn":"324XXXXXXXX","id":5XXXXXXXX,"invoiceNumber":"0XXXXXXXXXX","referenceDate":"2026-05-19","paymentDueDate":"2026-05-29","invoiceAmount":{"unit":"euro","value":10},"status":"paid"}
```

**Invoice PDF download**
(`GET /api/bff/invoices-details/v1/invoices/{invoiceNumber}/download?type=detailed&format=pdf`)
returns `application/pdf`.

### Usage / consumption

`GET /api/bff/info-consumption/v1/usage?timestamp={ms}` with header
`x-req-msisdn: 324XXXXXXXX`:

```json
{
  "MSISDN": "324XXXXXXXX",
  "customerType": "M",
  "BalancePresentation": [
    {"Name":"Buiten abonnement","Unit":"Euro","ConsumedAmount":{"Amount":0},"Category":"Voice","Zone":"National","Unlimited":true,"bundleTypology":"Out of subscription"},
    {"Name":"onbeperkt sms/mms","Unit":"Message","ConsumedAmount":{"Amount":0},"Category":"Voice","Unlimited":true,"bundleTypology":"SMS/MMS BE and EU"},
    {"Name":"onbeperkt bellen","Unit":"HH:MI","ConsumedAmount":{"Hours":0,"Minutes":0,"Seconds":0},"Category":"Voice","Unlimited":true,"bundleTypology":"Calls to any network"},
    {"Name":"Surfvolume","Unit":"MByte","ConsumedAmount":{"Amount":418.84,"Unit":"MByte"},"RemainingAmount":{"Amount":14941.16,"Unit":"MByte"},"AmountOfForfeit":{"Amount":15360,"Unit":"MByte"},"Category":"Data","Unlimited":false,"bundleTypology":"Data allowance"},
    {"Name":"Mobiel internet in het buitenland","Unit":"Euro","ConsumedAmount":{"Amount":0},"Category":"Data","Zone":"International","bundleTypology":"Mobile data abroad"},
    {"Name":"Mobiel internet","Unit":"Euro","ConsumedAmount":{"Amount":0},"RemainingAmount":{"Amount":50},"AmountOfForfeit":{"Amount":50},"Category":"Data","bundleTypology":"Mobile data - Out of bundle"}
  ]
}
```

Each `BalancePresentation` entry includes the billing window
(`PreviousInvoiceClosing` / `NextInvoiceClosing` / `LastConsumptionProcessed`),
a `Category` (`Voice`/`Data`), `Zone` (`National`/`International`), `Unlimited`
flag, and `ConsumedAmount` / `RemainingAmount` / `AmountOfForfeit` where relevant.

Selector headers for this endpoint:
- `x-req-msisdn: 324XXXXXXXX` → usage for a **mobile** line
- `x-req-fcli: 32XXXXXXX` → usage keyed by a **fixed customer line** id

---

## Authentication Flow (step by step)

```
1. GET  openid.heytelecom.be/oidc/authorize?...&code_challenge=...&state=...&nonce=...
        └─► 302 to partners-enrichment/.../login?returnUri=...&transactionId=XXXX
2. GET  partners-enrichment.heytelecom.be/authlogicimplicit/login?...
        └─► 302 to auth.heytelecom.be/login?...
3. GET  auth.heytelecom.be/nl/login/email?...        (renders login form)
4. POST api.heytelecom.be/api/bff/auth/v1/login/email
        body: email, password, returnUri
        └─► 302 (Location = the authorize URL) + Set-Cookie: wassup=...
5. GET  openid.heytelecom.be/oidc/authorize?...&transactionId=XXXX   (authenticated via wassup cookie)
        └─► 302 to ecare.heytelecom.be/index.html?code=YYYY&state=...
6. POST openid.heytelecom.be/oidc/token
        body: grant_type=authorization_code, code=YYYY, redirect_uri, code_verifier, client_id
        └─► { access_token, expires_in: 3600, ... }
7. GET  api.heytelecom.be/api/bff/...    (Authorization: Bearer <access_token>, x-api-key: <data key>)
```

Key points:
1. **`transactionId`** is minted by the server on the *first* `/oidc/authorize`
   call and embedded in the `Location`/`returnUri`. Extract it and feed it back
   into the `returnUri` you POST at step 4.
2. **`state` and `nonce` are identical** in this app (same random base64url value).
3. The **`wassup` cookie** (set by step 4) authenticates the second
   `/oidc/authorize` call so it issues the `code` instead of bouncing to login.
4. **PKCE S256**: `code_challenge = base64url(sha256(code_verifier))`.
5. The token is **opaque** and lasts **3600 s**; no refresh token → re-auth.

This flow is implemented in [`test.py`](./test.py).

---

## API Endpoints Reference

All BFF data endpoints require `Authorization: Bearer <token>` +
`x-api-key: KEQRymGhNEonxo79zqM40tphE7zk5NxHOGxjbVsrzsbrkpIs`.
Each data call is preceded by a CORS `OPTIONS` preflight (handled by the browser;
not needed from a plain HTTP client).

| Method | Endpoint | Purpose | Extra |
|--------|----------|---------|-------|
| GET | `/.well-known/openid-configuration` *(openid host)* | OIDC discovery | public |
| GET | `/oidc/jwks` *(openid host)* | signing keys (EC P-384 + RSA) | public |
| GET | `/oidc/authorize` *(openid host)* | start PKCE / get code | — |
| POST | `/oidc/token` *(openid host)* | code → access_token | form-urlencoded |
| POST | `/api/bff/auth/v1/login/email` | submit credentials | needs login `x-api-key` + `x-channel-id`, `x-usecase-id`, `x-usersession-id` |
| GET | `/api/bff/my-profile/v1/customer` | profile + address | — |
| GET | `/api/bff/product-inventory/v1/productInventory` | list of lines/products | — |
| GET | `/api/bff/billing-account-overview/v1/billingAccounts` | billing account | — |
| GET | `/api/bff/invoices-details/v1/invoices` | invoice list | — |
| GET | `/api/bff/invoices-details/v1/invoices/{number}/download?type=detailed&format=pdf` | invoice PDF | returns `application/pdf` |
| GET | `/api/bff/latest-invoice-overview/v1/invoices/latest` | most recent invoice | — |
| GET | `/api/bff/info-consumption/v1/usage?timestamp={ms}` | consumption/balances | needs `x-req-msisdn` (or `x-req-fcli`) header |
| GET | `/api/bff/cms/v1?lang=nl&view={view}&application={app}` | CMS content for UI | public-ish |
| POST | `/api/log-events/v1/log` | UI telemetry (screen changes) | optional |

---

## Headers Reference

**Shared browser headers** (sent on essentially every request):

```
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36
Accept-Language: nl-BE,nl;q=0.9
sec-ch-ua: "Google Chrome";v="149", "Chromium";v="149", "Not)A;Brand";v="24"
sec-ch-ua-mobile: ?0
sec-ch-ua-platform: "Windows"
```

**Login POST** (`/api/bff/auth/v1/login/email`):

```
Accept: application/json
Content-Type: application/x-www-form-urlencoded;charset=UTF-8
Origin: https://auth.heytelecom.be
Referer: https://auth.heytelecom.be/
x-api-key: ST70c4jIzkKpGTf0cIGbVZLRN7VMhGl0mzLp8D3vEe79oNaK
x-channel-id: web
x-usecase-id: login-email-pwd
x-usersession-id: <RANDOM_30_DIGITS>
sec-fetch-{dest:empty, mode:cors, site:same-site}
```

**Authenticated BFF GET** (e.g. `productInventory`):

```
Accept: application/json
Authorization: Bearer <access_token>
Content-Language: nl            (sometimes "fr" — UI locale)
Origin: https://ecare.heytelecom.be
Referer: https://ecare.heytelecom.be/
x-api-key: KEQRymGhNEonxo79zqM40tphE7zk5NxHOGxjbVsrzsbrkpIs
priority: u=1, i
sec-fetch-{dest:empty, mode:cors, site:same-site}
```

---

## Cookies Reference

| Cookie | Set by | Meaning |
|--------|--------|---------|
| `wassup` | `/auth/v1/login/email` (302) | **the auth session** — proves you logged in; required for the 2nd `/oidc/authorize` to emit a code. Domain `.heytelecom.be`, HttpOnly. |
| `visid_incap_*` / `incap_ses_*` | all hosts | **Imperva/Incapsula** session + visitor id (anti-bot). |
| `___utmvc` | Incapsula | anti-bot JS challenge value. |
| `SSESS…` | `www.heytelecom.be` | Drupal CMS session. |
| `JSESSIONID` | api/openid | Java backend session. |
| `language` / `lang` / `ecareLanguage` | various | UI locale (`nl`). |
| `ohap` | login UI | misc app cookie. |

Using a single `requests.Session()` carries all of these automatically, which is
essential — the `wassup` cookie *and* the Incapsula cookies must persist across
the redirect chain.

---

## Telemetry / Anti-bot

- **Imperva/Incapsula** fronts every `*.heytelecom.be` host. Requests to
  `/_Incapsula_Resource` and the `___utmvc` cookie are JS challenges. A plain
  `requests` client usually passes (cookies issued on first GET), but if it
  starts returning HTML challenge pages you must seed the session with cookies
  from a real browser visit.
- **New Relic** (`bam.nr-data.net`) — browser RUM/error telemetry. Pure 3rd-party
  noise; **do not replicate** (sending it adds fingerprintable junk).
- **`POST /api/log-events/v1/log`** — first-party UI analytics (screen changes,
  durations). Example body:
  ```json
  {"x-usersession-id":"<RANDOM_30_DIGITS>","x-usecase-id":"{}","screen":"/login","type":"change_screen","duration":"87","timestamp":"2026-06-17T19:56:09.743Z","status":"success"}
  ```
  Optional — skip it unless you want to look maximally "real".

---

## Notes & Gotchas

- **Token lifetime is 1 hour, no refresh token.** Re-run the full flow to renew.
- **`x-api-key` differs** between the login endpoint and the data endpoints — using
  the wrong one yields 401/403.
- **`transactionId` must round-trip**: read it from the first authorize redirect,
  put it back into the `returnUri` you submit at login.
- **`state` == `nonce`** in this app; both are a random `base64url` value.
- **MSISDN formats are inconsistent**: `productInventory` returns national form
  (`04XXXXXXXX`) while `usage` expects international (`324XXXXXXXX`, no `+`).
  Normalize with: drop leading `0`, prefix `32`.
- **National register number is encrypted** server-side (base64, ~16 bytes) — not
  the raw number.
- **To stay low-profile**: reuse one session, replicate the Chrome headers above,
  send only the first-party calls the SPA makes, and avoid New Relic. Random
  `state`/`nonce`/PKCE per run mirrors the real app.
- **Never commit a real HAR or real credentials.** A HAR contains your plaintext
  password and a live token — keep it out of the repo (add it to `.gitignore`).

---

*End of research notes.*
