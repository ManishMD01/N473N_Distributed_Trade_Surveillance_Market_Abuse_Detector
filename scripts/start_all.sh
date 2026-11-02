#!/bin/bash
cd "$(dirname "$0")/.."
docker compose -f infra/docker-compose.yml up -d
sleep 30
source .venv/bin/activate 2>/dev/null || true

# Start services in background
echo "Starting FastAPI..."
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > /tmp/fastapi.log 2>&1 &
echo "FastAPI started (PID: $!)"

echo "Starting Flask GUI..."
nohup python web/flask/gui_app.py > /tmp/flask.log 2>&1 &
echo "Flask started (PID: $!)"

echo "Starting PHP GUI..."
nohup php -S 0.0.0.0:8080 -t web/php > /tmp/php.log 2>&1 &
echo "PHP started (PID: $!)"

echo ""
echo "====================================================="
echo "  All Services Started"
echo "====================================================="
echo ""
echo "Access Points:"
echo "  - Neo4j Browser:  http://localhost:7474 (neo4j/surveillance123)"
echo "  - Kafka Broker:   localhost:9092"
echo "  - Zookeeper:       localhost:2181"
echo "  - FastAPI API:    http://localhost:8000/docs"
echo "  - Flask GUI:      http://localhost:5000"
echo "  - PHP GUI:        http://localhost:8080"
echo ""
echo "Logs: /tmp/fastapi.log, /tmp/flask.log, /tmp/php.log"
echo "====================================================="
