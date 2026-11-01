#!/bin/bash
cd /home/ee_2018_mrdhodare/Git/N473N_Distributed_Trade_Surveillance_Market_Abuse_Detector
docker compose -f infra/docker-compose.yml down 2>/dev/null || true
pkill -f "market_simulator|surveillance_pipeline|uvicorn|gui_app" 2>/dev/null || true
echo "All services stopped"
