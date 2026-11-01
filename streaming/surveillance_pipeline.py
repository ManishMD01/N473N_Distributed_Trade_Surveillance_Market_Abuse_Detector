#!/usr/bin/env python3
"""
Surveillance Pipeline - PySpark Structured Streaming
Part 3: Distributed Trade Surveillance & Market Abuse Detector

Processes L3 order book data from Kafka 'market-orders' topic,
computes stateful metrics for market abuse detection (Spoofing/Layering),
and writes alerts to Google BigQuery.
"""

import sys
from datetime import datetime
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, from_json, to_timestamp, window, 
    count, sum as spark_sum, avg, when, 
    max as spark_max, min as spark_min,
    expr, unix_timestamp, lit, current_timestamp,
    to_date, format_string
)
from pyspark.sql.types import (
    StructType, StructField, StringType, 
    LongType, DoubleType, IntegerType, TimestampType
)


class SurveillancePipeline:
    def __init__(self, 
                 kafka_bootstrap: str = "localhost:9092",
                 kafka_topic: str = "market-orders",
                 checkpoint_location: str = "/tmp/surveillance-checkpoint",
                 bigquery_project: str = "your-gcp-project-id",
                 bigquery_dataset: str = "surveillance",
                 bigquery_table: str = "market_abuse_alerts"):
        """
        Initialize the surveillance pipeline.
        
        Args:
            kafka_bootstrap: Kafka bootstrap servers
            kafka_topic: Kafka topic containing L3 order book data
            checkpoint_location: Checkpoint directory for streaming
            bigquery_project: GCP project for BigQuery
            bigquery_dataset: BigQuery dataset name
            bigquery_table: BigQuery table name for alerts
        """
        self.kafka_bootstrap = kafka_bootstrap
        self.kafka_topic = kafka_topic
        self.checkpoint_location = checkpoint_location
        self.bigquery_project = bigquery_project
        self.bigquery_dataset = bigquery_dataset
        self.bigquery_table = bigquery_table
        
        # Initialize Spark Session with BigQuery connector
        self.spark = self._create_spark_session()
        
        # Define strict schema for L3 order book events
        self.order_schema = self._define_order_schema()
        
    def _create_spark_session(self) -> SparkSession:
        """Create Spark session with necessary configurations."""
        spark = SparkSession.builder \
            .appName("DistributedTradeSurveillancePipeline") \
            .config("spark.sql.streaming.checkpointLocation", self.checkpoint_location) \
            .config("spark.sql.adaptive.enabled", "true") \
            .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
            .config("spark.streaming.stopGracefullyOnShutdown", "true") \
            .config("spark.sql.shuffle.partitions", "200") \
            .config("spark.jars.packages", 
                    "org.apache.spark:spark-sql-kafka-0-10_2.12:3.4.1,"
                    "com.google.cloud.spark:spark-bigquery-with-dependencies_2.12:0.36.1") \
            .getOrCreate()
        
        spark.sparkContext.setLogLevel("WARN")
        return spark
    
    def _define_order_schema(self) -> StructType:
        """
        Enforce strict schema corresponding to JSON objects from market simulator.
        Fields: timestamp (epoch ms), order_id, trader_id, symbol, side, 
        action, price, quantity, ip_address, routing_account
        """
        schema = StructType([
            StructField("timestamp", LongType(), nullable=False),
            StructField("order_id", StringType(), nullable=False),
            StructField("trader_id", StringType(), nullable=False),
            StructField("symbol", StringType(), nullable=False),
            StructField("side", StringType(), nullable=False),      # BUY/SELL
            StructField("action", StringType(), nullable=False),    # NEW, CANCEL, FILL
            StructField("price", DoubleType(), nullable=False),
            StructField("quantity", IntegerType(), nullable=False),
            StructField("ip_address", StringType(), nullable=False),
            StructField("routing_account", StringType(), nullable=False)
        ])
        return schema
    
    def read_from_kafka(self):
        """Read streaming data from Kafka market-orders topic."""
        kafka_df = self.spark \
            .readStream \
            .format("kafka") \
            .option("kafka.bootstrap.servers", self.kafka_bootstrap) \
            .option("subscribe", self.kafka_topic) \
            .option("startingOffsets", "latest") \
            .option("failOnDataLoss", "false") \
            .load()
        
        # Parse JSON data with strict schema
        parsed_df = kafka_df \
            .select(
                from_json(col("value").cast("string"), self.order_schema).alias("data")
            ) \
            .select("data.*") \
            .withColumn("event_timestamp", 
                       (col("timestamp") / 1000).cast(TimestampType())) \
            .withColumn("event_time_unix_ms", col("timestamp"))
        
        return parsed_df
    
    def compute_surveillance_metrics(self, parsed_df):
        """
        Compute stateful metrics with 10-second sliding window and 2-second watermark.
        Grouped by window, trader_id, and symbol.
        """
        # Apply watermark and sliding window
        windowed_df = parsed_df \
            .withWatermark("event_timestamp", "2 seconds") \
            .groupBy(
                window(col("event_timestamp"), "10 seconds", "5 seconds"),  # 10-sec window, sliding
                col("trader_id"),
                col("symbol")
            )
        
        # Compute metrics for each window
        metrics_df = windowed_df.agg(
            # Count of NEW orders
            count(when(col("action") == "NEW", 1)).alias("new_order_count"),
            
            # Count of FILL actions
            count(when(col("action") == "FILL", 1)).alias("fill_count"),
            
            # Count of CANCEL actions
            count(when(col("action") == "CANCEL", 1)).alias("cancel_count"),
            
            # Window boundaries
            spark_max("event_timestamp").alias("window_end_time"),
            spark_min("event_timestamp").alias("window_start_time"),
            
            # Additional metrics
            count("*").alias("total_orders")
        )
        
        # Compute derived metrics
        calculated_metrics_df = metrics_df \
            .withColumn("order_to_trade_ratio", 
                       when(col("fill_count") > 0, 
                            col("new_order_count").cast("double") / col("fill_count").cast("double"))
                       .otherwise(lit(float('inf')))) \
            .withColumn("cancellation_rate",
                       when(col("new_order_count") > 0,
                            (col("cancel_count").cast("double") / 
                             col("new_order_count").cast("double")))
                       .otherwise(lit(0.0)))
        
        # Calculate Average Execution Horizon: time between order's 'NEW' timestamp and its 'CANCEL' timestamp
        execution_horizon_df = self._calculate_execution_horizon(parsed_df, windowed_df)
        
        # Join execution horizon metrics
        final_metrics_df = calculated_metrics_df \
            .join(
                execution_horizon_df,
                ["window", "trader_id", "symbol"],
                "left"
            ) \
            .withColumn("avg_execution_horizon_ms",
                       when(col("avg_execution_horizon_ms").isNull(), lit(0.0))
                       .otherwise(col("avg_execution_horizon_ms")))
        
        return final_metrics_df
    
    def _calculate_execution_horizon(self, parsed_df, windowed_df):
        """
        Calculate Average time in milliseconds between an order's 'NEW' timestamp 
        and its 'CANCEL' timestamp.
        """
        # Create pairs of NEW and CANCEL orders for same trader/symbol
        new_orders = parsed_df \
            .filter(col("action") == "NEW") \
            .select(
                col("trader_id"),
                col("symbol"),
                col("order_id").alias("new_order_id"),
                col("event_timestamp").alias("new_timestamp"),
                col("event_time_unix_ms").alias("new_time_ms")
            )
        
        cancel_orders = parsed_df \
            .filter(col("action") == "CANCEL") \
            .select(
                col("trader_id"),
                col("symbol"),
                col("order_id").alias("cancel_order_id"),
                col("event_timestamp").alias("cancel_timestamp"),
                col("event_time_unix_ms").alias("cancel_time_ms")
            )
        
        # Join NEW and CANCEL orders (simplified pairing by order_id for spoofing pattern)
        order_pairs = new_orders \
            .join(
                cancel_orders,
                (new_orders.new_order_id == cancel_orders.cancel_order_id) &
                (new_orders.trader_id == cancel_orders.trader_id) &
                (new_orders.symbol == cancel_orders.symbol),
                "inner"
            ) \
            .withColumn("execution_horizon_ms", 
                       col("cancel_time_ms") - col("new_time_ms")) \
            .filter(col("execution_horizon_ms") >= 0) \
            .filter(col("execution_horizon_ms") <= 60000)  # Filter outliers
        
        # Apply same windowing
        horizon_windowed = order_pairs \
            .withWatermark("cancel_timestamp", "2 seconds") \
            .groupBy(
                window(col("cancel_timestamp"), "10 seconds", "5 seconds"),
                col("trader_id"),
                col("symbol")
            ) \
            .agg(
                avg(col("execution_horizon_ms")).alias("avg_execution_horizon_ms"),
                count("*").alias("paired_cancels_count")
            )
        
        return horizon_windowed
    
    def flag_alerts(self, final_metrics_df):
        """
        Flag alert records if trader's window exceeds:
        - OTR > 5
        - Cancellation Rate > 80%
        - Execution Horizon < 2000ms
        """
        alerts_df = final_metrics_df \
            .filter(
                (col("order_to_trade_ratio") > 5.0) &
                (col("cancellation_rate") > 0.80) &
                (col("avg_execution_horizon_ms") < 2000.0)
            ) \
            .select(
                # Alert metadata
                current_timestamp().alias("alert_timestamp"),
                to_date(current_timestamp()).alias("alert_date"),
                
                # Window information
                col("window.start").alias("window_start"),
                col("window.end").alias("window_end"),
                
                # Trader and symbol
                col("trader_id"),
                col("symbol"),
                
                # Computed metrics
                col("order_to_trade_ratio"),
                col("cancellation_rate"),
                col("avg_execution_horizon_ms"),
                
                # Supporting metrics
                col("new_order_count"),
                col("fill_count"),
                col("cancel_count"),
                col("total_orders"),
                
                # Alert classification
                lit("SPOOFING").alias("alert_type"),
                lit("HIGH").alias("alert_severity"),
                lit("L3_ORDER_BOOK_ANALYSIS").alias("detection_method"),
                
                # Additional context
                format_string("OTR:%.2f, CancelRate:%.2f%%, ExecHorizon:%dms",
                             col("order_to_trade_ratio"),
                             col("cancellation_rate") * 100.0,
                             col("avg_execution_horizon_ms").cast("long")).alias("alert_description")
            )
        
        return alerts_df
    
    def get_bigquery_ddl(self) -> str:
        """
        Provide the BigQuery DDL layout to store these alerts,
        partitioned by alert_date and clustered by trader_id and symbol.
        """
        ddl = f"""
-- BigQuery DDL for Market Abuse Alerts
-- Part 3: Distributed Trade Surveillance & Market Abuse Detector
-- Partitioned by alert_date and clustered by trader_id and symbol

CREATE TABLE IF NOT EXISTS `{self.bigquery_project}.{self.bigquery_dataset}.{self.bigquery_table}` (
  alert_timestamp TIMESTAMP NOT NULL,
  alert_date DATE NOT NULL,
  window_start TIMESTAMP,
  window_end TIMESTAMP,
  trader_id STRING NOT NULL,
  symbol STRING NOT NULL,
  order_to_trade_ratio FLOAT64,
  cancellation_rate FLOAT64,
  avg_execution_horizon_ms FLOAT64,
  new_order_count INT64,
  fill_count INT64,
  cancel_count INT64,
  total_orders INT64,
  alert_type STRING,
  alert_severity STRING,
  detection_method STRING,
  alert_description STRING
)
PARTITION BY alert_date
CLUSTER BY trader_id, symbol
OPTIONS(
  description="Market abuse alerts generated from L3 order book surveillance pipeline - SEC Rule 10b-5 compliance",
  labels=[("environment", "production"), ("team", "fincrime"), ("pipeline", "surveillance"), ("compliance", "sec_finra")]
);
"""
        return ddl
    
    def write_to_bigquery(self, alerts_df):
        """
        PySpark .writeStream code block configured to write alerts to BigQuery
        using the spark-bigquery connector format.
        """
        bigquery_table_full = f"{self.bigquery_project}.{self.bigquery_dataset}.{self.bigquery_table}"
        
        query = alerts_df.writeStream \
            .format("bigquery") \
            .option("table", bigquery_table_full) \
            .option("temporaryGcsBucket", "your-temporary-gcs-bucket") \
            .option("checkpointLocation", f"{self.checkpoint_location}/bigquery") \
            .option("createDisposition", "CREATE_IF_NEEDED") \
            .option("writeDisposition", "WRITE_APPEND") \
            .outputMode("append") \
            .trigger(processingTime="10 seconds") \
            .start()
        
        return query
    
    def run(self):
        """Run the complete surveillance pipeline."""
        try:
            print("=" * 80)
            print("DISTRIBUTED TRADE SURVEILLANCE & MARKET ABUSE DETECTOR - PART 3")
            print("=" * 80)
            print(f"Starting surveillance pipeline at {datetime.now()}")
            print(f"Kafka: {self.kafka_bootstrap}, Topic: {self.kafka_topic}")
            print(f"BigQuery: {self.bigquery_project}.{self.bigquery_dataset}.{self.bigquery_table}")
            print("=" * 80)
            
            # Display BigQuery DDL
            print("\nBIGQUERY DDL LAYOUT:")
            print(self.get_bigquery_ddl())
            print("=" * 80)
            
            # Read from Kafka
            print("\n[1/4] Reading from Kafka topic...")
            parsed_df = self.read_from_kafka()
            
            # Compute surveillance metrics
            print("[2/4] Computing stateful metrics (10s sliding window, 2s watermark)...")
            metrics_df = self.compute_surveillance_metrics(parsed_df)
            
            # Flag alerts
            print("[3/4] Flagging alerts (OTR>5, CancelRate>80%, ExecHorizon<2000ms)...")
            alerts_df = self.flag_alerts(metrics_df)
            
            # Write to BigQuery
            print("[4/4] Starting BigQuery streaming write...")
            query = self.write_to_bigquery(alerts_df)
            
            print("\nPipeline is running. Press Ctrl+C to stop.")
            print("=" * 80)
            
            query.awaitTermination()
            
        except KeyboardInterrupt:
            print("\n\nShutting down surveillance pipeline...")
            self.spark.stop()
        except Exception as e:
            print(f"Error in surveillance pipeline: {e}")
            raise


def main():
    """Main entry point."""
    pipeline = SurveillancePipeline(
        kafka_bootstrap="localhost:9092",
        kafka_topic="market-orders",
        checkpoint_location="/tmp/surveillance-checkpoint",
        bigquery_project="your-gcp-project-id",
        bigquery_dataset="surveillance",
        bigquery_table="market_abuse_alerts"
    )
    pipeline.run()


if __name__ == "__main__":
    main()
