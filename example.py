#!/usr/bin/env python3
"""
Example usage of the heytelecom library.

This example demonstrates how to use the HeyTelecomClient to:
1. Login to your Hey Telecom account
2. Retrieve product information
3. Get usage data
4. Fetch invoice information
"""

import json
import os
import traceback
from heytelecom import HeyTelecomClient

EMAIL = os.environ.get("HEY_EMAIL", "")
PASSWORD = os.environ.get("HEY_PASSWORD", "")


def main():
    """Main example function."""
    print("=" * 60)
    print("Hey Telecom Library Example")
    print("=" * 60)

    with HeyTelecomClient(email=EMAIL, password=PASSWORD) as client:
        if EMAIL and PASSWORD:
            print("\nLogging in...")
            try:
                client.login()
                print("Login successful!")
            except Exception as e:
                print(f"Login failed: {e}")
                return
        else:
            print("No credentials provided. Set HEY_EMAIL and HEY_PASSWORD.")
            return

        print("\nFetching account data...")
        try:
            account_data = client.get_account_data()
            print(f"Found {len(account_data.products)} product(s)")

            print("\n" + "=" * 60)
            print("PRODUCTS")
            print("=" * 60)
            for i, product in enumerate(account_data.products, 1):
                print(f"\nProduct {i}:")
                print(f"  Type: {product.product_type}")
                print(f"  Tariff: {product.tariff}")
                if product.phone_number:
                    print(f"  Phone: {product.phone_number}")
                if product.easy_switch_number:
                    print(f"  Easy Switch: {product.easy_switch_number}")
                if product.contract:
                    if product.contract.price_per_month_eur is not None:
                        print(f"  Price: {product.contract.price_per_month_eur:.2f} EUR/month")
                if product.usage:
                    usage = product.usage.to_dict()
                    if "data" in usage:
                        data = usage["data"]
                        used = data.get("used")
                        limit = data.get("limit")
                        unlimited = data.get("unlimited", False)
                        if unlimited:
                            print(f"  Data Usage: {used} GB (unlimited)")
                        else:
                            print(f"  Data Usage: {used} / {limit} GB")

            if account_data.latest_invoice:
                print("\n" + "=" * 60)
                print("LATEST INVOICE")
                print("=" * 60)
                invoice = account_data.latest_invoice
                print(f"  Amount: {invoice.amount_eur} EUR")
                print(f"  Status: {invoice.status}")
                print(f"  Paid: {'Yes' if invoice.paid else 'No'}")
                print(f"  Date: {invoice.date}")
                print(f"  Due Date: {invoice.due_date}")

            print("\n" + "=" * 60)
            print("JSON OUTPUT")
            print("=" * 60)
            print(json.dumps(account_data.to_dict(), indent=2, ensure_ascii=False))

        except Exception as e:
            print(f"Error fetching data: {e}")
            traceback.print_exc()

    print("\nExample completed!")


if __name__ == "__main__":
    main()
