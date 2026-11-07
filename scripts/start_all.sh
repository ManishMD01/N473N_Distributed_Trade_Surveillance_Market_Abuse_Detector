#!/bin/bash
set -uo pipefail

cd "$(dirname "$0")/.."
ROOT_DIR="$(pwd)"

log() { printf '[start_all] %s\n' "$*"; }
err() { printf '[start_all][ERROR] %s\n' "$*" >&2; }

port_in_use() {
  local port="$1"
  ss -tlnp 2>/dev/null | grep -q ":${port} " && return 0
  return 1
}

port_pid_hint() {
  local port="$1"
  ss -tlnp 2>/dev/null | grep ":${port} " | sed -n '1p' || true
}

require_port_free() {
  local port="$1" name="$2"
  if port_in_use "$port"; then
    err "Port ${port} (${name}) is already in use: $(port_pid_hint "$port")"
    err "Stop the conflicting process or run ./scripts/stop_all.sh, then retry."
    return 1
  fi
  return 0
}

wait_for_port() {
  local port="$1" name="$2" tries="${3:-15}"
  local i
  for i in $(seq 1 "$tries"); do
    if port_in_use "$port"; then
      log "${name} listening on port ${port}"
      return 0
    fi
    sleep 1
  done
  err "${name} did not start on port ${port}. Check its log."
  return 1
}

log "Stopping existing app services (if any)..."
pkill -f "uvicorn app.main:app|web/flask/gui_app.py|php -S .*:8080" 2>/dev/null || true
sleep 1

APP_PORTS=(8000 5000 8080)
APP_NAMES=("FastAPI" "Flask GUI" "PHP GUI")
FAIL=0
for i in "${!APP_PORTS[@]}"; do
  if ! require_port_free "${APP_PORTS[$i]}" "${APP_NAMES[$i]}"; then
    FAIL=1
  fi
done
if [ "$FAIL" -ne 0 ]; then
  err "One or more app ports are unavailable. Aborting before partial startup."
  exit 1
fi

log "Starting infrastructure..."
docker compose -f infra/docker-compose.yml up -d
log "Waiting for infrastructure to initialize..."
sleep 30

source .venv/bin/activate 2>/dev/null || true

log "Starting FastAPI (8000)..."
nohup python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 > /tmp/fastapi.log 2>&1 &
FASTAPI_PID=$!

log "Starting Flask GUI (5000)..."
nohup python web/flask/gui_app.py > /tmp/flask.log 2>&1 &
FLASK_PID=$!

log "Starting PHP GUI (8080)..."
nohup php -S 127.0.0.1:8080 -t "$ROOT_DIR/web/php/php_gui" > /tmp/php.log 2>&1 &
PHP_PID=$!

wait_for_port 8000 "FastAPI" 20 || true
wait_for_port 5000 "Flask GUI" 20 || true
wait_for_port 8080 "PHP GUI" 10 || true

echo ""
echo "====================================================="
echo "  Service Startup Summary"
echo "====================================================="
echo ""
echo "Access Points:"
echo "  - Neo4j Browser (direct):  http://localhost:7474/browser/ (neo4j/surveillance123)"
echo "  - Neo4j Browser (preview): http://localhost:7475/browser/ (use in Cloud Shell embedded preview)"
echo "  - Neo4j Bolt:              bolt://localhost:7687"
echo "  - Kafka Broker:            localhost:9092"
echo "  - Zookeeper:               localhost:2181"
echo "  - FastAPI API:             http://localhost:8000/docs"
echo "  - Flask GUI:               http://localhost:5000"
echo "  - PHP GUI:                 http://localhost:8080"
echo ""
echo "PIDs: FastAPI=$FASTAPI_PID Flask=$FLASK_PID PHP=$PHP_PID"
echo "Logs: /tmp/fastapi.log /tmp/flask.log /tmp/php.log"
echo "If a service is unavailable, check the log and ensure its port is free."
echo "====================================================="
