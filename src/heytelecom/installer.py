"""Playwright installation utilities."""
import subprocess
import sys


def install_playwright():
    """
    Install Playwright Chromium browser with dependencies for headless operation.
    
    Always installs chromium with --with-deps and --only-shell flags.
    
    Raises:
        RuntimeError: If installation fails
    """
    cmd = ["playwright", "install", "chromium", "--with-deps", "--only-shell"]
    
    try:
        print("Installing Playwright chromium...")
        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(result.stdout)
        print("Successfully installed Playwright chromium")
    except subprocess.CalledProcessError as e:
        print(f"Installation failed: {e.stderr}")
        raise RuntimeError(f"Failed to install Playwright: {e}")
    except FileNotFoundError:
        print("Playwright command not found. Make sure playwright is installed.")
        print("Try: pip install playwright")
        raise RuntimeError("Playwright not found in PATH")


def ensure_playwright_installed():
    """
    Check if Playwright chromium browser is installed and install if needed.
    
    Only installs if chromium is not already available.
    """
    try:
        # Try to import playwright
        from playwright.sync_api import sync_playwright
        
        # Try to launch browser to check if installed
        try:
            with sync_playwright() as p:
                browser_instance = p.chromium.launch(headless=True)
                browser_instance.close()
            print("Playwright chromium is already installed")
        except Exception:
            print("Playwright chromium not found, installing...")
            install_playwright()
    except ImportError:
        raise RuntimeError("Playwright package not installed. Install with: pip install playwright")


if __name__ == "__main__":
    """Allow running as a script for installation."""
    install_playwright()
