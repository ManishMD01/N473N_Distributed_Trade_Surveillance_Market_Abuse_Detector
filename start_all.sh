#!/bin/bash
echo "Starting Distributed Trade Surveillance System..."

# Start infrastructure
docker compose up -d
sleep 30

# Activate virtual environment
source .venv/bin/activate

echo "Infrastructure started. Ready to run components:"
echo "1. Market Simulator: python market_simulator.py"
echo "2. Surveillance Pipeline: spark-submit surveillance_pipeline.py"
echo "3. Graph Loader: python graph_loader.py"
echo "4. FastAPI Server: uvicorn app.main:app --reload"
echo "5. PHP GUI: php -S localhost:8080 -t php_gui"
echo "6. Flask GUI: python gui_app.py"
