<?php
$alerts = isset($GLOBALS['alerts']) ? $GLOBALS['alerts'] : array();
?>
<div class="card shadow mb-4">
  <div class="card-header py-3"><h6 class="m-0 fw-bold text-primary">Market Abuse Alerts</h6></div>
  <div class="card-body">
    <div class="table-responsive">
      <table class="table table-bordered table-hover" width="100%">
        <thead><tr><th>Alert ID</th><th>Type</th><th>Status</th><th>Severity</th><th>Symbol</th><th>Trader</th><th>Detected</th></tr></thead>
        <tbody>
        <?php if (empty($alerts)): ?>
          <tr><td colspan="7" class="text-center text-muted">No alerts found</td></tr>
        <?php else: foreach ($alerts as $a): ?>
          <tr>
            <td><strong class="text-primary"><?php echo htmlspecialchars($a['alert_id']); ?></strong></td>
            <td><?php echo htmlspecialchars($a['alert_type']); ?></td>
            <td><?php echo getStatusBadge($a['status']); ?></td>
            <td><?php echo getSeverityBadge($a['severity']); ?></td>
            <td><?php echo htmlspecialchars($a['symbol']); ?></td>
            <td><code><?php echo htmlspecialchars($a['trader_ref']); ?></code></td>
            <td class="text-muted"><?php echo htmlspecialchars($a['detected_at']); ?></td>
          </tr>
        <?php endforeach; endif; ?>
        </tbody>
      </table>
    </div>
  </div>
</div>
