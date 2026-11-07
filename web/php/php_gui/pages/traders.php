<?php
$traders = isset($GLOBALS['traders']) ? $GLOBALS['traders'] : array();
?>
<div class="card shadow mb-4">
  <div class="card-header py-3"><h6 class="m-0 fw-bold text-primary">Trader Risk Analysis</h6></div>
  <div class="card-body">
    <div class="table-responsive">
      <table class="table table-bordered table-hover" width="100%">
        <thead><tr><th>Trader</th><th>Alert Count</th><th>Confirmed</th><th>Total Notional</th><th>Risk Band</th><th>Last Alert</th></tr></thead>
        <tbody>
        <?php if (empty($traders)): ?>
          <tr><td colspan="6" class="text-center text-muted">No trader data available</td></tr>
        <?php else: foreach ($traders as $t): ?>
          <tr>
            <td><code><?php echo htmlspecialchars($t['trader_ref']); ?></code></td>
            <td><?php echo (int)$t['alert_count']; ?></td>
            <td><?php echo (int)$t['confirmed_count']; ?></td>
            <td>$<?php echo number_format($t['total_notional']); ?></td>
            <td><?php echo getSeverityBadge($t['risk_band']); ?></td>
            <td class="text-muted"><?php echo htmlspecialchars($t['last_alert']); ?></td>
          </tr>
        <?php endforeach; endif; ?>
        </tbody>
      </table>
    </div>
  </div>
</div>
