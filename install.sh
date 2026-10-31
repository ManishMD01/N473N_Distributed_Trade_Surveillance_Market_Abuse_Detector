#!/bin/bash

# =====================================================
# Distributed Trade Surveillance & Market Abuse Detector
# Complete Installation Script
# =====================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Print banner
print_banner() {
    echo -e "${BLUE}"
    echo "====================================================="
    echo "  Distributed Trade Surveillance & Market Abuse Detector"
    echo "  Enterprise Installation Script"
    echo "====================================================="
    echo -e "${NC}"
}

# Check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        log_warning "Running as root. This is not recommended for production."
    fi
}

# Check system requirements
check_requirements() {
    log_info "Checking system requirements..."
    
    # Check OS
    if [[ "$OSTYPE" != "linux-gnu"* ]]; then
        log_warning "This script is optimized for Linux. Other OS may require manual setup."
    fi
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is not installed. Please install Python 3.11+ first."
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    log_info "Python version: $PYTHON_VERSION"
    
    # Check Java (for Spark)
    if ! command -v java &> /dev/null; then
        log_warning "Java not found. PySpark may not work without Java 8/11."
    else
        JAVA_VERSION=$(java -version 2>&1 | head -n 1)
        log_info "Java: $JAVA_VERSION"
    fi
    
    # Check PHP
    if ! command -v php &> /dev/null; then
        log_warning "PHP not found. PHP GUI will not be available."
    else
        PHP_VERSION=$(php -v | head -n 1)
        log_info "PHP: $PHP_VERSION"
    fi
    
    log_success "System requirements check completed"
}

# Setup Python virtual environment
setup_python_env() {
    log_info "Setting up Python virtual environment..."
    
    if [ ! -d ".venv" ]; then
        python3 -m venv .venv
        log_success "Virtual environment created"
    else
        log_info "Virtual environment already exists"
    fi
    
    source .venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install base dependencies
    log_info "Installing Python dependencies..."
    pip install -e ".[test]" 2>/dev/null || pip install fastapi uvicorn[standard] pydantic-settings asyncpg pyspark kafka-python neo4j pandas sqlalchemy psycopg2-binary
    
    # Install additional dependencies for the full stack
    pip install confluent-kafka requests google-cloud-bigquery google-auth flask 2>/dev/null || true
    
    log_success "Python dependencies installed"
}

# Start infrastructure services
start_infrastructure() {
    log_info "Starting infrastructure services (Kafka, Zookeeper, Neo4j)..."
    
    # Stop any existing containers
    docker-compose down 2>/dev/null || docker compose down 2>/dev/null || true
    
    # Start services
    if command -v docker-compose &> /dev/null; then
        docker-compose up -d
    else
        docker compose up -d
    fi
    
    log_info "Waiting for services to be healthy..."
    sleep 30
    
    # Check service status
    log_info "Service status:"
    if command -v docker-compose &> /dev/null; then
        docker-compose ps
    else
        docker compose ps
    fi
    
    log_success "Infrastructure services started"
}

# Setup TimescaleDB (if available)
setup_timescaledb() {
    log_info "Checking for TimescaleDB setup..."
    
    if command -v psql &> /dev/null; then
        log_info "PostgreSQL client found. You can manually setup TimescaleDB using db/schema.sql"
        log_warning "TimescaleDB is not containerized in docker-compose.yml"
        log_info "To setup manually: CREATE EXTENSION IF NOT EXISTS timescaledb; then run db/schema.sql"
    else
        log_warning "PostgreSQL client not found. TimescaleDB setup requires manual configuration"
    fi
}

# Setup Neo4j
setup_neo4j() {
    log_info "Waiting for Neo4j to be ready..."
    sleep 60
    
    # Test Neo4j connection
    if command -v curl &> /dev/null; then
        for i in {1..30}; do
            if curl -s http://localhost:7474 > /dev/null; then
                log_success "Neo4j is ready at http://localhost:7474"
                log_info "Default credentials: neo4j/surveillance123"
                break
            fi
            log_info "Waiting for Neo4j... ($i/30)"
            sleep 10
        done
    fi
    
    # Load graph schema if possible
    if [ -f ".venv/bin/python" ]; then
        source .venv/bin/activate
        log_info "Initializing Neo4j graph schema..."
        timeout 60 python graph_loader.py 2>/dev/null || log_warning "Graph loader initialization skipped or failed"
    fi
}

