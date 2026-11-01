-- =====================================================
-- HISTORICAL REPORTING ANALYTICS
-- Distributed Trade Surveillance & Market Abuse Detector
-- =====================================================

-- =====================================================
-- 1. 90-DAY ROLLING WINDOW CALCULATION
-- Rank the top 10 highest risk traders over rolling 90-day periods
-- =====================================================

WITH daily_trader_metrics AS (
  SELECT 
    alert_date,
    trader_id,
    symbol,
    COUNT(*) AS alert_count,
    COUNTIF(alert_severity = 'CRITICAL') AS critical_alerts,
    COUNTIF(alert_severity = 'HIGH') AS high_alerts,
    AVG(order_to_trade_ratio) AS avg_otr,
    AVG(cancellation_rate) AS avg_cancel_rate,
    AVG(avg_execution_horizon_ms) AS avg_exec_horizon,
    SUM(CASE WHEN alert_type = 'SPOOFING' THEN 1 ELSE 0 END) AS spoofing_alerts,
    SUM(CASE WHEN alert_type = 'LAYERING' THEN 1 ELSE 0 END) AS layering_alerts
  FROM `your-gcp-project-id.surveillance.market_abuse_alerts`
  WHERE alert_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
  GROUP BY alert_date, trader_id, symbol
),

rolling_90day AS (
  SELECT 
    trader_id,
    symbol,
    SUM(alert_count) OVER (
      PARTITION BY trader_id, symbol 
      ORDER BY alert_date 
      RANGE BETWEEN INTERVAL 89 DAY PRECEDING AND CURRENT ROW
    ) AS rolling_90day_alerts,
    SUM(critical_alerts) OVER (
      PARTITION BY trader_id, symbol 
      ORDER BY alert_date 
      RANGE BETWEEN INTERVAL 89 DAY PRECEDING AND CURRENT ROW
    ) AS rolling_90day_critical,
    AVG(avg_otr) OVER (
      PARTITION BY trader_id, symbol 
      ORDER BY alert_date 
      RANGE BETWEEN INTERVAL 89 DAY PRECEDING AND CURRENT ROW
    ) AS rolling_90day_avg_otr,
    AVG(avg_cancel_rate) OVER (
      PARTITION BY trader_id, symbol 
      ORDER BY alert_date 
      RANGE BETWEEN INTERVAL 89 DAY PRECEDING AND CURRENT ROW
    ) AS rolling_90day_avg_cancel_rate,
    COUNT(DISTINCT alert_date) OVER (
      PARTITION BY trader_id, symbol 
      ORDER BY alert_date 
      RANGE BETWEEN INTERVAL 89 DAY PRECEDING AND CURRENT ROW
    ) AS active_days_90day,
    ROW_NUMBER() OVER (
      PARTITION BY trader_id, symbol 
      ORDER BY alert_date DESC
    ) AS rn
  FROM daily_trader_metrics
),

risk_scoring AS (
  SELECT 
    trader_id,
    symbol,
    rolling_90day_alerts,
    rolling_90day_critical,
    rolling_90day_avg_otr,
    rolling_90day_avg_cancel_rate,
    active_days_90day,
    -- Risk score calculation
    (rolling_90day_alerts * 10) + 
    (rolling_90day_critical * 25) + 
    (COALESCE(rolling_90day_avg_otr, 0) * 2) + 
    (COALESCE(rolling_90day_avg_cancel_rate, 0) * 100) AS risk_score
  FROM rolling_90day
  WHERE rn = 1 AND rolling_90day_alerts > 0
)

-- TOP 10 HIGHEST RISK TRADERS (90-DAY ROLLING)
SELECT 
  trader_id,
  symbol,
  rolling_90day_alerts AS alerts_90d,
  rolling_90day_critical AS critical_alerts_90d,
  ROUND(rolling_90day_avg_otr, 2) AS avg_otr_90d,
  ROUND(rolling_90day_avg_cancel_rate * 100, 2) AS avg_cancel_rate_pct_90d,
  active_days_90day,
  ROUND(risk_score, 2) AS composite_risk_score,
  RANK() OVER (ORDER BY risk_score DESC) AS risk_rank
