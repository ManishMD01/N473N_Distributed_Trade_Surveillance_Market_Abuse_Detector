#!/usr/bin/env python3
"""
Graph Loader - Neo4j AML Graph Analytics
Part 4: Distributed Trade Surveillance & Market Abuse Detector

Loads spoofing alerts from Spark pipeline into Neo4j and provides
graph analytics for detecting collusive spoofing networks.
"""

import json
import time
import uuid
from datetime import datetime
from typing import Dict, List, Any
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable, AuthError


class Neo4jGraphLoader:
    def __init__(self, 
                 uri: str = "bolt://localhost:7687",
                 user: str = "neo4j",
                 password: str = "surveillance123"):
        """
        Initialize Neo4j connection.
        
        Args:
            uri: Neo4j Bolt URI
            user: Neo4j username
            password: Neo4j password
        """
        self.uri = uri
        self.user = user
        self.password = password
        self.driver = None
        
    def connect(self):
        """Establish connection to Neo4j database."""
        try:
            self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
            # Verify connectivity
            with self.driver.session() as session:
                result = session.run("RETURN 'Connection Successful' AS status")
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                      f"{result.single()['status']} to Neo4j at {self.uri}")
        except AuthError:
            print("Authentication failed. Check credentials.")
            raise
        except ServiceUnavailable:
            print("Neo4j service unavailable. Ensure database is running.")
            raise
    
    def close(self):
        """Close Neo4j connection."""
        if self.driver:
            self.driver.close()
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                  f"Neo4j connection closed.")
    
    def create_constraints_and_indexes(self):
        """Create constraints and indexes for optimal performance."""
        constraints_indexes = [
            "CREATE CONSTRAINT trader_id_unique IF NOT EXISTS FOR (t:Trader) REQUIRE t.id IS UNIQUE",
            "CREATE CONSTRAINT account_number_unique IF NOT EXISTS FOR (a:Account) REQUIRE a.number IS UNIQUE",
            "CREATE CONSTRAINT ip_address_unique IF NOT EXISTS FOR (i:IPAddress) REQUIRE i.ip IS UNIQUE",
            "CREATE CONSTRAINT alert_id_unique IF NOT EXISTS FOR (al:Alert) REQUIRE al.id IS UNIQUE",
            "CREATE INDEX trader_symbol_idx IF NOT EXISTS FOR ()-[r:TRIGGERED_ALERT]-() ON (r.symbol)",
            "CREATE INDEX alert_timestamp_idx IF NOT EXISTS FOR (al:Alert) ON (al.timestamp)"
        ]
        
        with self.driver.session() as session:
            for query in constraints_indexes:
                try:
                    session.run(query)
                    print(f"  Executed: {query[:60]}...")
                except Exception as e:
                    print(f"  Warning: {e}")
        
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
              f"Constraints and indexes created/verified.")
    
    def load_spoofing_alerts(self, alerts_data: List[Dict[str, Any]]):
        """
        Load spoofing alerts into Neo4j with optimized queries.
        Creates nodes and relationships as specified.
        """
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
              f"Loading {len(alerts_data)} alerts into Neo4j...")
        
        # Optimized batch query for creating nodes and relationships
        load_query = """
        UNWIND $alerts AS alert
        // Create or merge Trader node
        MERGE (t:Trader {id: alert.trader_id})
        SET t.last_seen = datetime()
        
        // Create or merge Account node
        MERGE (a:Account {number: alert.routing_account})
        SET a.last_seen = datetime()
        
        // Create or merge IPAddress node
        MERGE (i:IPAddress {ip: alert.ip_address})
        SET i.last_seen = datetime()
        
        // Create or merge Alert node
        MERGE (al:Alert {id: alert.alert_id})
        SET al.typology = alert.typology,
            al.timestamp = datetime(alert.timestamp),
            al.symbol = alert.symbol,
            al.otr = alert.order_to_trade_ratio,
            al.cancellation_pct = alert.cancellation_percentage,
            al.execution_horizon_ms = alert.avg_execution_horizon_ms,
            al.severity = alert.alert_severity,
            al.description = alert.alert_description,
            al.window_start = datetime(alert.window_start),
            al.window_end = datetime(alert.window_end)
        
        // Create relationships
        MERGE (t)-[r1:USES_ACCOUNT]->(a)
        SET r1.first_seen = coalesce(r1.first_seen, datetime()),
            r1.last_seen = datetime()
        
        MERGE (t)-[r2:OPERATES_FROM]->(i)
        SET r2.first_seen = coalesce(r2.first_seen, datetime()),
            r2.last_seen = datetime()
        
        MERGE (t)-[r3:TRIGGERED_ALERT]->(al)
        SET r3.symbol = alert.symbol,
            r3.window_start = datetime(alert.window_start),
            r3.created_at = datetime()
        """
        
        with self.driver.session() as session:
            try:
                result = session.run(load_query, alerts=alerts_data)
                summary = result.consume()
                print(f"  Successfully processed alerts. "
                      f"Nodes created: {summary.counters.nodes_created}, "
                      f"Relationships created: {summary.counters.relationships_created}")
            except Exception as e:
                print(f"  Error loading alerts: {e}")
                raise
    
    def get_collusive_spoofing_networks(self):
        """
        Production-grade Cypher query to unmask 'Collusive Spoofing networks'.
        Isolates separate Trader nodes that are triggering individual market 
        manipulation alerts but are executing trades from the exact same IP 
        address or sharing a bank routing account.
        """
        collusion_query = """
        // Find collusive spoofing networks - traders sharing same IP or same account
        MATCH (t1:Trader)-[:TRIGGERED_ALERT]->(al1:Alert)
        MATCH (t2:Trader)-[:TRIGGERED_ALERT]->(al2:Alert)
        WHERE t1 <> t2 
          AND al1.typology = 'SPOOFING_SUSPECTED'
          AND al2.typology = 'SPOOFING_SUSPECTED'
        // Check if they share same IP address
        OPTIONAL MATCH (t1)-[:OPERATES_FROM]->(ip:IPAddress)<-[:OPERATES_FROM]-(t2)
        // Check if they share same routing account
        OPTIONAL MATCH (t1)-[:USES_ACCOUNT]->(acc:Account)<-[:USES_ACCOUNT]-(t2)
        WHERE ip IS NOT NULL OR acc IS NOT NULL
        // Collect network information
        WITH t1, t2, 
             collect(DISTINCT ip.ip) AS shared_ips,
             collect(DISTINCT acc.number) AS shared_accounts,
             collect(DISTINCT al1.id) AS t1_alerts,
             collect(DISTINCT al2.id) AS t2_alerts
        WHERE size(shared_ips) > 0 OR size(shared_accounts) > 0
        // Calculate risk metrics
        RETURN 
          t1.id AS trader1,
          t2.id AS trader2,
          shared_ips,
          shared_accounts,
          size(t1_alerts) AS trader1_alert_count,
          size(t2_alerts) AS trader2_alert_count,
          CASE 
            WHEN size(shared_ips) > 0 AND size(shared_accounts) > 0 THEN 'CRITICAL'
            WHEN size(shared_ips) > 0 OR size(shared_accounts) > 0 THEN 'HIGH'
            ELSE 'MEDIUM'
          END AS collusion_risk,
          CASE 
            WHEN size(shared_ips) > 0 AND size(shared_accounts) > 0 THEN 'IP_AND_ACCOUNT'
            WHEN size(shared_ips) > 0 THEN 'SAME_IP'
            WHEN size(shared_accounts) > 0 THEN 'SAME_ACCOUNT'
          END AS collusion_type,
          datetime() AS analysis_timestamp
        ORDER BY collusion_risk DESC, trader1, trader2
        """
        
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
              f"Scanning for collusive spoofing networks...")
        
        with self.driver.session() as session:
            result = session.run(collusion_query)
            records = list(result)
            
            if not records:
                print("  No collusive networks detected.")
                return []
            
            print(f"  Found {len(records)} potential collusive connections:")
            print("=" * 100)
            for record in records:
                print(f"  Trader1: {record['trader1']} | Trader2: {record['trader2']}")
                print(f"  Risk: {record['collusion_risk']} | Type: {record['collusion_type']}")
                print(f"  Shared IPs: {record['shared_ips']}")
                print(f"  Shared Accounts: {record['shared_accounts']}")
                print(f"  Alert Counts: {record['trader1']}({record['trader1_alert_count']}) vs {record['trader2']}({record['trader2_alert_count']})")
                print("-" * 100)
            
            return records
    
    def get_detailed_collusion_network(self, trader1_id: str, trader2_id: str):
        """
        Get detailed graph visualization data for specific collusive pair.
        """
        detail_query = """
        MATCH (t1:Trader {id: $trader1_id})-[r1:TRIGGERED_ALERT]->(al:Alert)
        OPTIONAL MATCH (t1)-[:OPERATES_FROM]->(ip:IPAddress)
        OPTIONAL MATCH (t1)-[:USES_ACCOUNT]->(acc:Account)
        OPTIONAL MATCH (t2:Trader {id: $trader2_id})-[r2:TRIGGERED_ALERT]->(al2:Alert)
        OPTIONAL MATCH (t2)-[:OPERATES_FROM]->(ip2:IPAddress)
        OPTIONAL MATCH (t2)-[:USES_ACCOUNT]->(acc2:Account)
        RETURN 
          t1, al, ip, acc,
          t2, al2, ip2, acc2
        """
        
        with self.driver.session() as session:
            result = session.run(detail_query, trader1_id=trader1_id, trader2_id=trader2_id)
            return list(result)


