#!/bin/bash
set -euo pipefail

# Manual TimescaleDB/PostgreSQL setup for this project.
# Creates role/database (if missing) and applies db/schema.sql.
#
# Usage:
#   ./scripts/setup_timescaledb.sh
#   DB_HOST=localhost DB_PORT=5432 DB_SUPERUSER=postgres DB_NAME=surveillance \
#   DB_USER=surveillance DB_PASSWORD='change_me' ./scripts/setup_timescaledb.sh
#
# Notes:
# - Requires psql (postgresql-client). TimescaleDB extension is optional but recommended.
# - If you run as a non-superuser without createdb/createrole, run the GRANT/CREATE steps
#   manually as a superuser, then re-run with SKIP_CREATE=1.

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SCHEMA_FILE="$ROOT_DIR/db/schema.sql"

DB_HOST="${DB_HOST:-${POSTGRES_HOST:-localhost}}"
DB_PORT="${DB_PORT:-${POSTGRES_PORT:-5432}}"
DB_SUPERUSER="${DB_SUPERUSER:-${POSTGRES_SUPERUSER:-postgres}}"
DB_NAME="${DB_NAME:-${POSTGRES_DB:-surveillance}}"
DB_USER="${DB_USER:-${POSTGRES_USER:-surveillance}}"
DB_PASSWORD="${DB_PASSWORD:-${POSTGRES_PASSWORD:-surveillance}}"
SKIP_CREATE="${SKIP_CREATE:-0}"

log() { printf '[setup_timescaledb] %s\n' "$*"; }
err() { printf '[setup_timescaledb][ERROR] %s\n' "$*" >&2; }

if ! command -v psql >/dev/null 2>&1; then
  err "psql not found. Install PostgreSQL client (e.g., sudo apt-get install -y postgresql-client)."
  exit 1
fi
if [ ! -f "$SCHEMA_FILE" ]; then
  err "Schema file not found: $SCHEMA_FILE"
  exit 1
fi

export PGPASSWORD="${PGPASSWORD:-}"
PSQL_SUPER=(psql -v ON_ERROR_STOP=1 -h "$DB_HOST" -p "$DB_PORT" -U "$DB_SUPERUSER")

log "Target: postgresql://$DB_USER@${DB_HOST}:${DB_PORT}/${DB_NAME} (admin: $DB_SUPERUSER)"

if [ "$SKIP_CREATE" != "1" ]; then
  log "Ensuring role/database exist..."
  "${PSQL_SUPER[@]}" -d postgres <<SQL
DO \$\$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '${DB_USER}') THEN
    CREATE ROLE ${DB_USER} LOGIN PASSWORD '${DB_PASSWORD}';
  END IF;
END
\$\$;

SELECT 'CREATE DATABASE ${DB_NAME} OWNER ${DB_USER}'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '${DB_NAME}')\gexec

GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};
SQL
else
  log "SKIP_CREATE=1: skipping role/database creation."
fi

log "Applying schema to ${DB_NAME}..."
"${PSQL_SUPER[@]}" -d "$DB_NAME" <<'SQL'
-- Enable TimescaleDB if available (safe to skip on plain PostgreSQL)
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_available_extensions WHERE name = 'timescaledb') THEN
    CREATE EXTENSION IF NOT EXISTS timescaledb;
  END IF;
END
$$;
SQL

"${PSQL_SUPER[@]}" -d "$DB_NAME" -f "$SCHEMA_FILE"

# Grant app user access to created objects
"${PSQL_SUPER[@]}" -d "$DB_NAME" <<SQL
GRANT USAGE ON SCHEMA public TO ${DB_USER};
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO ${DB_USER};
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO ${DB_USER};
SQL

log "Verifying..."
PGPASSWORD="$DB_PASSWORD" psql -v ON_ERROR_STOP=1 -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "\\dt" | sed -n '1,20p'

log "Done. Update config/config.yaml (timescaledb.connection_string) or env vars:"
log "  POSTGRES_HOST=$DB_HOST POSTGRES_PORT=$DB_PORT POSTGRES_DB=$DB_NAME POSTGRES_USER=$DB_USER POSTGRES_PASSWORD=***"
