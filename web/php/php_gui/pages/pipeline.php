<div class="card shadow mb-4">
  <div class="card-header py-3"><h6 class="m-0 fw-bold text-primary">Data Pipeline Status</h6></div>
  <div class="card-body">
    <ul class="list-group">
      <li class="list-group-item d-flex justify-content-between align-items-center">Kafka / Zookeeper (Docker)<span class="badge bg-success">Running</span></li>
      <li class="list-group-item d-flex justify-content-between align-items-center">Neo4j Graph DB<span class="badge bg-success">Running</span></li>
      <li class="list-group-item d-flex justify-content-between align-items-center">FastAPI API (8000)<span class="badge bg-success">Running</span></li>
      <li class="list-group-item d-flex justify-content-between align-items-center">Market Simulator<span class="badge bg-warning text-dark">Manual start</span></li>
      <li class="list-group-item d-flex justify-content-between align-items-center">PySpark Surveillance Pipeline<span class="badge bg-warning text-dark">Manual start</span></li>
      <li class="list-group-item d-flex justify-content-between align-items-center">Graph Loader<span class="badge bg-warning text-dark">Manual start</span></li>
    </ul>
    <p class="mt-3 mb-0 text-muted small">Start pipeline components in separate terminals: <code>python ingestion/market_simulator.py</code>, <code>spark-submit streaming/surveillance_pipeline.py</code>, <code>python graph/graph_loader.py</code>.</p>
  </div>
</div>
