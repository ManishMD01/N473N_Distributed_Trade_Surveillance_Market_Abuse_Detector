#!/bin/bash

# =====================================================
# Distributed Trade Surveillance & Market Abuse Detector
# Complete Uninstallation Script
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
    echo -e "${RED}"
    echo "====================================================="
    echo "  Trade Surveillance System - UNINSTALLATION"
    echo "====================================================="
    echo -e "${NC}"
}

# Stop all running processes
stop_processes() {
    log_info "Stopping all running processes..."
    
    pkill -f "market_simulator.py" 2>/dev/null || true
    pkill -f "surveillance_pipeline.py" 2>/dev/null || true
    pkill -f "graph_loader.py" 2>/dev/null || true
    pkill -f "uvicorn" 2>/dev/null || true
    pkill -f "gui_app.py" 2>/dev/null || true
    pkill -f "php -S" 2>/dev/null || true
    
    log_success "All processes stopped"
}

# Stop and remove Docker containers
stop_docker() {
    log_info "Stopping and removing Docker containers..."
    
    if command -v docker compose &> /dev/null; then
        docker compose down -v 2>/dev/null || true
    elif docker compose version &> /dev/null; then
        docker compose down -v 2>/dev/null || true
    fi
    
    # Remove any remaining containers
    docker rm -f trade_surveillance_kafka trade_surveillance_zookeeper trade_surveillance_neo4j 2>/dev/null || true
    
    log_success "Docker containers and volumes removed"
}

# Remove virtual environment
remove_venv() {
    log_info "Removing Python virtual environment..."
    
    if [ -d ".venv" ]; then
        rm -rf .venv
        log_success "Virtual environment removed"
    else
        log_info "Virtual environment not found"
    fi
}

# Remove generated files and scripts
remove_generated_files() {
    log_info "Removing generated files and scripts..."
    
    # Remove startup scripts
    rm -f start_all.sh stop_all.sh 2>/dev/null || true
    
    # Remove checkpoint directories
    rm -rf /tmp/surveillance-checkpoint 2>/dev/null || true
    
    # Remove __pycache__
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -name "*.pyc" -delete 2>/dev/null || true
    
    log_success "Generated files cleaned up"
}

# Ask user confirmation
confirm_uninstall() {
    echo -e "${YELLOW}WARNING: This will remove:${NC}"
    echo "  • All Docker containers and volumes (Kafka, Zookeeper, Neo4j data)"
    echo "  • Python virtual environment (.venv)"
    echo "  • Generated startup/stop scripts"
    echo "  • Temporary files and caches"
    echo ""
    echo -e "${RED}Project source files will NOT be deleted.${NC}"
    echo ""
    
    read -p "Are you sure you want to uninstall? (y/N): " confirm
    if [[ ! $confirm =~ ^[Yy]$ ]]; then
        log_info "Uninstallation cancelled"
        exit 0
    fi
}

# Display summary
display_summary() {
    echo -e "\n${GREEN}"
    echo "====================================================="
    echo "  Uninstallation Completed"
    echo "====================================================="
    echo -e "${NC}"
    
    echo "Removed:"
    echo "  • Docker containers and volumes"
    echo "  • Python virtual environment"
    echo "  • Generated scripts and temporary files"
    echo ""
    echo -e "${BLUE}Note:${NC} Project source files remain intact."
    echo ""
}

# Main uninstall flow
main() {
    print_banner
    confirm_uninstall
    stop_processes
    stop_docker
    remove_venv
    remove_generated_files
    display_summary
}

# Run main function
main "$@"
