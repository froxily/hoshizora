SELECT observed_at, forecast_at, north_max_percent, south_max_percent, north_boundary_lat, south_boundary_lat
FROM core.aurora_forecast
ORDER BY observed_at DESC
LIMIT 1
