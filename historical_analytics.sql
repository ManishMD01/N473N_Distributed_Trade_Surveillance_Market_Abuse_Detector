-- =====================================================
-- Part 5: Historical Analytics - 90-Day Rolling Compliance Audit
-- Distributed Trade Surveillance & Market Abuse Detector
-- =====================================================

-- Database/Schema Reference
-- Table: your-gcp-project-id.surveillance.market_abuse_alerts
-- Partitioned by: alert_date
-- Clustered by: trader_id, symbol

-- =====================================================
-- QUERY 1: REPEAT OFFENDERS - 90-Day Rolling Risk Score
-- Calculate running risk score for every trader based on
-- total alert count and average OTR over 90-day window
-- =====================================================

WITH trader_daily_stats AS (
  SELECT 
    trader_id,
    alert_date,
    COUNT(*) AS daily_alert_count,
    AVG(order_to_trade_ratio) AS daily_avg_otr,
    AVG(cancellation_percentage) AS daily_avg_cancellation_pct,
    AVG(avg_execution_horizon_ms) AS daily_avg_exec_horizon,
    MAX(alert_severity) AS max_severity_day,
    COUNT(DISTINCT symbol) AS symbols_targeted
  FROM 
    `your-gcp-project-id.surveillance.market_abuse_alerts`
  WHERE 
    alert_date BETWEEN DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY) 
                    AND CURRENT_DATE()
    AND alert_type = 'SPOOFING_SUSPECTED'
  GROUP BY 
    trader_id, alert_date
),

trader_90day_rolling AS (
  SELECT 
    trader_id,
    alert_date,
    daily_alert_count,
    daily_avg_otr,
    daily_avg_cancellation_pct,
    daily_avg_exec_horizon,
    symbols_targeted,
    SUM(daily_alert_count) OVER (
      PARTITION BY trader_id 
      ORDER BY alert_date 
      ROWS BETWEEN 89 PRECEDING AND CURRENT ROW
    ) AS rolling_90d_alert_count,
    AVG(daily_avg_otr) OVER (
      PARTITION BY trader_id 
      ORDER BY alert_date 
      ROWS BETWEEN 89 PRECEDING AND CURRENT ROW
    ) AS rolling_90d_avg_otr,
    AVG(daily_avg_cancellation_pct) OVER (
      PARTITION BY trader_id 
      ORDER BY alert_date 
      ROWS BETWEEN 89 PRECEDING AND CURRENT ROW
    ) AS rolling_90d_avg_cancellation_pct,
    AVG(daily_avg_exec_horizon) OVER (
      PARTITION BY trader_id 
      ORDER BY alert_date 
      ROWS BETWEEN 89 PRECEDING AND CURRENT ROW
    ) AS rolling_90d_avg_exec_horizon,
    ROW_NUMBER() OVER (
      PARTITION BY trader_id 
      ORDER BY alert_date
    ) AS days_observed
  FROM trader_daily_stats
),

repeat_offenders_risk AS (
  SELECT 
    trader_id,
    alert_date,
    rolling_90d_alert_count AS total_alerts_90d,
    ROUND(rolling_90d_avg_otr, 3) AS avg_otr_90d,
    ROUND(rolling_90d_avg_cancellation_pct, 2) AS avg_cancellation_pct_90d,
    ROUND(rolling_90d_avg_exec_horizon, 2) AS avg_exec_horizon_ms_90d,
    days_observed,
    ROUND(
      (rolling_90d_alert_count * 2.5) + 
      (rolling_90d_avg_otr * 1.8) + 
      (rolling_90d_avg_cancellation_pct * 0.3),
      2
    ) AS running_risk_score,
    CASE 
      WHEN (rolling_90d_alert_count * 2.5 + rolling_90d_avg_otr * 1.8 + rolling_90d_avg_cancellation_pct * 0.3) >= 200 THEN 'CRITICAL'
      WHEN (rolling_90d_alert_count * 2.5 + rolling_90d_avg_otr * 1.8 + rolling_90d_avg_cancellation_pct * 0.3) >= 150 THEN 'HIGH'
      WHEN (rolling_90d_alert_count * 2.5 + rolling_90d_avg_otr * 1.8 + rolling_90d_avg_cancellation_pct * 0.3) >= 100 THEN 'MEDIUM'
      WHEN (rolling_90d_alert_count * 2.5 + rolling_90d_avg_otr * 1.8 + rolling_90d_avg_cancellation_pct * 0.3) >= 50 THEN 'LOW'
      ELSE 'MINIMAL'
    END AS risk_category
  FROM trader_90day_rolling
  WHERE days_observed >= 1
)

