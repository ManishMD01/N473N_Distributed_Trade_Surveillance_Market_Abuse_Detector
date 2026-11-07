#!/bin/bash
set -uo pipefail
cd "$(dirname "$0")/.."
docker compose -f infra/docker-compose.yml down 2>/dev/null || true
pkill -f "market_simulator|surveillance_pipeline|uvicorn app.main:app|web/flask/gui_app.py|php -S .*:8080" 2>/dev/null || true
echo "All services stopped"
