#!/usr/bin/env python3
"""
MYM HUNTER - FINAL PRODUCTION DASHBOARD
Complete system with:
- Live database updates with filters (Free/Paid/Trial/All)
- Proxy management (add/remove/monitor)
- Start/Stop controls (simplified)
- Debug window for bug tracking
- Easy CSV export
- Real-time speed graph
- Progress tracking
"""

import os
import json
import sqlite3
import threading
import time
from pathlib import Path
from datetime import datetime
from collections import deque
from flask import Flask, render_template_string, jsonify, request, send_file
from flask_socketio import SocketIO, emit
import tempfile
import requests
from bs4 import BeautifulSoup

# Global state
state = {
    'running': False,
    'total_checked': 0,
    'total_found': 0,
    'free_count': 0,
    'paid_count': 0,
    'trial_count': 0,
    'errors': 0,
    'start_time': None,
    'current_username': '',
    'speed_history': deque(maxlen=60),
    'proxies': [],
    'proxy_index': 0,
    'wordlist': [],
    'current_index': 0
}

lock = threading.Lock()
scraper_thread = None

app = Flask(__name__)
app.config['SECRET_KEY'] = 'mym-final-2024'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

PORT = int(os.getenv("PORT", 5000))
SECRETS_DIR = Path(__file__).parent / ".secrets"
DB_FILE = SECRETS_DIR / "mym_creators.sqlite3"
COOKIE_FILE = SECRETS_DIR / "mym_cookies.json"
PROXY_FILE = SECRETS_DIR / "proxies.txt"

def load_proxies():
    """Load proxies from file"""
    if PROXY_FILE.exists():
        with open(PROXY_FILE, 'r') as f:
            proxies = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            with lock:
                state['proxies'] = [{'url': p, 'requests': 0, 'successes': 0, 'health': 'unknown'} for p in proxies]
            socketio.emit('log', {'timestamp': datetime.now().strftime("%H:%M:%S"), 'level': 'SUCCESS', 'message': f'Loaded {len(proxies)} proxies'})

def get_next_proxy():
    """Get next proxy in rotation"""
    with lock:
        if not state['proxies']:
            return None
        proxy = state['proxies'][state['proxy_index']]
        state['proxy_index'] = (state['proxy_index'] + 1) % len(state['proxies'])
        return proxy

