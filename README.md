<p align="center">
  <img width="1280" height="668" alt="HeyTelecom Banner" src="https://github.com/user-attachments/assets/e6da23c6-5911-4223-8358-c6856e617e9f" />
</p>


<h1 align="center">📱 HeyTelecom Python Library</h1>
<p align="center"><b>"I just want my usage data" Edition 🚀</b></p>

<p align="center">
  <a href="#-quick-install">Quick Install</a> |
  <a href="#%EF%B8%8F-getting-started">Getting Started</a> |
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

---

## 📦 Quick Install

For the Pythonistas 🐍:

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

It's super simple. Just tell it who you are, and it does the rest.

```python
from heytelecom import HeyTelecomClient

# Let the robot do the work 🤖
with HeyTelecomClient(email="your@email.com", password="your_password") as client:
    client.login() # Knock knock 🚪
    
    # Gimme the data!
    account_data = client.get_account_data()
    
    print(f"You have {len(account_data.products)} products.")
    print(f"Latest invoice: €{account_data.billing.latest_invoice.amount_eur} (Ouch? 💸)")
```

## 🤖 How it Works

1. **The Setup**: We use **requests** (plain HTTP) — no browser needed. Just OAuth2 with PKCE, exactly like the web app does.
2. **The Login**: Authenticates via the same OIDC flow the browser uses — email/password → BFF auth endpoint → authorization code → access token.
3. **The Grab**: Calls the same BFF JSON APIs the web app uses to get products, usage, and invoices.
4. **The Result**: You get nice, clean Python objects to play with. No more parsing HTML yourself!

---

## ✨ Features

- **Auto Login**: Handles the OAuth2/PKCE auth flow automatically.
- **Token Refresh**: Re-authenticates transparently when the access token expires.
- **Product Info**: Mobile, Internet, whatever you got.
- **Usage Stats**: Data, Calls, SMS. Know when to stop scrolling TikTok.
- **Invoices**: Track your latest invoice status.

---

## 📖 The Story (or "Why?")

So, here's the tea. I wanted to integrate my mobile usage into my dashboard. I checked for an API. Crickets.

The official API is not public, but I reverse-engineered the web app's traffic using a HAR capture (see the [research folder](./research)). The e-care portal uses standard OAuth2/PKCE + a set of BFF JSON endpoints, so I rebuilt the whole flow with plain HTTP requests — no browser required.

Now I can graph my data usage and feel guilty about it in real-time.

---

## 🤝 Contributing

Found a bug? Want to add a feature? PRs are welcome! Let's make this thing better together. 🎉

---

*Made with ❤️ and a lot of debugging.*

