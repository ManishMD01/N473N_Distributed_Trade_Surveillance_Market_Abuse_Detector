#!/bin/bash

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

print_banner() {
    echo -e "${BLUE}====================================================="
    echo "  Distributed Trade Surveillance & Market Abuse Detector"
    echo "=====================================================${NC}"
}

check_requirements() {
    log_info "Checking system requirements..."
    command -v docker &> /dev/null || { log_error "Docker required"; exit 1; }
    docker compose version &> /dev/null || { log_error "Docker Compose required"; exit 1; }
    command -v python3 &> /dev/null || { log_error "Python3 required"; exit 1; }
    log_success "Requirements OK"
}

setup_python_env() {
    log_info "Setting up Python virtual environment..."
    PROJECT_ROOT="/home/ee_2018_mrdhodare/Git/N473N_Distributed_Trade_Surveillance_Market_Abuse_Detector"
    cd "$PROJECT_ROOT"
    [ ! -d ".venv" ] && python3 -m venv .venv
    source .venv/bin/activate
    pip install --upgrade pip > /dev/null 2>&1
    pip install fastapi uvicorn[standard] pydantic-settings asyncpg pyspark kafka-python neo4j pandas sqlalchemy psycopg2-binary confluent-kafka google-cloud-bigquery flask pytest httpx > /dev/null 2>&1
    log_success "Dependencies installed"
}

start_infrastructure() {
    log_info "Starting infrastructure services..."
    PROJECT_ROOT="/home/ee_2018_mrdhodare/Git/N473N_Distributed_Trade_Surveillance_Market_Abuse_Detector"
    COMPOSE_FILE="$PROJECT_ROOT/infra/docker-compose.yml"
    docker compose -f "$COMPOSE_FILE" up -d
    sleep 30
    docker compose -f "$COMPOSE_FILE" ps
    log_success "Infrastructure started"
}

create_startup_scripts() {
    log_info "Creating startup scripts..."
    PROJECT_ROOT="/home/ee_2018_mrdhodare/Git/N473N_Distributed_Trade_Surveillance_Market_Abuse_Detector"
    cd "$PROJECT_ROOT"
    # Don't overwrite existing scripts - preserve their content
    if [ ! -f scripts/start_all.sh ]; then
        cat > scripts/start_all.sh << 'SCRIPT'
#!/bin/bash
cd "$(dirname "$0")/.."
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
SCRIPT
        chmod +x scripts/start_all.sh
    else
        log_info "start_all.sh already exists, skipping overwrite"
    fi
    
    if [ ! -f scripts/stop_all.sh ]; then
        cat > scripts/stop_all.sh << 'SCRIPT'
#!/bin/bash
cd "$(dirname "$0")/.."
docker compose -f infra/docker-compose.yml down 2>/dev/null || true
pkill -f "market_simulator|surveillance_pipeline|uvicorn|gui_app" 2>/dev/null || true
echo "All services stopped"
SCRIPT
        chmod +x scripts/stop_all.sh
    else
        log_info "stop_all.sh already exists, skipping overwrite"
    fi
    log_success "Scripts ready"
}

main() {
    print_banner
    check_requirements
    setup_python_env
    start_infrastructure
    create_startup_scripts
    echo -e "\n${GREEN}Installation complete!${NC}"
}
main "$@"
