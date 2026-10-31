#!/usr/bin/env python3
"""
Market Data Simulator - L3 Order Book Data Generator
Part 2: Distributed Trade Surveillance & Market Abuse Detector

Simulates realistic Level 3 (L3) order book traffic and injects
deterministic market abuse patterns for testing surveillance systems.
"""

import json
import random
import time
import uuid
from datetime import datetime
from typing import Dict, Any, List

from kafka import KafkaProducer
from kafka.errors import KafkaError


class MarketSimulator:
    def __init__(self, bootstrap_servers: str = 'localhost:9092', topic: str = 'market-orders'):
        """
        Initialize the market simulator with Kafka producer.
        
        Args:
            bootstrap_servers: Kafka broker address
            topic: Kafka topic to stream L3 order book data
        """
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.producer = None
        
        # Market configuration
        self.symbols = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'AMZN', 'NVDA']
        self.traders = [f'TRADER_{i:03d}' for i in range(1, 51)]  # 50 legitimate traders
        self.spoof_trader = 'TRADER_SPOOF_99'
        
        # Market state for realistic price movement
        self.current_prices = {
            'AAPL': 175.50,
            'MSFT': 380.25,
            'GOOGL': 142.80,
            'TSLA': 248.90,
            'AMZN': 145.60,
            'NVDA': 875.40
        }
        
        # IP addresses and routing accounts
        self.ip_pool = [f'192.168.{random.randint(1, 255)}.{random.randint(1, 255)}' for _ in range(100)]
        self.routing_accounts = [f'ACC_{random.randint(100000, 999999)}' for _ in range(30)]
        
        # Timing for spoofing injection
        self.last_spoof_time = time.time()
        self.spoof_interval = 30.0  # Inject spoofing every 30 seconds
        
        # Spoofing state
        self.active_spoof_orders = []
        
    def connect_kafka(self):
        """Establish connection to Kafka broker."""
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=[self.bootstrap_servers],
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                acks='all',
                retries=3,
                batch_size=16384,
                linger_ms=10,
                compression_type='gzip'
            )
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Connected to Kafka at {self.bootstrap_servers}")
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Streaming to topic: {self.topic}")
        except KafkaError as e:
            print(f"Error connecting to Kafka: {e}")
            raise
    
    def generate_order_id(self) -> str:
        """Generate a unique order ID."""
        return f"ORD_{uuid.uuid4().hex[:12].upper()}"
    
    def get_realistic_price(self, symbol: str) -> float:
        """Get realistic price with small random walk."""
        base_price = self.current_prices[symbol]
        # Small price movement (-0.1% to +0.1%)
        movement = random.uniform(-0.001, 0.001)
        new_price = round(base_price * (1 + movement), 2)
        self.current_prices[symbol] = new_price
        return new_price
    
    def create_order_event(self, trader_id: str, symbol: str, side: str, 
                          action: str, price: float, quantity: int) -> Dict[str, Any]:
        """
        Create a standardized L3 order book event.
        
        Schema fields: timestamp (epoch ms), order_id, trader_id, symbol, 
        side (BUY/SELL), action (NEW, CANCEL, FILL), price (float), 
        quantity (int), ip_address (string), routing_account (string)
        """
        return {
            "timestamp": int(time.time() * 1000),  # epoch ms
            "order_id": self.generate_order_id(),
            "trader_id": trader_id,
            "symbol": symbol,
            "side": side,
            "action": action,
            "price": round(float(price), 2),
            "quantity": int(quantity),
            "ip_address": random.choice(self.ip_pool),
            "routing_account": random.choice(self.routing_accounts)
        }
    
    def send_order(self, order_event: Dict[str, Any]):
        """Send order event to Kafka topic."""
        try:
            future = self.producer.send(
                self.topic, 
                key=order_event['order_id'], 
                value=order_event
            )
        except KafkaError as e:
            print(f"Error sending order to Kafka: {e}")
    
    def inject_spoofing_pattern(self):
        """
        Inject a clear, deterministic 'Spoofing' anomaly every 30 seconds.
        
        Pattern:
        1. Place 5 massive BUY orders (NEW) far below the current best bid (creating fake demand)
        2. Wait 800 milliseconds
        3. Issue 5 CANCEL actions immediately after a separate small target SELL order executes
        """
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
              f"*** INJECTING SPOOFING PATTERN - TRADER: {self.spoof_trader} ***")
        
        symbol = random.choice(self.symbols)
        current_price = self.current_prices[symbol]
        
        # Place 5 massive BUY orders far below the best bid (10-15% below to create fake demand)
        spoof_orders = []
        for i in range(5):
            spoof_price = round(current_price * random.uniform(0.85, 0.90), 2)  # 10-15% below
            spoof_qty = random.randint(50000, 100000)  # Massive orders
            order_event = self.create_order_event(
                self.spoof_trader, symbol, "BUY", "NEW", spoof_price, spoof_qty
            )
            self.send_order(order_event)
            spoof_orders.append(order_event)
            print(f"  [SPOOF] NEW BUY {spoof_qty} @ {spoof_price} (Order: {order_event['order_id']})")
            time.sleep(0.02)  # Small delay between orders
        
        # Wait 800 milliseconds as specified
        print(f"  [SPOOF] Waiting 800ms...")
        time.sleep(0.8)
        
        # Execute a separate small target SELL order to trigger the pattern
        target_sell_qty = random.randint(100, 500)
        target_sell_order = self.create_order_event(
            random.choice(self.traders), symbol, "SELL", "NEW", current_price, target_sell_qty
        )
        self.send_order(target_sell_order)
        print(f"  [TRIGGER] NEW SELL {target_sell_qty} @ {current_price}")
        time.sleep(0.01)
        
        # Execute FILL for target sell order
        fill_order = self.create_order_event(
            target_sell_order['trader_id'], symbol, "SELL", "FILL", 
            target_sell_order['price'], target_sell_order['quantity']
        )
        self.send_order(fill_order)
        print(f"  [TRIGGER] FILL SELL {target_sell_qty} @ {current_price}")
        time.sleep(0.05)
        
        # Issue 5 CANCEL actions immediately after
        print(f"  [SPOOF] Cancelling all spoof orders...")
        for spoof_order in spoof_orders:
            cancel_order = self.create_order_event(
                self.spoof_trader, symbol, "BUY", "CANCEL", 
                spoof_order['price'], spoof_order['quantity']
            )
            # Use same order context for cancellation
            cancel_order['order_id'] = spoof_order['order_id']  # Cancel the specific order
            self.send_order(cancel_order)
            print(f"  [SPOOF] CANCEL BUY @ {spoof_order['price']} (Order: {cancel_order['order_id']})")
            time.sleep(0.01)
        
        print(f"  [SPOOF] Pattern complete - {len(spoof_orders)} orders placed and cancelled\n")
    
    def generate_normal_trading(self):
        """Generate normal random trading activity."""
        symbol = random.choice(self.symbols)
        trader = random.choice(self.traders)
        side = random.choice(['BUY', 'SELL'])
        action = random.choices(['NEW', 'FILL', 'CANCEL'], weights=[0.6, 0.3, 0.1])[0]
        
        price = self.get_realistic_price(symbol)
        if side == 'BUY':
            price = round(price * random.uniform(0.9995, 1.0005), 2)
        else:
            price = round(price * random.uniform(0.9995, 1.0005), 2)
        
        quantity = random.randint(10, 1000)
        
        order_event = self.create_order_event(trader, symbol, side, action, price, quantity)
        self.send_order(order_event)
    
    def run(self, duration_minutes: int = None):
        """Run the market simulator."""
        try:
            self.connect_kafka()
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting market simulation...")
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Normal trading + Spoofing every 30 seconds")
            print("=" * 80)
            
            start_time = time.time()
            while True:
                if duration_minutes and (time.time() - start_time) > duration_minutes * 60:
                    break
                
                current_time = time.time()
                # Check if it's time to inject spoofing
                if current_time - self.last_spoof_time >= self.spoof_interval:
                    self.inject_spoofing_pattern()
                    self.last_spoof_time = current_time
                
                # Generate normal trading activity
                self.generate_normal_trading()
                
                # Random delay between orders (10-100ms for realistic high frequency)
                time.sleep(random.uniform(0.01, 0.1))
                
        except KeyboardInterrupt:
            print("\n\nShutting down market simulator...")
            if self.producer:
                self.producer.close()
        except Exception as e:
            print(f"Error in market simulator: {e}")
            raise


def main():
    simulator = MarketSimulator()
    simulator.run()


if __name__ == "__main__":
    main()
