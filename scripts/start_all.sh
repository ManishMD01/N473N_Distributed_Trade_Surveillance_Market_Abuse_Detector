#!/bin/bash
cd /home/ee_2018_mrdhodare/Git/N473N_Distributed_Trade_Surveillance_Market_Abuse_Detector
docker compose -f infra/docker-compose.yml up -d
sleep 30
source .venv/bin/activate 2>/dev/null || true

echo ""
echo "====================================================="
echo "  Infrastructure Started Successfully"
echo "====================================================="
echo ""
echo "Access Points:"
echo "  - Neo4j Browser:  http://localhost:7474 (neo4j/surveillance123)"
echo "  - Kafka Broker:   localhost:9092"
echo "  - Zookeeper:       localhost:2181"
echo ""
echo "Start additional services in separate terminals:"
echo "  1. FastAPI API:   uvicorn app.main:app --reload --port 8000  (http://localhost:8000/docs)"
echo "  2. Flask GUI:     python web/flask/gui_app.py                (http://localhost:5000)"
echo "  3. PHP GUI:       php -S localhost:8080 -t web/php           (http://localhost:8080)"
echo "  4. Market Sim:    python ingestion/market_simulator.py"
echo "  5. Pipeline:      spark-submit streaming/surveillance_pipeline.py"
echo "  6. Graph Loader:  python graph/graph_loader.py"
echo ""
echo "Activate env:     source .venv/bin/activate"
echo "====================================================="
