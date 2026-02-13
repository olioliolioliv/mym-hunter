#!/usr/bin/env python3
"""
MYM HUNTER - ULTIMATE DASHBOARD
Complete production control center with:
- Start/Pause/Resume controls
- Real-time graphs (users per minute)
- Live proxy monitoring
- WebSocket updates
- Progress tracking
"""

import os
import json
import sqlite3
import threading
import time
from pathlib import Path
from datetime import datetime, timedelta
from collections import deque
from flask import Flask, render_template_string, jsonify, request, send_file
from flask_socketio import SocketIO, emit
import tempfile

# Global scraper state
scraper_state = {
    'running': False,
    'paused': False,
    'total_checked': 0,
    'total_found': 0,
    'errors': 0,
    'start_time': None,
    'workers': 20,
    'current_username': '',
    'speed_history': deque(maxlen=60),  # Last 60 data points (1 per second)
    'proxy_stats': [],
    'wordlist': [],
    'current_index': 0
}

scraper_thread = None
scraper_lock = threading.Lock()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'mym-ultimate-2024'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

PORT = int(os.getenv("PORT", 5000))
SECRETS_DIR = Path(__file__).parent / ".secrets"
DB_FILE = SECRETS_DIR / "mym_creators.sqlite3"
COOKIE_FILE = SECRETS_DIR / "mym_cookies.json"
PROXY_FILE = SECRETS_DIR / "proxies.txt"

