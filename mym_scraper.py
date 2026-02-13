#!/usr/bin/env python3
"""
MYM.fans Creator Scraper
Discovers creators from MYM.fans using authenticated session
"""

import json
import sqlite3
import time
import re
import requests
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
from bs4 import BeautifulSoup

# Configuration
MYM_BASE = "https://mym.fans"
SECRETS_DIR = Path(__file__).parent / ".secrets"
COOKIE_FILE = SECRETS_DIR / "mym_cookies.json"
DB_FILE = SECRETS_DIR / "mym_creators.sqlite3"

# Regex for extracting MYM profiles
MYM_PATTERN = re.compile(r"https?://(?:www\.)?mym\.fans/(@?[A-Za-z0-9_.-]{2,50})")


class MYMScraper:
    def __init__(self, proxies=None):
        self.proxies = proxies or []
        self.proxy_index = 0
        self.session = self._load_session()
        self.db_conn = self._init_database()

    def _load_session(self) -> requests.Session:
        """Load authenticated session from saved cookies"""
        session = requests.Session()

        if not COOKIE_FILE.exists():
            print(f"⚠️  No cookies found at {COOKIE_FILE}")
            print("Run browser_login.py first to save MYM cookies")
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

        print(f"✅ Loaded {len(cookies_data)} cookies from {COOKIE_FILE}")
        return session

    def _init_database(self) -> sqlite3.Connection:
        """Initialize SQLite database for storing creators"""
        SECRETS_DIR.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.Connection(DB_FILE)
        conn.row_factory = sqlite3.Row

        # Create creators table
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

        # Create indices for fast lookups
        conn.execute("CREATE INDEX IF NOT EXISTS idx_username ON creators(username)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_classification ON creators(classification)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_free_to_message ON creators(is_free_to_message)")

        conn.commit()
        print(f"✅ Database initialized at {DB_FILE}")
        return conn

    def _get_next_proxy(self) -> Optional[Dict[str, str]]:
        """Get next proxy from rotation"""
        if not self.proxies:
            return None

        proxy_url = self.proxies[self.proxy_index]
        self.proxy_index = (self.proxy_index + 1) % len(self.proxies)

        return {
            "http": proxy_url,
            "https": proxy_url
        }

    def fetch_profile(self, username: str) -> Optional[Dict[str, Any]]:
        """Fetch a creator profile from MYM.fans"""
        # Clean username
        username = username.lstrip('@').strip()

        url = f"{MYM_BASE}/{username}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }

        proxies = self._get_next_proxy()

        try:
            r = self.session.get(url, headers=headers, proxies=proxies, timeout=15)

            # Check if profile exists
            if r.status_code == 404:
                return None

            r.raise_for_status()

            # Parse HTML to extract profile data
            soup = BeautifulSoup(r.text, 'html.parser')

            # Extract profile data (patterns to be refined based on actual HTML)
            profile_data = {
                'username': username,
                'profile_url': url,
                'exists': True
            }

            # Try to extract data from meta tags or structured data
            # Display name
            og_title = soup.find('meta', property='og:title')
            if og_title:
                profile_data['display_name'] = og_title.get('content', username)

            # Description/Bio
            og_desc = soup.find('meta', property='og:description')
            if og_desc:
                profile_data['bio'] = og_desc.get('content', '')

            # Avatar
            og_image = soup.find('meta', property='og:image')
            if og_image:
                profile_data['avatar_url'] = og_image.get('content', '')

            # Look for JSON-LD structured data
            json_ld = soup.find('script', type='application/ld+json')
            if json_ld:
                try:
                    ld_data = json.loads(json_ld.string)
                    if isinstance(ld_data, dict):
                        profile_data['structured_data'] = ld_data
                except:
                    pass

            return profile_data

        except requests.exceptions.RequestException as e:
            print(f"❌ Error fetching profile {username}: {e}")
            return None

    def save_creator(self, creator_data: Dict[str, Any]) -> bool:
        """Save or update a creator in the database"""
        try:
            username = creator_data.get('username', '').lstrip('@')
            if not username:
                return False

            # Classification logic (to be refined based on actual data)
            classification = creator_data.get('classification', 'unknown')
            is_free = classification == 'free'

            # Insert or update creator
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
            return True

        except Exception as e:
            print(f"❌ Error saving creator {creator_data.get('username')}: {e}")
            return False

    def check_username_exists(self, username: str) -> bool:
        """Quickly check if a username exists (HTTP HEAD request)"""
        username = username.lstrip('@').strip()
        url = f"{MYM_BASE}/{username}"

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }

        proxies = self._get_next_proxy()

        try:
            r = self.session.head(url, headers=headers, proxies=proxies, timeout=10, allow_redirects=True)
            return r.status_code == 200

        except:
            return False

    def get_creators(self, classification: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get creators from database with optional filtering"""
        if classification:
            cursor = self.db_conn.execute("""
                SELECT * FROM creators
                WHERE classification = ?
                ORDER BY last_seen_at DESC
                LIMIT ?
            """, (classification, limit))
        else:
            cursor = self.db_conn.execute("""
                SELECT * FROM creators
                ORDER BY last_seen_at DESC
                LIMIT ?
            """, (limit,))

        return [dict(row) for row in cursor.fetchall()]

    def get_stats(self) -> Dict[str, Any]:
        """Get scraper statistics"""
        cursor = self.db_conn.execute("""
            SELECT
                COUNT(*) as total_creators,
                SUM(CASE WHEN classification = 'free' THEN 1 ELSE 0 END) as free_creators,
                SUM(CASE WHEN classification = 'paid' THEN 1 ELSE 0 END) as paid_creators,
                SUM(CASE WHEN classification = 'trial_offer' THEN 1 ELSE 0 END) as trial_creators,
                SUM(CASE WHEN has_free_trial = 1 THEN 1 ELSE 0 END) as creators_with_trials,
                MAX(last_seen_at) as last_scraped
            FROM creators
        """)

        row = cursor.fetchone()
        return dict(row) if row else {}

    def export_csv(self, filename: str = "mym_creators.csv", classification: Optional[str] = None):
        """Export creators to CSV"""
        import csv

        creators = self.get_creators(classification=classification, limit=100000)

        output_file = Path(filename)
        with output_file.open('w', newline='', encoding='utf-8') as f:
            if creators:
                writer = csv.DictWriter(f, fieldnames=creators[0].keys())
                writer.writeheader()
                writer.writerows(creators)

        print(f"✅ Exported {len(creators)} creators to {output_file}")
        return output_file

    def close(self):
        """Close database connection"""
        if self.db_conn:
            self.db_conn.close()


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="MYM.fans Creator Scraper")
    parser.add_argument("--username", "-u", help="Fetch a specific creator profile")
    parser.add_argument("--check", "-c", help="Check if username exists (quick)")
    parser.add_argument("--stats", action="store_true", help="Show scraper statistics")
    parser.add_argument("--export", help="Export creators to CSV file")
    parser.add_argument("--classification", choices=['free', 'paid', 'trial_offer'], help="Filter by classification")

    args = parser.parse_args()

    scraper = MYMScraper()

    try:
        if args.stats:
            # Show statistics
            stats = scraper.get_stats()
            print("\n" + "="*80)
            print("MYM SCRAPER STATISTICS")
            print("="*80)
            print(f"Total creators: {stats.get('total_creators', 0)}")
            print(f"Free creators: {stats.get('free_creators', 0)}")
            print(f"Paid creators: {stats.get('paid_creators', 0)}")
            print(f"Trial offer creators: {stats.get('trial_creators', 0)}")
            print(f"Creators with trials: {stats.get('creators_with_trials', 0)}")
            print(f"Last scraped: {stats.get('last_scraped', 'Never')}")
            print()

        elif args.check:
            # Quick username check
            print(f"\n🔍 Checking if @{args.check} exists...")
            exists = scraper.check_username_exists(args.check)
            if exists:
                print(f"✅ Username @{args.check} exists on MYM.fans")
                print(f"   Profile: {MYM_BASE}/{args.check}")
            else:
                print(f"❌ Username @{args.check} does not exist")

        elif args.username:
            # Fetch specific profile
            print(f"\n📥 Fetching profile for @{args.username}...")
            profile = scraper.fetch_profile(args.username)

            if profile:
                print("\n✅ Profile found:")
                print(json.dumps(profile, indent=2))

                # Save to database
                if scraper.save_creator(profile):
                    print("\n💾 Saved to database")
            else:
                print(f"\n❌ Profile not found or error occurred")

        elif args.export:
            # Export to CSV
            scraper.export_csv(args.export, classification=args.classification)

        else:
            # Show help
            parser.print_help()

    finally:
        scraper.close()


if __name__ == "__main__":
    main()
