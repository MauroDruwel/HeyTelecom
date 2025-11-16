from playwright.sync_api import sync_playwright
import time
import json
import re
from datetime import datetime

# Hard-coded credentials
EMAIL = ""  # Replace with your actual email
PASSWORD = ""  # Replace with your actual password

def parse_data_amount(text):
    """Parse data amount like '2.25 GB' to numeric GB value."""
    if not text:
        return None
    match = re.search(r'([\d.]+)\s*(GB|MB|TB)', text, re.IGNORECASE)
    if match:
        value = float(match.group(1))
        unit = match.group(2).upper()
        if unit == 'MB':
            value = value / 1024  # Convert to GB
        elif unit == 'TB':
            value = value * 1024  # Convert to GB
        return round(value, 2)
    return None

def parse_price(text):
    """Parse price like '5 €/maand' to numeric value."""
    if not text:
        return None
    match = re.search(r'([\d.]+)\s*€', text)
    if match:
        return float(match.group(1))
    return None

def parse_date(text):
    """Parse date like '04.04.2025' or '20/10/2025' to ISO format."""
    if not text:
        return None
    # Try DD.MM.YYYY format
    match = re.search(r'(\d{2})\.(\d{2})\.(\d{4})', text)
    if match:
        day, month, year = match.groups()
        return f"{year}-{month}-{day}"
    # Try DD/MM/YYYY format
    match = re.search(r'(\d{2})/(\d{2})/(\d{4})', text)
    if match:
        day, month, year = match.groups()
        return f"{year}-{month}-{day}"
    return None

def parse_period(text):
    """Parse period like 'Van 11/10/2025 tot 11/11/2025' to start and end dates."""
    if not text:
        return None
    match = re.search(r'(\d{2}/\d{2}/\d{4})\s*tot\s*(\d{2}/\d{2}/\d{4})', text)
    if match:
        start_str, end_str = match.groups()
        return {
            "start": parse_date(start_str),
            "end": parse_date(end_str)
        }
    return None

def parse_minutes(text):
    """Parse minutes like '5 minuten' to numeric value."""
    if not text:
        return None
    match = re.search(r'([\d.]+)\s*min', text, re.IGNORECASE)
    if match:
        return float(match.group(1))
    return None

