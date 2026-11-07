<?php
$result = null; $error = null;
$query = isset($_POST['query']) ? trim($_POST['query']) : 'MATCH (n) RETURN labels(n)[0] AS label, count(*) AS count ORDER BY count DESC';
if ($_SERVER['REQUEST_METHOD'] === 'POST' && $query !== '') {
  $url = 'http://127.0.0.1:7474/db/neo4j/tx/commit';
  $payload = json_encode(array('statements' => array(array('statement' => $query, 'resultDataContents' => array('row','graph')))));
  $auth = base64_encode('neo4j:surveillance123');
  $ctx = stream_context_create(array('http' => array('method'=>'POST','header'=>"Content-Type: application/json\r\nAuthorization: Basic $auth\r\n",'content'=>$payload,'timeout'=>15,'ignore_errors'=>true)));
  $resp = @file_get_contents($url, false, $ctx);
  if ($resp === false) $error = 'Could not reach Neo4j HTTP API at 127.0.0.1:7474. Is the container running?';
  else $result = json_decode($resp, true);
}
function neo_cell($v) {
  if ($v === null) return '<span class="text-muted">null</span>';
  if (is_array($v) || is_object($v)) return '<code style="white-space:pre-wrap">'.htmlspecialchars(json_encode($v, JSON_UNESCAPED_SLASHES)).'</code>';
  return htmlspecialchars((string)$v);
}
?>
<div class="alert alert-warning"><strong>Cloud Shell note:</strong> Neo4j Browser <code>:server connect</code> needs Bolt/TCP (:7687), which Web Preview can’t proxy. This HTTP console works in previews.</div>
<div class="card shadow mb-3">
  <div class="card-header py-3"><h6 class="m-0 fw-bold text-primary">Neo4j HTTP Console (Cypher)</h6></div>
  <div class="card-body">
    <form method="post" action="?page=neo4j_console">
      <label class="form-label fw-semibold">Cypher</label>
      <textarea name="query" class="form-control font-monospace" rows="5"><?php echo htmlspecialchars($query); ?></textarea>
      <div class="mt-2 d-flex gap-2 flex-wrap">
        <button class="btn btn-primary">Run</button>
        <button class="btn btn-outline-secondary btn-sm" type="button" onclick="document.querySelector('[name=query]').value='MATCH (n) RETURN labels(n)[0] AS label, count(*) AS count ORDER BY count DESC'">Counts</button>
        <button class="btn btn-outline-secondary btn-sm" type="button" onclick="document.querySelector('[name=query]').value='MATCH (t:Trader)-[r]->(x) RETURN t.trader_id AS trader, type(r) AS rel, labels(x)[0] AS to, coalesce(x.alert_id,x.account_id,x.ip_address,x.symbol,\\'\\') AS id LIMIT 50'">Traders</button>
      </div>
    </form>
  </div>
</div>
<?php if ($error): ?>
  <div class="alert alert-danger"><?php echo htmlspecialchars($error); ?></div>
<?php elseif ($result !== null): ?>
  <?php $errs = isset($result['errors']) ? $result['errors'] : array(); if (!empty($errs)): ?>
    <div class="alert alert-danger"><?php echo htmlspecialchars(json_encode($errs, JSON_UNESCAPED_SLASHES)); ?></div>
  <?php endif; ?>
  <?php $res = (isset($result['results']) && isset($result['results'][0])) ? $result['results'][0] : null; $cols = $res && isset($res['columns']) ? $res['columns'] : array(); $rows = $res && isset($res['data']) ? $res['data'] : array(); ?>
  <ul class="nav nav-tabs" role="tablist">
    <li class="nav-item"><button class="nav-link active" data-bs-toggle="tab" data-bs-target="#neoTabTable" type="button">Table</button></li>
    <li class="nav-item"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#neoTabJson" type="button">JSON</button></li>
  </ul>
  <div class="tab-content card shadow border-top-0 rounded-top-0">
    <div class="tab-pane fade show active p-3" id="neoTabTable">
      <?php if (!empty($cols)): ?>
        <div class="table-responsive" style="max-height:55vh;overflow:auto">
          <table class="table table-sm table-bordered table-striped mb-0">
            <thead><tr><?php foreach ($cols as $c) echo '<th>'.htmlspecialchars($c).'</th>'; ?></tr></thead>
            <tbody>
              <?php if (empty($rows)): ?><tr><td colspan="<?php echo count($cols); ?>" class="text-muted text-center">No rows</td></tr>
              <?php else: foreach ($rows as $r): $row = isset($r['row']) ? $r['row'] : array(); ?>
                <tr><?php foreach ($cols as $i => $_) echo '<td>'.neo_cell(isset($row[$i]) ? $row[$i] : null).'</td>'; ?></tr>
              <?php endforeach; endif; ?>
            </tbody>
          </table>
        </div>
        <div class="text-muted small mt-1"><?php echo count($rows); ?> row(s)</div>
      <?php else: ?>
        <span class="text-muted">Query executed (no tabular columns).</span>
      <?php endif; ?>
    </div>
    <div class="tab-pane fade p-3" id="neoTabJson">
      <pre class="mb-0" style="white-space:pre-wrap;max-height:55vh;overflow:auto"><?php echo htmlspecialchars(json_encode($result, JSON_PRETTY_PRINT|JSON_UNESCAPED_SLASHES)); ?></pre>
    </div>
  </div>
<?php else: ?>
  <div class="card shadow"><div class="card-body text-muted">Ready.</div></div>
<?php endif; ?>
