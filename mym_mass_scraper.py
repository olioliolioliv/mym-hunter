#!/usr/bin/env python3
"""
MYM.fans MASS SCRAPER - Production Grade
- Proxy rotation with health checks
- Debug window with real-time stats
- Cookie manager with import/export
- Mass discovery using multiple methods
- Filtering for free-to-message and trial creators
"""

import json
import sqlite3
import time
import threading
import requests
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import deque
import sys

# Configuration
MYM_BASE = "https://mym.fans"
SECRETS_DIR = Path(__file__).parent / ".secrets"
COOKIE_FILE = SECRETS_DIR / "mym_cookies.json"
DB_FILE = SECRETS_DIR / "mym_creators.sqlite3"
PROXY_FILE = SECRETS_DIR / "proxies.txt"

class ProxyRotator:
    """Intelligent proxy rotation with health checks"""

    def __init__(self, proxy_file: Optional[Path] = None):
        self.proxies = []
        self.proxy_stats = {}
        self.current_index = 0
        self.lock = threading.Lock()

        if proxy_file and proxy_file.exists():
            self.load_proxies(proxy_file)

    def load_proxies(self, proxy_file: Path):
        """Load proxies from file (format: protocol://user:pass@host:port)"""
        with open(proxy_file, 'r') as f:
            self.proxies = [line.strip() for line in f if line.strip() and not line.startswith('#')]

        for proxy in self.proxies:
            self.proxy_stats[proxy] = {
                'requests': 0,
                'successes': 0,
                'failures': 0,
                'avg_response_time': 0,
                'last_used': None,
                'health': 'unknown'
            }

        print(f"✅ Loaded {len(self.proxies)} proxies")

    def get_next_proxy(self) -> Optional[Dict[str, str]]:
        """Get next healthy proxy in rotation"""
        with self.lock:
            if not self.proxies:
                return None

            # Skip unhealthy proxies
            max_attempts = len(self.proxies)
            attempts = 0

            while attempts < max_attempts:
                proxy_url = self.proxies[self.current_index]
                stats = self.proxy_stats[proxy_url]

                # Skip if proxy is marked as down
                if stats['health'] == 'down':
                    self.current_index = (self.current_index + 1) % len(self.proxies)
                    attempts += 1
                    continue

                # Use this proxy
                self.current_index = (self.current_index + 1) % len(self.proxies)
                stats['last_used'] = datetime.now()

                return {
                    "http": proxy_url,
                    "https": proxy_url
                }

            # All proxies are down
            return None

    def report_success(self, proxy_dict: Dict[str, str], response_time: float):
        """Report successful request"""
        if not proxy_dict:
            return

        proxy_url = proxy_dict.get('http')
        if proxy_url in self.proxy_stats:
            stats = self.proxy_stats[proxy_url]
            stats['requests'] += 1
            stats['successes'] += 1
            stats['health'] = 'healthy'

            # Update avg response time
            total = stats['avg_response_time'] * (stats['successes'] - 1) + response_time
            stats['avg_response_time'] = total / stats['successes']

    def report_failure(self, proxy_dict: Dict[str, str]):
        """Report failed request"""
        if not proxy_dict:
            return

        proxy_url = proxy_dict.get('http')
        if proxy_url in self.proxy_stats:
            stats = self.proxy_stats[proxy_url]
            stats['requests'] += 1
            stats['failures'] += 1

            # Mark as down if too many failures
            if stats['failures'] > 10 and stats['failures'] / max(stats['requests'], 1) > 0.8:
                stats['health'] = 'down'

    def get_stats(self) -> List[Dict[str, Any]]:
        """Get proxy statistics"""
        return [
            {
                'proxy': proxy,
                **stats,
                'success_rate': stats['successes'] / max(stats['requests'], 1) * 100
            }
            for proxy, stats in self.proxy_stats.items()
        ]


