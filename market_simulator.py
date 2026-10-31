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
        
        Args:
            trader_id: ID of the trader placing the order
            symbol: Trading symbol
            side: BUY or SELL
            action: NEW, CANCEL, or FILL
            price: Order price
            quantity: Order quantity
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
            # Use order_id as key for partitioning
            future = self.producer.send(
                self.topic, 
                key=order_event['order_id'], 
                value=order_event
            )
            # Optional: wait for confirmation (disabled for high throughput)
            # future.get(timeout=10)
        except KafkaError as e:
            print(f"Error sending order to Kafka: {e}")
    
    def inject_spoofing_pattern(self):
        """
        Inject a clear, deterministic 'Spoofing' pattern every 30 seconds.
        
        Pattern:
        1. Place 5 massive BUY orders (NEW) far below the best bid
        2. Wait exactly 500ms to create false market depth pressure
        3. Rapidly issue CANCEL commands for all 5 orders immediately after
           a small matching transaction executes
        """
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
              f"*** INJECTING SPOOFING PATTERN - TRADER: {self.spoof_trader} ***")
        
        symbol = random.choice(self.symbols)
        current_price = self.current_prices[symbol]
        
        # Place 5 massive BUY orders far below the best bid (10-15% below)
        spoof_orders = []
        for i in range(5):
            # Place orders significantly below market (spoofing layer)
            spoof_price = round(current_price * random.uniform(0.85, 0.90), 2)  # 10-15% below
            spoof_quantity = random.randint(5000, 10000)  # Massive orders
            
            order_event = self.create_order_event(
                trader_id=self.spoof_trader,
                symbol=symbol,
                side='BUY',
                action='NEW',
                price=spoof_price,
                quantity=spoof_quantity
            )
            spoof_orders.append(order_event)
            self.send_order(order_event)
            print(f"  [SPOOF] NEW BUY {order_event['order_id']} @ ${spoof_price} "
                  f"qty={spoof_quantity} (far below market ${current_price})")
            time.sleep(0.01)  # Small delay between spoof orders
        
        # Wait exactly 500ms to create false market depth pressure
        print(f"  [SPOOF] Creating false market depth pressure... waiting 500ms")
        time.sleep(0.5)
        
        # Execute a small matching transaction (to trigger the cancel pattern)
        print(f"  [SPOOF] Executing small matching transaction to trigger cancels...")
        legitimate_trader = random.choice([t for t in self.traders if t != self.spoof_trader])
        small_fill_price = round(current_price * random.uniform(0.99, 1.01), 2)
        small_fill_quantity = random.randint(10, 50)
        
        fill_order = self.create_order_event(
            trader_id=legitimate_trader,
            symbol=symbol,
            side='SELL',
            action='FILL',
            price=small_fill_price,
            quantity=small_fill_quantity
        )
        self.send_order(fill_order)
        print(f"  [LEGIT] FILL {fill_order['order_id']} SELL {legitimate_trader} "
              f"@ ${small_fill_price} qty={small_fill_quantity}")
        
        # Rapidly issue CANCEL commands for all 5 spoof orders
        print(f"  [SPOOF] Rapidly cancelling all spoof orders...")
        for order_event in spoof_orders:
            cancel_event = self.create_order_event(
                trader_id=self.spoof_trader,
                symbol=symbol,
                side=order_event['side'],
                action='CANCEL',
                price=order_event['price'],
                quantity=order_event['quantity']
            )
            # Use same order_id context conceptually - in real system would reference original
            cancel_event['original_order_id'] = order_event['order_id']
            self.send_order(cancel_event)
            print(f"  [SPOOF] CANCEL {cancel_event['order_id']} (orig: {order_event['order_id']})")
            time.sleep(0.005)  # Very rapid cancellation
        
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
              f"*** SPOOFING PATTERN COMPLETE ***\n")
        
        self.last_spoof_time = time.time()
    
    def generate_normal_activity(self):
        """Generate normal market activity."""
        symbol = random.choice(self.symbols)
        trader_id = random.choice(self.traders)
        side = random.choice(['BUY', 'SELL'])
        action = random.choices(['NEW', 'CANCEL', 'FILL'], weights=[0.6, 0.2, 0.2])[0]
        
        current_price = self.current_prices[symbol]
        
        if action == 'NEW':
            # New orders around current price
            price_variance = random.uniform(-0.02, 0.02)
            price = round(current_price * (1 + price_variance), 2)
            quantity = random.randint(1, 1000)
        elif action == 'CANCEL':
            # Cancellations of existing orders
            price_variance = random.uniform(-0.015, 0.015)
            price = round(current_price * (1 + price_variance), 2)
            quantity = random.randint(1, 500)
        else:  # FILL
            # Fills at market-like prices
            price_variance = random.uniform(-0.01, 0.01)
            price = round(current_price * (1 + price_variance), 2)
            quantity = random.randint(1, 200)
        
        order_event = self.create_order_event(
            trader_id=trader_id,
            symbol=symbol,
            side=side,
            action=action,
            price=price,
            quantity=quantity
        )
        
        self.send_order(order_event)
        return order_event
    
    def run(self):
        """Run the market simulator continuously."""
        try:
            self.connect_kafka()
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                  f"Starting L3 order book simulation...")
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                  f"Spoofing injection every {self.spoof_interval} seconds")
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                  f"Press Ctrl+C to stop\n")
            
            while True:
                current_time = time.time()
                
                # Check if it's time to inject spoofing pattern (every 30 seconds)
                if current_time - self.last_spoof_time >= self.spoof_interval:
                    self.inject_spoofing_pattern()
                
                # Generate normal market activity
                order_event = self.generate_normal_activity()
                
                # Log activity occasionally
                if random.random() < 0.01:  # Log 1% of orders
                    print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] "
                          f"{order_event['action']} {order_event['side']} "
                          f"{order_event['symbol']} {order_event['trader_id']} "
                          f"@${order_event['price']} qty={order_event['quantity']}")
                
                # Sleep 10ms between loops for high rate simulation
                time.sleep(0.01)
                
        except KeyboardInterrupt:
            print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                  f"Shutting down market simulator...")
        except Exception as e:
            print(f"Error in market simulator: {e}")
            raise
        finally:
            if self.producer:
                self.producer.flush()
                self.producer.close()
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                      f"Kafka producer closed.")


def main():
    """Main entry point."""
    simulator = MarketSimulator(
        bootstrap_servers='localhost:9092',
        topic='market-orders'
    )
    simulator.run()


if __name__ == "__main__":
    main()
