#!/usr/bin/env python3
import json
import os
import traceback

from heytelecom import HeyTelecomClient

EMAIL = os.environ.get("HEY_EMAIL")
PASSWORD = os.environ.get("HEY_PASSWORD")


def main():
    print("=" * 60)
    print("Hey Telecom Library Example")
    print("=" * 60)

    with HeyTelecomClient(email=EMAIL, password=PASSWORD) as client:
        if not EMAIL or not PASSWORD:
            print("No credentials provided. Set HEY_EMAIL and HEY_PASSWORD environment variables.")
            return

        print("\nLogging in...")
        try:
            client.login()
            print("Login successful!")
        except Exception as e:
            print(f"Login failed: {e}")
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
                if product.contract and product.contract.price_per_month_eur is not None:
                    print(f"  Price: {product.contract.price_per_month_eur:.2f} EUR/month")
                if product.usage:
                    usage = product.usage.to_dict()
                    if "data" in usage:
                        d = usage["data"]
                        if d.get("unlimited"):
                            print("  Data: unlimited")
                        elif d.get("used") is not None and d.get("limit") is not None:
                            print(f"  Data: {d['used']} / {d['limit']} GB")
                        elif d.get("used") is not None:
                            print(f"  Data: {d['used']} GB")
                    if "calls" in usage:
                        d = usage["calls"]
                        parts = []
                        if d.get("used") is not None:
                            parts.append(f"{d['used']} min")
                        if d.get("unlimited"):
                            parts.append("unlimited")
                        print(f"  Calls: {', '.join(parts) if parts else 'N/A'}")
                    if "sms_mms" in usage:
                        d = usage["sms_mms"]
                        parts = []
                        if d.get("used") is not None:
                            parts.append(f"{d['used']} sent")
                        if d.get("unlimited"):
                            parts.append("unlimited")
                        if d.get("limit") is not None:
                            parts.append(f"{d['limit']} limit")
                        print(f"  SMS/MMS: {', '.join(parts) if parts else 'N/A'}")

            if account_data.latest_invoice:
                print("\n" + "=" * 60)
                print("LATEST INVOICE")
                print("=" * 60)
                inv = account_data.latest_invoice
                print(f"  ID: {inv.invoice_id}")
                print(f"  Amount: {inv.amount_eur} EUR")
                print(f"  Status: {inv.status}")
                print(f"  Paid: {'Yes' if inv.paid else 'No'}")
                if inv.date:
                    print(f"  Date: {inv.date}")
                if inv.due_date:
                    print(f"  Due Date: {inv.due_date}")

            # -- new endpoints --
            invoices = client.get_invoices()
            if invoices:
                print("\n" + "=" * 60)
                print(f"ALL INVOICES ({len(invoices)})")
                print("=" * 60)
                for inv in invoices[:3]:
                    print(f"  {inv.invoice_id}: {inv.amount_eur} EUR ({inv.status})")

            benefits = client.get_benefits()
            if benefits:
                print("\n" + "=" * 60)
                print("BENEFITS")
                print("=" * 60)
                print(json.dumps(benefits, indent=2, ensure_ascii=False)[:500])

            profile_products = client.get_profile_products()
            if profile_products:
                print("\n" + "=" * 60)
                print("PROFILE PRODUCTS")
                print("=" * 60)
                print(json.dumps(profile_products, indent=2, ensure_ascii=False)[:500])

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
