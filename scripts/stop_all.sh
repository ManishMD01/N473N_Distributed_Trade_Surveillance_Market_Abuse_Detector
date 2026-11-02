#!/bin/bash
cd "$(dirname "$0")/.."
docker compose -f infra/docker-compose.yml down 2>/dev/null || true
pkill -f "market_simulator|surveillance_pipeline|uvicorn|gui_app" 2>/dev/null || true
echo "All services stopped"
