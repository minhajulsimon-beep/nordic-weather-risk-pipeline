-- SQL analytics queries for BOTH SQLite and PostgreSQL.
-- Run individually against the weather_daily table.
-- A (city, record_date) primary key makes repeat runs idempotent.

-- Q1. Which city had the most days with potentially problematic conditions?
SELECT city, data_origin, COUNT(*) AS days,
       SUM(CASE WHEN risk_level = 'high' THEN 1 ELSE 0 END) AS high_risk_days,
       ROUND(100.0 * SUM(CASE WHEN risk_level = 'high' THEN 1 ELSE 0 END) / COUNT(*), 1)
         AS high_risk_pct
FROM weather_daily
GROUP BY city, data_origin
ORDER BY high_risk_pct DESC, city;

-- Q2. Weather patterns by month and city.
SELECT year_month, city, data_origin, COUNT(*) AS days,
       ROUND(AVG(temp_max_c), 1) AS avg_daily_max_c,
       ROUND(SUM(precipitation_mm), 1) AS total_precipitation_mm,
       SUM(strong_wind) AS windy_days,
       SUM(heavy_rain) AS heavy_rain_days,
       SUM(frost) AS frost_days
FROM weather_daily
GROUP BY year_month, city, data_origin
ORDER BY year_month, city;

-- Q3. Daily events flagged as high risk by the illustrative rule engine.
SELECT record_date, city, precipitation_mm, wind_max_kmh,
       temp_min_c, risk_score, risk_reasons, data_origin
FROM weather_daily
WHERE risk_level = 'high'
ORDER BY record_date DESC, risk_score DESC, city;

-- Q4. Last available dataset date (note: data availability varies by model).
SELECT city, data_origin, MIN(record_date) AS first_date,
       MAX(record_date) AS last_date, COUNT(*) AS daily_rows
FROM weather_daily
GROUP BY city, data_origin
ORDER BY city, data_origin;
