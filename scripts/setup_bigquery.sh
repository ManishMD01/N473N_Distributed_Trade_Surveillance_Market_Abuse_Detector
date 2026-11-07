#!/bin/bash
set -euo pipefail

# Manual BigQuery setup for this project.
# Creates dataset/table (via bq or prints DDL) and reminds about credentials.
#
# Usage:
#   ./scripts/setup_bigquery.sh --print-ddl
#   GCP_PROJECT=my-project BQ_DATASET=surveillance BQ_LOCATION=US ./scripts/setup_bigquery.sh
#
# Requires: gcloud + bq (Google Cloud SDK) for apply mode, authenticated to GCP_PROJECT.

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ANALYTICS_SQL="$ROOT_DIR/analytics/historical_analytics.sql"

GCP_PROJECT="${GCP_PROJECT:-${BIGQUERY_PROJECT_ID:-your-gcp-project-id}}"
BQ_DATASET="${BQ_DATASET:-${BIGQUERY_DATASET:-surveillance}}"
BQ_TABLE="${BQ_TABLE:-${BIGQUERY_TABLE:-market_abuse_alerts}}"
BQ_LOCATION="${BQ_LOCATION:-${BIGQUERY_LOCATION:-US}}"
PRINT_DDL="${PRINT_DDL:-0}"

log() { printf '[setup_bigquery] %s\n' "$*"; }
err() { printf '[setup_bigquery][ERROR] %s\n' "$*" >&2; }

ddl() {
cat <<SQL
-- BigQuery DDL (project.dataset.table)
CREATE TABLE IF NOT EXISTS \`${GCP_PROJECT}.${BQ_DATASET}.${BQ_TABLE}\` (
  alert_date DATE NOT NULL,
  alert_timestamp TIMESTAMP NOT NULL,
  trader_id STRING NOT NULL,
  symbol STRING NOT NULL,
  window_start TIMESTAMP NOT NULL,
  window_end TIMESTAMP NOT NULL,
  alert_type STRING NOT NULL,
  order_to_trade_ratio FLOAT64 NOT NULL,
  cancellation_rate FLOAT64 NOT NULL,
  avg_execution_horizon_ms FLOAT64 NOT NULL,
  new_order_count INT64 NOT NULL,
  fill_count INT64 NOT NULL,
  cancel_count INT64 NOT NULL,
  alert_severity STRING NOT NULL,
  detection_rule STRING NOT NULL
)
PARTITION BY alert_date
CLUSTER BY trader_id, symbol, alert_type
OPTIONS (
  description = 'Market abuse alerts for spoofing and layering detection - SEC/FINRA compliance',
  partition_expiration_days = 2555,
  require_partition_filter = FALSE
);
SQL
}

if [ "${1:-}" = "--print-ddl" ] || [ "$PRINT_DDL" = "1" ]; then
  ddl
  exit 0
fi

if [ "$GCP_PROJECT" = "your-gcp-project-id" ]; then
  err "Set GCP_PROJECT (or BIGQUERY_PROJECT_ID) to your real GCP project."
  log "To print DDL only: $0 --print-ddl"
  exit 1
fi

if ! command -v bq >/dev/null 2>&1; then
  err "bq not found. Install Google Cloud SDK or run: $0 --print-ddl"
  exit 1
fi

log "Ensuring dataset ${GCP_PROJECT}:${BQ_DATASET} (${BQ_LOCATION})..."
bq --location="$BQ_LOCATION" mk --dataset --description "Trade surveillance analytics" \
  "${GCP_PROJECT}:${BQ_DATASET}" 2>/dev/null || log "Dataset exists or already created."

log "Applying table DDL for ${GCP_PROJECT}.${BQ_DATASET}.${BQ_TABLE}..."
ddl | bq query --project_id="$GCP_PROJECT" --use_legacy_sql=false --nouse_cache

log "Done. Next steps:"
log "  1. Create a service account with BigQuery Data Editor (and Storage if using temp GCS bucket)."
log "  2. Download JSON key and set config/config.yaml -> bigquery.credentials_path (and protect the file; don't commit it)."
log "  3. Set bigquery.project_id/dataset/table/location/temporary_gcs_bucket in config/config.yaml."
log "  4. Historical queries: analytics/historical_analytics.sql uses placeholder project 'your-gcp-project-id.surveillance.market_abuse_alerts' - replace with ${GCP_PROJECT}.${BQ_DATASET}.${BQ_TABLE} or parameterize."