class DebugWindow:
    """Real-time debug window with stats"""

    def __init__(self):
        self.stats = {
            'total_checked': 0,
            'found': 0,
            'errors': 0,
            'rate': 0,
            'proxies_active': 0,
            'proxies_down': 0,
            'free_creators': 0,
            'trial_creators': 0,
            'paid_creators': 0,
            'last_username': '',
            'running': False,
            'start_time': None
        }
        self.recent_logs = deque(maxlen=100)
        self.lock = threading.Lock()

    def log(self, message: str, level: str = "INFO"):
        """Add log message"""
        with self.lock:
            timestamp = datetime.now().strftime("%H:%M:%S")
            log_entry = f"[{timestamp}] [{level}] {message}"
            self.recent_logs.append(log_entry)
            print(log_entry)

    def update_stats(self, **kwargs):
        """Update statistics"""
        with self.lock:
            self.stats.update(kwargs)

            # Calculate rate
            if self.stats['start_time']:
                elapsed = (datetime.now() - self.stats['start_time']).total_seconds()
                if elapsed > 0:
                    self.stats['rate'] = self.stats['total_checked'] / elapsed * 60  # per minute

    def increment(self, key: str, amount: int = 1):
        """Increment a counter"""
        with self.lock:
            self.stats[key] = self.stats.get(key, 0) + amount

    def print_dashboard(self):
        """Print beautiful dashboard"""
        with self.lock:
            # Clear screen (works on Unix/Linux/Mac)
            print("\033[2J\033[H")

            print("="*80)
            print(" "*25 + "MYM.FANS MASS SCRAPER v2.0")
            print("="*80)

            # Stats
            print(f"\n📊 STATISTICS")
            print(f"  Total Checked: {self.stats['total_checked']:,}")
            print(f"  Found: {self.stats['found']:,}")
            print(f"  Errors: {self.stats['errors']:,}")
            print(f"  Rate: {self.stats['rate']:.1f} checks/min")

            print(f"\n🎯 DISCOVERY")
            print(f"  Free Creators: {self.stats['free_creators']:,}")
            print(f"  Trial Creators: {self.stats['trial_creators']:,}")
            print(f"  Paid Creators: {self.stats['paid_creators']:,}")

            print(f"\n🌐 PROXIES")
            print(f"  Active: {self.stats['proxies_active']}")
            print(f"  Down: {self.stats['proxies_down']}")

            print(f"\n⚡ STATUS")
            print(f"  Running: {'✅ YES' if self.stats['running'] else '❌ NO'}")
            print(f"  Last Check: {self.stats['last_username']}")

            # Recent logs
            print(f"\n📜 RECENT LOGS (last 10)")
            print("-"*80)
            for log in list(self.recent_logs)[-10:]:
                print(f"  {log}")

            print("\n" + "="*80)

    def get_stats_dict(self) -> Dict[str, Any]:
        """Get stats as dictionary"""
        with self.lock:
            return self.stats.copy()


