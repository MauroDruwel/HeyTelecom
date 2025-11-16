"""Hey Telecom client for accessing mobile usage information."""
import time
from typing import Optional, Dict, Any, List
from playwright.sync_api import sync_playwright, Browser, Page, BrowserContext

from .models import Product, Contract, UsageData, Invoice, AccountData
from .parsers import (
    parse_data_amount, parse_price, parse_date, parse_period,
    parse_minutes, parse_sms_count, parse_last_update, is_unlimited
)


class HeyTelecomClient:
    """Client for interacting with Hey Telecom account."""

    BASE_URL = "https://ecare.heytelecom.be"
    AUTH_URL = "https://auth.heytelecom.be"

    def __init__(self, email: Optional[str] = None, password: Optional[str] = None,
                 user_data_dir: str = "hey_browser_data", auto_install: bool = True):
        """
        Initialize Hey Telecom client.

        Args:
            email: Email address for login (optional if already logged in)
            password: Password for login (optional if already logged in)
            user_data_dir: Directory to store browser session data
            auto_install: Automatically install Playwright chromium if not found (default: True)
        
        Note:
            Browser always runs in headless mode (no GUI).
        """
        self.email = email
        self.password = password
        self.user_data_dir = user_data_dir
        self.auto_install = auto_install
        self.headless = True  # Always run headless
        self._playwright = None
        self._browser: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def connect(self):
        """Start browser and create page."""
        # Ensure Playwright chromium is installed before connecting
        if self.auto_install:
            from .installer import ensure_playwright_installed
            ensure_playwright_installed()
        
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch_persistent_context(
            user_data_dir=self.user_data_dir,
            headless=self.headless
        )
        self._page = self._browser.new_page()

    def close(self):
        """Close browser and cleanup."""
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()

    def _handle_cookie_popup(self):
        """Check for and handle cookie popup if present."""
        if not self._page:
            return False
        
        try:
            reject_button = self._page.locator('button#onetrust-reject-all-handler')
            if reject_button.count() > 0:
                reject_button.click()
                time.sleep(0.5)  # Reduced from 1 second
                return True
        except:
            pass
        return False

    def _wait_for_page_load(self, timeout: int = 30000):
        """Wait for page to load completely."""
        if not self._page:
            raise RuntimeError("Browser not connected. Call connect() first.")
        
        time.sleep(1)  # Minimum 1 second (reduced from 2)
        
        # Wait for all spinners to disappear
        try:
            start_time = time.time()
            while time.time() - start_time < timeout / 1000:
                spinners = self._page.locator('svg.p-progress-spinner')
                if spinners.count() == 0:
                    return True
                time.sleep(0.2)  # Check every 200ms (reduced from 300ms)
            return False
        except Exception:
            return False

    def _check_logged_in(self) -> bool:
        """Check if user is logged in."""
        if not self._page:
            return False
        
        mijn_account = self._page.locator('span.p-menuitem-text.ng-star-inserted.button-label:has-text("Mijn account")')
        return mijn_account.count() > 0

    def login(self):
        """
        Login to Hey Telecom account.
        
        Raises:
            ValueError: If email or password not provided
            RuntimeError: If login fails
        """
        if not self._page:
            raise RuntimeError("Browser not connected. Call connect() first.")
        
        # Navigate to products page
        self._page.goto(f"{self.BASE_URL}/nl/mijn-producten")
        self._wait_for_page_load()
        
        # Check if already logged in (before handling cookies)
        if self._check_logged_in():
            return
        
        if not self.email or not self.password:
            raise ValueError("Email and password required for login")
        
        # Wait for redirect to auth page
        self._page.wait_for_url(f"**{self.AUTH_URL}/**", timeout=10000)
        
        # Click on "Inloggen via E-mail" button
        email_login_btn = self._page.locator('a#Login_loginByEmail')
        email_login_btn.wait_for(state="visible", timeout=10000)
        email_login_btn.click()
        self._wait_for_page_load()
        
        # Fill in email
        email_input = self._page.locator('input#Login_byEmail_emailAddress')
        email_input.wait_for(state="visible", timeout=10000)
        email_input.fill(self.email)
        
        # Fill in password
        password_input = self._page.locator('input#Login_byEmail_password')
        password_input.wait_for(state="visible", timeout=10000)
        password_input.fill(self.password)
        
        # Click login button
        login_btn = self._page.locator('button#Login_byEmail_login')
        login_btn.click()
        self._wait_for_page_load()
        
        # Check for error message
        error_msg = self._page.locator('div.error_msgs:has-text("Verkeerde gebruikersnaam en/of wachtwoord")')
        if error_msg.count() > 0:
            raise RuntimeError("Login failed: Wrong username and/or password")
        
        # Wait for successful login
        try:
            self._page.wait_for_selector('span.p-menuitem-text.ng-star-inserted.button-label:has-text("Mijn account")', timeout=10000)
        except:
            pass
        
        self._wait_for_page_load()
        
        # Verify login
        if not self._check_logged_in():
            raise RuntimeError("Login verification failed")

    def get_products(self) -> List[Product]:
        """
        Get all products from the account.
        
        Returns:
            List of Product objects
        """
        if not self._page:
            raise RuntimeError("Browser not connected. Call connect() first.")
        
        # Navigate to products page
        self._page.goto(f"{self.BASE_URL}/nl/mijn-producten")
        self._wait_for_page_load()
        
        # Handle cookie popup
        self._handle_cookie_popup()
        time.sleep(1)
        
        self._page.wait_for_selector('li.iris-products__item', timeout=10000)
        
        products = self._page.locator('li.iris-products__item')
        product_count = products.count()
        
        if product_count == 0:
            return []
        
        # Collect product data
        products_data = []
        for i in range(product_count):
            product = products.nth(i)
            product_data = self._extract_product_basic_info(product)
            identifier = self._get_product_identifier(product)
            products_data.append({
                "identifier": identifier,
                "data": product_data
            })
        
        # Extract usage data for each product
        for product_info in products_data:
            identifier = product_info["identifier"]
            product_data = product_info["data"]
            
            # Find product again (in case page reloaded)
            product = self._find_product_by_identifier(identifier)
            if not product:
                continue
            
            # Extract usage
            consumption_link = product.locator('a.iris-products__link[data-event_category="MyProducts"]')
            if consumption_link.count() > 0:
                consumption_link.click()
                usage_data = self._extract_usage_data()
                if usage_data:
                    product_data["usage"] = usage_data
                
                # Go back using browser back (faster than full page reload)
                self._page.go_back()
                self._wait_for_page_load()
                self._page.wait_for_selector('li.iris-products__item', timeout=10000)
        
        # Convert to Product objects
        return [self._create_product_object(p["data"]) for p in products_data]

    def get_latest_invoice(self) -> Optional[Invoice]:
        """
        Get the latest invoice.
        
        Returns:
            Invoice object or None if no invoice found
        """
        if not self._page:
            raise RuntimeError("Browser not connected. Call connect() first.")
        
        self._page.goto(f"{self.BASE_URL}/nl/mijn-facturen")
        self._wait_for_page_load()
        
        # Handle cookie popup (reduced wait time)
        self._handle_cookie_popup()
        time.sleep(0.5)
        
        try:
            self._page.wait_for_selector('lib-obe-latest-invoice section.iris-invoice', timeout=10000)
        except:
            return None
        
        invoice_section = self._page.locator('lib-obe-latest-invoice section.iris-invoice')
        if invoice_section.count() == 0:
            return None
        
        invoice_data = {}
        
        # Extract amount
        amount_element = invoice_section.locator('p.iris-invoice__main-data-title:has-text("Bedrag")').locator('xpath=following-sibling::p').first
        if amount_element.count() > 0:
            amount_text = amount_element.inner_text().strip()
            invoice_data["amount_eur"] = parse_price(amount_text)
        
        # Extract status
        status_element = invoice_section.locator('p.iris-invoice__main-data-title:has-text("Status")').locator('xpath=following-sibling::p').first
        if status_element.count() > 0:
            status_text = status_element.inner_text().strip()
            invoice_data["status"] = status_text
            invoice_data["paid"] = status_text.lower() == "betaald"
        
        # Extract date
        date_element = invoice_section.locator('p.iris-invoice__main-data-title:has-text("Datum")').locator('xpath=following-sibling::p').first
        if date_element.count() > 0:
            date_text = date_element.inner_text().strip()
            invoice_data["date"] = parse_date(date_text)
        
        # Extract due date
        due_date_element = invoice_section.locator('p.iris-invoice__main-data-title:has-text("Vervaldatum")').locator('xpath=following-sibling::p').first
        if due_date_element.count() > 0:
            due_date_text = due_date_element.inner_text().strip()
            invoice_data["due_date"] = parse_date(due_date_text)
        
        # Generate invoice ID
        if invoice_data.get("date"):
            invoice_data["invoice_id"] = f"INV-{invoice_data['date'].replace('-', '')}"
        
        return Invoice(**invoice_data)

    def get_account_data(self) -> AccountData:
        """
        Get all account data including products and latest invoice.
        
        Returns:
            AccountData object with all information
        """
        products = self.get_products()
        invoice = self.get_latest_invoice()
        
        return AccountData(
            products=products,
            latest_invoice=invoice
        )

    def _extract_product_basic_info(self, product) -> Dict[str, Any]:
        """Extract basic product information."""
        product_data = {}
        
        # Phone number
        phone_number = product.locator('span.iris-products__details-tariff-number')
        if phone_number.count() > 0:
            product_data["phone_number"] = phone_number.inner_text()
        
        # Tariff name
        tariff_name = product.locator('span.iris-products__details-tariff-name')
        if tariff_name.count() > 0:
            product_data["tariff"] = tariff_name.inner_text()
        
        # Easy Switch number
        easy_switch = product.locator('span.iris-products__details-info-title:has-text("Nummer Easy Switch")').locator('xpath=following-sibling::span')
        if easy_switch.count() > 0:
            product_data["easy_switch_number"] = easy_switch.inner_text()
        
        # Contract start date
        start_date_label = product.locator('span.iris-products__details-info-title:has-text("Begindatum contract")')
        if start_date_label.count() > 0:
            start_date_value = start_date_label.locator('xpath=following-sibling::span').first
            start_date_text = start_date_value.inner_text().strip()
            if start_date_text:
                product_data["contract_start_date"] = parse_date(start_date_text)
        
        # Price
        price_label = product.locator('span.iris-products__details-info-title:has-text("Prijs")')
        if price_label.count() > 0:
            price_value = price_label.locator('xpath=following-sibling::span').first
            price_text = price_value.inner_text()
            product_data["price_per_month_eur"] = parse_price(price_text)
        
        return product_data

    def _extract_usage_data(self) -> Optional[Dict[str, Any]]:
        """Extract usage data from detailed usage page."""
        try:
            self._page.wait_for_url("**/gedetailleerd-gebruik**", timeout=10000)
        except:
            pass
        
        # Only wait for page load (selector check is redundant)
        self._wait_for_page_load()
        
        if "gedetailleerd-gebruik" not in self._page.url:
            return None
        
        usage_data = {}
        
        # Extract date range
        date_range = self._page.locator('p.iris-consumption__main-date-range')
        if date_range.count() > 0:
            period_text = date_range.inner_text()
            usage_data["period"] = parse_period(period_text)
        
        # Extract Data usage (mobile)
        data_block = self._page.locator('div#consumption-data')
        if data_block.count() > 0:
            usage_data["data"] = self._extract_data_usage(data_block)
        
        # Extract Data usage (internet)
        fix_block = self._page.locator('div#consumption-fix')
        if fix_block.count() > 0:
            usage_data["data"] = self._extract_data_usage(fix_block)
        
        # Extract Calls usage
        calls_block = self._page.locator('div#consumption-calls')
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
        sms_block = self._page.locator('div#consumption-sms')
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

    def _extract_data_usage(self, block) -> Dict[str, Any]:
        """Extract data usage from a block."""
        data_limit = block.locator('span.iris-consumption__main-data-limit')
        data_usage = block.locator('span.iris-consumption__main-data-usage strong')
        data_update = block.locator('span.iris-consumption__main-data-update')
        
        if data_limit.count() > 0 and data_usage.count() > 0:
            limit_text = data_limit.inner_text()
            used_text = data_usage.inner_text()
            return {
                "used": parse_data_amount(used_text),
                "limit": parse_data_amount(limit_text),
                "unlimited": is_unlimited(limit_text),
                "last_update": parse_last_update(data_update.inner_text() if data_update.count() > 0 else None)
            }
        return {}

    def _get_product_identifier(self, product):
        """Get unique identifier for a product."""
        # Try phone number
        phone_number = product.locator('span.iris-products__details-tariff-number')
        if phone_number.count() > 0:
            return ("phone", phone_number.inner_text())
        
        # Try Easy Switch number
        easy_switch = product.locator('span.iris-products__details-info-title:has-text("Nummer Easy Switch")').locator('xpath=following-sibling::span')
        if easy_switch.count() > 0:
            return ("easy_switch", easy_switch.inner_text())
        
        # Fallback to tariff name
        tariff_name = product.locator('span.iris-products__details-tariff-name')
        if tariff_name.count() > 0:
            return ("tariff", tariff_name.inner_text())
        
        return None

    def _find_product_by_identifier(self, identifier):
        """Find product by identifier."""
        if not identifier:
            return None
        
        products = self._page.locator('li.iris-products__item')
        for i in range(products.count()):
            product = products.nth(i)
            current_id = self._get_product_identifier(product)
            if current_id and current_id == identifier:
                return product
        
        return None

    def _create_product_object(self, data: Dict[str, Any]) -> Product:
        """Create Product object from data dictionary."""
        # Determine product type and ID
        if "phone_number" in data:
            product_type = "mobile"
            phone_clean = data["phone_number"].replace(" ", "")
            product_id = f"mobile_{phone_clean}"
        elif "easy_switch_number" in data:
            product_type = "internet"
            product_id = f"internet_{data['easy_switch_number']}"
        else:
            product_type = "unknown"
            product_id = f"unknown_{data.get('tariff', 'product')}"
        
        # Create contract if exists
        contract = None
        if "contract_start_date" in data or "price_per_month_eur" in data:
            contract = Contract(
                start_date=data.get("contract_start_date"),
                price_per_month_eur=data.get("price_per_month_eur")
            )
        
        # Create usage if exists
        usage = None
        if "usage" in data:
            usage = UsageData(**data["usage"])
        
        return Product(
            product_id=product_id,
            product_type=product_type,
            phone_number=data.get("phone_number"),
            easy_switch_number=data.get("easy_switch_number"),
            tariff=data.get("tariff"),
            contract=contract,
            usage=usage
        )
