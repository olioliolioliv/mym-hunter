#!/usr/bin/env python3
"""
MYM.fans Hunter - Web Dashboard
Simple Flask web interface for the MYM.fans creator hunter
"""

import os
from flask import Flask, render_template, jsonify, request
from pathlib import Path
import json

# Import our scraper
from mym_scraper import MYMScraper

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')

# Get port from environment (Railway sets this)
PORT = int(os.environ.get('PORT', 5000))

@app.route('/')
def index():
    """Home page"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>MYM.fans Hunter</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
                color: #333;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
            }
            .header {
                background: white;
                padding: 30px;
                border-radius: 12px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                margin-bottom: 30px;
                text-align: center;
            }
            h1 {
                color: #667eea;
                font-size: 2.5em;
                margin-bottom: 10px;
            }
            .subtitle {
                color: #666;
                font-size: 1.1em;
            }
            .stats {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }
            .stat-card {
                background: white;
                padding: 25px;
                border-radius: 12px;
                box-shadow: 0 5px 15px rgba(0,0,0,0.1);
                text-align: center;
            }
            .stat-value {
                font-size: 3em;
                font-weight: bold;
                color: #667eea;
                margin: 10px 0;
            }
            .stat-label {
                color: #666;
                font-size: 0.9em;
                text-transform: uppercase;
                letter-spacing: 1px;
            }
            .actions {
                background: white;
                padding: 30px;
                border-radius: 12px;
                box-shadow: 0 5px 15px rgba(0,0,0,0.1);
                margin-bottom: 30px;
            }
            .action-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin-top: 20px;
            }
            button, .btn {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                padding: 15px 30px;
                border-radius: 8px;
                font-size: 1em;
                cursor: pointer;
                transition: transform 0.2s, box-shadow 0.2s;
                text-decoration: none;
                display: inline-block;
                text-align: center;
            }
            button:hover, .btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
            }
            button:disabled {
                opacity: 0.5;
                cursor: not-allowed;
            }
            .creators-table {
                background: white;
                padding: 30px;
                border-radius: 12px;
                box-shadow: 0 5px 15px rgba(0,0,0,0.1);
                overflow-x: auto;
            }
            table {
                width: 100%;
                border-collapse: collapse;
            }
            th, td {
                padding: 12px;
                text-align: left;
                border-bottom: 1px solid #eee;
            }
            th {
                background: #f8f9fa;
                font-weight: 600;
                color: #667eea;
            }
            tr:hover {
                background: #f8f9fa;
            }
            .avatar {
                width: 40px;
                height: 40px;
                border-radius: 50%;
                object-fit: cover;
            }
            .status {
                display: inline-block;
                padding: 4px 12px;
                border-radius: 12px;
                font-size: 0.85em;
                font-weight: 500;
            }
            .status-unknown { background: #e9ecef; color: #495057; }
            .status-free { background: #d4edda; color: #155724; }
            .status-paid { background: #cce5ff; color: #004085; }
            .loading {
                text-align: center;
                padding: 40px;
                color: #666;
            }
            .spinner {
                border: 3px solid #f3f3f3;
                border-top: 3px solid #667eea;
                border-radius: 50%;
                width: 40px;
                height: 40px;
                animation: spin 1s linear infinite;
                margin: 20px auto;
            }
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            .footer {
                text-align: center;
                color: white;
                margin-top: 40px;
                opacity: 0.9;
            }
            .footer a {
                color: white;
                text-decoration: underline;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🔍 MYM.fans Hunter</h1>
                <p class="subtitle">Creator Discovery & Lead Generation Dashboard</p>
            </div>

            <div class="stats" id="stats">
                <div class="stat-card">
                    <div class="stat-label">Total Creators</div>
                    <div class="stat-value" id="total-creators">-</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Free Creators</div>
                    <div class="stat-value" id="free-creators">-</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Paid Creators</div>
                    <div class="stat-value" id="paid-creators">-</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Trial Offers</div>
                    <div class="stat-value" id="trial-creators">-</div>
                </div>
            </div>

            <div class="actions">
                <h2 style="margin-bottom: 20px;">Quick Actions</h2>
                <div class="action-grid">
                    <button onclick="refreshStats()">🔄 Refresh Stats</button>
                    <button onclick="exportCSV()">📥 Export CSV</button>
                    <button onclick="checkUsername()">🔍 Check Username</button>
                    <a href="/api/docs" class="btn" style="display: block;">📖 API Docs</a>
                </div>
            </div>

            <div class="creators-table">
                <h2 style="margin-bottom: 20px;">Recent Creators</h2>
                <div id="creators-list"></div>
            </div>

            <div class="footer">
                <p>MYM.fans Hunter v1.0 | <a href="https://github.com/olioliolioliv/mym-hunter" target="_blank">GitHub</a></p>
                <p style="font-size: 0.9em; margin-top: 10px;">Built with Flask • Powered by Playwright & BeautifulSoup</p>
            </div>
        </div>

        <script>
            async function refreshStats() {
                try {
                    const response = await fetch('/api/stats');
                    const stats = await response.json();

                    document.getElementById('total-creators').textContent = stats.total_creators || 0;
                    document.getElementById('free-creators').textContent = stats.free_creators || 0;
                    document.getElementById('paid-creators').textContent = stats.paid_creators || 0;
                    document.getElementById('trial-creators').textContent = stats.trial_creators || 0;
                } catch (error) {
                    console.error('Error fetching stats:', error);
                }
            }

            async function loadCreators() {
                const container = document.getElementById('creators-list');
                container.innerHTML = '<div class="loading"><div class="spinner"></div><p>Loading creators...</p></div>';

                try {
                    const response = await fetch('/api/creators?limit=20');
                    const creators = await response.json();

                    if (creators.length === 0) {
                        container.innerHTML = '<p style="text-align: center; color: #666; padding: 40px;">No creators found. Start scraping to discover creators!</p>';
                        return;
                    }

                    let html = '<table><thead><tr><th>Avatar</th><th>Username</th><th>Display Name</th><th>Classification</th><th>Actions</th></tr></thead><tbody>';

                    creators.forEach(creator => {
                        const statusClass = `status-${creator.classification || 'unknown'}`;
                        html += `
                            <tr>
                                <td><img src="${creator.avatar_url || ''}" alt="${creator.username}" class="avatar" onerror="this.src='data:image/svg+xml,%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 width=%2740%27 height=%2740%27%3E%3Crect fill=%27%23ddd%27 width=%2740%27 height=%2740%27/%3E%3C/svg%3E'"></td>
                                <td><strong>@${creator.username}</strong></td>
                                <td>${creator.display_name || '-'}</td>
                                <td><span class="status ${statusClass}">${creator.classification || 'unknown'}</span></td>
                                <td><a href="${creator.profile_url}" target="_blank" style="color: #667eea;">Visit Profile →</a></td>
                            </tr>
                        `;
                    });

                    html += '</tbody></table>';
                    container.innerHTML = html;
                } catch (error) {
                    container.innerHTML = '<p style="text-align: center; color: #dc3545; padding: 40px;">Error loading creators</p>';
                    console.error('Error fetching creators:', error);
                }
            }

            function exportCSV() {
                window.location.href = '/api/export';
            }

            function checkUsername() {
                const username = prompt('Enter username to check:');
                if (username) {
                    window.location.href = `/api/check/${encodeURIComponent(username)}`;
                }
            }

            // Load data on page load
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
        <title>MYM Hunter API Docs</title>
        <style>
            body { font-family: monospace; max-width: 800px; margin: 40px auto; padding: 20px; }
            h1 { color: #667eea; }
            .endpoint { background: #f5f5f5; padding: 15px; margin: 20px 0; border-radius: 5px; }
            code { background: #e9ecef; padding: 2px 6px; border-radius: 3px; }
        </style>
    </head>
    <body>
        <h1>MYM.fans Hunter API Documentation</h1>

        <div class="endpoint">
            <h3>GET /api/stats</h3>
            <p>Get scraper statistics</p>
            <p><strong>Response:</strong> <code>{"total_creators": 3, "free_creators": 0, ...}</code></p>
        </div>

        <div class="endpoint">
            <h3>GET /api/creators</h3>
            <p>Get list of creators</p>
            <p><strong>Parameters:</strong></p>
            <ul>
                <li><code>limit</code> (optional, default: 100) - Number of creators to return</li>
                <li><code>classification</code> (optional) - Filter by classification (free/paid/trial_offer)</li>
            </ul>
            <p><strong>Example:</strong> <code>/api/creators?limit=10&classification=free</code></p>
        </div>

        <div class="endpoint">
            <h3>GET /api/check/:username</h3>
            <p>Check if a username exists</p>
            <p><strong>Example:</strong> <code>/api/check/Sweetbodymary</code></p>
            <p><strong>Response:</strong> <code>{"username": "Sweetbodymary", "exists": true}</code></p>
        </div>

        <div class="endpoint">
            <h3>GET /api/export</h3>
            <p>Export all creators to CSV</p>
            <p><strong>Response:</strong> <code>{"success": true, "file": "mym_creators_export.csv"}</code></p>
        </div>

        <p><a href="/">← Back to Dashboard</a></p>
    </body>
    </html>
    """

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "service": "mym-hunter"})

if __name__ == '__main__':
    # Run the Flask app
    print(f"🚀 Starting MYM.fans Hunter Dashboard on port {PORT}")
    print(f"📊 Dashboard: http://0.0.0.0:{PORT}")
    print(f"📖 API Docs: http://0.0.0.0:{PORT}/api/docs")
    app.run(host='0.0.0.0', port=PORT, debug=False)