class MYMMassScraper:
    """Production-grade mass scraper for MYM.fans"""

    def __init__(self, proxy_file: Optional[Path] = None, max_workers: int = 10):
        self.proxy_rotator = ProxyRotator(proxy_file)
        self.debug = DebugWindow()
        self.max_workers = max_workers
        self.session = self._load_session()
        self.db_conn = self._init_database()
        self.running = False

    def _load_session(self) -> requests.Session:
        """Load authenticated session from cookies"""
        session = requests.Session()

        if not COOKIE_FILE.exists():
            self.debug.log("⚠️  No cookies found", "WARNING")
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

        self.debug.log(f"✅ Loaded {len(cookies_data)} cookies", "SUCCESS")
        return session

    def _init_database(self) -> sqlite3.Connection:
        """Initialize database"""
        SECRETS_DIR.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.Connection(DB_FILE)
        conn.row_factory = sqlite3.Row

        conn.execute("""
            CREATE TABLE IF NOT EXISTS creators (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                display_name TEXT,
                profile_url TEXT,
                avatar_url TEXT,
                bio TEXT,
                location TEXT,
                subscriber_count INTEGER DEFAULT 0,
                post_count INTEGER DEFAULT 0,
                is_verified BOOLEAN DEFAULT 0,
                subscription_price DECIMAL(10,2),
                has_free_trial BOOLEAN DEFAULT 0,
                trial_days INTEGER DEFAULT 0,
                is_free_to_message BOOLEAN DEFAULT 0,
                classification TEXT,
                first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.execute("CREATE INDEX IF NOT EXISTS idx_username ON creators(username)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_classification ON creators(classification)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_free_to_message ON creators(is_free_to_message)")

        conn.commit()
        return conn

    def export_cookies(self, output_file: Path):
        """Export cookies to file"""
        if COOKIE_FILE.exists():
            import shutil
            shutil.copy(COOKIE_FILE, output_file)
            self.debug.log(f"✅ Exported cookies → {output_file}", "SUCCESS")

    def import_cookies(self, input_file: Path):
        """Import cookies from file"""
        if input_file.exists():
            import shutil
            shutil.copy(input_file, COOKIE_FILE)
            self.session = self._load_session()
            self.debug.log(f"✅ Imported cookies from {input_file}", "SUCCESS")

    def check_username_fast(self, username: str, use_proxy: bool = True) -> bool:
        """Fast HEAD request to check username exists"""
        username = username.lstrip('@').strip()
        url = f"{MYM_BASE}/{username}"

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }

        proxies = self.proxy_rotator.get_next_proxy() if use_proxy else None
        start_time = time.time()

        try:
            r = self.session.head(url, headers=headers, proxies=proxies, timeout=10, allow_redirects=True)
            response_time = time.time() - start_time

            if proxies:
                self.proxy_rotator.report_success(proxies, response_time)

            return r.status_code == 200

        except Exception as e:
            if proxies:
                self.proxy_rotator.report_failure(proxies)
            return False

    def fetch_profile_detailed(self, username: str) -> Optional[Dict[str, Any]]:
        """Fetch detailed profile data"""
        username = username.lstrip('@').strip()
        url = f"{MYM_BASE}/{username}"

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }

        proxies = self.proxy_rotator.get_next_proxy()

        try:
            r = self.session.get(url, headers=headers, proxies=proxies, timeout=15)

            if r.status_code == 404:
                return None

            r.raise_for_status()

            soup = BeautifulSoup(r.text, 'html.parser')

            profile_data = {
                'username': username,
                'profile_url': url,
                'exists': True
            }

            # Extract meta tags
            og_title = soup.find('meta', property='og:title')
            if og_title:
                profile_data['display_name'] = og_title.get('content', username)

            og_desc = soup.find('meta', property='og:description')
            if og_desc:
                profile_data['bio'] = og_desc.get('content', '')

            og_image = soup.find('meta', property='og:image')
            if og_image:
                profile_data['avatar_url'] = og_image.get('content', '')

            # Look for pricing info in HTML
            # Check if "free" or "gratuit" appears
            html_lower = r.text.lower()
            if 'free trial' in html_lower or 'essai gratuit' in html_lower:
                profile_data['has_free_trial'] = True
                profile_data['classification'] = 'trial_offer'
            elif 'free' in html_lower or 'gratuit' in html_lower:
                profile_data['is_free_to_message'] = True
                profile_data['classification'] = 'free'
            else:
                profile_data['classification'] = 'paid'

            return profile_data

        except Exception as e:
            self.debug.log(f"❌ Error fetching {username}: {e}", "ERROR")
            return None

    def save_creator(self, creator_data: Dict[str, Any]) -> bool:
        """Save creator to database"""
        try:
            username = creator_data.get('username', '').lstrip('@')
            if not username:
                return False

            classification = creator_data.get('classification', 'unknown')
            is_free = creator_data.get('is_free_to_message', False)

            self.db_conn.execute("""
                INSERT INTO creators (
                    username, display_name, profile_url, avatar_url, bio, location,
                    subscriber_count, post_count, is_verified, subscription_price,
                    has_free_trial, trial_days, is_free_to_message, classification,
                    last_seen_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(username) DO UPDATE SET
                    display_name = excluded.display_name,
                    profile_url = excluded.profile_url,
                    avatar_url = excluded.avatar_url,
                    bio = excluded.bio,
                    location = excluded.location,
                    subscriber_count = excluded.subscriber_count,
                    post_count = excluded.post_count,
                    is_verified = excluded.is_verified,
                    subscription_price = excluded.subscription_price,
                    has_free_trial = excluded.has_free_trial,
                    trial_days = excluded.trial_days,
                    is_free_to_message = excluded.is_free_to_message,
                    classification = excluded.classification,
                    last_seen_at = CURRENT_TIMESTAMP
            """, (
                username,
                creator_data.get('display_name', username),
                creator_data.get('profile_url', f"{MYM_BASE}/{username}"),
                creator_data.get('avatar_url'),
                creator_data.get('bio'),
                creator_data.get('location'),
                creator_data.get('subscriber_count', 0),
                creator_data.get('post_count', 0),
                creator_data.get('is_verified', False),
                creator_data.get('subscription_price'),
                creator_data.get('has_free_trial', False),
                creator_data.get('trial_days', 0),
                is_free,
                classification
            ))

            self.db_conn.commit()

            # Update debug stats
            if classification == 'free':
                self.debug.increment('free_creators')
            elif classification == 'trial_offer':
                self.debug.increment('trial_creators')
            elif classification == 'paid':
                self.debug.increment('paid_creators')

            return True

        except Exception as e:
            self.debug.log(f"❌ Error saving {creator_data.get('username')}: {e}", "ERROR")
            return False

    def enumerate_usernames(self, wordlist: List[str], max_suffix: int = 999):
        """Mass username enumeration"""
        self.debug.log("🚀 Starting username enumeration", "INFO")
        self.debug.update_stats(running=True, start_time=datetime.now())

        username_candidates = []

        # Generate candidates
        for word in wordlist:
            # Base username
            username_candidates.append(word)

            # With numbers
            for i in range(1, max_suffix + 1):
                username_candidates.append(f"{word}{i}")
                username_candidates.append(f"{word}_{i}")
                username_candidates.append(f"{word}-{i}")

        self.debug.log(f"📋 Generated {len(username_candidates)} username candidates", "INFO")

        # Multi-threaded checking
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_username = {
                executor.submit(self.check_and_fetch, username): username
                for username in username_candidates
            }

            for future in as_completed(future_to_username):
                username = future_to_username[future]
                try:
                    future.result()
                except Exception as e:
                    self.debug.log(f"❌ Error processing {username}: {e}", "ERROR")
                    self.debug.increment('errors')

        self.debug.update_stats(running=False)
        self.debug.log("✅ Username enumeration complete", "SUCCESS")

    def check_and_fetch(self, username: str):
        """Check if username exists and fetch if it does"""
        self.debug.update_stats(last_username=username)
        self.debug.increment('total_checked')

        # Quick check first
        if self.check_username_fast(username):
            self.debug.log(f"✅ Found: @{username}", "SUCCESS")
            self.debug.increment('found')

            # Fetch detailed profile
            profile = self.fetch_profile_detailed(username)
            if profile:
                self.save_creator(profile)

        # Update proxy stats in debug
        proxy_stats = self.proxy_rotator.get_stats()
        active = sum(1 for p in proxy_stats if p['health'] == 'healthy')
        down = sum(1 for p in proxy_stats if p['health'] == 'down')
        self.debug.update_stats(proxies_active=active, proxies_down=down)

    def get_free_creators(self) -> List[Dict[str, Any]]:
        """Get all free-to-message creators"""
        cursor = self.db_conn.execute("""
            SELECT * FROM creators
            WHERE is_free_to_message = 1 OR classification = 'free'
            ORDER BY last_seen_at DESC
        """)
        return [dict(row) for row in cursor.fetchall()]

    def get_trial_creators(self) -> List[Dict[str, Any]]:
        """Get all creators with free trials"""
        cursor = self.db_conn.execute("""
            SELECT * FROM creators
            WHERE has_free_trial = 1 OR classification = 'trial_offer'
            ORDER BY last_seen_at DESC
        """)
        return [dict(row) for row in cursor.fetchall()]

    def close(self):
        """Cleanup"""
        if self.db_conn:
            self.db_conn.close()


def main():
    import argparse

    parser = argparse.ArgumentParser(description="MYM.fans Mass Scraper")
    parser.add_argument("--proxies", help="Path to proxy file")
    parser.add_argument("--workers", type=int, default=10, help="Number of concurrent workers")
    parser.add_argument("--wordlist", help="Path to wordlist for enumeration")
    parser.add_argument("--export-cookies", help="Export cookies to file")
    parser.add_argument("--import-cookies", help="Import cookies from file")
    parser.add_argument("--get-free", action="store_true", help="Get all free creators")
    parser.add_argument("--get-trials", action="store_true", help="Get all trial creators")

    args = parser.parse_args()

    # Initialize scraper
    proxy_file = Path(args.proxies) if args.proxies else None
    scraper = MYMMassScraper(proxy_file=proxy_file, max_workers=args.workers)

    try:
        if args.export_cookies:
            scraper.export_cookies(Path(args.export_cookies))

        elif args.import_cookies:
            scraper.import_cookies(Path(args.import_cookies))

        elif args.get_free:
            free_creators = scraper.get_free_creators()
            print(f"\n✅ Found {len(free_creators)} free creators:")
            for c in free_creators:
                print(f"  @{c['username']} - {c['display_name']}")

        elif args.get_trials:
            trial_creators = scraper.get_trial_creators()
            print(f"\n✅ Found {len(trial_creators)} trial creators:")
            for c in trial_creators:
                print(f"  @{c['username']} - {c['display_name']}")

        elif args.wordlist:
            # Load wordlist
            with open(args.wordlist, 'r') as f:
                wordlist = [line.strip() for line in f if line.strip()]

            # Run enumeration
            scraper.enumerate_usernames(wordlist)

        else:
            parser.print_help()

    finally:
        scraper.close()


if __name__ == "__main__":
    main()
