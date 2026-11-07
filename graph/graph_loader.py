#!/usr/bin/env python3
"""
Graph Intelligence Layer - Neo4j Entity Resolution
Part 4: Distributed Trade Surveillance & Market Abuse Detector

Syncs alerted profiles to Neo4j to resolve bad-actor collusion networks
and detects collusive spoofing patterns.
"""

import json
import time
from datetime import datetime
from typing import List, Dict, Any

from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable, AuthError


class GraphLoader:
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
            # Test connection
            with self.driver.session() as session:
                result = session.run("RETURN 'Connection successful' as message")
                record = result.single()
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {record['message']}")
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Connected to Neo4j at {self.uri}")
        except AuthError as e:
            print(f"Authentication failed: {e}")
            raise
        except ServiceUnavailable as e:
            print(f"Neo4j service unavailable: {e}")
            raise
        except Exception as e:
            print(f"Error connecting to Neo4j: {e}")
            raise
    
    def close(self):
        """Close Neo4j connection."""
        if self.driver:
            self.driver.close()
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Neo4j connection closed")
    
    def setup_schema(self):
        """Create constraints and indexes for the graph schema."""
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Setting up graph schema...")
        
        with self.driver.session() as session:
            # Create constraints
            constraints = [
                "CREATE CONSTRAINT trader_id IF NOT EXISTS FOR (t:Trader) REQUIRE t.trader_id IS UNIQUE",
                "CREATE CONSTRAINT account_id IF NOT EXISTS FOR (a:Account) REQUIRE a.account_id IS UNIQUE",
                "CREATE CONSTRAINT ip_address IF NOT EXISTS FOR (i:IPAddress) REQUIRE i.ip_address IS UNIQUE",
                "CREATE CONSTRAINT alert_id IF NOT EXISTS FOR (al:Alert) REQUIRE al.alert_id IS UNIQUE"
            ]
            
            for constraint in constraints:
                try:
                    session.run(constraint)
                    print(f"  ✓ Created constraint")
                except Exception as e:
                    print(f"  ⚠ Constraint may already exist: {e}")
            
            # Create indexes
            indexes = [
                "CREATE INDEX trader_risk IF NOT EXISTS FOR (t:Trader) ON (t.risk_score)",
                "CREATE INDEX alert_severity IF NOT EXISTS FOR (al:Alert) ON (al.severity)",
                "CREATE INDEX alert_type IF NOT EXISTS FOR (al:Alert) ON (al.alert_type)"
            ]
            
            for index in indexes:
                try:
                    session.run(index)
                    print(f"  ✓ Created index")
                except Exception as e:
                    print(f"  ⚠ Index may already exist: {e}")
        
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Schema setup complete\n")
    
    def load_alert_data(self, alerts: List[Dict[str, Any]]):
        """
        Load flagged alerts and build graph relationships.
        Maps: (:Trader)-[:USES_ACCOUNT]->(:Account) and (:Trader)-[:OPERATES_FROM]->(:IPAddress)
        """
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Loading {len(alerts)} alerts to graph...")
        
        with self.driver.session() as session:
            for alert in alerts:
                # Create Trader, Account, IPAddress nodes and relationships
                query = """
                MERGE (t:Trader {trader_id: $trader_id})
                SET t.last_alert = datetime($alert_timestamp),
                    t.risk_score = CASE 
                        WHEN t.risk_score IS NULL THEN $risk_score
                        ELSE t.risk_score + $risk_score 
                    END,
                    t.alert_count = CASE 
                        WHEN t.alert_count IS NULL THEN 1
                        ELSE t.alert_count + 1 
                    END
                
                MERGE (a:Account {account_id: $routing_account})
                MERGE (ip:IPAddress {ip_address: $ip_address})
                
                MERGE (t)-[:USES_ACCOUNT]->(a)
                MERGE (t)-[:OPERATES_FROM]->(ip)
                
                MERGE (al:Alert {alert_id: $alert_id})
                SET al.alert_type = $alert_type,
                    al.severity = $severity,
                    al.symbol = $symbol,
                    al.detected_at = datetime($alert_timestamp),
                    al.otr = $order_to_trade_ratio,
                    al.cancellation_rate = $cancellation_rate,
                    al.execution_horizon = $avg_execution_horizon_ms,
                    al.window_start = datetime($window_start),
                    al.window_end = datetime($window_end)
                
                MERGE (t)-[:TRIGGERED]->(al)
                MERGE (al)-[:INVOLVES_SYMBOL]->(s:Symbol {symbol: $symbol})
                
                RETURN t.trader_id, a.account_id, ip.ip_address
                """
                
                try:
                    result = session.run(query, {
                        "trader_id": alert["trader_id"],
                        "alert_timestamp": alert["alert_timestamp"],
                        "risk_score": alert.get("risk_score", 85.0),
                        "routing_account": alert.get("routing_account", f"ACC_{hash(alert['trader_id']) % 1000000:06d}"),
                        "ip_address": alert.get("ip_address", f"192.168.{hash(alert['trader_id']) % 255}.{hash(alert['symbol']) % 255}"),
                        "alert_id": alert["alert_id"],
                        "alert_type": alert["alert_type"],
                        "severity": alert["alert_severity"],
                        "symbol": alert["symbol"],
                        "order_to_trade_ratio": alert["order_to_trade_ratio"],
                        "cancellation_rate": alert["cancellation_rate"],
                        "avg_execution_horizon_ms": alert["avg_execution_horizon_ms"],
                        "window_start": alert["window_start"],
                        "window_end": alert["window_end"]
                    })
                    result.consume()
                except Exception as e:
                    print(f"  ⚠ Error loading alert {alert['alert_id']}: {e}")
        
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Alert loading complete\n")
    
    def detect_collusive_spoofing(self):
        """
        Robust Cypher Query to detect 'Collusive Spoofing'—
        finding separate Trader nodes that triggered high-risk spoofing alerts 
        while routing through the exact same IPAddress or using the same underlying Account.
        """
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Detecting collusive spoofing networks...")
        
        with self.driver.session() as session:
            q_ip = """
            MATCH (t1:Trader)-[:OPERATES_FROM]->(ip:IPAddress)<-[:OPERATES_FROM]-(t2:Trader)
            WHERE t1.trader_id < t2.trader_id
            MATCH (t1)-[:TRIGGERED]->(al1:Alert)
            MATCH (t2)-[:TRIGGERED]->(al2:Alert)
            WHERE al1.alert_type = 'SPOOFING' AND al1.severity IN ['HIGH', 'CRITICAL']
              AND al2.alert_type = 'SPOOFING' AND al2.severity IN ['HIGH', 'CRITICAL']
              AND al1.symbol = al2.symbol
            WITH ip, t1, t2, collect(DISTINCT al1.alert_id) as alerts1, collect(DISTINCT al2.alert_id) as alerts2
            RETURN
                ip.ip_address as shared_entity,
                t1.trader_id as trader1,
                t2.trader_id as trader2,
                size(alerts1) as trader1_spoof_alerts,
                size(alerts2) as trader2_spoof_alerts,
                alerts1 + alerts2 as all_alerts,
                'COLLUSION_VIA_IP' as collusion_type
            ORDER BY size(alerts1) + size(alerts2) DESC
            """
            q_acct = """
            MATCH (t1:Trader)-[:USES_ACCOUNT]->(a:Account)<-[:USES_ACCOUNT]-(t2:Trader)
            WHERE t1.trader_id < t2.trader_id
            MATCH (t1)-[:TRIGGERED]->(al1:Alert)
            MATCH (t2)-[:TRIGGERED]->(al2:Alert)
            WHERE al1.alert_type = 'SPOOFING' AND al1.severity IN ['HIGH', 'CRITICAL']
              AND al2.alert_type = 'SPOOFING' AND al2.severity IN ['HIGH', 'CRITICAL']
              AND al1.symbol = al2.symbol
            WITH a, t1, t2, collect(DISTINCT al1.alert_id) as alerts1, collect(DISTINCT al2.alert_id) as alerts2
            RETURN
                a.account_id as shared_entity,
                t1.trader_id as trader1,
                t2.trader_id as trader2,
                size(alerts1) as trader1_spoof_alerts,
                size(alerts2) as trader2_spoof_alerts,
                alerts1 + alerts2 as all_alerts,
                'COLLUSION_VIA_ACCOUNT' as collusion_type
            ORDER BY size(alerts1) + size(alerts2) DESC
            """
            records = list(session.run(q_ip)) + list(session.run(q_acct))

            
            if not records:
                print("  ✓ No collusive spoofing patterns detected")
            else:
                print(f"  🚨 DETECTED {len(records)} potential collusion patterns:")
                for i, record in enumerate(records, 1):
                    if record.get('collusion_type') == 'COLLUSION_VIA_IP':
                        print(f"    {i}. IP {record.get('shared_entity')}: {record['trader1']} <-> {record['trader2']} "
                              f"({record['trader1_spoof_alerts']} + {record['trader2_spoof_alerts']} spoof alerts)")
                    else:
                        print(f"    {i}. Account {record.get('shared_entity')}: {record['trader1']} <-> {record['trader2']} "
                              f"({record['trader1_spoof_alerts']} + {record['trader2_spoof_alerts']} spoof alerts)")
            print()
            return records
    
    def get_network_analysis(self):
        """Get overall network analysis of suspicious traders."""
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Generating network analysis...")
        
        query = """
        MATCH (t:Trader)-[:TRIGGERED]->(al:Alert)
        WHERE al.alert_type IN ['SPOOFING', 'LAYERING']
        WITH t, count(al) as alert_count, 
             sum(CASE WHEN al.severity = 'CRITICAL' THEN 1 ELSE 0 END) as critical_count,
             collect(DISTINCT al.symbol) as symbols
        OPTIONAL MATCH (t)-[:OPERATES_FROM]->(ip:IPAddress)
        OPTIONAL MATCH (t)-[:USES_ACCOUNT]->(a:Account)
        RETURN 
            t.trader_id,
            alert_count,
            critical_count,
            symbols,
            count(DISTINCT ip) as ip_count,
            count(DISTINCT a) as account_count
        ORDER BY alert_count DESC, critical_count DESC
        LIMIT 20
        """
        
        with self.driver.session() as session:
            result = session.run(query)
            records = list(result)
            
            print(f"  Top {len(records)} suspicious traders:")
            for i, record in enumerate(records, 1):
                print(f"    {i}. {record['t.trader_id']}: {record['alert_count']} alerts "
                      f"({record['critical_count']} critical), {len(record['symbols'])} symbols, "
                      f"{record['ip_count']} IPs, {record['account_count']} accounts")
            print()
            return records


