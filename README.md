# HeyTelecom Python Library

<img width="1280" height="668" alt="HeyTelecom Banner" src="https://github.com/user-attachments/assets/d141fb44-e5c3-48af-a2b0-42ba4d2c510f" />

<p align="center">
  <img alt="PyPI" src="https://img.shields.io/pypi/v/heytelecom"/>
  <img alt="Python Version" src="https://img.shields.io/pypi/pyversions/heytelecom"/>
  <img alt="License" src="https://img.shields.io/github/license/MauroDruwel/HeyTelecom"/>
  <img alt="GitHub commit activity" src="https://img.shields.io/github/commit-activity/m/MauroDruwel/HeyTelecom"/>
  <img alt="GitHub last commit" src="https://img.shields.io/github/last-commit/MauroDruwel/HeyTelecom"/>
</p>

<p align="center">
  <a href="#installation">Installation</a> -
  <a href="#quick-start">Quick Start</a> -
  <a href="#features">Features</a> -
  <a href="#api-reference">API Reference</a> -
  <a href="https://github.com/MauroDruwel/HeyTelecom/issues">Bug Reports</a>
</p>

A Python library for interacting with [Hey Telecom](https://ecare.heytelecom.be) (hey!) accounts using Playwright for web automation. Automatically extract your mobile/internet usage, invoices, and account information.

## Features

- 🔐 Automatic login with session persistence
- 📱 Retrieve mobile and internet product information
- 📊 Get usage data (data, calls, SMS/MMS)
- 💰 Fetch invoice information
- 🎭 Built on Playwright for reliable web automation (headless only)
- 🔧 Object-oriented API for easy integration
- 🚀 Chromium browser with automatic dependency installation

## Installation

```bash
pip install heytelecom
```

## Quick Start

```python
from heytelecom import HeyTelecomClient

with HeyTelecomClient(email="your@email.com", password="your_password") as client:
    client.login()
    account_data = client.get_account_data()
    
    import json
    print(json.dumps(account_data.to_dict(), indent=2))
```

## API Reference

### HeyTelecomClient

Main client class for interacting with Hey Telecom.

#### Constructor

```python
HeyTelecomClient(
    email: Optional[str] = None,
    password: Optional[str] = None,
    user_data_dir: str = "hey_browser_data",
    auto_install: bool = True
)
```

**Parameters:**
- `email`: Email address for login (optional if using saved session)
- `password`: Password for login (optional if using saved session)
- `user_data_dir`: Directory to store browser session data (default: "hey_browser_data")
- `auto_install`: Automatically install Playwright chromium if not found (default: True)

**Note:** Browser always runs in headless mode (no GUI) for reliable automation.

**Auto-Installation:**
When `auto_install=True` (default), the client automatically checks if Playwright chromium is installed when connecting. The check works by attempting to launch chromium - if it fails, the installer runs `playwright install chromium --with-deps --only-shell`. Set `auto_install=False` to disable this behavior and handle installation manually.

#### Methods

- `login()`: Login to Hey Telecom account
- `get_products()`: Get list of all products (mobile and internet)
- `get_latest_invoice()`: Get the latest invoice
- `get_account_data()`: Get complete account data including products and invoice

### Data Models

#### Product
- `product_id`: Unique product identifier
- `product_type`: Type of product ("mobile" or "internet")
- `phone_number`: Phone number (for mobile products)
- `easy_switch_number`: Easy Switch number (for internet products)
- `tariff`: Tariff/plan name
- `contract`: Contract information (Contract object)
- `usage`: Usage data (UsageData object)

#### Contract
- `start_date`: Contract start date (ISO format)
- `price_per_month_eur`: Monthly price in EUR

#### UsageData
- `period`: Billing period with start and end dates
- `data`: Data usage information (used, limit, unlimited)
- `calls`: Call usage information (used, unlimited)
- `sms_mms`: SMS/MMS usage information (used, unlimited)

#### Invoice
- `invoice_id`: Invoice identifier
- `amount_eur`: Invoice amount in EUR
- `status`: Invoice status
- `paid`: Whether invoice is paid (boolean)
- `date`: Invoice date (ISO format)
- `due_date`: Invoice due date (ISO format)

#### AccountData
- `provider`: Provider name (always "hey!")
- `last_sync`: Last synchronization timestamp
- `products`: List of Product objects
- `latest_invoice`: Latest Invoice object

## Example Output

```json
{
  "provider": "hey!",
  "account": {
    "last_sync": "2025-11-09T15:30:00"
  },
  "products": [
    {
      "id": "mobile_0412345678",
      "type": "mobile",
      "phone_number": "0412 34 56 78",
      "tariff": "Hey! Mobile Plus",
      "contract": {
        "start_date": "2024-01-15",
        "price_per_month_eur": 15.0
      },
      "usage": {
        "period": {
          "start": "2025-10-11",
          "end": "2025-11-11"
        },
        "data": {
          "used": 2.5,
          "limit": 10.0,
          "unlimited": false,
          "last_update": "2025-11-09T14:30:00"
        },
        "calls": {
          "used": 45.0,
          "unlimited": true,
          "last_update": "2025-11-09T14:30:00"
        },
        "sms_mms": {
          "used": 12,
          "unlimited": true,
          "last_update": "2025-11-09T14:30:00"
        }
      }
    }
  ],
  "billing": {
    "latest_invoice": {
      "invoice_id": "INV-20251101",
      "amount_eur": 15.0,
      "status": "betaald",
      "paid": true,
      "date": "2025-11-01",
      "due_date": "2025-11-15"
    }
  }
}
```

## Project Structure

```
heytestdev/
├── src/
│   └── heytelecom/
│       ├── __init__.py          # Package initialization and exports
│       ├── client.py            # Main HeyTelecomClient class
│       ├── models.py            # Data models (Product, Invoice, etc.)
│       ├── parsers.py           # Parsing utilities
│       └── installer.py         # Playwright installation utilities
├── README.md                    # This file
├── pyproject.toml              # Package configuration
└── .gitignore                  # Git ignore rules
```

## Requirements

- Python 3.8+
- playwright

## Advanced Usage

### Using Saved Sessions

After the first login, the browser session is saved. You can use the library without credentials:

```python
from heytelecom import HeyTelecomClient

with HeyTelecomClient() as client:
    account_data = client.get_account_data()
    print(f"Found {len(account_data.products)} products")
```

### Getting Specific Data

```python
from heytelecom import HeyTelecomClient

with HeyTelecomClient() as client:
    # Get only products
    products = client.get_products()
    for product in products:
        print(f"Product: {product.tariff}")
        print(f"Type: {product.product_type}")
        if product.usage:
            print(f"Usage: {product.usage.to_dict()}")
    
    # Get only latest invoice
    invoice = client.get_latest_invoice()
    if invoice:
        print(f"Invoice: {invoice.amount_eur} EUR")
        print(f"Status: {invoice.status}")
        print(f"Paid: {invoice.paid}")
```

### Manual Playwright Installation

Playwright chromium is automatically installed on first use. If you prefer manual installation:

```bash
# Manual installation (optional)
playwright install chromium --with-deps --only-shell
```

Or use the built-in installer:

```python
from heytelecom import ensure_playwright_installed
ensure_playwright_installed()
```

### Disabling Auto-Installation

If you prefer to handle Playwright installation manually:

```python
from heytelecom import HeyTelecomClient

with HeyTelecomClient(auto_install=False) as client:
    account_data = client.get_account_data()
    print(account_data.to_dict())
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License

## Support

For issues and questions, please open an issue on the GitHub repository.