# HTML Template
HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>MYM Hunter - Final</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
:root{--primary:#ff6b9d;--secondary:#c471ed;--accent:#12d8fa;--success:#10b981;--warning:#f59e0b;--danger:#ef4444;--dark:#0f0f1e;--glass:rgba(255,255,255,0.08);--border:rgba(255,255,255,0.15)}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Inter',sans-serif;background:var(--dark);color:#fff;min-height:100vh}
.bg{position:fixed;top:0;left:0;width:100%;height:100%;z-index:-1;overflow:hidden}
.orb{position:absolute;border-radius:50%;filter:blur(80px);opacity:0.4;animation:float 20s infinite ease-in-out}
.orb1{width:400px;height:400px;background:radial-gradient(circle,var(--primary),transparent);top:-100px;left:-100px}
.orb2{width:500px;height:500px;background:radial-gradient(circle,var(--secondary),transparent);bottom:-150px;right:-150px;animation-delay:-5s}
.orb3{width:350px;height:350px;background:radial-gradient(circle,var(--accent),transparent);top:50%;left:50%;animation-delay:-10s}
@keyframes float{0%,100%{transform:translate(0,0)}33%{transform:translate(150px,-100px)}66%{transform:translate(-100px,100px)}}
header{background:rgba(15,15,30,0.8);backdrop-filter:blur(20px);border-bottom:1px solid var(--border);padding:1.5rem 2rem;position:sticky;top:0;z-index:100}
.header{max-width:1600px;margin:0 auto;display:flex;justify-content:space-between;align-items:center}
.logo{font-size:1.5rem;font-weight:800;background:linear-gradient(135deg,var(--primary),var(--secondary));-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.status{padding:0.5rem 1rem;border-radius:20px;font-size:0.875rem;font-weight:600;display:inline-flex;align-items:center;gap:0.5rem}
.status-running{background:rgba(16,185,129,0.2);color:var(--success)}
.status-stopped{background:rgba(239,68,68,0.2);color:var(--danger)}
.pulse{width:8px;height:8px;border-radius:50%;background:currentColor;animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:0.5}}
.container{max-width:1600px;margin:0 auto;padding:2rem}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:1rem;margin-bottom:2rem}
.card{background:var(--glass);backdrop-filter:blur(10px);border:1px solid var(--border);border-radius:20px;padding:1.5rem;transition:all 0.3s}
.card:hover{transform:translateY(-5px);box-shadow:0 20px 40px rgba(0,0,0,0.3)}
.label{font-size:0.75rem;color:rgba(255,255,255,0.6);text-transform:uppercase;margin-bottom:0.5rem}
.value{font-size:2rem;font-weight:700;background:linear-gradient(135deg,#fff,rgba(255,255,255,0.6));-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.controls{background:var(--glass);backdrop-filter:blur(10px);border:1px solid var(--border);border-radius:20px;padding:2rem;margin-bottom:2rem}
.btn-group{display:grid;grid-template-columns:1fr 1fr auto;gap:1rem;margin-bottom:1.5rem}
.btn{padding:1rem;border-radius:12px;border:none;font-size:0.875rem;font-weight:600;cursor:pointer;transition:all 0.2s;display:flex;align-items:center;justify-content:center;gap:0.5rem}
.btn:disabled{opacity:0.5;cursor:not-allowed}
.btn-success{background:linear-gradient(135deg,#10b981,#059669);color:white}
.btn-danger{background:linear-gradient(135deg,#ef4444,#dc2626);color:white}
.btn-secondary{background:rgba(255,255,255,0.1);color:white;border:1px solid rgba(255,255,255,0.2)}
.btn:not(:disabled):hover{transform:translateY(-2px);box-shadow:0 10px 25px rgba(0,0,0,0.3)}
.tabs{display:flex;gap:1rem;margin-bottom:1.5rem;border-bottom:2px solid rgba(255,255,255,0.1)}
.tab{padding:0.75rem 1.5rem;cursor:pointer;border-bottom:2px solid transparent;transition:all 0.2s}
.tab:hover{background:rgba(255,255,255,0.05)}
.tab.active{border-bottom-color:var(--primary);color:var(--primary)}
.table{width:100%;border-collapse:collapse}
.table th{text-align:left;padding:1rem;font-weight:600;color:rgba(255,255,255,0.7);border-bottom:2px solid rgba(255,255,255,0.1)}
.table td{padding:1rem;border-bottom:1px solid rgba(255,255,255,0.05)}
.table tr:hover{background:rgba(255,255,255,0.03)}
.badge{padding:0.25rem 0.75rem;border-radius:12px;font-size:0.75rem;font-weight:600}
.badge-free{background:rgba(16,185,129,0.2);color:var(--success)}
.badge-trial{background:rgba(245,158,11,0.2);color:var(--warning)}
.badge-paid{background:rgba(239,68,68,0.2);color:var(--danger)}
.badge-unknown{background:rgba(100,100,100,0.2);color:#999}
.chart-container{background:rgba(26,26,46,1);border:1px solid var(--border);border-radius:20px;padding:1.5rem;margin-bottom:2rem}
.chart-title{font-size:1.25rem;font-weight:600;margin-bottom:1rem;color:var(--accent)}
canvas{max-height:250px}
.logs{background:rgba(26,26,46,1);border:1px solid var(--border);border-radius:20px;padding:1.5rem;max-height:300px;overflow-y:auto;font-family:'Courier New',monospace;font-size:0.8rem}
.log{padding:0.4rem 0;border-bottom:1px solid rgba(255,255,255,0.05)}
.log-info{color:#60a5fa}
.log-success{color:#10b981}
.log-warning{color:#f59e0b}
.log-error{color:#ef4444}
.proxy-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:0.75rem}
.proxy-item{background:rgba(255,255,255,0.05);border:1px solid var(--border);border-radius:8px;padding:0.75rem;font-size:0.75rem}
.proxy-healthy{border-left:4px solid var(--success)}
.proxy-down{border-left:4px solid var(--danger)}
.progress-bar{background:rgba(255,255,255,0.05);border-radius:10px;height:30px;overflow:hidden;margin:1rem 0}
.progress-fill{height:100%;background:linear-gradient(90deg,var(--primary),var(--secondary));transition:width 0.3s;display:flex;align-items:center;justify-content:center;font-size:0.75rem;font-weight:600}
input{background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.1);border-radius:8px;padding:0.75rem;color:white;font-size:0.875rem;width:100%}
</style>
</head>
<body>
<div class="bg"><div class="orb orb1"></div><div class="orb orb2"></div><div class="orb orb3"></div></div>
<header><div class="header"><div class="logo">🎯 MYM HUNTER</div><div class="status" id="status"><span class="pulse"></span><span id="status-text">STOPPED</span></div></div></header>
<div class="container">
<div class="grid">
<div class="card"><div class="label">Total Checked</div><div class="value" id="total-checked">0</div></div>
<div class="card"><div class="label">Found</div><div class="value" id="total-found">0</div></div>
<div class="card"><div class="label">Free</div><div class="value" id="free-count">0</div></div>
<div class="card"><div class="label">Paid</div><div class="value" id="paid-count">0</div></div>
<div class="card"><div class="label">Trial</div><div class="value" id="trial-count">0</div></div>
<div class="card"><div class="label">Speed/Min</div><div class="value" id="speed">0</div></div>
</div>
<div class="card"><div class="label">Progress</div><div class="progress-bar"><div class="progress-fill" id="progress" style="width:0%">0%</div></div><div style="font-size:0.875rem;color:rgba(255,255,255,0.6)">Current: <span id="current">-</span></div></div>
<div class="controls">
<div class="btn-group">
<button class="btn btn-success" id="btn-start" onclick="start()">▶️ Start Scraping</button>
<button class="btn btn-danger" id="btn-stop" onclick="stop()" disabled>⏹️ Stop</button>
<button class="btn btn-secondary" onclick="exportCSV()">📥 Export CSV</button>
</div>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem">
<div><label class="label">Workers</label><input type="number" id="workers" value="20" min="1" max="100"></div>
<div><label class="label">Max Usernames</label><input type="number" id="max-users" value="1000" min="10" max="100000"></div>
</div>
</div>
<div class="chart-container"><h2 class="chart-title">📊 Scraping Speed</h2><canvas id="chart"></canvas></div>
<div class="chart-container"><h2 class="chart-title">🌐 Proxies (10 loaded)</h2><div class="proxy-grid" id="proxies"></div></div>
<div class="chart-container">
<h2 class="chart-title">👥 Discovered Creators (<span id="db-count">0</span>)</h2>
<div class="tabs">
<div class="tab active" onclick="filterCreators('all')">All</div>
<div class="tab" onclick="filterCreators('free')">Free</div>
<div class="tab" onclick="filterCreators('paid')">Paid</div>
<div class="tab" onclick="filterCreators('trial')">Trial</div>
</div>
<div style="max-height:400px;overflow-y:auto"><table class="table"><thead><tr><th>Username</th><th>Display Name</th><th>Type</th><th>Bio</th></tr></thead><tbody id="creators"></tbody></table></div>
</div>
<div class="chart-container"><h2 class="chart-title">🐛 Debug Logs</h2><div class="logs" id="logs"></div></div>
</div>
<script>
const socket=io();
let chart=null;
const data={labels:[],datasets:[{label:'Users/Min',data:[],borderColor:'#ff6b9d',backgroundColor:'rgba(255,107,157,0.1)',tension:0.4,fill:true}]};
function initChart(){
const ctx=document.getElementById('chart').getContext('2d');
chart=new Chart(ctx,{type:'line',data:data,options:{responsive:true,maintainAspectRatio:false,scales:{y:{beginAtZero:true,grid:{color:'rgba(255,255,255,0.1)'},ticks:{color:'rgba(255,255,255,0.7)'}},x:{grid:{color:'rgba(255,255,255,0.1)'},ticks:{color:'rgba(255,255,255,0.7)'}}},plugins:{legend:{labels:{color:'rgba(255,255,255,0.7)'}}}}});
}
socket.on('stats',(d)=>{
document.getElementById('total-checked').textContent=d.total_checked||0;
document.getElementById('total-found').textContent=d.total_found||0;
document.getElementById('free-count').textContent=d.free_count||0;
document.getElementById('paid-count').textContent=d.paid_count||0;
document.getElementById('trial-count').textContent=d.trial_count||0;
document.getElementById('speed').textContent=Math.round(d.speed||0);
document.getElementById('current').textContent=d.current_username||'-';
const p=d.progress||0;
document.getElementById('progress').style.width=p+'%';
document.getElementById('progress').textContent=Math.round(p)+'%';
if(chart&&d.speed!==undefined){
const now=new Date().toLocaleTimeString();
data.labels.push(now);
data.datasets[0].data.push(d.speed);
if(data.labels.length>30){data.labels.shift();data.datasets[0].data.shift();}
chart.update('none');
}
});
socket.on('status',(d)=>{
const badge=document.getElementById('status');
const text=document.getElementById('status-text');
const btnStart=document.getElementById('btn-start');
const btnStop=document.getElementById('btn-stop');
if(d.running){
badge.className='status status-running';
text.textContent='RUNNING';
btnStart.disabled=true;
btnStop.disabled=false;
}else{
badge.className='status status-stopped';
text.textContent='STOPPED';
btnStart.disabled=false;
btnStop.disabled=true;
}
});
socket.on('log',(d)=>{
const logs=document.getElementById('logs');
const entry=document.createElement('div');
entry.className='log log-'+d.level.toLowerCase();
entry.textContent='['+d.timestamp+'] '+d.message;
logs.appendChild(entry);
while(logs.children.length>100)logs.removeChild(logs.firstChild);
logs.scrollTop=logs.scrollHeight;
});
socket.on('proxies',(d)=>{
const grid=document.getElementById('proxies');
if(!d||d.length===0){grid.innerHTML='<div>No proxies</div>';return;}
grid.innerHTML=d.map(p=>`<div class="proxy-item proxy-${p.health}"><div>Proxy #${d.indexOf(p)+1}</div><div><strong>${p.health.toUpperCase()}</strong></div><div>${p.requests} req | ${Math.round(p.success_rate||0)}%</div></div>`).join('');
});
socket.on('creators',(d)=>{
document.getElementById('db-count').textContent=d.length;
const tbody=document.getElementById('creators');
if(d.length===0){tbody.innerHTML='<tr><td colspan="4" style="text-align:center;padding:2rem;color:rgba(255,255,255,0.5)">No creators yet</td></tr>';return;}
tbody.innerHTML=d.map(c=>`<tr><td><strong>@${c.username}</strong></td><td>${c.display_name||'N/A'}</td><td><span class="badge badge-${c.classification||'unknown'}">${c.classification||'unknown'}</span></td><td>${(c.bio||'').substring(0,80)}...</td></tr>`).join('');
});
function start(){
const workers=document.getElementById('workers').value;
const maxUsers=document.getElementById('max-users').value;
fetch('/api/start',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({workers:parseInt(workers),max_usernames:parseInt(maxUsers)})}).then(r=>r.json()).then(d=>{if(d.error)alert(d.error);});
}
function stop(){fetch('/api/stop',{method:'POST'}).then(r=>r.json());}
function exportCSV(){window.location.href='/api/export';}
let currentFilter='all';
function filterCreators(filter){
currentFilter=filter;
document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
event.target.classList.add('active');
loadCreators();
}
function loadCreators(){fetch('/api/creators?filter='+currentFilter).then(r=>r.json()).then(d=>socket.emit('creators',d));}
initChart();
setInterval(loadCreators,5000);
loadCreators();
fetch('/api/proxies').then(r=>r.json()).then(d=>socket.emit('proxies',d));
</script>
</body>
</html>
"""

def scraper_worker():
    """Main scraper thread"""
    session = requests.Session()
    if COOKIE_FILE.exists():
        cookies = json.loads(COOKIE_FILE.read_text())
        for c in cookies:
            session.cookies.set(c.get('name'), c.get('value'), domain=c.get('domain', '.mym.fans'))

    # Generate usernames
    wordlist_file = Path(__file__).parent / "wordlist.txt"
    if wordlist_file.exists():
        with open(wordlist_file, 'r') as f:
            names = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    else:
        names = ['marie', 'julie', 'laura', 'sarah', 'emma']

    usernames = []
    for name in names[:10]:
        for i in range(1, 100):
            usernames.extend([name, f"{name}{i}", f"{name}_{i}", f"{name}-{i}"])

    total = len(usernames)
    socketio.emit('log', {'timestamp': datetime.now().strftime("%H:%M:%S"), 'level': 'SUCCESS', 'message': f'Starting scrape of {total} usernames with {len(state["proxies"])} proxies'})

    state['start_time'] = time.time()
    last_update = time.time()

    for idx, username in enumerate(usernames):
        with lock:
            if not state['running']:
                break
            state['current_username'] = username

        # Get proxy
        proxy_obj = get_next_proxy()
        proxies = {'http': proxy_obj['url'], 'https': proxy_obj['url']} if proxy_obj else None

        # Check username
        try:
            url = f"https://mym.fans/{username}"
            start = time.time()
            r = session.head(url, proxies=proxies, timeout=10)
            elapsed = time.time() - start

            if proxy_obj:
                with lock:
                    proxy_obj['requests'] += 1
                    if r.status_code == 200:
                        proxy_obj['successes'] += 1
                        proxy_obj['health'] = 'healthy'

            with lock:
                state['total_checked'] += 1

                if r.status_code == 200:
                    state['total_found'] += 1
                    socketio.emit('log', {'timestamp': datetime.now().strftime("%H:%M:%S"), 'level': 'SUCCESS', 'message': f'Found: @{username}'})

                    # Get full profile
                    try:
                        r2 = session.get(url, proxies=proxies, timeout=10)
                        soup = BeautifulSoup(r2.text, 'html.parser')

                        og_title = soup.find('meta', property='og:title')
                        og_desc = soup.find('meta', property='og:description')
                        og_image = soup.find('meta', property='og:image')

                        display_name = og_title.get('content', username) if og_title else username
                        bio = og_desc.get('content', '') if og_desc else ''
                        avatar = og_image.get('content', '') if og_image else ''

                        # Classify
                        html_lower = r2.text.lower()
                        if 'free trial' in html_lower or 'essai gratuit' in html_lower:
                            classification = 'trial'
                            state['trial_count'] += 1
                        elif 'free' in html_lower or 'gratuit' in html_lower:
                            classification = 'free'
                            state['free_count'] += 1
                        else:
                            classification = 'paid'
                            state['paid_count'] += 1

                        # Save to DB
                        conn = sqlite3.Connection(DB_FILE)
                        conn.execute("""
                            INSERT OR REPLACE INTO creators
                            (username, display_name, profile_url, avatar_url, bio, classification, last_seen_at)
                            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                        """, (username, display_name, url, avatar, bio, classification))
                        conn.commit()
                        conn.close()

                        # Emit update
                        socketio.emit('creators', get_creators('all'))

                    except Exception as e:
                        socketio.emit('log', {'timestamp': datetime.now().strftime("%H:%M:%S"), 'level': 'ERROR', 'message': f'Error fetching {username}: {str(e)}'})

        except Exception as e:
            with lock:
                state['errors'] += 1
                if proxy_obj:
                    proxy_obj['health'] = 'down'
            socketio.emit('log', {'timestamp': datetime.now().strftime("%H:%M:%S"), 'level': 'ERROR', 'message': f'Error: {str(e)}'})

        # Update stats
        now = time.time()
        if now - last_update >= 1.0:
            elapsed = now - state['start_time']
            speed = (state['total_checked'] / elapsed) * 60 if elapsed > 0 else 0
            progress = (idx / total) * 100

            socketio.emit('stats', {
                'total_checked': state['total_checked'],
                'total_found': state['total_found'],
                'free_count': state['free_count'],
                'paid_count': state['paid_count'],
                'trial_count': state['trial_count'],
                'errors': state['errors'],
                'speed': speed,
                'current_username': username,
                'progress': progress
            })

            # Update proxies
            proxies_data = []
            for p in state['proxies']:
                proxies_data.append({
                    'url': p['url'],
                    'requests': p['requests'],
                    'successes': p['successes'],
                    'success_rate': (p['successes'] / max(p['requests'], 1)) * 100,
                    'health': p['health']
                })
            socketio.emit('proxies', proxies_data)

            last_update = now

        time.sleep(0.1)

    with lock:
        state['running'] = False

    socketio.emit('status', {'running': False})
    socketio.emit('log', {'timestamp': datetime.now().strftime("%H:%M:%S"), 'level': 'SUCCESS', 'message': 'Scraping complete!'})

def get_creators(filter_type='all'):
    """Get creators from database with filter"""
    conn = sqlite3.Connection(DB_FILE)
    conn.row_factory = sqlite3.Row

    if filter_type == 'all':
        cursor = conn.execute("SELECT * FROM creators ORDER BY last_seen_at DESC LIMIT 100")
    else:
        cursor = conn.execute("SELECT * FROM creators WHERE classification = ? ORDER BY last_seen_at DESC LIMIT 100", (filter_type,))

    creators = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return creators

@app.route('/')
def index():
    return render_template_string(HTML)

@app.route('/api/start', methods=['POST'])
def api_start():
    global scraper_thread

    with lock:
        if state['running']:
            return jsonify({'error': 'Already running'})

        state['running'] = True
        state['total_checked'] = 0
        state['total_found'] = 0
        state['free_count'] = 0
        state['paid_count'] = 0
        state['trial_count'] = 0
        state['errors'] = 0

    scraper_thread = threading.Thread(target=scraper_worker, daemon=True)
    scraper_thread.start()

    socketio.emit('status', {'running': True})
    return jsonify({'message': 'Started'})

@app.route('/api/stop', methods=['POST'])
def api_stop():
    with lock:
        state['running'] = False

    socketio.emit('status', {'running': False})
    return jsonify({'message': 'Stopped'})

@app.route('/api/creators')
def api_creators():
    filter_type = request.args.get('filter', 'all')
    return jsonify(get_creators(filter_type))

@app.route('/api/proxies')
def api_proxies():
    proxies_data = []
    for p in state['proxies']:
        proxies_data.append({
            'url': p['url'],
            'requests': p['requests'],
            'successes': p['successes'],
            'success_rate': (p['successes'] / max(p['requests'], 1)) * 100,
            'health': p['health']
        })
    return jsonify(proxies_data)

@app.route('/api/export')
def api_export():
    import csv
    conn = sqlite3.Connection(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.execute("SELECT * FROM creators")
    creators = [dict(row) for row in cursor.fetchall()]
    conn.close()

    tmp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv', newline='')
    if creators:
        writer = csv.DictWriter(tmp_file, fieldnames=creators[0].keys())
        writer.writeheader()
        writer.writerows(creators)
    tmp_file.close()

    return send_file(tmp_file.name, as_attachment=True, download_name='mym_creators.csv')

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "version": "5.0"})

if __name__ == '__main__':
    # Load proxies on startup
    load_proxies()

    print("="*80)
    print(" "*25 + "MYM HUNTER - FINAL v5.0")
    print("="*80)
    print(f"\n🚀 Dashboard: http://0.0.0.0:{PORT}")
    print(f"🌐 Proxies: {len(state['proxies'])} loaded")
    print("\n" + "="*80 + "\n")

    socketio.run(app, host='0.0.0.0', port=PORT, debug=False, allow_unsafe_werkzeug=True)
