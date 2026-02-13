# MYM HUNTER - COMMANDS CHEAT SHEET

Quick reference for all important commands.

---

## 🔐 AUTHENTICATION

### First Time Login
```bash
python3 browser_login.py --email olivier.david.06@gmail.com --password "gyDher-3jeggi-hogzem"
```

### Test Cookies
```bash
python3 browser_login.py --test
```

### Re-login (if cookies expired)
```bash
python3 browser_login.py --email olivier.david.06@gmail.com --password "gyDher-3jeggi-hogzem" --timeout 180
```

---

## 🚀 PRODUCTION DASHBOARD

### Start Dashboard
```bash
python3 app_production.py
```
Then open: **http://localhost:5000**

### Start with Custom Port
```bash
PORT=8080 python3 app_production.py
```

---

## 🎯 MASS SCRAPER (CLI)

### Basic Scraping
```bash
python3 mym_mass_scraper.py --wordlist wordlist.txt --workers 20
```

### With Proxies
```bash
python3 mym_mass_scraper.py --wordlist wordlist.txt --workers 20 --proxies .secrets/proxies.txt
```

### High-Speed Scraping
```bash
python3 mym_mass_scraper.py --wordlist wordlist.txt --workers 50 --proxies .secrets/proxies.txt
```

---

## 📊 DATA QUERIES

### Get All Free Creators
```bash
python3 mym_mass_scraper.py --get-free
```

### Get All Trial Creators
```bash
python3 mym_mass_scraper.py --get-trials
```

### View Stats
```bash
python3 mym_scraper.py --stats
```

### Check Single Username
```bash
python3 mym_scraper.py --check username123
```

### Fetch Single Profile
```bash
python3 mym_scraper.py --username Sweetbodymary
```

---

## 🍪 COOKIE MANAGEMENT

### Export Cookies
```bash
python3 mym_mass_scraper.py --export-cookies backup.json
```

### Import Cookies
```bash
python3 mym_mass_scraper.py --import-cookies backup.json
```

---

## 📥 EXPORT DATA

### Export to CSV
```bash
python3 mym_scraper.py --export creators.csv
```

### Export Free Creators Only
```bash
python3 mym_scraper.py --export free_creators.csv --classification free
```

### Export Trial Creators
```bash
python3 mym_scraper.py --export trial_creators.csv --classification trial_offer
```

---

## 🔍 API DISCOVERY

### Reverse Engineer APIs
```bash
python3 api_discovery.py
```

This will:
- Test common API endpoints
- Capture network requests via browser
- Save results to `.secrets/api_endpoints.json`

---

## 🗄️ DATABASE

### SQLite CLI
```bash
sqlite3 .secrets/mym_creators.sqlite3
```

### Useful SQL Queries

#### Count Creators
```sql
SELECT COUNT(*) FROM creators;
```

#### Free Creators
```sql
SELECT username, display_name, bio FROM creators
WHERE is_free_to_message = 1 OR classification = 'free';
```

#### Trial Creators
```sql
SELECT username, display_name, bio FROM creators
WHERE has_free_trial = 1 OR classification = 'trial_offer';
```

#### Recent Discoveries
```sql
SELECT username, classification, last_seen_at FROM creators
ORDER BY last_seen_at DESC LIMIT 20;
```

---

## 🚢 DEPLOYMENT

### Railway (Auto-Deploy)
```bash
git push origin main
```
Railway auto-deploys on push.

### Production Mode (Local)
```bash
gunicorn app_production:app --bind 0.0.0.0:5000 --workers 2 --threads 4 --timeout 120
```

### With Environment Variables
```bash
PORT=8080 python3 app_production.py
```

---

## 🔧 MAINTENANCE

### Update Dependencies
```bash
pip3 install -r requirements.txt --upgrade
```

### Install Playwright Browsers
```bash
playwright install chromium
```

### Check Git Status
```bash
git status
```

### Pull Latest Changes
```bash
git pull origin main
```

### View Logs (Railway)
Check your Railway dashboard for live logs.

---

## 📝 WORDLIST

### Edit Wordlist
```bash
nano wordlist.txt
```

### Create Custom Wordlist
```bash
cat > custom_wordlist.txt << 'EOF'
name1
name2
name3
EOF
```

### Use Custom Wordlist
```bash
python3 mym_mass_scraper.py --wordlist custom_wordlist.txt --workers 20
```

---

## 🌐 PROXY SETUP

### Create Proxy File
```bash
nano .secrets/proxies.txt
```

Format:
```
http://username:password@proxy1.example.com:8080
http://username:password@proxy2.example.com:8080
socks5://10.0.0.1:1080
```

### Test Proxies
```bash
curl -x http://username:password@proxy.example.com:8080 https://mym.fans
```

---

## 🐛 DEBUGGING

### Verbose Logging
```bash
python3 mym_mass_scraper.py --wordlist wordlist.txt --workers 10 2>&1 | tee scraper.log
```

### Check Running Processes
```bash
ps aux | grep python3
```

### Kill Process
```bash
pkill -f "python3 app_production.py"
```

---

## 🔄 WORKFLOW

### Full Scraping Session
```bash
# 1. Login
python3 browser_login.py --email olivier.david.06@gmail.com --password "gyDher-3jeggi-hogzem"

# 2. Start dashboard
python3 app_production.py &

# 3. Open browser
open http://localhost:5000

# 4. Click "Start Scraping" in UI

# 5. Wait for completion

# 6. Export CSV
curl http://localhost:5000/api/export -o creators.csv
```

---

## 📊 API ENDPOINTS

### Get Stats
```bash
curl http://localhost:5000/api/stats | python3 -m json.tool
```

### Get Creators
```bash
curl "http://localhost:5000/api/creators?limit=10" | python3 -m json.tool
```

### Start Scraping (API)
```bash
curl -X POST http://localhost:5000/api/start \
  -H "Content-Type: application/json" \
  -d '{"workers": 20, "max_usernames": 10000}'
```

### Stop Scraping (API)
```bash
curl -X POST http://localhost:5000/api/stop
```

### Health Check
```bash
curl http://localhost:5000/health
```

---

## 🎯 QUICK TASKS

### Scrape 1000 Creators Fast
```bash
python3 mym_mass_scraper.py --wordlist wordlist.txt --workers 30
```

### Find Free Creators
```bash
python3 mym_mass_scraper.py --get-free > free_creators.txt
```

### Export Everything
```bash
python3 mym_scraper.py --export all_creators.csv
```

### Backup Database
```bash
cp .secrets/mym_creators.sqlite3 backup_$(date +%Y%m%d).sqlite3
```

---

## 💡 PRO TIPS

### Run in Background
```bash
nohup python3 app_production.py > dashboard.log 2>&1 &
```

### Monitor Logs
```bash
tail -f dashboard.log
```

### Auto-Restart on Crash
```bash
while true; do
    python3 app_production.py
    echo "Crashed! Restarting in 5 seconds..."
    sleep 5
done
```

### Scheduled Scraping (Cron)
```bash
# Add to crontab
0 */6 * * * cd /path/to/mym-hunter && python3 mym_mass_scraper.py --wordlist wordlist.txt --workers 20
```

---

**Use this cheatsheet to quickly execute any command you need!**

*Last updated: 2026-02-13*
