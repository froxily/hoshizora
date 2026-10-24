SELECT longitude, latitude, probability_percent
FROM core.aurora_cell
WHERE observed_at = :observed_at
  AND probability_percent >= :min_percent
ORDER BY latitude DESC, longitude
