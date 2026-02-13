#!/usr/bin/env python3
"""
MYM.fans API Explorer
Login and capture API endpoints for reverse engineering
"""

import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

SECRETS_DIR = Path(__file__).parent / ".secrets"
COOKIES_FILE = SECRETS_DIR / "mym_cookies.json"
API_LOG_FILE = SECRETS_DIR / "api_requests.json"

def explore_mym_api(email: str, password: str):
    """Login to MYM.fans and capture API requests"""

    SECRETS_DIR.mkdir(parents=True, exist_ok=True)

    print("🚀 Starting MYM.fans API exploration...")
    print(f"📧 Email: {email}")

    api_requests = []

    with sync_playwright() as p:
        # Launch browser
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )

        # Capture network requests
        def handle_request(request):
            if any(x in request.url for x in ['/api/', '/app/', 'mym.fans']):
                api_requests.append({
                    "url": request.url,
                    "method": request.method,
                    "headers": dict(request.headers),
                    "post_data": request.post_data if request.method == "POST" else None
                })
                print(f"📡 {request.method} {request.url}")

        def handle_response(response):
            if any(x in response.url for x in ['/api/', '/app/', 'mym.fans']):
                try:
                    if 'json' in response.headers.get('content-type', ''):
                        body = response.json()
                        for req in api_requests:
                            if req['url'] == response.url:
                                req['response'] = body
                                req['status'] = response.status
                                break
                except Exception:
                    pass

        context.on("request", handle_request)
        context.on("response", handle_response)

        page = context.new_page()

        # Navigate to login
        print("\n🌐 Navigating to MYM.fans login...")
        page.goto("https://mym.fans/app/sign-in/email", wait_until="domcontentloaded", timeout=60000)
        time.sleep(3)

        # Fill login form
        print("📝 Filling login form...")
        page.fill('input[type="email"]', email)
        page.fill('input[type="password"]', password)

        # Click login button
        print("🔐 Logging in...")
        page.click('button[type="submit"]')

        # Wait for redirect
        try:
            page.wait_for_url("**/app/feed*", timeout=30000)
            print("✅ Login successful!")
        except Exception:
            print("⚠️  Redirect timeout, but continuing...")
            time.sleep(3)

        # Navigate to search page
        print("\n🔍 Exploring search page...")
        page.goto("https://mym.fans/app/search", wait_until="domcontentloaded", timeout=60000)
        time.sleep(3)

        # Try searching for a creator
        print("🔎 Testing search functionality...")
        search_input = page.query_selector('input[type="text"]')
        if search_input:
            search_input.fill("test")
            time.sleep(2)

        # Visit a creator profile
        print("\n👤 Visiting creator profile...")
        page.goto("https://mym.fans/Sweetbodymary", wait_until="domcontentloaded", timeout=60000)
        time.sleep(3)

        # Check subscriptions page
        print("\n📋 Checking subscriptions...")
        page.goto("https://mym.fans/app/feed?subscribed=1", wait_until="domcontentloaded", timeout=60000)
        time.sleep(3)

        # Save cookies
        cookies = context.cookies()
        COOKIES_FILE.write_text(json.dumps(cookies, indent=2))
        print(f"\n💾 Saved {len(cookies)} cookies to {COOKIES_FILE}")

        # Save API requests
        API_LOG_FILE.write_text(json.dumps(api_requests, indent=2))
        print(f"💾 Saved {len(api_requests)} API requests to {API_LOG_FILE}")

        # Print summary
        print("\n" + "="*80)
        print("API ENDPOINTS DISCOVERED:")
        print("="*80)

        unique_endpoints = {}
        for req in api_requests:
            endpoint = req['url'].split('?')[0]  # Remove query params
            if endpoint not in unique_endpoints:
                unique_endpoints[endpoint] = req['method']

        for endpoint, method in sorted(unique_endpoints.items()):
            print(f"{method:6} {endpoint}")

        print(f"\nTotal unique endpoints: {len(unique_endpoints)}")
        print(f"Total requests captured: {len(api_requests)}")

        # Keep browser open for inspection
        print("\n🔍 Browser will stay open for 30 seconds for inspection...")
        time.sleep(30)

        browser.close()

if __name__ == "__main__":
    import sys

    if len(sys.argv) != 3:
        print("Usage: python explore_mym_api.py <email> <password>")
        sys.exit(1)

    email = sys.argv[1]
    password = sys.argv[2]

    explore_mym_api(email, password)
