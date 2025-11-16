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
from heytelecom import HeyTelecomClient

# Hard-coded credentials (replace with your own or pass as arguments)
EMAIL = ""  # Replace with your actual email
PASSWORD = ""  # Replace with your actual password


def main():
    """Main example function."""
    print("=" * 60)
    print("Hey Telecom Library Example")
    print("=" * 60)
    
    # Create client - credentials are optional if session already exists
    # Browser always runs in headless mode (no GUI)
    # Chromium is automatically installed if not present
    with HeyTelecomClient(email=EMAIL, password=PASSWORD) as client:
        # Login (only needed first time or if session expired)
        if EMAIL and PASSWORD:
            print("\n📝 Logging in...")
            try:
                client.login()
                print("✓ Login successful!")
            except Exception as e:
                print(f"✗ Login failed: {e}")
                return
        
        # Get all account data
        print("\n📊 Fetching account data...")
        try:
            account_data = client.get_account_data()
            print(f"✓ Found {len(account_data.products)} product(s)")
            
            # Display products
            print("\n" + "=" * 60)
            print("PRODUCTS")
            print("=" * 60)
            for i, product in enumerate(account_data.products, 1):
                print(f"\nProduct {i}:")
                print(f"  Type: {product.product_type}")
                print(f"  Tariff: {product.tariff}")
                # Note: Displaying phone number and account details for demonstration purposes
                if product.phone_number:
                    print(f"  Phone: {product.phone_number}")
                if product.easy_switch_number:
                    print(f"  Easy Switch: {product.easy_switch_number}")
                if product.contract:
                    print(f"  Contract Start: {product.contract.start_date}")
                    print(f"  Price: {product.contract.price_per_month_eur} EUR/month")
                if product.usage:
                    usage = product.usage.to_dict()
                    if "data" in usage:
                        data = usage["data"]
                        print(f"  Data Usage: {data.get('used')} / {data.get('limit')} GB")
            
            # Display latest invoice
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
            
            # Display as JSON
            print("\n" + "=" * 60)
            print("JSON OUTPUT")
            print("=" * 60)
            print(json.dumps(account_data.to_dict(), indent=2, ensure_ascii=False))
            
        except Exception as e:
            print(f"✗ Error fetching data: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n✓ Example completed!")


if __name__ == "__main__":
    main()
