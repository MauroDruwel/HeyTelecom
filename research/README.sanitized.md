gzip, deflate, br, zstd
authorization

# HeyTelecom API Reverse Engineering Research

> **Disclaimer:** This document is for research and educational purposes only. It contains notes and findings from reverse engineering the HeyTelecom API. Do not use this information for unauthorized access or in violation of HeyTelecom's terms of service.

---

## Table of Contents

- [HeyTelecom API Reverse Engineering Research](#heytelecom-api-reverse-engineering-research)
  - [Table of Contents](#table-of-contents)
  - [Overview](#overview)
  - [Authentication Flow](#authentication-flow)
    - [1. Required Credentials](#1-required-credentials)
    - [2. Obtaining Bearer Token](#2-obtaining-bearer-token)
    - [3. Authorization Code Flow](#3-authorization-code-flow)
  - [API Endpoints](#api-endpoints)
  - [Example Request Headers](#example-request-headers)
  - [Notes](#notes)

---

## Overview

This document details the process of reverse engineering the HeyTelecom API, focusing on authentication and required headers for accessing product inventory data.

## Authentication Flow

### 1. Required Credentials

- `x-api-key` (required)
- Bearer token (required)

### 2. Obtaining Bearer Token

**Endpoint:**

```
POST https://openid.heytelecom.be/oidc/token
```

**Parameters:**

```json
[
  { "name": "grant_type", "value": "authorization_code" },
  { "name": "code", "value": "<REDACTED_CODE>" },
  { "name": "redirect_uri", "value": "https://ecare.heytelecom.be/index.html" },
  { "name": "code_verifier", "value": "<REDACTED_CODE_VERIFIER>" },
  { "name": "client_id", "value": "4x5cSOWeuG" }
]
```

### 3. Authorization Code Flow

The `code` parameter is obtained from a previous API call to the authorization endpoint:

```
GET https://openid.heytelecom.be/oidc/authorize?...&code_challenge=<REDACTED_CODE_CHALLENGE>&...&nonce=<REDACTED_NONCE>&...&transactionId=<REDACTED_TRANSACTION_ID>&...
```

**Example Parameters:**

```json
[
  { "name": "response_type", "value": "code" },
  { "name": "client_id", "value": "4x5cSOWeuG" },
  { "name": "state", "value": "<REDACTED_STATE>" },
  { "name": "redirect_uri", "value": "https://ecare.heytelecom.be/index.html" },
  { "name": "scope", "value": "openid%20ecare" },
  { "name": "code_challenge", "value": "<REDACTED_CODE_CHALLENGE>" },
  { "name": "code_challenge_method", "value": "S256" },
  { "name": "nonce", "value": "<REDACTED_NONCE>" },
  { "name": "ui_locales", "value": "nl" },
  { "name": "transactionId", "value": "<REDACTED_TRANSACTION_ID>" },
  { "name": "redirectedToAuthForm", "value": "" }
]
```

> **Note:** `state`, `code_challenge`, `nonce`, and `transactionId` are either random or obtained from other API calls or redirections.

## API Endpoints

- **Product Inventory:**
  - `GET https://api.heytelecom.be/api/bff/product-inventory/v1/productInventory`

## Example Request Headers

```http
GET /api/bff/product-inventory/v1/productInventory HTTP/1.1
Host: api.heytelecom.be
Accept: application/json
Accept-Encoding: gzip, deflate, br, zstd
Accept-Language: nl
Authorization: Bearer <REDACTED_BEARER_TOKEN>
Content-Language: fr
Origin: https://ecare.heytelecom.be
Referer: https://ecare.heytelecom.be/
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36
x-api-key: <REDACTED_X_API_KEY>
```

## Notes

- The `code_verifier` appears to be random or generated per session.
- The `code` is obtained from the authorization endpoint after user authentication.
- Some parameters (e.g., `state`, `nonce`, `transactionId`) are dynamic and may be generated or returned by the server during the authentication process.

---

*End of research notes.*
