<div class="card shadow mb-4">
  <div class="card-header py-3"><h6 class="m-0 fw-bold text-primary">API Endpoints</h6></div>
  <div class="card-body">
    <p>FastAPI provides privacy-preserving compliance endpoints.</p>
    <div class="table-responsive">
      <table class="table table-bordered">
        <thead><tr><th>Endpoint</th><th>Description</th></tr></thead>
        <tbody>
          <tr><td><a href="http://localhost:8000/docs" target="_blank">GET /docs</a></td><td>OpenAPI / Swagger UI</td></tr>
          <tr><td><a href="http://localhost:8000/healthz" target="_blank">GET /healthz</a></td><td>Health check</td></tr>
          <tr><td><code>GET /v1/alerts</code></td><td>List redacted alerts (filters: status, alert_type, symbol, since, limit)</td></tr>
          <tr><td><code>GET /v1/alerts/{alert_id}</code></td><td>Alert detail</td></tr>
          <tr><td><code>GET /v1/risk/daily</code></td><td>Daily trader risk aggregates (as_of, trader_ref, limit)</td></tr>
        </tbody>
      </table>
    </div>
    <p class="text-muted small mb-0">Note: <code>/v1/alerts</code> returns live API data (currently empty until alerts are ingested). Dashboard subscreens show demo data when the API has no records.</p>
  </div>
</div>
