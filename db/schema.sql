-- TimescaleDB schema. Keep source identity in a separate restricted vault.
CREATE TABLE IF NOT EXISTS trades (
  event_id TEXT PRIMARY KEY,
  symbol TEXT NOT NULL,
  event_time TIMESTAMPTZ NOT NULL,
  buyer_ref TEXT NOT NULL, -- pseudonymized before ingestion
  seller_ref TEXT NOT NULL, -- pseudonymized before ingestion
  price NUMERIC(20,8) NOT NULL CHECK (price >= 0),
  quantity NUMERIC(20,8) NOT NULL CHECK (quantity > 0),
  ingested_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
SELECT create_hypertable('trades', by_range('event_time'), if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS trades_symbol_time_idx ON trades (symbol, event_time DESC);
CREATE INDEX IF NOT EXISTS trades_buyer_time_idx ON trades (buyer_ref, event_time DESC);

CREATE TABLE IF NOT EXISTS surveillance_alerts (
  alert_id TEXT PRIMARY KEY,
  alert_type TEXT NOT NULL CHECK (alert_type IN ('wash_trade', 'spoofing')),
  status TEXT NOT NULL DEFAULT 'open',
  severity TEXT NOT NULL,
  detected_at TIMESTAMPTZ NOT NULL,
  symbol TEXT NOT NULL,
  trader_ref TEXT NOT NULL,
  risk_score NUMERIC(5,2) NOT NULL,
  notional_value NUMERIC(24,8) NOT NULL,
  rationale TEXT NOT NULL,
  evidence_refs TEXT[] NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS alerts_detected_idx ON surveillance_alerts (detected_at DESC, symbol);

-- Window-based wash-trade candidate query. Tune the interval and thresholds per venue.
WITH ordered AS (
  SELECT *,
    lag(event_time) OVER (
      PARTITION BY symbol, price, quantity, buyer_ref, seller_ref
      ORDER BY event_time
    ) AS previous_time
  FROM trades
  WHERE event_time >= $1 AND event_time < $2
)
SELECT event_id, symbol, event_time, buyer_ref, seller_ref, price, quantity
FROM ordered
WHERE previous_time IS NOT NULL
  AND event_time - previous_time <= INTERVAL '500 milliseconds'
  AND buyer_ref = seller_ref;