FROM risk_scoring
ORDER BY risk_score DESC
LIMIT 10;


-- =====================================================
-- 2. SYMBOL-BASED ANALYTIC PARTITIONING
-- Identify which tickers are experiencing highest concentration of market manipulation alerts
-- =====================================================

WITH symbol_alert_summary AS (
  SELECT 
    symbol,
    alert_date,
    alert_type,
    trader_id,
    alert_severity,
    order_to_trade_ratio,
    cancellation_rate
  FROM `your-gcp-project-id.surveillance.market_abuse_alerts`
  WHERE alert_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
),

symbol_partitioned AS (
  SELECT 
    symbol,
    alert_date,
    COUNT(*) AS daily_alerts,
    COUNT(DISTINCT trader_id) AS unique_traders,
    COUNTIF(alert_severity = 'CRITICAL') AS daily_critical,
    COUNTIF(alert_type = 'SPOOFING') AS daily_spoofing,
    COUNTIF(alert_type = 'LAYERING') AS daily_layering,
    AVG(order_to_trade_ratio) AS avg_otr,
    AVG(cancellation_rate) AS avg_cancel_rate,
    -- Analytic functions partitioned by symbol
    SUM(COUNT(*)) OVER (
      PARTITION BY symbol 
      ORDER BY alert_date 
      RANGE BETWEEN INTERVAL 29 DAY PRECEDING AND CURRENT ROW
    ) AS rolling_30day_alerts_by_symbol,
    AVG(COUNT(*)) OVER (
      PARTITION BY symbol 
      ORDER BY alert_date 
      ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ) AS ma7_daily_alerts,
    SUM(COUNT(DISTINCT trader_id)) OVER (
      PARTITION BY symbol 
      ORDER BY alert_date 
      RANGE BETWEEN INTERVAL 29 DAY PRECEDING AND CURRENT ROW
    ) AS rolling_30day_unique_traders,
    ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY alert_date DESC) AS rn
  FROM symbol_alert_summary
  GROUP BY symbol, alert_date
)

-- TOP TICKERS BY MANIPULATION CONCENTRATION (30-DAY ROLLING)
SELECT 
  symbol,
  rolling_30day_alerts_by_symbol AS alerts_30d,
  rolling_30day_unique_traders AS unique_traders_30d,
  ROUND(rolling_30day_alerts_by_symbol / NULLIF(rolling_30day_unique_traders, 0), 2) AS alerts_per_trader,
  SUM(daily_critical) OVER (PARTITION BY symbol ORDER BY alert_date DESC ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS total_critical_30d,
  ROUND(ma7_daily_alerts, 2) AS ma7_alerts,
  RANK() OVER (ORDER BY rolling_30day_alerts_by_symbol DESC) AS concentration_rank
FROM symbol_partitioned
WHERE rn = 1
ORDER BY rolling_30day_alerts_by_symbol DESC
LIMIT 15;


-- =====================================================
-- 3. WEEKLY ALERT VELOCITY ANALYSIS WITH LAG/LEAD DELTA
-- Isolate individuals whose weekly alert velocity has expanded by over 50%
-- =====================================================

WITH weekly_trader_stats AS (
  SELECT 
    trader_id,
    DATE_TRUNC(alert_date, WEEK(MONDAY)) AS week_start,
    symbol,
    COUNT(*) AS weekly_alerts,
    COUNTIF(alert_severity = 'CRITICAL') AS weekly_critical,
    COUNTIF(alert_type = 'SPOOFING') AS weekly_spoofing,
    AVG(order_to_trade_ratio) AS avg_otr_week,
    AVG(cancellation_rate) AS avg_cancel_week
  FROM `your-gcp-project-id.surveillance.market_abuse_alerts`
  WHERE alert_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 12 WEEK)
  GROUP BY trader_id, week_start, symbol
),