SELECT 
  trader_id,
  alert_date,
  total_alerts_90d,
  avg_otr_90d,
  avg_cancellation_pct_90d,
  avg_exec_horizon_ms_90d,
  running_risk_score,
  risk_category,
  CASE 
    WHEN total_alerts_90d >= 10 AND running_risk_score >= 150 THEN TRUE 
    ELSE FALSE 
  END AS is_repeat_offender
FROM repeat_offenders_risk
WHERE alert_date = CURRENT_DATE()
ORDER BY running_risk_score DESC, total_alerts_90d DESC;


-- =====================================================
-- QUERY 2: TICKER TARGETING ANALYSIS
-- Partition alerts by stock symbol to identify which
-- specific tickers are being targeted by manipulative algorithms
-- =====================================================

WITH symbol_daily_metrics AS (
  SELECT 
    symbol,
    alert_date,
    COUNT(*) AS alert_count,
    COUNT(DISTINCT trader_id) AS unique_traders,
    AVG(order_to_trade_ratio) AS avg_otr,
    AVG(cancellation_percentage) AS avg_cancellation_pct,
    AVG(avg_execution_horizon_ms) AS avg_exec_horizon,
    SUM(new_order_count) AS total_new_orders,
    SUM(fill_count) AS total_fills,
    SUM(cancel_count) AS total_cancels
  FROM 
    `your-gcp-project-id.surveillance.market_abuse_alerts`
  WHERE 
    alert_date BETWEEN DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY) 
                    AND CURRENT_DATE()
    AND alert_type = 'SPOOFING_SUSPECTED'
  GROUP BY 
    symbol, alert_date
),

symbol_partitioned_analysis AS (
  SELECT 
    symbol,
    alert_date,
    alert_count,
    unique_traders,
    ROUND(avg_otr, 3) AS avg_otr,
    ROUND(avg_cancellation_pct, 2) AS avg_cancellation_pct,
    ROUND(avg_exec_horizon, 2) AS avg_exec_horizon,
    total_new_orders,
    total_fills,
    total_cancels,
    RANK() OVER (
      PARTITION BY symbol 
      ORDER BY alert_count DESC, avg_otr DESC
    ) AS daily_rank_in_symbol,
    DENSE_RANK() OVER (
      ORDER BY alert_count DESC
    ) AS overall_rank,
    SUM(alert_count) OVER (
      PARTITION BY symbol 
      ORDER BY alert_date 
      ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ) AS rolling_7d_alerts,
    AVG(alert_count) OVER (
      PARTITION BY symbol 
      ORDER BY alert_date 
      ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ) AS rolling_7d_avg_alerts,
    SUM(alert_count) OVER (
      PARTITION BY symbol 
      ORDER BY alert_date 
      ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
    ) AS rolling_30d_alerts,
    SUM(alert_count) OVER (
      PARTITION BY symbol 
      ORDER BY alert_date 
      ROWS BETWEEN 89 PRECEDING AND CURRENT ROW
    ) AS rolling_90d_total,
    ROUND(alert_count * 100.0 / SUM(alert_count) OVER (
      PARTITION BY alert_date
    ), 2) AS pct_of_daily_alerts,
    ROUND(unique_traders * 100.0 / SUM(unique_traders) OVER (
      PARTITION BY alert_date
    ), 2) AS pct_of_daily_traders
  FROM symbol_daily_metrics
)

SELECT 
  symbol,
  alert_count AS alerts_today,
  unique_traders AS traders_today,
  avg_otr,
  avg_cancellation_pct,
  rolling_7d_alerts,
  rolling_30d_alerts,
  rolling_90d_total AS total_alerts_90d,
  ROUND((rolling_90d_total * 3.0) + (unique_traders * 2.0) + (avg_otr * 1.5), 2) AS targeting_intensity_score,
  CASE 
    WHEN rolling_90d_total >= 100 AND avg_otr >= 10 THEN 'HEAVILY_TARGETED'
    WHEN rolling_90d_total >= 50 AND avg_otr >= 7 THEN 'MODERATELY_TARGETED'
    WHEN rolling_90d_total >= 20 AND avg_otr >= 5 THEN 'TARGETED'
    ELSE 'LIGHTLY_TARGETED'
  END AS targeting_classification,
  pct_of_daily_alerts,
  pct_of_daily_traders