# Setup Kafka topics
setup_kafka() {
    log_info "Setting up Kafka topics..."
    sleep 20
    
    # Create market-orders topic
    if command -v docker &> /dev/null; then
        docker exec trade_surveillance_kafka kafka-topics --create \
            --bootstrap-server localhost:9092 \
            --replication-factor 1 \
            --partitions 3 \
            --topic market-orders 2>/dev/null || log_info "Topic may already exist"
        
        log_info "Listing Kafka topics:"
        docker exec trade_surveillance_kafka kafka-topics --list --bootstrap-server localhost:9092 2>/dev/null || true
    fi
    
    log_success "Kafka setup completed"
}

# Create startup scripts
create_startup_scripts() {
    log_info "Creating startup scripts..."
    
    # Create start_all.sh
    cat > start_all.sh << 'SCRIPT'
#!/bin/bash
echo "Starting Distributed Trade Surveillance System..."

# Start infrastructure
docker-compose up -d
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
SCRIPT
    chmod +x start_all.sh
    
    # Create stop_all.sh
    cat > stop_all.sh << 'SCRIPT'
#!/bin/bash
echo "Stopping all services..."
docker-compose down
pkill -f "market_simulator.py" 2>/dev/null || true
pkill -f "surveillance_pipeline.py" 2>/dev/null || true
pkill -f "uvicorn" 2>/dev/null || true
pkill -f "gui_app.py" 2>/dev/null || true
echo "All services stopped"
SCRIPT
    chmod +x stop_all.sh
    
    log_success "Startup scripts created (start_all.sh, stop_all.sh)"
}

# Display summary
display_summary() {
    echo -e "\n${GREEN}"
    echo "====================================================="
    echo "  Installation Completed Successfully!"
    echo "====================================================="
    echo -e "${NC}"
    
    echo -e "${BLUE}Services Available:${NC}"
    echo "  • Kafka: localhost:9092"
    echo "  • Zookeeper: localhost:2181"
    echo "  • Neo4j Browser: http://localhost:7474 (neo4j/surveillance123)"
    echo "  • FastAPI Docs: http://localhost:8000/docs (when running)"
    echo "  • PHP GUI: http://localhost:8080 (when running)"
    echo "  • Flask GUI: http://localhost:5000 (when running)"
    
    echo -e "\n${BLUE}Quick Start:${NC}"
    echo "  1. Activate environment: source .venv/bin/activate"
    echo "  2. Start infrastructure: ./start_all.sh"
    echo "  3. Run components in separate terminals:"
    echo "     - Market Simulator: python market_simulator.py"
    echo "     - Surveillance Pipeline: spark-submit surveillance_pipeline.py"
    echo "     - Graph Analysis: python graph_loader.py"
    echo "     - FastAPI API: uvicorn app.main:app --reload --port 8000"
    echo "     - PHP GUI: php -S localhost:8080 -t php_gui"
    echo "     - Flask GUI: python gui_app.py"
    
    echo -e "\n${BLUE}Files Created:${NC}"
    echo "  • docker-compose.yml - Infrastructure"
    echo "  • market_simulator.py - Kafka producer with spoofing injection"
    echo "  • surveillance_pipeline.py - PySpark streaming pipeline"
    echo "  • graph_loader.py - Neo4j graph intelligence"
    echo "  • historical_analytics.sql - BigQuery analytics"
    echo "  • php_gui/ - PHP web interface"
    echo "  • gui_app.py - Flask web interface"
    echo "  • start_all.sh / stop_all.sh - Management scripts"
    
    echo -e "\n${YELLOW}Note:${NC}"
    echo "  • TimescaleDB requires manual setup (see db/schema.sql)"
    echo "  • BigQuery requires GCP credentials and project configuration"
    echo "  • Spark requires Java for full functionality"
    
    echo -e "\n${GREEN}Installation complete!${NC}\n"
}

# Main installation flow
main() {
    print_banner
    check_root
    check_requirements
    setup_python_env
    start_infrastructure
    setup_kafka
    setup_neo4j
    setup_timescaledb
    create_startup_scripts
    display_summary
}

# Run main function
main "$@"
