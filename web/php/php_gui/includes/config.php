<?php
// Configuration for Trade Surveillance Dashboard
define('SITE_NAME', 'Trade Surveillance & Market Abuse Detector');
define('API_BASE_URL', 'http://localhost:8000/v1');

// Mock data configuration
$GLOBALS['alerts'] = [
    [
        "alert_id" => "ALT_001",
        "alert_type" => "spoofing",
        "status" => "open",
        "severity" => "high",
        "detected_at" => "2024-01-15T10:30:45Z",
        "symbol" => "AAPL",
        "trader_ref" => "TRADER_REF_abc123",
        "risk_score" => 87.5,
        "evidence_count" => 5,
        "window_start" => "2024-01-15T10:30:00Z",
        "window_end" => "2024-01-15T10:30:10Z",
        "notional_value" => 2500000.0,
        "order_count" => 15,
        "rationale" => "Excessive order-to-trade ratio with rapid cancellations",
        "evidence_refs" => ["EV_001", "EV_002", "EV_003"]
    ],
    [
        "alert_id" => "ALT_002",
        "alert_type" => "wash_trade",
        "status" => "investigating",
        "severity" => "critical",
        "detected_at" => "2024-01-15T11:15:20Z",
        "symbol" => "TSLA",
        "trader_ref" => "TRADER_REF_def456",
        "risk_score" => 94.2,
        "evidence_count" => 8,
        "window_start" => "2024-01-15T11:15:00Z",
        "window_end" => "2024-01-15T11:15:30Z",
        "notional_value" => 5000000.0,
        "order_count" => 12,
        "rationale" => "Same buyer/seller within sub-second window",
        "evidence_refs" => ["EV_004", "EV_005"]
    ],
    [
        "alert_id" => "ALT_003",
        "alert_type" => "spoofing",
        "status" => "confirmed",
        "severity" => "critical",
        "detected_at" => "2024-01-15T12:45:10Z",
        "symbol" => "NVDA",
        "trader_ref" => "TRADER_REF_ghi789",
        "risk_score" => 91.8,
        "evidence_count" => 6,
        "window_start" => "2024-01-15T12:45:00Z",
        "window_end" => "2024-01-15T12:45:08Z",
        "notional_value" => 3200000.0,
        "order_count" => 20,
        "rationale" => "Layering pattern detected with fake depth",
        "evidence_refs" => ["EV_006", "EV_007", "EV_008"]
    ]
];

$GLOBALS['traders'] = [
    ["trader_ref" => "TRADER_REF_abc123", "alert_count" => 3, "confirmed_count" => 1, "total_notional" => 7500000, "risk_band" => "high", "last_alert" => "2024-01-15T10:30:45Z"],
    ["trader_ref" => "TRADER_REF_def456", "alert_count" => 2, "confirmed_count" => 1, "total_notional" => 5000000, "risk_band" => "critical", "last_alert" => "2024-01-15T11:15:20Z"],
    ["trader_ref" => "TRADER_REF_ghi789", "alert_count" => 1, "confirmed_count" => 1, "total_notional" => 3200000, "risk_band" => "critical", "last_alert" => "2024-01-15T12:45:10Z"],
];

$GLOBALS['stats'] = [
    "total_alerts" => 23,
    "open_alerts" => 12,
    "critical_alerts" => 3,
    "traders_monitored" => 156,
    "orders_processed" => 145000,
    "detection_rate" => 98.7
];
?>