velocity_calculation AS (
  SELECT 
    trader_id,
    symbol,
    week_start,
    weekly_alerts,
    weekly_critical,
    weekly_spoofing,
    LAG(weekly_alerts, 1) OVER (
      PARTITION BY trader_id, symbol 
      ORDER BY week_start
    ) AS prev_week_alerts,
    LAG(weekly_alerts, 2) OVER (
      PARTITION BY trader_id, symbol 
      ORDER BY week_start
    ) AS prev_2week_alerts,
    LEAD(weekly_alerts, 1) OVER (
      PARTITION BY trader_id, symbol 
      ORDER BY week_start
    ) AS next_week_alerts
  FROM weekly_trader_stats
),

velocity_delta AS (
  SELECT 
    trader_id,
    symbol,
    week_start,
    weekly_alerts,
    prev_week_alerts,
    -- Calculate week-over-week delta
    CASE 
      WHEN prev_week_alerts IS NULL OR prev_week_alerts = 0 THEN NULL
      ELSE ROUND((weekly_alerts - prev_week_alerts) / prev_week_alerts * 100, 2)
    END AS wow_velocity_pct,
    -- Calculate acceleration (change in velocity)
    CASE 
      WHEN prev_2week_alerts IS NOT NULL AND prev_week_alerts IS NOT NULL AND prev_2week_alerts > 0 THEN
        CASE 
          WHEN (weekly_alerts - prev_week_alerts) / prev_week_alerts > (prev_week_alerts - prev_2week_alerts) / prev_2week_alerts THEN 'ACCELERATING'
          WHEN (weekly_alerts - prev_week_alerts) / prev_week_alerts < (prev_week_alerts - prev_2week_alerts) / prev_2week_alerts THEN 'DECELERATING'
          ELSE 'STABLE'
        END
      ELSE 'INSUFFICIENT_HISTORY'
    END AS velocity_trend
  FROM velocity_calculation
)

-- TRADERS WITH WEEKLY ALERT VELOCITY EXPANDED BY OVER 50%
SELECT 
  trader_id,
  symbol,
  week_start,
  weekly_alerts AS current_week_alerts,
  prev_week_alerts AS previous_week_alerts,
  wow_velocity_pct AS week_over_week_change_pct,
  velocity_trend,
  CASE 
    WHEN wow_velocity_pct > 50 THEN 'CRITICAL_ESCALATION'
    WHEN wow_velocity_pct > 25 THEN 'HIGH_ESCALATION'
    WHEN wow_velocity_pct > 0 THEN 'MODERATE_INCREASE'
    ELSE 'OTHER'
  END AS escalation_level
FROM velocity_delta
WHERE wow_velocity_pct > 50
  AND week_start >= DATE_SUB(DATE_TRUNC(CURRENT_DATE(), WEEK(MONDAY)), INTERVAL 8 WEEK)
ORDER BY wow_velocity_pct DESC, weekly_alerts DESC;


-- =====================================================
-- 4. COMPREHENSIVE SURVEILLANCE SUMMARY DASHBOARD
-- =====================================================

WITH summary_metrics AS (
  SELECT 
    COUNT(*) AS total_alerts_90d,
    COUNT(DISTINCT trader_id) AS unique_suspicious_traders,
    COUNT(DISTINCT symbol) AS affected_symbols,
    COUNTIF(alert_severity = 'CRITICAL') AS critical_alerts,
    COUNTIF(alert_type = 'SPOOFING') AS spoofing_cases,
    COUNTIF(alert_type = 'LAYERING') AS layering_cases,
    AVG(order_to_trade_ratio) AS overall_avg_otr,
    AVG(cancellation_rate) AS overall_avg_cancel_rate
  FROM `your-gcp-project-id.surveillance.market_abuse_alerts`
  WHERE alert_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
)

SELECT 
  'SURVEILLANCE_SUMMARY_90D' AS report_type,
  total_alerts_90d,
  unique_suspicious_traders,
  affected_symbols,
  critical_alerts,
  spoofing_cases,
  layering_cases,
  ROUND(overall_avg_otr, 2) AS avg_otr,
  ROUND(overall_avg_cancel_rate * 100, 2) AS avg_cancel_rate_pct,
  ROUND(critical_alerts / NULLIF(total_alerts_90d, 0) * 100, 2) AS critical_percentage
FROM summary_metrics;