def main():
    """Main entry point for graph loader."""
    print("=" * 80)
    print("GRAPH INTELLIGENCE LAYER - NEO4J ENTITY RESOLUTION")
    print("=" * 80)
    print(f"Starting Graph Loader at {datetime.now()}")
    print("=" * 80)
    
    loader = GraphLoader()
    try:
        loader.connect()
        loader.setup_schema()
        
        # Simulate loading alerts from BigQuery/Spark stream output
        simulated_alerts = [
            {
                "alert_id": "ALT_SPOOF_001",
                "trader_id": "TRADER_SPOOF_99",
                "alert_timestamp": "2024-01-15T10:30:45Z",
                "alert_type": "SPOOFING",
                "alert_severity": "HIGH",
                "symbol": "AAPL",
                "order_to_trade_ratio": 15.5,
                "cancellation_rate": 0.95,
                "avg_execution_horizon_ms": 450.0,
                "window_start": "2024-01-15T10:30:00Z",
                "window_end": "2024-01-15T10:30:10Z",
                "routing_account": "ACC_123456",
                "ip_address": "192.168.1.100"
            },
            {
                "alert_id": "ALT_SPOOF_002",
                "trader_id": "TRADER_COLLUSION_01",
                "alert_timestamp": "2024-01-15T10:31:15Z",
                "alert_type": "SPOOFING",
                "alert_severity": "HIGH",
                "symbol": "AAPL",
                "order_to_trade_ratio": 12.3,
                "cancellation_rate": 0.92,
                "avg_execution_horizon_ms": 380.0,
                "window_start": "2024-01-15T10:31:00Z",
                "window_end": "2024-01-15T10:31:10Z",
                "routing_account": "ACC_123456",  # Same account as TRADER_SPOOF_99
                "ip_address": "192.168.1.100"     # Same IP as TRADER_SPOOF_99
            },
            {
                "alert_id": "ALT_SPOOF_003",
                "trader_id": "TRADER_COLLUSION_02",
                "alert_timestamp": "2024-01-15T11:15:20Z",
                "alert_type": "SPOOFING",
                "alert_severity": "CRITICAL",
                "symbol": "TSLA",
                "order_to_trade_ratio": 18.7,
                "cancellation_rate": 0.98,
                "avg_execution_horizon_ms": 250.0,
                "window_start": "2024-01-15T11:15:00Z",
                "window_end": "2024-01-15T11:15:10Z",
                "routing_account": "ACC_789012",
                "ip_address": "192.168.2.50"
            }
        ]
        
        loader.load_alert_data(simulated_alerts)
        loader.detect_collusive_spoofing()
        loader.get_network_analysis()
        
        print("=" * 80)
        print("Graph analysis complete. Check Neo4j Browser at http://localhost:7474")
        print("=" * 80)
        
    except Exception as e:
        print(f"Error: {e}")
        raise
    finally:
        loader.close()


if __name__ == "__main__":
    main()
