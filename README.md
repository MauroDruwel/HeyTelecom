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

For the Container lovers 🐳:

This container exposes a simple endpoint that returns **one giant JSON** with everything you need. It was born to serve the Home Assistant add-on, but hey, free JSON is free JSON.

```bash
docker run -d \
  --name 23118c7a-heytelecom-addon \
  --restart unless-stopped \
  -p 8099:8099 \
  -e HEYTELECOM_EMAIL="your@email.com" \
  -e HEYTELECOM_PASSWORD="your_password" \
  -v heytelecom-data:/data \
  ghcr.io/maurodruwel/heytelecom:latest
```

💡 **Tip:** The name `23118c7a-heytelecom-addon` is the default hostname the Home Assistant integration looks for. If you are running Home Assistant in Docker (not HAOS), naming it this way makes the integration work out of the box!

---

## 🏠 Home Assistant Integration

This whole project was basically an excuse to get my data into Home Assistant. 😅

**The Problem:** You can't just run Playwright inside a standard Home Assistant integration. It's too heavy, requires a browser, and HA generally says "no thanks" to that. 🚫

**The Solution:** I split it up!
1.  **The Add-on**: A Docker container that runs Playwright and does the heavy lifting (scraping). It exposes the data as JSON.
    *   👉 [Get the Add-on here](https://github.com/maurodruwel/addons)
2.  **The Integration**: A lightweight component that talks to the Add-on and creates sensors in HA.
    *   👉 [Get the Integration here](https://github.com/maurodruwel/heytelecomha)

It's the easiest way to get your "Hey!" usage on your dashboard without breaking your HA install.

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

1. **The Setup**: We use **Playwright** (a headless browser) to pretend to be a real human. 🎭
2. **The Login**: It goes to the website, types in your stuff, and handles the session.
3. **The Grab**: It scrapes the mobile/internet usage, invoices, and contract details.
4. **The Result**: You get nice, clean Python objects to play with. No more parsing HTML yourself! 🤢

**Note:** The first time you run it, it might take a sec to download the browser. It's automatic, don't panic. 😱

---

## ✨ Features

- 🔐 **Auto Login**: Handles the boring auth stuff.
- 💾 **Session Saving**: Remembers you so it doesn't have to login every single time. Smart.
- 📱 **Product Info**: Mobile, Internet, whatever you got.
- 📊 **Usage Stats**: Data, Calls, SMS. Know when to stop scrolling TikTok.
- 💰 **Invoices**: Download them, track them, pay them (well, you still have to pay them).
- 🐳 **Docker Ready**: Comes with a REST API if you're into that.

---

## 📖 The Story (or "Why?")

So, here's the tea ☕. I wanted to integrate my mobile usage into my dashboard. I checked for an API. *Crickets*. 🦗

The official API is not open source and was extremely difficult to reverse engineer. I did some digging though (see the [research folder](./research) if you're curious), but ultimately Playwright was the more reliable path.

I didn't want to manually check the website every time I was curious about my data cap. That's what robots are for! So I built this wrapper around Playwright to do the heavy lifting. It spins up a browser in the background (headless, so no popping windows to annoy you), logs in, and scrapes the data.

Now I can graph my data usage and feel guilty about it in real-time. 📈

---

## 🤝 Contributing

Found a bug? Want to add a feature? PRs are welcome! Let's make this thing better together. 🎉

---

*Made with ❤️ and a lot of debugging.*

