#!/usr/bin/env python3
"""
MYM.FANS HUNTER - PRODUCTION DASHBOARD
The best creator scraper dashboard in the world
- Real-time debug window
- Proxy management
- Cookie import/export
- Mass discovery with filters
- Free & trial creator filtering
"""

import os
import json
import sqlite3
import threading
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template_string, jsonify, request, send_file
from flask_socketio import Socket IO, emit
from mym_mass_scraper import MYMMassScraper

app = Flask(__name__)
app.config['SECRET_KEY'] = 'mym-hunter-production-2024'
socketio = SocketIO(app, cors_allowed_origins="*")

PORT = int(os.getenv("PORT", 5000))
SECRETS_DIR = Path(__file__).parent / ".secrets"
DB_FILE = SECRETS_DIR / "mym_creators.sqlite3"
COOKIE_FILE = SECRETS_DIR / "mym_cookies.json"

# Global scraper instance
scraper = None
scraper_thread = None
scraper_running = False

# HTML Template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MYM Hunter - Production Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
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

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

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
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
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
            width: 400px;
            height: 400px;
            background: radial-gradient(circle, var(--primary), transparent);
            top: -100px;
            left: -100px;
        }

        .orb2 {
            width: 500px;
            height: 500px;
            background: radial-gradient(circle, var(--secondary), transparent);
            bottom: -150px;
            right: -150px;
            animation-delay: -5s;
        }

        .orb3 {
            width: 350px;
            height: 350px;
            background: radial-gradient(circle, var(--accent), transparent);
            top: 50%;
            left: 50%;
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
            max-width: 1400px;
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
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .status-badge {
            padding: 0.4rem 0.8rem;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 600;
            display: inline-flex;
            align-items: center;
            gap: 0.4rem;
        }

        .status-running {
            background: rgba(16, 185, 129, 0.2);
            color: var(--success);
            border: 1px solid rgba(16, 185, 129, 0.3);
        }

        .status-stopped {
            background: rgba(239, 68, 68, 0.2);
            color: var(--danger);
            border: 1px solid rgba(239, 68, 68, 0.3);
        }

        .pulse-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: currentColor;
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }

        /* Main Container */
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 2rem;
        }

        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }

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

        .stat-card {
            position: relative;
            overflow: hidden;
        }

        .stat-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 4px;
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
        .controls {
            background: var(--glass);
            backdrop-filter: blur(10px);
            border: 1px solid var(--glass-border);
            border-radius: 20px;
            padding: 2rem;
            margin-bottom: 2rem;
        }

        .controls-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
        }

        .btn {
            padding: 0.75rem 1.5rem;
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

        .btn-primary {
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            color: white;
        }

        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 25px rgba(255, 107, 157, 0.3);
        }

        .btn-success {
            background: linear-gradient(135deg, #10b981, #059669);
            color: white;
        }

        .btn-danger {
            background: linear-gradient(135deg, #ef4444, #dc2626);
            color: white;
        }

        .btn-secondary {
            background: rgba(255, 255, 255, 0.1);
            color: white;
            border: 1px solid rgba(255, 255, 255, 0.2);
        }

        /* Debug Console */
        .debug-console {
            background: var(--dark-card);
            border: 1px solid var(--glass-border);
            border-radius: 20px;
            padding: 1.5rem;
            margin-bottom: 2rem;
            max-height: 400px;
            overflow-y: auto;
        }

        .debug-console h2 {
            font-size: 1.25rem;
            margin-bottom: 1rem;
            color: var(--accent);
        }

        .log-entry {
            font-family: 'Courier New', monospace;
            font-size: 0.8rem;
            padding: 0.4rem 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            opacity: 0;
            animation: fadeIn 0.3s ease forwards;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateX(-10px); }
            to { opacity: 1; transform: translateX(0); }
        }

        .log-info { color: #60a5fa; }
        .log-success { color: #10b981; }
        .log-warning { color: #f59e0b; }
        .log-error { color: #ef4444; }

        /* Creators Table */
        .creators-table {
            background: var(--glass);
            backdrop-filter: blur(10px);
            border: 1px solid var(--glass-border);
            border-radius: 20px;
            padding: 1.5rem;
            overflow-x: auto;
        }

        table {
            width: 100%;
            border-collapse: collapse;
        }

        th {
            text-align: left;
            padding: 1rem;
            font-weight: 600;
            color: rgba(255, 255, 255, 0.7);
            border-bottom: 2px solid rgba(255, 255, 255, 0.1);
        }

        td {
            padding: 1rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        }

        tr:hover {
            background: rgba(255, 255, 255, 0.03);
        }

        .badge {
            padding: 0.25rem 0.75rem;
            border-radius: 12px;
            font-size: 0.75rem;
            font-weight: 600;
        }

        .badge-free {
            background: rgba(16, 185, 129, 0.2);
            color: var(--success);
        }

        .badge-trial {
            background: rgba(245, 158, 11, 0.2);
            color: var(--warning);
        }

        .badge-paid {
            background: rgba(239, 68, 68, 0.2);
            color: var(--danger);
        }

        /* Input Fields */
        input, select {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 8px;
            padding: 0.75rem 1rem;
            color: white;
            font-size: 0.875rem;
            width: 100%;
        }

        input:focus, select:focus {
            outline: none;
            border-color: var(--primary);
        }

        /* Scrollbar */
        ::-webkit-scrollbar {
            width: 8px;
            height: 8px;
        }

        ::-webkit-scrollbar-track {
            background: rgba(255, 255, 255, 0.05);
        }

        ::-webkit-scrollbar-thumb {
            background: linear-gradient(180deg, var(--primary), var(--secondary));
            border-radius: 4px;
        }
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
            <div class="logo">
                🎯 MYM HUNTER
            </div>
            <div class="status-badge" id="status-badge">
                <span class="pulse-dot"></span>
                <span id="status-text">READY</span>
            </div>
        </div>
    </header>

    <div class="container">
        <!-- Stats Grid -->
        <div class="grid">
            <div class="glass-card stat-card">
                <div class="stat-label">Total Creators</div>
                <div class="stat-value" id="total-creators">0</div>
            </div>
            <div class="glass-card stat-card">
                <div class="stat-label">Free Creators</div>
                <div class="stat-value" id="free-creators">0</div>
            </div>
            <div class="glass-card stat-card">
                <div class="stat-label">Trial Offers</div>
                <div class="stat-value" id="trial-creators">0</div>
            </div>
            <div class="glass-card stat-card">
                <div class="stat-label">Checks/Min</div>
                <div class="stat-value" id="check-rate">0</div>
            </div>
        </div>

        <!-- Controls -->
        <div class="controls">
            <h2 style="margin-bottom: 1.5rem;">Scraper Controls</h2>
            <div class="controls-grid">
                <button class="btn btn-success" onclick="startScraper()">▶️ Start Scraping</button>
                <button class="btn btn-danger" onclick="stopScraper()">⏹️ Stop</button>
                <button class="btn btn-secondary" onclick="exportCookies()">🍪 Export Cookies</button>
                <button class="btn btn-secondary" onclick="downloadCSV()">📥 Download CSV</button>
            </div>

            <div style="margin-top: 1.5rem; display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
                <div>
                    <label style="display: block; margin-bottom: 0.5rem; font-size: 0.875rem; color: rgba(255, 255, 255, 0.7);">Workers</label>
                    <input type="number" id="workers" value="10" min="1" max="50">
                </div>
                <div>
                    <label style="display: block; margin-bottom: 0.5rem; font-size: 0.875rem; color: rgba(255, 255, 255, 0.7);">Max Usernames</label>
                    <input type="number" id="max-usernames" value="1000" min="10" max="100000">
                </div>
            </div>
        </div>

        <!-- Debug Console -->
        <div class="debug-console">
            <h2>🐛 Debug Console</h2>
            <div id="debug-logs"></div>
        </div>

        <!-- Creators Table -->
        <div class="creators-table">
            <h2 style="margin-bottom: 1.5rem;">📋 Discovered Creators</h2>
            <table>
                <thead>
                    <tr>
                        <th>Username</th>
                        <th>Display Name</th>
                        <th>Classification</th>
                        <th>Bio</th>
                        <th>Last Seen</th>
                    </tr>
                </thead>
                <tbody id="creators-tbody">
                    <tr>
                        <td colspan="5" style="text-align: center; padding: 2rem; color: rgba(255, 255, 255, 0.5);">
                            No creators discovered yet. Start scraping to find creators!
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>
    </div>

    <script>
        const socket = io();

        // Update stats
        socket.on('stats_update', (data) => {
            document.getElementById('total-creators').textContent = data.total_creators || 0;
            document.getElementById('free-creators').textContent = data.free_creators || 0;
            document.getElementById('trial-creators').textContent = data.trial_creators || 0;
            document.getElementById('check-rate').textContent = (data.rate || 0).toFixed(1);
        });

        // Update logs
        socket.on('log', (data) => {
            const logsContainer = document.getElementById('debug-logs');
            const logEntry = document.createElement('div');
            logEntry.className = `log-entry log-${data.level.toLowerCase()}`;
            logEntry.textContent = `[${data.timestamp}] [${data.level}] ${data.message}`;
            logsContainer.appendChild(logEntry);

            // Keep only last 100 logs
            while (logsContainer.children.length > 100) {
                logsContainer.removeChild(logsContainer.firstChild);
            }

            // Auto scroll
            logsContainer.scrollTop = logsContainer.scrollHeight;
        });

        // Update status
        socket.on('status', (data) => {
            const badge = document.getElementById('status-badge');
            const text = document.getElementById('status-text');

            if (data.running) {
                badge.className = 'status-badge status-running';
                text.textContent = 'RUNNING';
            } else {
                badge.className = 'status-badge status-stopped';
                text.textContent = 'STOPPED';
            }
        });

        // Update creators table
        function loadCreators() {
            fetch('/api/creators?limit=50')
                .then(r => r.json())
                .then(data => {
                    const tbody = document.getElementById('creators-tbody');

                    if (data.creators && data.creators.length > 0) {
                        tbody.innerHTML = data.creators.map(c => `
                            <tr>
                                <td><strong>@${c.username}</strong></td>
                                <td>${c.display_name || 'N/A'}</td>
                                <td><span class="badge badge-${c.classification}">${c.classification}</span></td>
                                <td>${(c.bio || '').substring(0, 80)}...</td>
                                <td>${c.last_seen_at}</td>
                            </tr>
                        `).join('');
                    }
                });
        }

        // Load initial data
        fetch('/api/stats')
            .then(r => r.json())
            .then(data => {
                document.getElementById('total-creators').textContent = data.total_creators || 0;
                document.getElementById('free-creators').textContent = data.free_creators || 0;
                document.getElementById('trial-creators').textContent = data.trial_creators || 0;
            });

        loadCreators();

        // Refresh creators every 30s
        setInterval(loadCreators, 30000);

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
            .then(data => alert(data.message));
        }

        function stopScraper() {
            fetch('/api/stop', {method: 'POST'})
                .then(r => r.json())
                .then(data => alert(data.message));
        }

        function downloadCSV() {
            window.location.href = '/api/export';
        }

        function exportCookies() {
            fetch('/api/cookies/export')
                .then(r => r.blob())
                .then(blob => {
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = 'mym_cookies.json';
                    a.click();
                });
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/stats')
def api_stats():
    conn = sqlite3.Connection(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.execute("""
        SELECT
            COUNT(*) as total_creators,
            SUM(CASE WHEN classification = 'free' OR is_free_to_message = 1 THEN 1 ELSE 0 END) as free_creators,
            SUM(CASE WHEN classification = 'trial_offer' OR has_free_trial = 1 THEN 1 ELSE 0 END) as trial_creators,
            SUM(CASE WHEN classification = 'paid' THEN 1 ELSE 0 END) as paid_creators
        FROM creators
    """)
    row = cursor.fetchone()
    conn.close()
    return jsonify(dict(row) if row else {})

@app.route('/api/creators')
def api_creators():
    limit = request.args.get('limit', 100, type=int)
    classification = request.args.get('classification')

    conn = sqlite3.Connection(DB_FILE)
    conn.row_factory = sqlite3.Row

    if classification:
        cursor = conn.execute("""
            SELECT * FROM creators WHERE classification = ? ORDER BY last_seen_at DESC LIMIT ?
        """, (classification, limit))
    else:
        cursor = conn.execute("""
            SELECT * FROM creators ORDER BY last_seen_at DESC LIMIT ?
        """, (limit,))

    creators = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return jsonify({"creators": creators})

@app.route('/api/start', methods=['POST'])
def api_start():
    global scraper, scraper_thread, scraper_running

    if scraper_running:
        return jsonify({"message": "Scraper already running"})

    data = request.json
    workers = data.get('workers', 10)
    max_usernames = data.get('max_usernames', 1000)

    # Load wordlist
    wordlist_file = Path(__file__).parent / "wordlist.txt"
    if wordlist_file.exists():
        with open(wordlist_file, 'r') as f:
            wordlist = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    else:
        wordlist = ['marie', 'julie', 'laura', 'sarah', 'emma']

    # Initialize scraper
    scraper = MYMMassScraper(max_workers=workers)
    scraper_running = True

    # Start scraping in background thread
    def scrape_thread():
        global scraper_running
        try:
            scraper.enumerate_usernames(wordlist[:10], max_suffix=min(max_usernames // 10, 100))
        finally:
            scraper_running = False
            socketio.emit('status', {'running': False})

    scraper_thread = threading.Thread(target=scrape_thread, daemon=True)
    scraper_thread.start()

    socketio.emit('status', {'running': True})
    socketio.emit('log', {'timestamp': datetime.now().strftime("%H:%M:%S"), 'level': 'SUCCESS', 'message': 'Scraper started!'})

    return jsonify({"message": "Scraper started successfully"})

@app.route('/api/stop', methods=['POST'])
def api_stop():
    global scraper_running
    scraper_running = False
    return jsonify({"message": "Scraper stopped"})

@app.route('/api/export')
def api_export():
    import csv
    import tempfile

    conn = sqlite3.Connection(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.execute("SELECT * FROM creators")
    creators = [dict(row) for row in cursor.fetchall()]
    conn.close()

    # Create CSV
    tmp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv', newline='')
    if creators:
        writer = csv.DictWriter(tmp_file, fieldnames=creators[0].keys())
        writer.writeheader()
        writer.writerows(creators)
    tmp_file.close()

    return send_file(tmp_file.name, as_attachment=True, download_name='mym_creators.csv')

@app.route('/api/cookies/export')
def api_cookies_export():
    if COOKIE_FILE.exists():
        return send_file(COOKIE_FILE, as_attachment=True, download_name='mym_cookies.json')
    return jsonify({"error": "No cookies found"}), 404

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "service": "mym-hunter-production", "version": "3.0"})

if __name__ == '__main__':
    print("="*80)
    print(" "*20 + "MYM HUNTER - PRODUCTION DASHBOARD v3.0")
    print("="*80)
    print(f"\n🚀 Dashboard: http://0.0.0.0:{PORT}")
    print(f"💚 Health: http://0.0.0.0:{PORT}/health")
    print(f"📊 API: http://0.0.0.0:{PORT}/api/stats")
    print("\n" + "="*80 + "\n")

    socketio.run(app, host='0.0.0.0', port=PORT, debug=False, allow_unsafe_werkzeug=True)