def parse_sms_count(text):
    """Parse SMS count like '0 sms/mms' to numeric value."""
    if not text:
        return None
    match = re.search(r'([\d.]+)\s*sms', text, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None

def parse_last_update(text):
    """Parse last update like 'Laatste update : 03/11 17:54' to ISO datetime."""
    if not text:
        return None
    match = re.search(r'(\d{2}/\d{2})\s*(\d{2}:\d{2})', text)
    if match:
        date_part, time_part = match.groups()
        day, month = date_part.split('/')
        # Assume current year
        year = datetime.now().year
        return f"{year}-{month}-{day}T{time_part}:00"
    return None

def is_unlimited(text):
    """Check if a limit is unlimited."""
    if not text:
        return False
    return 'onbeperkt' in text.lower() or 'unlimited' in text.lower()

def wait_for_page_load(page, timeout=30000):
    """Wait minimum 2 seconds and then wait for all loading spinners to disappear."""
    print("  >> Waiting for page to load (min 2s + no spinners)...")
    time.sleep(2)  # Minimum 2 seconds
    
    # Wait for all spinners to disappear
    try:
        start_time = time.time()
        while time.time() - start_time < timeout / 1000:
            spinners = page.locator('svg.p-progress-spinner')
            if spinners.count() == 0:
                print("  >> Page fully loaded (no spinners)")
                return True
            time.sleep(0.3)  # Check every 300ms
        print("  >> Warning: Timeout waiting for spinners to disappear")
        return False
    except Exception as e:
        print(f"  >> Warning: Error waiting for spinners: {e}")
        return False

def format_output_structure(products_data, latest_invoice):
    """Format the extracted data into the desired output structure."""
    # Process products into structured format
    formatted_products = []
    
    for product in products_data:
        # Determine product type and ID
        if "phone_number" in product:
            product_type = "mobile"
            # Clean phone number for ID (remove spaces)
            phone_clean = product["phone_number"].replace(" ", "")
            product_id = f"mobile_{phone_clean}"
        elif "easy_switch_number" in product:
            product_type = "internet"
            product_id = f"internet_{product['easy_switch_number']}"
        else:
            product_type = "unknown"
            product_id = f"unknown_{product.get('tariff', 'product')}"
        
        # Build product structure
        formatted_product = {
            "id": product_id,
            "type": product_type
        }
        
        # Add phone number for mobile
        if "phone_number" in product:
            formatted_product["phone_number"] = product["phone_number"]
        
        # Add easy switch number for internet
        if "easy_switch_number" in product:
            formatted_product["easy_switch_number"] = product["easy_switch_number"]
        
        # Add tariff
        if "tariff" in product:
            formatted_product["tariff"] = product["tariff"]
        
        # Add contract information
        contract = {}
        if "contract_start_date" in product:
            contract["start_date"] = product["contract_start_date"]
        if "price_per_month_eur" in product:
            contract["price_per_month_eur"] = product["price_per_month_eur"]
        
        if contract:
            formatted_product["contract"] = contract
        
        # Add usage information
        if "usage" in product:
            formatted_product["usage"] = product["usage"]
        
        formatted_products.append(formatted_product)
    
    # Build the final structure
    result = {
        "provider": "hey!",
        "account": {
            "last_sync": datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        },
        "products": formatted_products
    }
    
    # Add billing information
    if latest_invoice:
        # Generate invoice ID from date if available
        invoice_id = None
        if "date" in latest_invoice and latest_invoice["date"]:
            invoice_id = f"INV-{latest_invoice['date'].replace('-', '')}"
        
        billing_info = {
            "latest_invoice": {}
        }
        
        if invoice_id:
            billing_info["latest_invoice"]["invoice_id"] = invoice_id
        
        if "amount_eur" in latest_invoice:
            billing_info["latest_invoice"]["amount_eur"] = latest_invoice["amount_eur"]
        
        if "status" in latest_invoice:
            billing_info["latest_invoice"]["status"] = latest_invoice["status"].lower()
        
        if "paid" in latest_invoice:
            billing_info["latest_invoice"]["paid"] = latest_invoice["paid"]
        
        if "date" in latest_invoice:
            billing_info["latest_invoice"]["date"] = latest_invoice["date"]
        
        if "due_date" in latest_invoice:
            billing_info["latest_invoice"]["due_date"] = latest_invoice["due_date"]
        
        result["billing"] = billing_info
    
    return result

def check_logged_in_and_navigate(page):
    """Check if logged in and navigate to products page if needed."""
    print("Checking if logged in...")
    mijn_account = page.locator('span.p-menuitem-text.ng-star-inserted.button-label:has-text("Mijn account")')
    
    if mijn_account.count() > 0:
        print("✓ Logged in! Found 'Mijn account' element.")
        
        # Check if we're on the products page, if not navigate to it
        if page.url != "https://ecare.heytelecom.be/nl/mijn-producten":
            print("Navigating to mijn-producten page...")
            page.goto("https://ecare.heytelecom.be/nl/mijn-producten")
            # time.sleep(2)
        
        return True
    return False

def main():
    with sync_playwright() as p:
        # Launch browser with saved data and NOT headless
        browser = p.chromium.launch_persistent_context(
            user_data_dir="hey_browser_data",
            headless=False
        )
        
        page = browser.new_page()
        
        # Navigate to the products page
        print("Navigating to mijn-producten page...")
        page.goto("https://ecare.heytelecom.be/nl/mijn-producten")
        wait_for_page_load(page)
        
        # Check if already logged in
        if not check_logged_in_and_navigate(page):
            print("Not logged in. Proceeding with login...")
            
            # Wait for redirect to auth page
            page.wait_for_url("**/auth.heytelecom.be/**", timeout=10000)
            print(f"Current URL: {page.url}")
            
            # Click on "Inloggen via E-mail" button
            print("Clicking 'Inloggen via E-mail' button...")
            email_login_btn = page.locator('a#Login_loginByEmail')
            email_login_btn.wait_for(state="visible", timeout=10000)
            email_login_btn.click()
            wait_for_page_load(page)
            
            # Fill in email
            print("Filling in email...")
            email_input = page.locator('input#Login_byEmail_emailAddress')
            email_input.wait_for(state="visible", timeout=10000)
            email_input.fill(EMAIL)
            
            # Fill in password
            print("Filling in password...")
            password_input = page.locator('input#Login_byEmail_password')
            password_input.wait_for(state="visible", timeout=10000)
            password_input.fill(PASSWORD)
            
            # Click login button
            print("Clicking 'Inloggen maar!' button...")
            login_btn = page.locator('button#Login_byEmail_login')
            login_btn.click()
            wait_for_page_load(page)
            
            # Check for error message
            error_msg = page.locator('div.error_msgs:has-text("Verkeerde gebruikersnaam en/of wachtwoord")')
            
            if error_msg.count() > 0:
                print("✗ Login failed: Wrong username and/or password.")
                print("Closing browser...")
                browser.close()
                return
            
            # Wait for the Mijn account element to appear (indicates successful login)
            try:
                page.wait_for_selector('span.p-menuitem-text.ng-star-inserted.button-label:has-text("Mijn account")', timeout=10000)
            except:
                pass
            
            wait_for_page_load(page)
            
            # Verify we're logged in
            print(f"Current URL after login: {page.url}")
            if not check_logged_in_and_navigate(page):
                print("⚠ Login may have failed. 'Mijn account' element not found.")
        
        # Extract and format products
        print("\n" + "="*60)
        print("EXTRACTING PRODUCTS")
        print("="*60)
        
        products_data = extract_and_format_products(page)
        
        # Extract latest invoice
        print("\n" + "="*60)
        print("EXTRACTING LATEST INVOICE")
        print("="*60)
        
        latest_invoice = extract_latest_invoice(page)
        
        # Combine all data in the structured format
        result_data = format_output_structure(products_data, latest_invoice)
        
        # Output as JSON
        print("\n" + "="*60)
        print("JSON OUTPUT")
        print("="*60)
        print(json.dumps(result_data, indent=2, ensure_ascii=False))
        
        print("\nBrowser will remain open. Close it manually when done.")
        # Keep browser open - wait for user to close it manually
        page.pause()
        
        browser.close()

def extract_detailed_usage(page):
    """Extract detailed usage data from the current page and return as dict."""
    # Wait for navigation to complete
    try:
        page.wait_for_url("**/gedetailleerd-gebruik**", timeout=10000)
        page.wait_for_selector('section.iris-consumption', timeout=10000)
    except:
        pass
    
    wait_for_page_load(page)
    
    # Get the full URL
    current_url = page.url
    
    # Check if we're on the correct page
    if "gedetailleerd-gebruik" not in current_url:
        return None
    
    usage_data = {}
    
    # Extract date range (for mobile)
    date_range = page.locator('p.iris-consumption__main-date-range')
    if date_range.count() > 0:
        period_text = date_range.inner_text()
        usage_data["period"] = parse_period(period_text)
    
    # Extract Data usage (for mobile - Belgium + Roaming EU)
    data_block = page.locator('div#consumption-data')
    if data_block.count() > 0:
        data_limit = data_block.locator('span.iris-consumption__main-data-limit')
        data_usage = data_block.locator('span.iris-consumption__main-data-usage strong')
        data_update = data_block.locator('span.iris-consumption__main-data-update')
        
        if data_limit.count() > 0 and data_usage.count() > 0:
            limit_text = data_limit.inner_text()
            used_text = data_usage.inner_text()
            usage_data["data"] = {
                "used": parse_data_amount(used_text),
                "limit": parse_data_amount(limit_text),
                "unlimited": is_unlimited(limit_text),
                "last_update": parse_last_update(data_update.inner_text() if data_update.count() > 0 else None)
            }
    
    # Extract Data usage (for internet - fixed)
    fix_block = page.locator('div#consumption-fix')
    if fix_block.count() > 0:
        fix_limit = fix_block.locator('span.iris-consumption__main-data-limit')
        fix_usage = fix_block.locator('span.iris-consumption__main-data-usage strong')
        fix_update = fix_block.locator('span.iris-consumption__main-data-update')
        
        if fix_limit.count() > 0 and fix_usage.count() > 0:
            limit_text = fix_limit.inner_text()
            used_text = fix_usage.inner_text()
            usage_data["data"] = {
                "used": parse_data_amount(used_text),
                "limit": parse_data_amount(limit_text),
                "unlimited": is_unlimited(limit_text),
                "last_update": parse_last_update(fix_update.inner_text() if fix_update.count() > 0 else None)
            }
    
    # Extract Calls usage
    calls_block = page.locator('div#consumption-calls')
    if calls_block.count() > 0:
        calls_limit = calls_block.locator('span.iris-consumption__main-data-limit')
        calls_usage = calls_block.locator('span.iris-consumption__main-data-usage strong')
        calls_update = calls_block.locator('span.iris-consumption__main-data-update')
        
        if calls_limit.count() > 0 and calls_usage.count() > 0:
            limit_text = calls_limit.inner_text()
            used_text = calls_usage.inner_text()
            usage_data["calls"] = {
                "used": parse_minutes(used_text),
                "unlimited": is_unlimited(limit_text),
                "last_update": parse_last_update(calls_update.inner_text() if calls_update.count() > 0 else None)
            }
    
    # Extract SMS/MMS usage
    sms_block = page.locator('div#consumption-sms')
    if sms_block.count() > 0:
        sms_limit = sms_block.locator('span.iris-consumption__main-data-limit')
        sms_usage = sms_block.locator('span.iris-consumption__main-data-usage strong')
        sms_update = sms_block.locator('span.iris-consumption__main-data-update')
        
        if sms_limit.count() > 0 and sms_usage.count() > 0:
            limit_text = sms_limit.inner_text()
            used_text = sms_usage.inner_text()
            usage_data["sms_mms"] = {
                "used": parse_sms_count(used_text),
                "unlimited": is_unlimited(limit_text),
                "last_update": parse_last_update(sms_update.inner_text() if sms_update.count() > 0 else None)
            }
    
    return usage_data

def extract_latest_invoice(page):
    """Navigate to invoices page and extract the latest invoice data."""
    print("Navigating to invoices page...")
    page.goto("https://ecare.heytelecom.be/nl/mijn-facturen")
    wait_for_page_load(page)
    page.wait_for_selector('lib-obe-latest-invoice section.iris-invoice', timeout=10000)
    
    invoice_data = {}
    
    # Find the latest invoice section
    invoice_section = page.locator('lib-obe-latest-invoice section.iris-invoice')
    
    if invoice_section.count() == 0:
        print("  >> No invoice found")
        return None
    
    # Extract amount
    amount_element = invoice_section.locator('p.iris-invoice__main-data-title:has-text("Bedrag")').locator('xpath=following-sibling::p').first
    if amount_element.count() > 0:
        amount_text = amount_element.inner_text().strip()
        invoice_data["amount_eur"] = parse_price(amount_text)
        print(f"  >> Amount: {invoice_data['amount_eur']} EUR")
    
    # Extract status
    status_element = invoice_section.locator('p.iris-invoice__main-data-title:has-text("Status")').locator('xpath=following-sibling::p').first
    if status_element.count() > 0:
        status_text = status_element.inner_text().strip()
        invoice_data["status"] = status_text
        invoice_data["paid"] = status_text.lower() == "betaald"
        print(f"  >> Status: {status_text} (Paid: {invoice_data['paid']})")
    
    # Extract date
    date_element = invoice_section.locator('p.iris-invoice__main-data-title:has-text("Datum")').locator('xpath=following-sibling::p').first
    if date_element.count() > 0:
        date_text = date_element.inner_text().strip()
        invoice_data["date"] = parse_date(date_text)
        print(f"  >> Date: {invoice_data['date']}")
    
    # Extract due date
    due_date_element = invoice_section.locator('p.iris-invoice__main-data-title:has-text("Vervaldatum")').locator('xpath=following-sibling::p').first
    if due_date_element.count() > 0:
        due_date_text = due_date_element.inner_text().strip()
        invoice_data["due_date"] = parse_date(due_date_text)
        print(f"  >> Due Date: {invoice_data['due_date']}")
    
    return invoice_data
    
def get_product_identifier(product):
    """Get a unique identifier for a product."""
    # Try phone number first
    phone_number = product.locator('span.iris-products__details-tariff-number')
    if phone_number.count() > 0:
        return ("phone", phone_number.inner_text())
    
    # Try Easy Switch number (for internet)
    easy_switch = product.locator('span.iris-products__details-info-title:has-text("Nummer Easy Switch")').locator('xpath=following-sibling::span')
    if easy_switch.count() > 0:
        return ("easy_switch", easy_switch.inner_text())
    
    # Fallback to tariff name
    tariff_name = product.locator('span.iris-products__details-tariff-name')
    if tariff_name.count() > 0:
        return ("tariff", tariff_name.inner_text())
    
    return None

def find_product_by_identifier(page, identifier):
    """Find a product by its identifier after navigating back."""
    if not identifier:
        return None
    
    id_type, id_value = identifier
    products = page.locator('li.iris-products__item')
    
    for i in range(products.count()):
        product = products.nth(i)
        current_id = get_product_identifier(product)
        if current_id and current_id == identifier:
            return product
    
    return None

def extract_and_format_products(page):
    """Extract and format all products from the page and return as list of dicts."""
    
    # Wait for products to load
    wait_for_page_load(page)
    page.wait_for_selector('li.iris-products__item', timeout=10000)
    
    # Find all product items
    products = page.locator('li.iris-products__item')
    product_count = products.count()
    
    if product_count == 0:
        print("No products found on the page.")
        return []
    
    print(f"\nFound {product_count} product(s)\n")
    
    # First pass: collect all product identifiers and basic info
    products_to_process = []
    for i in range(product_count):
        product = products.nth(i)
        identifier = get_product_identifier(product)
        
        product_data = {}
        
        # Extract phone number (if exists)
        phone_number = product.locator('span.iris-products__details-tariff-number')
        if phone_number.count() > 0:
            product_data["phone_number"] = phone_number.inner_text()
        
        # Extract tariff name
        tariff_name = product.locator('span.iris-products__details-tariff-name')
        if tariff_name.count() > 0:
            product_data["tariff"] = tariff_name.inner_text()
        
        # Extract Easy Switch number (for internet)
        easy_switch = product.locator('span.iris-products__details-info-title:has-text("Nummer Easy Switch")').locator('xpath=following-sibling::span')
        if easy_switch.count() > 0:
            product_data["easy_switch_number"] = easy_switch.inner_text()
        
        # Extract contract start date
        start_date_label = product.locator('span.iris-products__details-info-title:has-text("Begindatum contract")')
        if start_date_label.count() > 0:
            start_date_value = start_date_label.locator('xpath=following-sibling::span').first
            start_date_text = start_date_value.inner_text().strip()
            if start_date_text:
                product_data["contract_start_date"] = parse_date(start_date_text)
        
        # Extract price
        price_label = product.locator('span.iris-products__details-info-title:has-text("Prijs")')
        if price_label.count() > 0:
            price_value = price_label.locator('xpath=following-sibling::span').first
            price_text = price_value.inner_text()
            product_data["price_per_month_eur"] = parse_price(price_text)
        
        products_to_process.append({
            "identifier": identifier,
            "data": product_data
        })
    
    # Second pass: extract usage data for each product
    for idx, product_info in enumerate(products_to_process):
        identifier = product_info["identifier"]
        product_data = product_info["data"]
        
        # Find the product by identifier
        product = find_product_by_identifier(page, identifier)
        if not product:
            print(f"  >> Warning: Could not find product with identifier {identifier}")
            continue
        
        # Click on detailed consumption link
        consumption_link = product.locator('a.iris-products__link[data-event_category="MyProducts"]')
        if consumption_link.count() > 0:
            print(f"  >> Extracting usage data for product {idx+1} ({identifier[1]})...")
            consumption_link.click()
            
            # Extract detailed usage data
            usage_data = extract_detailed_usage(page)
            if usage_data:
                product_data["usage"] = usage_data
            
            # Go back to products page
            page.goto("https://ecare.heytelecom.be/nl/mijn-producten")
            wait_for_page_load(page)
            page.wait_for_selector('li.iris-products__item', timeout=10000)
    
    # Return the collected data
    return [p["data"] for p in products_to_process]

if __name__ == "__main__":
    main()
