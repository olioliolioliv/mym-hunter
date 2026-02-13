#!/usr/bin/env python3
"""
MYM.fans Browser Login
Automated login using Playwright to handle reCAPTCHA v3
Saves session cookies for use in scraper
"""

import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# Configuration
SECRETS_DIR = Path(__file__).parent / ".secrets"
COOKIES_FILE = SECRETS_DIR / "mym_cookies.json"
MYM_BASE = "https://mym.fans"

def login_to_mym(email: str, password: str, headless: bool = False, timeout: int = 120):
    """
    Login to MYM.fans using Playwright browser automation

    Args:
        email: User email address
        password: User password
        headless: Run browser in headless mode (default: False for reCAPTCHA)
        timeout: Login timeout in seconds (default: 120 for manual reCAPTCHA solving)

    Returns:
        bool: True if login successful, False otherwise
    """

    SECRETS_DIR.mkdir(parents=True, exist_ok=True)

    print("="*80)
    print("MYM.FANS BROWSER LOGIN")
    print("="*80)
    print(f"\n📧 Email: {email}")
    print(f"🌐 Target: {MYM_BASE}")
    print(f"💾 Cookies will be saved to: {COOKIES_FILE}\n")

    if not headless:
        print("⚠️  Browser will open. Please solve reCAPTCHA if prompted.")
        print("⏱️  You have {timeout} seconds to complete login.\n")

    with sync_playwright() as p:
        # Launch browser (visible for reCAPTCHA solving)
        print("🚀 Launching browser...")
        browser = p.chromium.launch(
            headless=headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox'
            ]
        )

        # Create context with realistic user agent
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1280, 'height': 720},
            locale='en-US',
            timezone_id='America/New_York'
        )

        page = context.new_page()

        try:
            # Navigate to login page
            print(f"🌐 Navigating to login page...")
            page.goto(f"{MYM_BASE}/app/sign-in/email", wait_until="domcontentloaded", timeout=30000)
            time.sleep(2)

            # Fill email
            print("📝 Filling email...")
            email_input = page.locator('input[type="email"]')
            email_input.wait_for(state="visible", timeout=10000)
            email_input.fill(email)
            time.sleep(0.5)

            # Fill password
            print("🔒 Filling password...")
            password_input = page.locator('input[type="password"]')
            password_input.wait_for(state="visible", timeout=10000)
            password_input.fill(password)
            time.sleep(0.5)

            # Click login button
            print("🔐 Clicking login button...")
            login_button = page.locator('button[type="submit"]')
            login_button.click()

            # Wait for navigation or error
            print(f"\n⏳ Waiting for login to complete (timeout: {timeout}s)...")
            print("   If reCAPTCHA appears, please solve it manually.")

            try:
                # Wait for redirect to feed (successful login)
                page.wait_for_url("**/app/feed*", timeout=timeout*1000)
                print("\n✅ Login successful! Redirected to feed.")

            except PlaywrightTimeout:
                # Check if we're still on login page (failed login)
                current_url = page.url
                if "/sign-in" in current_url:
                    print(f"\n❌ Login failed - still on login page: {current_url}")
                    print("   This could be due to:")
                    print("   - Incorrect credentials")
                    print("   - reCAPTCHA not solved")
                    print("   - Timeout exceeded")
                    browser.close()
                    return False
                else:
                    # We're somewhere else, might be success
                    print(f"\n⚠️  Timeout but redirected to: {current_url}")
                    print("   Continuing to save cookies...")

            # Give page time to fully load
            time.sleep(3)

            # Save cookies
            cookies = context.cookies()

            # Validate we have the required cookies
            required_cookies = {'PHPSESSID', '_locale'}
            cookie_names = {c['name'] for c in cookies}

            if not required_cookies.issubset(cookie_names):
                missing = required_cookies - cookie_names
                print(f"\n⚠️  Warning: Missing required cookies: {missing}")
                print(f"   Found cookies: {cookie_names}")

            # Save to file
            COOKIES_FILE.write_text(json.dumps(cookies, indent=2))
            print(f"\n💾 Saved {len(cookies)} cookies to {COOKIES_FILE}")

            # Display important cookies
            print("\n📋 Important cookies:")
            for cookie in cookies:
                if cookie['name'] in required_cookies or 'id_creator' in cookie['name']:
                    print(f"   {cookie['name']}: {cookie['value'][:50]}{'...' if len(cookie['value']) > 50 else ''}")

            # Keep browser open briefly for inspection
            if not headless:
                print("\n🔍 Browser will stay open for 10 seconds for inspection...")
                time.sleep(10)

            print("\n" + "="*80)
            print("LOGIN COMPLETE")
            print("="*80)
            print(f"✅ Cookies saved to: {COOKIES_FILE}")
            print(f"✅ Session should be valid for ~30 days")
            print(f"✅ Ready to use with mym_scraper.py\n")

            browser.close()
            return True

        except Exception as e:
            print(f"\n❌ Error during login: {e}")
            import traceback
            traceback.print_exc()
            browser.close()
            return False


def test_cookies():
    """Test if saved cookies are valid by making a request"""
    import requests

    if not COOKIES_FILE.exists():
        print("❌ No cookies file found. Run browser_login.py first.")
        return False

    print("\n🧪 Testing saved cookies...")

    # Load cookies
    cookies_data = json.loads(COOKIES_FILE.read_text())

    # Convert to requests format
    session = requests.Session()
    for cookie in cookies_data:
        session.cookies.set(
            cookie['name'],
            cookie['value'],
            domain=cookie.get('domain', '.mym.fans'),
            path=cookie.get('path', '/')
        )

    # Test request to authenticated page
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }

    try:
        r = session.get(f"{MYM_BASE}/app/feed", headers=headers, timeout=10)

        if r.status_code == 200 and "/sign-in" not in r.url:
            print("✅ Cookies are valid! Authenticated successfully.")
            return True
        else:
            print(f"❌ Cookies may be invalid. Status: {r.status_code}, URL: {r.url}")
            return False

    except Exception as e:
        print(f"❌ Error testing cookies: {e}")
        return False


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="MYM.fans Browser Login")
    parser.add_argument("--email", "-e", help="Email address")
    parser.add_argument("--password", "-p", help="Password")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode (not recommended)")
    parser.add_argument("--timeout", type=int, default=120, help="Login timeout in seconds (default: 120)")
    parser.add_argument("--test", action="store_true", help="Test saved cookies")

    args = parser.parse_args()

    if args.test:
        test_cookies()
        return

    # Get credentials
    email = args.email
    password = args.password

    if not email or not password:
        print("❌ Email and password are required!")
        print("Usage: python browser_login.py --email user@example.com --password yourpass")
        print("   or: python browser_login.py --test  (to test saved cookies)")
        return

    # Run login
    success = login_to_mym(email, password, headless=args.headless, timeout=args.timeout)

    if success:
        # Test the cookies
        print("\n" + "="*80)
        test_cookies()
    else:
        print("\n❌ Login failed. Please try again.")


if __name__ == "__main__":
    main()