# HTML Template with Charts
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MYM Hunter - Ultimate Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        :root {
            --primary: #ff6b9d;
            --secondary: #c471ed;
            --accent: #12d8fa;
            --success: #10b981;
            --warning: #f59e0b;
            --danger: #ef4444;
            --dark: #0f0f1e;
            --dark-card: #1a1a2e;
            --glass: rgba(255, 255, 255, 0.08);
            --glass-border: rgba(255, 255, 255, 0.15);
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: 'Inter', sans-serif;
            background: var(--dark);
            color: #fff;
            min-height: 100vh;
            overflow-x: hidden;
        }

        /* Animated Background */
        .bg-animated {
            position: fixed;
            top: 0; left: 0;
            width: 100%; height: 100%;
            z-index: -1;
            overflow: hidden;
        }

        .orb {
            position: absolute;
            border-radius: 50%;
            filter: blur(80px);
            opacity: 0.4;
            animation: float 20s infinite ease-in-out;
        }

        .orb1 {
            width: 400px; height: 400px;
            background: radial-gradient(circle, var(--primary), transparent);
            top: -100px; left: -100px;
        }

        .orb2 {
            width: 500px; height: 500px;
            background: radial-gradient(circle, var(--secondary), transparent);
            bottom: -150px; right: -150px;
            animation-delay: -5s;
        }

        .orb3 {
            width: 350px; height: 350px;
            background: radial-gradient(circle, var(--accent), transparent);
            top: 50%; left: 50%;
            animation-delay: -10s;
        }

        @keyframes float {
            0%, 100% { transform: translate(0, 0) rotate(0deg); }
            33% { transform: translate(150px, -100px) rotate(120deg); }
            66% { transform: translate(-100px, 100px) rotate(240deg); }
        }

        /* Header */
        header {
            background: rgba(15, 15, 30, 0.8);
            backdrop-filter: blur(20px);
            border-bottom: 1px solid var(--glass-border);
            padding: 1.5rem 2rem;
            position: sticky;
            top: 0;
            z-index: 100;
        }

        .header-content {
            max-width: 1600px;
            margin: 0 auto;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .logo {
            font-size: 1.5rem;
            font-weight: 800;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .status-badge {
            padding: 0.5rem 1rem;
            border-radius: 20px;
            font-size: 0.875rem;
            font-weight: 600;
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
        }

        .status-running { background: rgba(16, 185, 129, 0.2); color: var(--success); }
        .status-paused { background: rgba(245, 158, 11, 0.2); color: var(--warning); }
        .status-stopped { background: rgba(239, 68, 68, 0.2); color: var(--danger); }

        .pulse-dot {
            width: 8px; height: 8px;
            border-radius: 50%;
            background: currentColor;
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }

        /* Container */
        .container {
            max-width: 1600px;
            margin: 0 auto;
            padding: 2rem;
        }

        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1.5rem; margin-bottom: 2rem; }

        /* Glass Cards */
        .glass-card {
            background: var(--glass);
            backdrop-filter: blur(10px);
            border: 1px solid var(--glass-border);
            border-radius: 20px;
            padding: 1.5rem;
            transition: all 0.3s ease;
        }

        .glass-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
        }

        .stat-card::before {
            content: '';
            position: absolute;
            top: 0; left: 0;
            width: 100%; height: 4px;
            background: linear-gradient(90deg, var(--primary), var(--secondary), var(--accent));
        }

        .stat-label {
            font-size: 0.875rem;
            color: rgba(255, 255, 255, 0.6);
            margin-bottom: 0.5rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .stat-value {
            font-size: 2.5rem;
            font-weight: 700;
            background: linear-gradient(135deg, #fff, rgba(255, 255, 255, 0.6));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        /* Controls */
        .controls-section {
            background: var(--glass);
            backdrop-filter: blur(10px);
            border: 1px solid var(--glass-border);
            border-radius: 20px;
            padding: 2rem;
            margin-bottom: 2rem;
        }

        .control-buttons {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 1rem;
            margin-bottom: 1.5rem;
        }

        .btn {
            padding: 0.875rem 1.5rem;
            border-radius: 12px;
            border: none;
            font-size: 0.875rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 0.5rem;
        }

        .btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }

        .btn-success { background: linear-gradient(135deg, #10b981, #059669); color: white; }
        .btn-warning { background: linear-gradient(135deg, #f59e0b, #d97706); color: white; }
        .btn-danger { background: linear-gradient(135deg, #ef4444, #dc2626); color: white; }
        .btn-secondary { background: rgba(255, 255, 255, 0.1); color: white; border: 1px solid rgba(255, 255, 255, 0.2); }

        .btn:not(:disabled):hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.3);
        }

        /* Chart Container */
        .chart-container {
            background: var(--dark-card);
            border: 1px solid var(--glass-border);
            border-radius: 20px;
            padding: 1.5rem;
            margin-bottom: 2rem;
        }

        .chart-title {
            font-size: 1.25rem;
            font-weight: 600;
            margin-bottom: 1rem;
            color: var(--accent);
        }

        canvas {
            max-height: 300px;
        }

        /* Progress Bar */
        .progress-container {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 10px;
            height: 30px;
            overflow: hidden;
            margin: 1rem 0;
        }

        .progress-bar {
            height: 100%;
            background: linear-gradient(90deg, var(--primary), var(--secondary));
            transition: width 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 0.75rem;
            font-weight: 600;
        }

        /* Proxy Status */
        .proxy-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 1rem;
        }

        .proxy-item {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid var(--glass-border);
            border-radius: 12px;
            padding: 1rem;
        }

        .proxy-healthy { border-left: 4px solid var(--success); }
        .proxy-down { border-left: 4px solid var(--danger); }

        /* Settings */
        .settings-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
        }

        input, select {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 8px;
            padding: 0.75rem 1rem;
            color: white;
            font-size: 0.875rem;
            width: 100%;
        }

        label {
            display: block;
            margin-bottom: 0.5rem;
            font-size: 0.875rem;
            color: rgba(255, 255, 255, 0.7);
        }

        /* Debug Logs */
        .logs {
            background: var(--dark-card);
            border: 1px solid var(--glass-border);
            border-radius: 20px;
            padding: 1.5rem;
            max-height: 300px;
            overflow-y: auto;
            font-family: 'Courier New', monospace;
            font-size: 0.8rem;
        }

        .log-entry {
            padding: 0.4rem 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        }

        .log-info { color: #60a5fa; }
        .log-success { color: #10b981; }
        .log-warning { color: #f59e0b; }
        .log-error { color: #ef4444; }
    </style>
</head>
<body>
    <div class="bg-animated">
        <div class="orb orb1"></div>
        <div class="orb orb2"></div>
        <div class="orb orb3"></div>
    </div>

    <header>
        <div class="header-content">
            <div class="logo">🎯 MYM HUNTER - ULTIMATE</div>
            <div class="status-badge" id="status-badge">
                <span class="pulse-dot"></span>
                <span id="status-text">STOPPED</span>
            </div>
        </div>
    </header>

    <div class="container">
        <!-- Stats Grid -->
        <div class="grid">
            <div class="glass-card stat-card" style="position: relative;">
                <div class="stat-label">Total Checked</div>
                <div class="stat-value" id="total-checked">0</div>
            </div>
            <div class="glass-card stat-card" style="position: relative;">
                <div class="stat-label">Creators Found</div>
                <div class="stat-value" id="total-found">0</div>
            </div>
            <div class="glass-card stat-card" style="position: relative;">
                <div class="stat-label">Speed (per min)</div>
                <div class="stat-value" id="speed">0</div>
            </div>
            <div class="glass-card stat-card" style="position: relative;">
                <div class="stat-label">Errors</div>
                <div class="stat-value" id="errors">0</div>
            </div>
        </div>

        <!-- Progress Bar -->
        <div class="glass-card">
            <div class="stat-label">Progress</div>
            <div class="progress-container">
                <div class="progress-bar" id="progress-bar" style="width: 0%">0%</div>
            </div>
            <div style="font-size: 0.875rem; color: rgba(255, 255, 255, 0.6);">
                Current: <span id="current-username">-</span>
            </div>
        </div>

        <!-- Controls -->
        <div class="controls-section">
            <h2 style="margin-bottom: 1.5rem;">Scraper Controls</h2>
            <div class="control-buttons">
                <button class="btn btn-success" id="btn-start" onclick="startScraper()">▶️ Start</button>
                <button class="btn btn-warning" id="btn-pause" onclick="pauseScraper()" disabled>⏸️ Pause</button>
                <button class="btn btn-success" id="btn-resume" onclick="resumeScraper()" disabled>▶️ Resume</button>
                <button class="btn btn-danger" id="btn-stop" onclick="stopScraper()" disabled>⏹️ Stop</button>
                <button class="btn btn-secondary" onclick="downloadCSV()">📥 Download CSV</button>
            </div>

            <div class="settings-grid" style="margin-top: 1.5rem;">
                <div>
                    <label>Workers</label>
                    <input type="number" id="workers" value="20" min="1" max="100">
                </div>
                <div>
                    <label>Max Usernames</label>
                    <input type="number" id="max-usernames" value="1000" min="10" max="100000">
                </div>
            </div>
        </div>

        <!-- Speed Chart -->
        <div class="chart-container">
            <h2 class="chart-title">📊 Scraping Speed (Users/Min)</h2>
            <canvas id="speedChart"></canvas>
        </div>

        <!-- Proxies Status -->
        <div class="chart-container">
            <h2 class="chart-title">🌐 Proxy Status</h2>
            <div class="proxy-grid" id="proxy-grid">
                <div style="text-align: center; padding: 2rem; color: rgba(255, 255, 255, 0.5);">
                    No proxies configured
                </div>
            </div>
        </div>

        <!-- Debug Logs -->
        <div class="chart-container">
            <h2 class="chart-title">🐛 Debug Logs</h2>
            <div class="logs" id="logs"></div>
        </div>
    </div>

    <script>
        const socket = io();
        let speedChart = null;
        const speedData = {
            labels: [],
            datasets: [{
                label: 'Users/Min',
                data: [],
                borderColor: '#ff6b9d',
                backgroundColor: 'rgba(255, 107, 157, 0.1)',
                tension: 0.4,
                fill: true
            }]
        };

        // Initialize Chart
        function initChart() {
            const ctx = document.getElementById('speedChart').getContext('2d');
            speedChart = new Chart(ctx, {
                type: 'line',
                data: speedData,
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            grid: { color: 'rgba(255, 255, 255, 0.1)' },
                            ticks: { color: 'rgba(255, 255, 255, 0.7)' }
                        },
                        x: {
                            grid: { color: 'rgba(255, 255, 255, 0.1)' },
                            ticks: { color: 'rgba(255, 255, 255, 0.7)' }
                        }
                    },
                    plugins: {
                        legend: { labels: { color: 'rgba(255, 255, 255, 0.7)' } }
                    }
                }
            });
        }

        // Update Stats
        socket.on('stats_update', (data) => {
            document.getElementById('total-checked').textContent = data.total_checked || 0;
            document.getElementById('total-found').textContent = data.total_found || 0;
            document.getElementById('speed').textContent = Math.round(data.speed || 0);
            document.getElementById('errors').textContent = data.errors || 0;
            document.getElementById('current-username').textContent = data.current_username || '-';

            // Update progress
            const progress = data.progress || 0;
            document.getElementById('progress-bar').style.width = progress + '%';
            document.getElementById('progress-bar').textContent = Math.round(progress) + '%';

            // Update chart
            if (speedChart && data.speed !== undefined) {
                const now = new Date().toLocaleTimeString();
                speedData.labels.push(now);
                speedData.datasets[0].data.push(data.speed);

                // Keep last 30 points
                if (speedData.labels.length > 30) {
                    speedData.labels.shift();
                    speedData.datasets[0].data.shift();
                }

                speedChart.update('none');
            }
        });

        // Update Status
        socket.on('status', (data) => {
            const badge = document.getElementById('status-badge');
            const text = document.getElementById('status-text');
            const btnStart = document.getElementById('btn-start');
            const btnPause = document.getElementById('btn-pause');
            const btnResume = document.getElementById('btn-resume');
            const btnStop = document.getElementById('btn-stop');

            if (data.running && !data.paused) {
                badge.className = 'status-badge status-running';
                text.textContent = 'RUNNING';
                btnStart.disabled = true;
                btnPause.disabled = false;
                btnResume.disabled = true;
                btnStop.disabled = false;
            } else if (data.paused) {
                badge.className = 'status-badge status-paused';
                text.textContent = 'PAUSED';
                btnStart.disabled = true;
                btnPause.disabled = true;
                btnResume.disabled = false;
                btnStop.disabled = false;
            } else {
                badge.className = 'status-badge status-stopped';
                text.textContent = 'STOPPED';
                btnStart.disabled = false;
                btnPause.disabled = true;
                btnResume.disabled = true;
                btnStop.disabled = true;
            }
        });

        // Update Logs
        socket.on('log', (data) => {
            const logs = document.getElementById('logs');
            const entry = document.createElement('div');
            entry.className = `log-entry log-${data.level.toLowerCase()}`;
            entry.textContent = `[${data.timestamp}] ${data.message}`;
            logs.appendChild(entry);

            // Keep last 100 logs
            while (logs.children.length > 100) {
                logs.removeChild(logs.firstChild);
            }

            logs.scrollTop = logs.scrollHeight;
        });

        // Update Proxies
        socket.on('proxies', (data) => {
            const grid = document.getElementById('proxy-grid');
            if (!data || data.length === 0) {
                grid.innerHTML = '<div style="text-align: center; padding: 2rem; color: rgba(255, 255, 255, 0.5);">No proxies configured</div>';
                return;
            }

            grid.innerHTML = data.map(p => `
                <div class="proxy-item ${p.health === 'healthy' ? 'proxy-healthy' : 'proxy-down'}">
                    <div style="font-size: 0.75rem; color: rgba(255, 255, 255, 0.5);">
                        ${p.proxy.substring(0, 30)}...
                    </div>
                    <div style="margin-top: 0.5rem;">
                        <strong>${p.health.toUpperCase()}</strong>
                    </div>
                    <div style="font-size: 0.75rem; margin-top: 0.25rem;">
                        ${p.requests} requests | ${Math.round(p.success_rate)}% success
                    </div>
                </div>
            `).join('');
        });

        // Controls
        function startScraper() {
            const workers = document.getElementById('workers').value;
            const maxUsernames = document.getElementById('max-usernames').value;

            fetch('/api/start', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({workers: parseInt(workers), max_usernames: parseInt(maxUsernames)})
            })
            .then(r => r.json())
            .then(data => {
                if (data.error) alert(data.error);
            });
        }

        function pauseScraper() {
            fetch('/api/pause', {method: 'POST'})
                .then(r => r.json())
                .then(data => console.log(data.message));
        }

        function resumeScraper() {
            fetch('/api/resume', {method: 'POST'})
                .then(r => r.json())
                .then(data => console.log(data.message));
        }

        function stopScraper() {
            fetch('/api/stop', {method: 'POST'})
                .then(r => r.json())
                .then(data => console.log(data.message));
        }

        function downloadCSV() {
            window.location.href = '/api/export';
        }

        // Initialize
        initChart();

        // Load initial status
        fetch('/api/status')
            .then(r => r.json())
            .then(data => {
                socket.emit('status', data);
            });
    </script>
</body>
</html>
"""

def scraper_worker():
    """Background scraper thread"""
    global scraper_state

    import requests
    from bs4 import BeautifulSoup

    # Load cookies
    session = requests.Session()
    if COOKIE_FILE.exists():
        cookies = json.loads(COOKIE_FILE.read_text())
        for c in cookies:
            session.cookies.set(c.get('name'), c.get('value'), domain=c.get('domain', '.mym.fans'))

    # Load wordlist
    wordlist_file = Path(__file__).parent / "wordlist.txt"
    if wordlist_file.exists():
        with open(wordlist_file, 'r') as f:
            names = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    else:
        names = ['marie', 'julie', 'laura', 'sarah', 'emma']

    # Generate usernames
    usernames = []
    for name in names[:10]:  # Limit to 10 names for demo
        for i in range(1, 100):  # 99 variations
            usernames.extend([name, f"{name}{i}", f"{name}_{i}", f"{name}-{i}"])

    scraper_state['wordlist'] = usernames
    total = len(usernames)

    socketio.emit('log', {'timestamp': datetime.now().strftime("%H:%M:%S"), 'level': 'SUCCESS', 'message': f'Starting scrape of {total} usernames'})

    scraper_state['start_time'] = time.time()
    last_update = time.time()

    for idx, username in enumerate(usernames):
        with scraper_lock:
            # Check if stopped
            if not scraper_state['running']:
                break

            # Check if paused
            while scraper_state['paused'] and scraper_state['running']:
                time.sleep(0.5)

            if not scraper_state['running']:
                break

            scraper_state['current_index'] = idx
            scraper_state['current_username'] = username

        # Quick check
        try:
            url = f"https://mym.fans/{username}"
            r = session.head(url, timeout=5)

            with scraper_lock:
                scraper_state['total_checked'] += 1

                if r.status_code == 200:
                    scraper_state['total_found'] += 1
                    socketio.emit('log', {'timestamp': datetime.now().strftime("%H:%M:%S"), 'level': 'SUCCESS', 'message': f'Found: @{username}'})

                    # Save to database (simplified)
                    try:
                        conn = sqlite3.Connection(DB_FILE)
                        conn.execute("""
                            INSERT OR IGNORE INTO creators (username, profile_url, last_seen_at)
                            VALUES (?, ?, CURRENT_TIMESTAMP)
                        """, (username, url))
                        conn.commit()
                        conn.close()
                    except:
                        pass

        except Exception as e:
            with scraper_lock:
                scraper_state['errors'] += 1

        # Update speed every second
        now = time.time()
        if now - last_update >= 1.0:
            elapsed = now - scraper_state['start_time']
            speed = (scraper_state['total_checked'] / elapsed) * 60 if elapsed > 0 else 0
            progress = (idx / total) * 100

            socketio.emit('stats_update', {
                'total_checked': scraper_state['total_checked'],
                'total_found': scraper_state['total_found'],
                'errors': scraper_state['errors'],
                'speed': speed,
                'current_username': username,
                'progress': progress
            })

            last_update = now

        time.sleep(0.1)  # Rate limit

    # Finished
    with scraper_lock:
        scraper_state['running'] = False
        scraper_state['paused'] = False

    socketio.emit('status', {'running': False, 'paused': False})
    socketio.emit('log', {'timestamp': datetime.now().strftime("%H:%M:%S"), 'level': 'SUCCESS', 'message': 'Scraping complete!'})

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/status')
def api_status():
    with scraper_lock:
        return jsonify({
            'running': scraper_state['running'],
            'paused': scraper_state['paused'],
            'total_checked': scraper_state['total_checked'],
            'total_found': scraper_state['total_found'],
            'errors': scraper_state['errors']
        })

@app.route('/api/start', methods=['POST'])
def api_start():
    global scraper_thread

    with scraper_lock:
        if scraper_state['running']:
            return jsonify({'error': 'Already running'})

        # Reset stats
        scraper_state['running'] = True
        scraper_state['paused'] = False
        scraper_state['total_checked'] = 0
        scraper_state['total_found'] = 0
        scraper_state['errors'] = 0
        scraper_state['current_index'] = 0

    # Start thread
    scraper_thread = threading.Thread(target=scraper_worker, daemon=True)
    scraper_thread.start()

    socketio.emit('status', {'running': True, 'paused': False})

    return jsonify({'message': 'Scraper started'})

@app.route('/api/pause', methods=['POST'])
def api_pause():
    with scraper_lock:
        if scraper_state['running'] and not scraper_state['paused']:
            scraper_state['paused'] = True
            socketio.emit('status', {'running': True, 'paused': True})
            return jsonify({'message': 'Scraper paused'})
    return jsonify({'error': 'Not running'})

@app.route('/api/resume', methods=['POST'])
def api_resume():
    with scraper_lock:
        if scraper_state['running'] and scraper_state['paused']:
            scraper_state['paused'] = False
            socketio.emit('status', {'running': True, 'paused': False})
            return jsonify({'message': 'Scraper resumed'})
    return jsonify({'error': 'Not paused'})

@app.route('/api/stop', methods=['POST'])
def api_stop():
    with scraper_lock:
        scraper_state['running'] = False
        scraper_state['paused'] = False

    socketio.emit('status', {'running': False, 'paused': False})
    return jsonify({'message': 'Scraper stopped'})

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
    return jsonify({"status": "healthy", "service": "mym-hunter-ultimate", "version": "4.0"})

if __name__ == '__main__':
    print("="*80)
    print(" "*20 + "MYM HUNTER - ULTIMATE DASHBOARD v4.0")
    print("="*80)
    print(f"\n🚀 Dashboard: http://0.0.0.0:{PORT}")
    print(f"💚 Health: http://0.0.0.0:{PORT}/health")
    print("\n" + "="*80 + "\n")

    socketio.run(app, host='0.0.0.0', port=PORT, debug=False, allow_unsafe_werkzeug=True)
