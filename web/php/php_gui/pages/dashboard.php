<?php
$alerts = isset($GLOBALS['alerts']) ? $GLOBALS['alerts'] : array();
$traders = isset($GLOBALS['traders']) ? $GLOBALS['traders'] : array();
$stats = isset($GLOBALS['stats']) ? $GLOBALS['stats'] : array('total_alerts'=>23,'open_alerts'=>12,'critical_alerts'=>3,'orders_processed'=>145000,'detection_rate'=>98.7);
?>
<div class="row mb-4">
    <div class="col-xl-3 col-md-6 mb-4">
        <div class="card stat-card h-100">
            <div class="card-body">
                <div class="d-flex align-items-center justify-content-between">
                    <div>
                        <div class="text-xs mb-1">Total Alerts</div>
                        <div class="h5 mb-0"><?php echo $stats['total_alerts']; ?></div>
                    </div>
                    <div class="opacity-75"><i class="fas fa-triangle-exclamation fa-2x"></i></div>
                </div>
            </div>
        </div>
    </div>
    <div class="col-xl-3 col-md-6 mb-4">
        <div class="card h-100" style="background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); color: white; border: none;">
            <div class="card-body">
                <div class="d-flex align-items-center justify-content-between">
                    <div>
                        <div class="text-xs mb-1" style="opacity: 0.9;">Open Alerts</div>
                        <div class="h5 mb-0"><?php echo $stats['open_alerts']; ?></div>
                    </div>
                    <div class="opacity-75"><i class="fas fa-bell fa-2x"></i></div>
                </div>
            </div>
        </div>
    </div>
    <div class="col-xl-3 col-md-6 mb-4">
        <div class="card h-100" style="background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%); color: white; border: none;">
            <div class="card-body">
                <div class="d-flex align-items-center justify-content-between">
                    <div>
                        <div class="text-xs mb-1" style="opacity: 0.9;">Critical Alerts</div>
                        <div class="h5 mb-0"><?php echo $stats['critical_alerts']; ?></div>
                    </div>
                    <div class="opacity-75"><i class="fas fa-skull-crossbones fa-2x"></i></div>
                </div>
            </div>
        </div>
    </div>
    <div class="col-xl-3 col-md-6 mb-4">
        <div class="card h-100" style="background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: white; border: none;">
            <div class="card-body">
                <div class="d-flex align-items-center justify-content-between">
                    <div>
                        <div class="text-xs mb-1" style="opacity: 0.9;">Orders Processed</div>
                        <div class="h5 mb-0"><?php echo number_format($stats['orders_processed']); ?></div>
                    </div>
                    <div class="opacity-75"><i class="fas fa-chart-bar fa-2x"></i></div>
                </div>
            </div>
        </div>
    </div>
</div>

<div class="row">
    <div class="col-lg-8 mb-4">
        <div class="card h-100">
            <div class="card-header d-flex justify-content-between align-items-center">
                <h6 class="mb-0"><i class="fas fa-clock-rotate-left me-2 text-primary"></i>Recent Alerts</h6>
                <a href="?page=alerts" class="btn btn-sm btn-primary">View All <i class="fas fa-arrow-right ms-1"></i></a>
            </div>
            <div class="card-body p-0">
                <div class="table-responsive">
                    <table class="table table-hover mb-0">
                        <thead>
                            <tr>
                                <th>Alert ID</th><th>Type</th><th>Symbol</th><th>Severity</th><th>Status</th><th>Detected</th><th></th>
                            </tr>
                        </thead>
                        <tbody>
                            <?php foreach(array_slice($alerts, 0, 3) as $alert): ?>
                            <tr class="alert-<?php echo $alert['severity']; ?>">
                                <td><strong class="text-primary"><?php echo $alert['alert_id']; ?></strong></td>
                                <td><?php if($alert['alert_type']=='spoofing'): ?><span class="badge bg-warning text-dark"><i class="fas fa-ghost me-1"></i>Spoofing</span><?php else: ?><span class="badge bg-danger"><i class="fas fa-exchange-alt me-1"></i>Wash Trade</span><?php endif; ?></td>
                                <td><strong><?php echo $alert['symbol']; ?></strong></td>
                                <td><?php echo getSeverityBadge($alert['severity']); ?></td>
                                <td><?php echo getStatusBadge($alert['status']); ?></td>
                                <td class="text-muted"><?php echo date('H:i:s', strtotime($alert['detected_at'])); ?></td>
                                <td><a href="?page=alerts" class="btn btn-sm btn-outline-primary"><i class="fas fa-eye"></i></a></td>
                            </tr>
                            <?php endforeach; ?>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
    <div class="col-lg-4 mb-4">
        <div class="card h-100">
            <div class="card-header"><h6 class="mb-0"><i class="fas fa-server me-2 text-success"></i>System Status</h6></div>
            <div class="card-body">
                <div class="mb-3"><div class="d-flex justify-content-between mb-1"><small class="text-muted">Kafka Stream</small><small class="text-success fw-semibold">Active</small></div><div class="progress" style="height:6px;"><div class="progress-bar bg-success" style="width:95%"></div></div></div>
                <div class="mb-3"><div class="d-flex justify-content-between mb-1"><small class="text-muted">PySpark Pipeline</small><small class="text-success fw-semibold">Running</small></div><div class="progress" style="height:6px;"><div class="progress-bar bg-success" style="width:98%"></div></div></div>
                <div class="mb-3"><div class="d-flex justify-content-between mb-1"><small class="text-muted">Neo4j Graph DB</small><small class="text-success fw-semibold">Connected</small></div><div class="progress" style="height:6px;"><div class="progress-bar bg-success" style="width:100%"></div></div></div>
                <div class="mb-3"><div class="d-flex justify-content-between mb-1"><small class="text-muted">Detection Rate</small><small class="fw-semibold"><?php echo $stats['detection_rate']; ?>%</small></div><div class="progress" style="height:6px;"><div class="progress-bar bg-primary" style="width:<?php echo $stats['detection_rate']; ?>%"></div></div></div>
                <hr>
                <div class="row text-center">
                    <div class="col-6"><div class="h6 mb-0 text-primary">156</div><small class="text-muted">Traders Monitored</small></div>
                    <div class="col-6"><div class="h6 mb-0 text-success">98.7%</div><small class="text-muted">Accuracy</small></div>
                </div>
            </div>
        </div>
    </div>
</div>
