#!/usr/bin/env python3
"""
Web GUI for Distributed Trade Surveillance & Market Abuse Detector
"""
import json
import time
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, request, redirect, url_for
import threading
import random

app = Flask(__name__, template_folder='templates', static_folder='static')

# Mock data for demonstration
alerts_data = [
    {
        "alert_id": "ALT_001",
        "alert_type": "spoofing",
        "status": "open",
        "severity": "high",
        "detected_at": "2024-01-15T10:30:45Z",
        "symbol": "AAPL",
        "trader_ref": "TRADER_REF_abc123",
        "risk_score": 87.5,
        "evidence_count": 5,
        "window_start": "2024-01-15T10:30:00Z",
        "window_end": "2024-01-15T10:30:10Z",
        "notional_value": 2500000.0,
        "order_count": 15,
        "rationale": "Excessive order-to-trade ratio with rapid cancellations",
        "evidence_refs": ["EV_001", "EV_002", "EV_003"]
    },
    {
        "alert_id": "ALT_002", 
        "alert_type": "wash_trade",
        "status": "investigating",
        "severity": "critical",
        "detected_at": "2024-01-15T11:15:20Z",
        "symbol": "TSLA",
        "trader_ref": "TRADER_REF_def456",
        "risk_score": 94.2,
        "evidence_count": 8,
        "window_start": "2024-01-15T11:15:00Z",
        "window_end": "2024-01-15T11:15:30Z",
        "notional_value": 5000000.0,
        "order_count": 12,
        "rationale": "Same buyer/seller within sub-second window",
        "evidence_refs": ["EV_004", "EV_005"]
    }
]

traders_data = [
    {"trader_ref": "TRADER_REF_abc123", "alert_count": 3, "confirmed_count": 1, "total_notional": 7500000, "risk_band": "high", "last_alert": "2024-01-15T10:30:45Z"},
    {"trader_ref": "TRADER_REF_def456", "alert_count": 2, "confirmed_count": 1, "total_notional": 5000000, "risk_band": "critical", "last_alert": "2024-01-15T11:15:20Z"},
    {"trader_ref": "TRADER_REF_ghi789", "alert_count": 1, "confirmed_count": 0, "total_notional": 1200000, "risk_band": "medium", "last_alert": "2024-01-15T09:45:10Z"},
]

market_stats = {
    "total_alerts": 23,
    "open_alerts": 12,
    "critical_alerts": 3,
    "traders_monitored": 156,
    "orders_processed": 145000,
    "detection_rate": 98.7
}



import os
try:
    import requests
except Exception:
    requests = None

API_BASE = os.getenv('API_BASE_URL', 'http://127.0.0.1:8000')

def _fetch(path):
    if not requests:
        return None
    try:
        r = requests.get(f"{API_BASE}{path}", timeout=1.5)
        if r.ok:
            return r.json()
    except Exception:
        return None
    return None

def get_alerts_data():
    data = _fetch('/v1/alerts')
    return data if isinstance(data, list) and data else alerts_data

def get_traders_data():
    data = _fetch('/v1/risk/daily')
    return data if isinstance(data, list) and data else traders_data

def get_stats():
    alerts = get_alerts_data()
    return {
        'total_alerts': len(alerts) if alerts else market_stats['total_alerts'],
        'open_alerts': sum(1 for a in alerts if a.get('status') in ('open','investigating')) if alerts else market_stats['open_alerts'],
        'critical_alerts': sum(1 for a in alerts if a.get('severity')=='critical') if alerts else market_stats['critical_alerts'],
        'traders_monitored': market_stats.get('traders_monitored', 156),
        'orders_processed': market_stats.get('orders_processed', 145000),
        'detection_rate': market_stats.get('detection_rate', 98.7),
    }

@app.route('/')
def dashboard():
    items=get_alerts_data(); t=get_traders_data(); return render_template('dashboard.html', alerts=items[:5], traders=t, stats=get_stats())

@app.route('/alerts')
def alerts():
    status_filter = request.args.get('status')
    type_filter = request.args.get('type')
    symbol_filter = request.args.get('symbol')
    items = get_alerts_data()
    filtered = items
    if status_filter:
        filtered = [a for a in filtered if a.get('status') == status_filter]
    if type_filter:
        filtered = [a for a in filtered if a.get('alert_type') == type_filter]
    if symbol_filter:
        filtered = [a for a in filtered if a.get('symbol') == symbol_filter]
    return render_template('alerts.html', alerts=filtered)

@app.route('/alerts/<alert_id>')
def alert_detail(alert_id):
    alert = next((a for a in get_alerts_data() if a.get('alert_id') == alert_id), None)
    if not alert:
        return redirect(url_for('alerts'))
    return render_template('alert_detail.html', alert=alert)

@app.route('/traders')
def traders():
    return render_template('traders.html', traders=get_traders_data())

@app.route('/pipeline')
def pipeline():
    return render_template('pipeline.html', stats=get_stats())

@app.route('/graph')
def graph():
    return render_template('graph.html')

@app.route('/api-docs')
def api_docs():
    return render_template('api.html')

@app.route('/api/alerts')
def api_alerts():
    return jsonify(get_alerts_data())

@app.route('/api/stats')
def api_stats():
    return jsonify(get_stats())

@app.route('/api/stream')
def api_stream():
    # Simulated real-time data
    data = {
        "timestamp": datetime.now().isoformat(),
        "orders_per_sec": random.randint(800, 1200),
        "active_traders": random.randint(40, 60),
        "alerts_last_min": random.randint(0, 5),
        "kafka_lag": random.randint(0, 100)
    }
    return jsonify(data)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
