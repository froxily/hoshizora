SELECT observed_at, north_max_percent, south_max_percent
FROM core.aurora_forecast
WHERE observed_at > CAST(:latest AS timestamptz) - interval '48 hours'
  AND observed_at <= CAST(:latest AS timestamptz)
ORDER BY observed_at
