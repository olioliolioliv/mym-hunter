#!/usr/bin/env python3
"""
MYM.fans Hunter - Premium Web Dashboard
Award-winning modern interface with glassmorphism design and real-time analytics
"""

import os
from flask import Flask, render_template, jsonify, request, send_file
from pathlib import Path
import json
from datetime import datetime

# Import our scraper
from mym_scraper import MYMScraper

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')

# Get port from environment (Railway sets this)
PORT = int(os.environ.get('PORT', 5000))

@app.route('/')
def index():
    """Premium Dashboard Home"""
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>MYM Hunter - Premium Creator Intelligence</title>
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }

            :root {
                --primary: #ff6b9d;
                --secondary: #c471ed;
                --accent: #12d8fa;
                --dark: #0f0f1e;
                --dark-light: #1a1a2e;
                --glass: rgba(255, 255, 255, 0.1);
                --glass-border: rgba(255, 255, 255, 0.18);
            }

            body {
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
                background: var(--dark);
                color: #fff;
                overflow-x: hidden;
                position: relative;
            }

            /* Animated background */
            .bg-animation {
                position: fixed;
                width: 100vw;
                height: 100vh;
                top: 0;
                left: 0;
                z-index: 0;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
                opacity: 0.15;
            }

            .bg-animation::before {
                content: '';
                position: absolute;
                width: 500px;
                height: 500px;
                background: radial-gradient(circle, var(--primary) 0%, transparent 70%);
                top: -250px;
                left: -250px;
                animation: float 20s ease-in-out infinite;
            }

            .bg-animation::after {
                content: '';
                position: absolute;
                width: 400px;
                height: 400px;
                background: radial-gradient(circle, var(--accent) 0%, transparent 70%);
                bottom: -200px;
                right: -200px;
                animation: float 15s ease-in-out infinite reverse;
            }

            @keyframes float {
                0%, 100% { transform: translate(0, 0) rotate(0deg); }
                33% { transform: translate(100px, -100px) rotate(120deg); }
                66% { transform: translate(-50px, 50px) rotate(240deg); }
            }

            .container {
                position: relative;
                z-index: 1;
                max-width: 1400px;
                margin: 0 auto;
                padding: 40px 20px;
            }

            /* Glassmorphism Cards */
            .glass-card {
                background: var(--glass);
                backdrop-filter: blur(10px);
                border: 1px solid var(--glass-border);
                border-radius: 24px;
                padding: 30px;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.37);
                transition: all 0.3s ease;
            }

            .glass-card:hover {
                transform: translateY(-5px);
                box-shadow: 0 12px 48px rgba(0, 0, 0, 0.5);
                border-color: rgba(255, 255, 255, 0.3);
            }

            /* Header */
            .header {
                text-align: center;
                margin-bottom: 60px;
                animation: fadeInDown 0.8s ease;
            }

            .logo {
                font-size: 4em;
                font-weight: 800;
                background: linear-gradient(135deg, var(--primary), var(--secondary), var(--accent));
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
                margin-bottom: 10px;
                text-shadow: 0 0 30px rgba(255, 107, 157, 0.5);
            }

            .tagline {
                font-size: 1.3em;
                color: rgba(255, 255, 255, 0.8);
                font-weight: 300;
                letter-spacing: 2px;
            }

            /* Stats Grid */
            .stats-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 25px;
                margin-bottom: 50px;
                animation: fadeInUp 0.8s ease 0.2s both;
            }

            .stat-card {
                background: linear-gradient(135deg, var(--glass), rgba(255, 255, 255, 0.05));
                backdrop-filter: blur(10px);
                border: 1px solid var(--glass-border);
                border-radius: 20px;
                padding: 30px;
                text-align: center;
                position: relative;
                overflow: hidden;
                transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            }

            .stat-card::before {
                content: '';
                position: absolute;
                top: 0;
                left: -100%;
                width: 100%;
                height: 100%;
                background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.1), transparent);
                transition: left 0.5s;
            }

            .stat-card:hover::before {
                left: 100%;
            }

            .stat-card:hover {
                transform: scale(1.05) translateY(-5px);
                border-color: rgba(255, 255, 255, 0.4);
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.6);
            }

            .stat-icon {
                font-size: 2.5em;
                margin-bottom: 15px;
                opacity: 0.9;
            }

            .stat-value {
                font-size: 3.5em;
                font-weight: 800;
                background: linear-gradient(135deg, #fff, rgba(255, 255, 255, 0.7));
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                margin: 10px 0;
                line-height: 1;
            }

            .stat-label {
                color: rgba(255, 255, 255, 0.7);
                text-transform: uppercase;
                font-size: 0.85em;
                letter-spacing: 2px;
                font-weight: 600;
            }

            /* Action Buttons */
            .actions {
                animation: fadeInUp 0.8s ease 0.4s both;
                margin-bottom: 50px;
            }

            .actions h2 {
                color: #fff;
                margin-bottom: 25px;
                font-size: 1.8em;
                font-weight: 700;
            }

            .action-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
            }

            .btn {
                background: linear-gradient(135deg, var(--primary), var(--secondary));
                color: white;
                border: none;
                padding: 18px 35px;
                border-radius: 16px;
                font-size: 1em;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s ease;
                text-decoration: none;
                display: inline-block;
                text-align: center;
                position: relative;
                overflow: hidden;
                box-shadow: 0 4px 15px rgba(255, 107, 157, 0.4);
            }

            .btn::before {
                content: '';
                position: absolute;
                top: 50%;
                left: 50%;
                width: 0;
                height: 0;
                border-radius: 50%;
                background: rgba(255, 255, 255, 0.3);
                transform: translate(-50%, -50%);
                transition: width 0.6s, height 0.6s;
            }

            .btn:hover::before {
                width: 300px;
                height: 300px;
            }

            .btn:hover {
                transform: translateY(-3px);
                box-shadow: 0 8px 30px rgba(255, 107, 157, 0.6);
            }

            .btn:active {
                transform: translateY(-1px);
            }

            /* Creators Table */
            .creators-section {
                animation: fadeInUp 0.8s ease 0.6s both;
            }

            .creators-section h2 {
                color: #fff;
                margin-bottom: 25px;
                font-size: 1.8em;
                font-weight: 700;
            }

            .table-container {
                background: var(--glass);
                backdrop-filter: blur(10px);
                border: 1px solid var(--glass-border);
                border-radius: 24px;
                padding: 30px;
                overflow-x: auto;
            }

            table {
                width: 100%;
                border-collapse: separate;
                border-spacing: 0 12px;
            }

            thead tr {
                background: rgba(255, 255, 255, 0.05);
                border-radius: 12px;
            }

            th {
                padding: 18px 20px;
                text-align: left;
                font-weight: 700;
                color: rgba(255, 255, 255, 0.9);
                text-transform: uppercase;
                font-size: 0.85em;
                letter-spacing: 1.5px;
                border: none;
            }

            tbody tr {
                background: rgba(255, 255, 255, 0.03);
                transition: all 0.3s ease;
                border-radius: 12px;
            }

            tbody tr:hover {
                background: rgba(255, 255, 255, 0.08);
                transform: scale(1.01);
                box-shadow: 0 5px 20px rgba(0, 0, 0, 0.3);
            }

            td {
                padding: 18px 20px;
                border: none;
                color: rgba(255, 255, 255, 0.85);
            }

            .avatar {
                width: 50px;
                height: 50px;
                border-radius: 50%;
                object-fit: cover;
                border: 2px solid var(--glass-border);
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
            }

            .badge {
                display: inline-block;
                padding: 6px 16px;
                border-radius: 20px;
                font-size: 0.85em;
                font-weight: 600;
                letter-spacing: 0.5px;
            }

            .badge-unknown {
                background: linear-gradient(135deg, #667eea, #764ba2);
                color: white;
            }

            .badge-free {
                background: linear-gradient(135deg, #11998e, #38ef7d);
                color: white;
            }

            .badge-paid {
                background: linear-gradient(135deg, #667eea, #764ba2);
                color: white;
            }

            .badge-trial {
                background: linear-gradient(135deg, #f093fb, #f5576c);
                color: white;
            }

            .profile-link {
                color: var(--accent);
                text-decoration: none;
                font-weight: 600;
                transition: all 0.3s ease;
                display: inline-flex;
                align-items: center;
                gap: 5px;
            }

            .profile-link:hover {
                color: #fff;
                text-shadow: 0 0 10px var(--accent);
            }

            /* Loading State */
            .loading {
                text-align: center;
                padding: 60px;
            }

            .spinner {
                width: 60px;
                height: 60px;
                border: 4px solid rgba(255, 255, 255, 0.1);
                border-top: 4px solid var(--primary);
                border-radius: 50%;
                animation: spin 1s cubic-bezier(0.68, -0.55, 0.265, 1.55) infinite;
                margin: 0 auto 20px;
            }

            @keyframes spin {
                to { transform: rotate(360deg); }
            }

            /* Animations */
            @keyframes fadeInDown {
                from {
                    opacity: 0;
                    transform: translateY(-30px);
                }
                to {
                    opacity: 1;
                    transform: translateY(0);
                }
            }

            @keyframes fadeInUp {
                from {
                    opacity: 0;
                    transform: translateY(30px);
                }
                to {
                    opacity: 1;
                    transform: translateY(0);
                }
            }

            /* Footer */
            .footer {
                text-align: center;
                margin-top: 80px;
                padding: 40px 0;
                color: rgba(255, 255, 255, 0.6);
                font-size: 0.9em;
                animation: fadeInUp 0.8s ease 0.8s both;
            }

            .footer a {
                color: var(--accent);
                text-decoration: none;
                transition: all 0.3s ease;
            }

            .footer a:hover {
                color: #fff;
                text-shadow: 0 0 10px var(--accent);
            }

            /* Responsive */
            @media (max-width: 768px) {
                .logo { font-size: 2.5em; }
                .tagline { font-size: 1em; }
                .stat-value { font-size: 2.5em; }
                th, td { padding: 12px; }
            }

            /* Pulse animation for live data */
            .live-indicator {
                display: inline-block;
                width: 8px;
                height: 8px;
                background: #38ef7d;
                border-radius: 50%;
                margin-left: 10px;
                animation: pulse 2s ease-in-out infinite;
                box-shadow: 0 0 10px #38ef7d;
            }

            @keyframes pulse {
                0%, 100% { opacity: 1; transform: scale(1); }
                50% { opacity: 0.5; transform: scale(1.2); }
            }
        </style>
    </head>
    <body>
        <div class="bg-animation"></div>

        <div class="container">
            <div class="header">
                <div class="logo">MYM HUNTER</div>
                <div class="tagline">PREMIUM CREATOR INTELLIGENCE PLATFORM<span class="live-indicator"></span></div>
            </div>

            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-icon">👥</div>
                    <div class="stat-value" id="total-creators">-</div>
                    <div class="stat-label">Total Creators</div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon">💚</div>
                    <div class="stat-value" id="free-creators">-</div>
                    <div class="stat-label">Free Access</div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon">💎</div>
                    <div class="stat-value" id="paid-creators">-</div>
                    <div class="stat-label">Premium</div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon">🎁</div>
                    <div class="stat-value" id="trial-creators">-</div>
                    <div class="stat-label">Trial Offers</div>
                </div>
            </div>

            <div class="actions glass-card">
                <h2>Quick Actions</h2>
                <div class="action-grid">
                    <button class="btn" onclick="refreshStats()">🔄 Refresh Data</button>
                    <button class="btn" onclick="exportCSV()">📥 Export CSV</button>
                    <button class="btn" onclick="checkUsername()">🔍 Check Username</button>
                    <a href="/api/docs" class="btn">📚 API Documentation</a>
                </div>
            </div>

            <div class="creators-section">
                <div class="glass-card">
                    <h2>Discovered Creators</h2>
                    <div class="table-container">
                        <div id="creators-list"></div>
                    </div>
                </div>
            </div>

            <div class="footer">
                <p><strong>MYM Hunter</strong> v2.0 - Premium Edition</p>
                <p style="margin-top: 10px;">
                    <a href="https://github.com/olioliolioliv/mym-hunter" target="_blank">GitHub</a> •
                    <a href="/api/docs">API</a> •
                    Built with Flask & Playwright
                </p>
            </div>
        </div>

        <script>
            async function refreshStats() {
                try {
                    const response = await fetch('/api/stats');
                    const stats = await response.json();

                    animateValue('total-creators', 0, stats.total_creators || 0, 1000);
                    animateValue('free-creators', 0, stats.free_creators || 0, 1000);
                    animateValue('paid-creators', 0, stats.paid_creators || 0, 1000);
                    animateValue('trial-creators', 0, stats.trial_creators || 0, 1000);
                } catch (error) {
                    console.error('Error fetching stats:', error);
                }
            }

            function animateValue(id, start, end, duration) {
                const element = document.getElementById(id);
                const range = end - start;
                const increment = range / (duration / 16);
                let current = start;

                const timer = setInterval(() => {
                    current += increment;
                    if ((increment > 0 && current >= end) || (increment < 0 && current <= end)) {
                        current = end;
                        clearInterval(timer);
                    }
                    element.textContent = Math.floor(current);
                }, 16);
            }

            async function loadCreators() {
                const container = document.getElementById('creators-list');
                container.innerHTML = '<div class="loading"><div class="spinner"></div><p>Loading creators...</p></div>';

                try {
                    const response = await fetch('/api/creators?limit=20');
                    const creators = await response.json();

                    if (creators.length === 0) {
                        container.innerHTML = '<p style="text-align: center; padding: 60px; color: rgba(255,255,255,0.5);">No creators discovered yet. Start scraping to populate your database!</p>';
                        return;
                    }

                    let html = `
                        <table>
                            <thead>
                                <tr>
                                    <th>Avatar</th>
                                    <th>Username</th>
                                    <th>Display Name</th>
                                    <th>Status</th>
                                    <th>Profile</th>
                                </tr>
                            </thead>
                            <tbody>
                    `;

                    creators.forEach(creator => {
                        const badgeClass = `badge badge-${creator.classification || 'unknown'}`;
                        const statusText = creator.classification || 'unknown';

                        html += `
                            <tr>
                                <td>
                                    <img src="${creator.avatar_url || ''}"
                                         alt="${creator.username}"
                                         class="avatar"
                                         onerror="this.src='data:image/svg+xml,%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 width=%2750%27 height=%2750%27%3E%3Ccircle cx=%2725%27 cy=%2725%27 r=%2725%27 fill=%27%23667eea%27/%3E%3C/svg%3E'">
                                </td>
                                <td><strong>@${creator.username}</strong></td>
                                <td>${creator.display_name || '-'}</td>
                                <td><span class="${badgeClass}">${statusText.toUpperCase()}</span></td>
                                <td>
                                    <a href="${creator.profile_url}" target="_blank" class="profile-link">
                                        Visit Profile →
                                    </a>
                                </td>
                            </tr>
                        `;
                    });

                    html += '</tbody></table>';
                    container.innerHTML = html;
                } catch (error) {
                    container.innerHTML = '<p style="text-align: center; padding: 60px; color: #f5576c;">Error loading creators. Please try again.</p>';
                    console.error('Error:', error);
                }
            }

            function exportCSV() {
                fetch('/api/export')
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            alert('✅ Export successful! File: ' + data.file);
                        }
                    })
                    .catch(error => {
                        alert('❌ Export failed: ' + error);
                    });
            }

            function checkUsername() {
                const username = prompt('Enter username to check:');
                if (username) {
                    fetch(`/api/check/${encodeURIComponent(username)}`)
                        .then(response => response.json())
                        .then(data => {
                            if (data.exists) {
                                alert(`✅ Username @${username} exists on MYM.fans!`);
                            } else {
                                alert(`❌ Username @${username} not found.`);
                            }
                        })
                        .catch(error => {
                            alert('Error checking username: ' + error);
                        });
                }
            }

            // Initialize
            window.addEventListener('load', () => {
                refreshStats();
                loadCreators();
            });

            // Auto-refresh every 30 seconds
            setInterval(refreshStats, 30000);
        </script>
    </body>
    </html>
    """

@app.route('/api/stats')
def api_stats():
    """Get scraper statistics"""
    try:
        scraper = MYMScraper()
        stats = scraper.get_stats()
        scraper.close()
        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/creators')
def api_creators():
    """Get list of creators"""
    try:
        limit = request.args.get('limit', 100, type=int)
        classification = request.args.get('classification', None)

        scraper = MYMScraper()
        creators = scraper.get_creators(classification=classification, limit=limit)
        scraper.close()
        return jsonify(creators)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/export')
def api_export():
    """Export creators to CSV"""
    try:
        scraper = MYMScraper()
        csv_file = scraper.export_csv("mym_creators_export.csv")
        scraper.close()
        return jsonify({"success": True, "file": str(csv_file)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/check/<username>')
def api_check(username):
    """Check if username exists"""
    try:
        scraper = MYMScraper()
        exists = scraper.check_username_exists(username)
        scraper.close()
        return jsonify({"username": username, "exists": exists})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/docs')
def api_docs():
    """API documentation"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>MYM Hunter API</title>
        <meta charset="utf-8">
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Inter', sans-serif;
                background: #0f0f1e;
                color: #fff;
                padding: 40px 20px;
                line-height: 1.6;
            }
            .container { max-width: 900px; margin: 0 auto; }
            h1 {
                font-size: 2.5em;
                margin-bottom: 10px;
                background: linear-gradient(135deg, #ff6b9d, #c471ed);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }
            .subtitle { color: rgba(255,255,255,0.6); margin-bottom: 40px; }
            .endpoint {
                background: rgba(255, 255, 255, 0.05);
                backdrop-filter: blur(10px);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 16px;
                padding: 25px;
                margin: 20px 0;
            }
            .endpoint h3 {
                color: #12d8fa;
                margin-bottom: 10px;
            }
            code {
                background: rgba(0,0,0,0.3);
                padding: 3px 8px;
                border-radius: 4px;
                font-size: 0.9em;
                color: #ff6b9d;
            }
            a { color: #12d8fa; text-decoration: none; }
            a:hover { text-decoration: underline; }
            ul { margin: 15px 0 15px 30px; }
            li { margin: 8px 0; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>API Documentation</h1>
            <p class="subtitle">RESTful endpoints for MYM Hunter</p>

            <div class="endpoint">
                <h3>GET /api/stats</h3>
                <p>Retrieve current database statistics</p>
                <p><strong>Response:</strong></p>
                <code>{"total_creators": 3, "free_creators": 0, "paid_creators": 0, "trial_creators": 0}</code>
            </div>

            <div class="endpoint">
                <h3>GET /api/creators</h3>
                <p>Get list of discovered creators</p>
                <p><strong>Query Parameters:</strong></p>
                <ul>
                    <li><code>limit</code> (optional, default: 100) - Number of results</li>
                    <li><code>classification</code> (optional) - Filter: free | paid | trial_offer</li>
                </ul>
                <p><strong>Example:</strong> <code>/api/creators?limit=10&classification=free</code></p>
            </div>

            <div class="endpoint">
                <h3>GET /api/check/:username</h3>
                <p>Verify if a username exists on MYM.fans</p>
                <p><strong>Example:</strong> <code>/api/check/Sweetbodymary</code></p>
                <p><strong>Response:</strong> <code>{"username": "Sweetbodymary", "exists": true}</code></p>
            </div>

            <div class="endpoint">
                <h3>GET /api/export</h3>
                <p>Export all creators to CSV format</p>
                <p><strong>Response:</strong> <code>{"success": true, "file": "mym_creators_export.csv"}</code></p>
            </div>

            <p style="margin-top: 40px; text-align: center;">
                <a href="/">← Back to Dashboard</a>
            </p>
        </div>
    </body>
    </html>
    """

@app.route('/health')
def health():
    """Health check for Railway"""
    return jsonify({
        "status": "healthy",
        "service": "mym-hunter",
        "version": "2.0",
        "timestamp": datetime.now().isoformat()
    })

if __name__ == '__main__':
    print("🚀 MYM Hunter Premium Dashboard")
    print(f"📊 Dashboard: http://0.0.0.0:{PORT}")
    print(f"📖 API Docs: http://0.0.0.0:{PORT}/api/docs")
    print(f"💚 Health: http://0.0.0.0:{PORT}/health")
    app.run(host='0.0.0.0', port=PORT, debug=False)