def generate_sample_alerts_from_spark() -> List[Dict[str, Any]]:
    """
    Simulate alert structures produced by Spark in Part 3.
    In production, these would come from BigQuery or streaming results.
    """
    sample_alerts = []
    
    # Simulate spoofing alerts including collusive patterns
    # Trader pair sharing same IP
    base_time = datetime.now().isoformat()
    
    # Alert 1 - TRADER_SPOOF_99 (from simulator)
    sample_alerts.append({
        "alert_id": f"ALERT_{uuid.uuid4().hex[:12].upper()}",
        "trader_id": "TRADER_SPOOF_99",
        "routing_account": "ACC_123456",
        "ip_address": "192.168.1.100",
        "symbol": "AAPL",
        "typology": "SPOOFING_SUSPECTED",
        "timestamp": base_time,
        "order_to_trade_ratio": 15.5,
        "cancellation_percentage": 92.3,
        "avg_execution_horizon_ms": 450.0,
        "alert_severity": "HIGH",
        "alert_description": "OTR:15.50, Cancel%:92.30, ExecHorizon:450ms",
        "window_start": (datetime.now().timestamp() - 10) * 1000,
        "window_end": datetime.now().timestamp() * 1000
    })
    
    # Alert 2 - Collusive trader sharing same IP
    sample_alerts.append({
        "alert_id": f"ALERT_{uuid.uuid4().hex[:12].upper()}",
        "trader_id": "TRADER_015",
        "routing_account": "ACC_789012",
        "ip_address": "192.168.1.100",  # Same IP as TRADER_SPOOF_99
        "symbol": "AAPL",
        "typology": "SPOOFING_SUSPECTED",
        "timestamp": base_time,
        "order_to_trade_ratio": 12.3,
        "cancellation_percentage": 88.7,
        "avg_execution_horizon_ms": 650.0,
        "alert_severity": "HIGH",
        "alert_description": "OTR:12.30, Cancel%:88.70, ExecHorizon:650ms",
        "window_start": (datetime.now().timestamp() - 10) * 1000,
        "window_end": datetime.now().timestamp() * 1000
    })
    
    # Alert 3 - Another trader sharing same routing account
    sample_alerts.append({
        "alert_id": f"ALERT_{uuid.uuid4().hex[:12].upper()}",
        "trader_id": "TRADER_023",
        "routing_account": "ACC_123456",  # Same account as TRADER_SPOOF_99
        "ip_address": "192.168.50.75",
        "symbol": "MSFT",
        "typology": "SPOOFING_SUSPECTED",
        "timestamp": base_time,
        "order_to_trade_ratio": 18.2,
        "cancellation_percentage": 95.1,
        "avg_execution_horizon_ms": 320.0,
        "alert_severity": "CRITICAL",
        "alert_description": "OTR:18.20, Cancel%:95.10, ExecHorizon:320ms",
        "window_start": (datetime.now().timestamp() - 10) * 1000,
        "window_end": datetime.now().timestamp() * 1000
    })
    
    # Alert 4 - Isolated spoofing trader (no collusion)
    sample_alerts.append({
        "alert_id": f"ALERT_{uuid.uuid4().hex[:12].upper()}",
        "trader_id": "TRADER_042",
        "routing_account": "ACC_555666",
        "ip_address": "10.0.0.50",
        "symbol": "TSLA",
        "typology": "SPOOFING_SUSPECTED",
        "timestamp": base_time,
        "order_to_trade_ratio": 9.8,
        "cancellation_percentage": 85.4,
        "avg_execution_horizon_ms": 780.0,
        "alert_severity": "HIGH",
        "alert_description": "OTR:9.80, Cancel%85.4, ExecHorizon:780ms",
        "window_start": (datetime.now().timestamp() - 10) * 1000,
        "window_end": datetime.now().timestamp() * 1000
    })
    
    return sample_alerts


def main():
    """Main entry point for graph loader."""
    loader = Neo4jGraphLoader(
        uri="bolt://localhost:7687",
        user="neo4j",
        password="surveillance123"
    )
    
    try:
        # Connect to Neo4j
        loader.connect()
        
        # Create constraints and indexes
        loader.create_constraints_and_indexes()
        
        # Simulate alerts from Spark pipeline
        alerts_data = generate_sample_alerts_from_spark()
        
        # Load alerts into graph
        loader.load_spoofing_alerts(alerts_data)
        
        # Detect collusive spoofing networks
        collusion_results = loader.get_collusive_spoofing_networks()
        
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
              f"Graph analytics complete.")
        print(f"Total potential collusive connections identified: {len(collusion_results)}")
        
    except Exception as e:
        print(f"Error in graph loader: {e}")
        raise
    finally:
        loader.close()


if __name__ == "__main__":
    main()
