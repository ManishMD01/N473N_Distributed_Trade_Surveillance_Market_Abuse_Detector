# Distributed Trade Surveillance & Market Abuse Detector

Enterprise-grade platform for ingesting high-throughput Level 3 (L3) order book data, processing in real-time, and detecting market manipulation (Spoofing/Layering) for SEC Rule 10b-5 and FINRA Rule 5210 compliance.

## Architecture

| Component | Technology | Purpose |
|-----------|------------|---------|
| Message Broker | Apache Kafka + Zookeeper | L3 order book event streaming |
| Stream Processing | PySpark Structured Streaming | Real-time windowed analytics & detection |
| Graph Database | Neo4j (APOC) | Entity resolution & collusion detection |
| Time-Series DB | TimescaleDB/PostgreSQL | Operational trade storage |
| Data Warehouse | Google BigQuery | Alert storage & historical analytics |
| API | FastAPI | Privacy-preserving compliance endpoints |
| GUIs | Flask, PHP | Web dashboards |

## Project Structure

```
├── app/                    # FastAPI application
├── analytics/              # BigQuery SQL analytics
├── config/                 # Configuration files (config.yaml, .env.example)
├── db/                     # Database schemas
├── graph/                  # Neo4j graph loader
├── infra/                  # Docker infrastructure (docker-compose.yml)
├── ingestion/              # Market simulator (Kafka producer)
├── scripts/                # Installation & uninstallation scripts
├── streaming/              # PySpark surveillance pipeline
├── tests/                  # Unit tests
└── web/                    # Web interfaces (Flask & PHP)
```

## Quick Start

### 1. Install Dependencies & Infrastructure
```bash
chmod +x scripts/install.sh scripts/uninstall.sh
./scripts/install.sh
```

### 2. Start All Services
```bash
./scripts/start_all.sh
```

### 3. Run Components (in separate terminals)

**Activate environment:**
```bash
source .venv/bin/activate
```

**Market Simulator (Kafka Producer):**
```bash
python ingestion/market_simulator.py
```

**Surveillance Pipeline (PySpark Streaming):**
```bash
spark-submit streaming/surveillance_pipeline.py
```

**Graph Loader (Neo4j):**
```bash
python graph/graph_loader.py
```

**FastAPI Server:**
```bash
uvicorn app.main:app --reload --port 8000
```

**Flask GUI:**
```bash
python web/flask/gui_app.py
```

**PHP GUI:**
```bash
php -S localhost:8080 -t web/php
```

### 4. Stop All Services
```bash
./scripts/stop_all.sh
```

## Access Points

| Service | URL | Credentials |
|---------|-----|-------------|
| Kafka | localhost:9092 | - |
| Zookeeper | localhost:2181 | - |
| Neo4j Browser | http://localhost:7474 | neo4j/surveillance123 |
| FastAPI Docs | http://localhost:8000/docs | - |
| Flask GUI | http://localhost:5000 | - |
| PHP GUI | http://localhost:8080 | - |

## Configuration

Edit `config/config.yaml` or copy `config/.env.example` to `.env` for environment variables.

**Key configurations:**
- Kafka: `config/config.yaml` → kafka section
- Neo4j: `config/config.yaml` → neo4j section
- TimescaleDB: Requires manual setup using `db/schema.sql`
- BigQuery: Requires GCP credentials in `config/config.yaml` → bigquery section
- Spark: Requires Java 8/11 installed

## Detection Logic

Alerts triggered when:
- **Order-to-Trade Ratio (OTR)** > 5
- **Cancellation Rate** > 80%
- **Execution Horizon** < 2000ms

## Testing

```bash
source .venv/bin/activate
pytest
```

## Notes
- TimescaleDB is not containerized - setup manually with `db/schema.sql`
- BigQuery requires GCP project and service account credentials
- PySpark requires Java runtime

## Database Setup

### TimescaleDB/PostgreSQL (Manual Setup Required)
TimescaleDB is not containerized in this setup. Install and configure manually:

```sql
-- Create database
CREATE DATABASE surveillance;

-- Connect to database and enable TimescaleDB
\c surveillance
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Run schema
\i db/schema.sql
```

Or from command line:
```bash
psql -U postgres -d surveillance -f db/schema.sql
```

### Neo4j
Auto-configured via Docker. Access at http://localhost:7474 with `neo4j/surveillance123`.

### Google BigQuery
1. Create a GCP project
2. Create dataset `surveillance` and table `market_abuse_alerts`
3. Run DDL from `analytics/historical_analytics.sql` or `streaming/surveillance_pipeline.py`
4. Add service account credentials to `config/config.yaml` under `bigquery.credentials_path`

### Kafka
Auto-configured via Docker. Topic `market-orders` created automatically.
