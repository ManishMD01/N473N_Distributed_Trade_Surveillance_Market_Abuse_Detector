<?php
function getPageTitle($page) {
    $titles = [
        'dashboard' => 'Surveillance Dashboard',
        'alerts' => 'Market Abuse Alerts',
        'traders' => 'Trader Risk Analysis',
        'pipeline' => 'Data Pipeline Status',
        'graph' => 'Graph Analysis & Collusion Detection',
        'api' => 'API Endpoints'
    ];
    return isset($titles[$page]) ? $titles[$page] : 'Dashboard';
}

function getSeverityBadge($severity) {
    switch($severity) {
        case 'critical':
            return '<span class="badge bg-danger">Critical</span>';
        case 'high':
            return '<span class="badge bg-warning text-dark">High</span>';
        case 'medium':
            return '<span class="badge bg-info">Medium</span>';
        case 'low':
            return '<span class="badge bg-success">Low</span>';
        default:
            return '<span class="badge bg-secondary">' . $severity . '</span>';
    }
}

function getStatusBadge($status) {
    switch($status) {
        case 'open':
            return '<span class="badge bg-danger">Open</span>';
        case 'investigating':
            return '<span class="badge bg-warning text-dark">Investigating</span>';
        case 'confirmed':
            return '<span class="badge bg-dark">Confirmed</span>';
        case 'dismissed':
            return '<span class="badge bg-success">Dismissed</span>';
        default:
            return '<span class="badge bg-secondary">' . $status . '</span>';
    }
}
?>
