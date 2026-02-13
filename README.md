# MYM.fans Hunter

Creator discovery and lead generation tool for MYM.fans platform.

## Features

- 🔐 **Browser-based authentication** with session persistence
- 🔍 **Multiple discovery methods**: Authenticated search, social media scraping, username enumeration
- 💾 **SQLite database** for creator storage and deduplication
- 📊 **Classification system**: Free, paid, and trial offer creators
- 📁 **Export functionality**: CSV, JSON formats
- 🌐 **Web dashboard** with real-time metrics (coming soon)
- 💬 **CRM integration** for outreach management (coming soon)

## Quick Start

### 1. Install Dependencies

```bash
pip3 install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

### 2. Login to MYM.fans

```bash
python3 browser_login.py --email your@email.com --password yourpassword
```

This will:
- Open a browser window
- Navigate to MYM.fans login page
- Allow you to solve reCAPTCHA manually
- Save session cookies to `.secrets/mym_cookies.json`
- Session lasts ~30 days

### 3. Test Authentication

```bash
python3 browser_login.py --test
```

### 4. Start Scraping

#### Check if a username exists:
```bash
python3 mym_scraper.py --check username123
```

#### Fetch a specific profile:
```bash
python3 mym_scraper.py --username Sweetbodymary
```

#### View statistics:
```bash
python3 mym_scraper.py --stats
```

#### Export to CSV:
```bash
python3 mym_scraper.py --export mym_creators.csv
```

## Project Structure

```
mym hunter/
├── browser_login.py          # Playwright-based authentication
├── mym_scraper.py             # Core scraping logic
├── app.py                     # Flask web dashboard (coming soon)
├── api_discovery.py           # API reverse engineering (coming soon)
├── social_aggregator.py       # Social media scraping (coming soon)
├── username_enumerator.py     # Brute force discovery (coming soon)
├── leads_db.py                # Leads database (coming soon)
├── requirements.txt           # Python dependencies
├── .secrets/                  # Cookies and databases (gitignored)
│   ├── mym_cookies.json       # Session cookies
│   ├── mym_creators.sqlite3   # Creator database
│   └── leads.sqlite3          # Leads database
└── templates/                 # Web UI templates (coming soon)
```

## Database Schema

### Creators Table

```sql
CREATE TABLE creators (
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
    classification TEXT,  -- 'free', 'paid', 'trial_offer'
    first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Planned Features

- [ ] **Web Dashboard**: Flask-based UI with real-time metrics
- [ ] **Social Media Aggregation**: Twitter/X, Linktr.ee, Beacons.ai scraping
- [ ] **Username Enumeration**: Wordlist-based brute force discovery
- [ ] **API Discovery**: Reverse engineer MYM.fans internal APIs
- [ ] **CRM Integration**: Manage outreach campaigns and messaging
- [ ] **Proxy Support**: Rotate proxies to avoid rate limiting
- [ ] **Multi-threading**: Concurrent scraping for faster discovery

## Tips

### Session Management

- Cookies last ~30 days
- Run `browser_login.py --test` to verify session is still valid
- Re-login if you get 401/403 errors

### Rate Limiting

- MYM.fans has anti-bot measures
- Use delays between requests (0.5-2s recommended)
- Consider using proxies for large-scale scraping

### Data Quality

- Profile data is extracted from HTML meta tags
- Some fields may be empty if not available
- Classification is based on available pricing information

## Troubleshooting

### Browser login fails

- Make sure you solve the reCAPTCHA manually
- Increase timeout: `--timeout 300`
- Check credentials are correct

### "No cookies found" error

- Run `browser_login.py` first to save cookies
- Check `.secrets/mym_cookies.json` exists

### Scraper returns no data

- Verify cookies are valid: `browser_login.py --test`
- Check username exists on MYM.fans
- Look for error messages in output

## Legal Notice

This tool is for educational and research purposes only. Users are responsible for:
- Complying with MYM.fans Terms of Service
- Respecting rate limits and robots.txt
- Not using data for spam or harassment
- Following applicable data protection laws (GDPR, etc.)

## License

MIT License - See LICENSE file

## Credits

Based on patterns from:
- Fanvue Hunter
- Fancentro Hunter
