#!/bin/bash
echo "Stopping all services..."
docker compose down
pkill -f "market_simulator.py" 2>/dev/null || true
pkill -f "surveillance_pipeline.py" 2>/dev/null || true
pkill -f "uvicorn" 2>/dev/null || true
pkill -f "gui_app.py" 2>/dev/null || true
echo "All services stopped"