FROM symbol_partitioned_analysis
WHERE alert_date = CURRENT_DATE()
ORDER BY targeting_intensity_score DESC, total_alerts_90d DESC;


-- =====================================================
-- QUERY 3: WEEKLY VELOCITY - Week-over-Week Alert Frequency
-- Use LAG() function to calculate weekly velocity
-- Flag traders whose spoofing alert frequency increased by >50% week-over-week
-- =====================================================

WITH weekly_trader_stats AS (
  SELECT 
    trader_id,
    DATE_TRUNC(alert_date, WEEK(MONDAY)) AS week_start,
    COUNT(*) AS weekly_alert_count,
    COUNT(DISTINCT symbol) AS weekly_symbols_targeted,
    AVG(order_to_trade_ratio) AS weekly_avg_otr,
    AVG(cancellation_percentage) AS weekly_avg_cancellation_pct,
    AVG(avg_execution_horizon_ms) AS weekly_avg_exec_horizon
  FROM 
    `your-gcp-project-id.surveillance.market_abuse_alerts`
  WHERE 
    alert_date BETWEEN DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY) 
                    AND CURRENT_DATE()
    AND alert_type = 'SPOOFING_SUSPECTED'
  GROUP BY 
    trader_id, week_start
),

weekly_velocity AS (
  SELECT 
    trader_id,
    week_start,
    weekly_alert_count,
    weekly_symbols_targeted,
    weekly_avg_otr,
    weekly_avg_cancellation_pct,
    weekly_avg_exec_horizon,
    LAG(weekly_alert_count, 1) OVER (
      PARTITION BY trader_id 
      ORDER BY week_start
    ) AS previous_week_alert_count,
    LAG(weekly_avg_otr, 1) OVER (
      PARTITION BY trader_id 
      ORDER BY week_start
    ) AS previous_week_avg_otr
  FROM weekly_trader_stats
)

SELECT 
  trader_id,
  week_start,
  weekly_alert_count AS current_week_alerts,
  previous_week_alert_count AS last_week_alerts,
  CASE 
    WHEN previous_week_alert_count IS NULL OR previous_week_alert_count = 0 THEN NULL
    ELSE (weekly_alert_count - previous_week_alert_count)
  END AS week_change,
  CASE 
    WHEN previous_week_alert_count IS NULL OR previous_week_alert_count = 0 THEN NULL
    ELSE ROUND(((weekly_alert_count - previous_week_alert_count) * 100.0 / previous_week_alert_count), 2)
  END AS week_change_pct,
  CASE 
    WHEN previous_week_alert_count IS NULL THEN 'NEW_ACTOR'
    WHEN weekly_alert_count > previous_week_alert_count * 1.5 THEN 'ACCELERATING'
    WHEN weekly_alert_count > previous_week_alert_count THEN 'INCREASING'
    WHEN weekly_alert_count < previous_week_alert_count THEN 'DECLINING'
    ELSE 'STABLE'
  END AS velocity_trend,
  weekly_symbols_targeted AS symbols_targeted,
  ROUND(weekly_avg_otr, 3) AS avg_otr_week,
  ROUND(weekly_avg_cancellation_pct, 2) AS avg_cancellation_pct_week,
  ROUND(weekly_avg_exec_horizon, 2) AS avg_exec_horizon_ms_week,
  CASE 
    WHEN previous_week_alert_count IS NOT NULL 
         AND previous_week_alert_count > 0 
         AND weekly_alert_count > previous_week_alert_count * 1.5 
    THEN TRUE 
    ELSE FALSE 
  END AS flagged_velocity_increase
FROM weekly_velocity
WHERE week_start >= DATE_SUB(DATE_TRUNC(CURRENT_DATE(), WEEK(MONDAY)), INTERVAL 12 WEEK)
  AND (
    (previous_week_alert_count IS NOT NULL AND previous_week_alert_count > 0 AND weekly_alert_count > previous_week_alert_count * 1.5)
    OR (previous_week_alert_count IS NULL AND weekly_alert_count >= 5)
  )
ORDER BY week_change_pct DESC NULLS LAST, week_start DESC, trader_id;
