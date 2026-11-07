<div class="alert alert-warning">
  <strong>Cloud Shell / Web Preview:</strong> Neo4j Browser <code>:server connect</code> uses <strong>Bolt (TCP :7687)</strong>, which Web Preview cannot proxy. Use the <strong>HTTP Graph Console</strong> (works now), or open Neo4j Browser locally via SSH port forwarding.
</div>
<div class="row">
  <div class="col-lg-6 mb-4">
    <div class="card shadow h-100">
      <div class="card-header py-3"><h6 class="m-0 fw-bold text-primary">HTTP Graph Console (works in preview)</h6></div>
      <div class="card-body">
        <p>Runs Cypher via Neo4j’s HTTP transactional API (no Bolt).</p>
        <a class="btn btn-primary" href="?page=neo4j_console">Open Graph Console</a>
        <p class="mt-3 text-muted small mb-0">Uses <code>http://127.0.0.1:7474</code> with <code>neo4j/surveillance123</code>.</p>
      </div>
    </div>
  </div>
  <div class="col-lg-6 mb-4">
    <div class="card shadow h-100">
      <div class="card-header py-3"><h6 class="m-0 fw-bold text-primary">Neo4j Browser (requires Bolt/TCP)</h6></div>
      <div class="card-body">
        <a class="btn btn-outline-primary me-2" href="http://localhost:7475/browser/" target="_blank" rel="noopener">Preview UI (:7475)</a>
        <a class="btn btn-outline-secondary" href="http://localhost:7474/browser/" target="_blank" rel="noopener">Direct (:7474)</a>
        <hr>
        <div class="small text-muted">
          <div><strong>Full Browser locally:</strong></div>
          <code>gcloud cloud-shell ssh --authorize-session -- -N -L 7474:localhost:7474 -L 7687:localhost:7687</code>
          <div class="mt-1">Open <code>http://localhost:7474/browser/</code>, <code>:server connect</code> → <code>bolt://localhost:7687</code> (neo4j/surveillance123).</div>
          <div class="mt-2"><strong>CLI:</strong> <code>docker exec -it trade_surveillance_neo4j cypher-shell -u neo4j -p surveillance123</code></div>
        </div>
      </div>
    </div>
  </div>
</div>
