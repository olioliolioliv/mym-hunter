#!/usr/bin/env python3
"""
MYM.fans API Discovery & Reverse Engineering
Discovers internal APIs for mass creator scraping
"""

import json
import requests
from pathlib import Path
from typing import Dict, List, Any, Optional
from playwright.sync_api import sync_playwright
import time

SECRETS_DIR = Path(__file__).parent / ".secrets"
COOKIE_FILE = SECRETS_DIR / "mym_cookies.json"
API_ENDPOINTS_FILE = SECRETS_DIR / "api_endpoints.json"

class MYMAPIDiscovery:
    def __init__(self):
        self.session = self._load_session()
        self.discovered_endpoints = {}

    def _load_session(self) -> requests.Session:
        """Load authenticated session from saved cookies"""
        session = requests.Session()

        if not COOKIE_FILE.exists():
            print("⚠️  No cookies found. Run browser_login.py first")
            return session

        cookies_data = json.loads(COOKIE_FILE.read_text())
        for c in cookies_data:
            if isinstance(c, dict):
                name = c.get('name')
                value = c.get('value')
                domain = c.get('domain', '.mym.fans')
                path = c.get('path', '/')
                if name and value is not None:
                    session.cookies.set(name, value, domain=domain, path=path)

        print(f"✅ Loaded {len(cookies_data)} cookies")
        return session

    def test_endpoint(self, method: str, url: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Test an API endpoint and return response data"""
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://mym.fans/app/feed",
            "X-Requested-With": "XMLHttpRequest"
        }

        try:
            if method.upper() == "GET":
                r = self.session.get(url, headers=headers, timeout=10, **kwargs)
            elif method.upper() == "POST":
                r = self.session.post(url, headers=headers, timeout=10, **kwargs)
            else:
                return None

            print(f"{method} {url} → {r.status_code}")

            if r.status_code == 200:
                try:
                    return {
                        "url": url,
                        "method": method,
                        "status": r.status_code,
                        "data": r.json() if "application/json" in r.headers.get("Content-Type", "") else r.text[:500]
                    }
                except:
                    return {
                        "url": url,
                        "method": method,
                        "status": r.status_code,
                        "data": r.text[:500]
                    }
            return None

        except Exception as e:
            print(f"❌ Error: {e}")
            return None

    def discover_search_api(self):
        """Discover search/discovery APIs"""
        print("\n🔍 Testing Search APIs...")

        endpoints = [
            ("GET", "https://mym.fans/api/search"),
            ("GET", "https://mym.fans/api/creators/search"),
            ("GET", "https://mym.fans/api/discovery/creators"),
            ("GET", "https://mym.fans/app/api/search"),
            ("GET", "https://mym.fans/app/api/creators"),
            ("GET", "https://mym.fans/app/api/discovery"),
        ]

        for method, url in endpoints:
            result = self.test_endpoint(method, url)
            if result:
                self.discovered_endpoints['search'] = result
                return result

        return None

    def discover_creator_list_api(self):
        """Discover API for listing all creators"""
        print("\n📋 Testing Creator List APIs...")

        endpoints = [
            ("GET", "https://mym.fans/api/creators?page=1&limit=100"),
            ("GET", "https://mym.fans/api/creators/list?page=1"),
            ("GET", "https://mym.fans/app/api/creators?page=1"),
            ("GET", "https://mym.fans/app/feed/creators"),
        ]

        for method, url in endpoints:
            result = self.test_endpoint(method, url)
            if result:
                self.discovered_endpoints['creator_list'] = result
                return result

        return None

    def discover_trending_api(self):
        """Discover trending/featured creators API"""
        print("\n🔥 Testing Trending APIs...")

        endpoints = [
            ("GET", "https://mym.fans/api/trending"),
            ("GET", "https://mym.fans/api/featured"),
            ("GET", "https://mym.fans/api/discover/trending"),
            ("GET", "https://mym.fans/app/api/trending"),
        ]

        for method, url in endpoints:
            result = self.test_endpoint(method, url)
            if result:
                self.discovered_endpoints['trending'] = result
                return result

        return None

    def explore_with_browser(self):
        """Use browser automation to capture actual API calls"""
        print("\n🌐 Launching browser to capture real API calls...")

        api_calls = []

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                viewport={'width': 1920, 'height': 1080}
            )

            # Load cookies
            if COOKIE_FILE.exists():
                cookies_data = json.loads(COOKIE_FILE.read_text())
                context.add_cookies(cookies_data)

            page = context.new_page()

            # Monitor network requests
            def capture_request(request):
                url = request.url
                if 'api' in url or '/app/' in url:
                    api_calls.append({
                        "url": url,
                        "method": request.method,
                        "headers": request.headers
                    })
                    print(f"  📡 {request.method} {url}")

            page.on("request", capture_request)

            # Navigate to search page
            print("\n→ Navigating to search page...")
            page.goto("https://mym.fans/app/search", wait_until="networkidle")
            time.sleep(3)

            # Try searching
            print("\n→ Attempting search...")
            search_input = page.locator('input[type="search"], input[placeholder*="search" i], input[placeholder*="chercher" i]').first
            if search_input.is_visible():
                search_input.fill("test")
                time.sleep(2)

            # Navigate to discover/feed
            print("\n→ Checking feed/discover...")
            page.goto("https://mym.fans/app/feed", wait_until="networkidle")
            time.sleep(3)

            browser.close()

        # Save captured API calls
        api_file = SECRETS_DIR / "captured_apis.json"
        api_file.write_text(json.dumps(api_calls, indent=2))
        print(f"\n✅ Captured {len(api_calls)} API calls → {api_file}")

        return api_calls

    def analyze_graphql(self):
        """Check if MYM uses GraphQL"""
        print("\n🔍 Testing for GraphQL...")

        endpoints = [
            "https://mym.fans/graphql",
            "https://mym.fans/api/graphql",
            "https://mym.fans/app/graphql",
        ]

        for url in endpoints:
            result = self.test_endpoint("POST", url, json={"query": "{__schema{types{name}}}"})
            if result:
                print("✅ GraphQL endpoint found!")
                self.discovered_endpoints['graphql'] = result
                return result

        return None

    def save_results(self):
        """Save all discovered endpoints"""
        API_ENDPOINTS_FILE.write_text(json.dumps(self.discovered_endpoints, indent=2))
        print(f"\n💾 Saved discovered endpoints → {API_ENDPOINTS_FILE}")

    def run_full_discovery(self):
        """Run complete API discovery"""
        print("="*80)
        print("MYM.FANS API DISCOVERY")
        print("="*80)

        # Test known endpoints
        self.discover_search_api()
        self.discover_creator_list_api()
        self.discover_trending_api()
        self.analyze_graphql()

        # Browser-based discovery
        self.explore_with_browser()

        # Save results
        self.save_results()

        print("\n" + "="*80)
        print("DISCOVERY COMPLETE")
        print("="*80)
        print(f"\n📊 Discovered {len(self.discovered_endpoints)} API categories")
        for category, data in self.discovered_endpoints.items():
            print(f"  ✅ {category}: {data.get('url')}")


def main():
    discovery = MYMAPIDiscovery()
    discovery.run_full_discovery()


if __name__ == "__main__":
    main()
