SELECT d.year, d.method, d.planets, d.from_space
FROM mart.exoplanet_discoveries_yearly d
WHERE (CAST(:from_year AS integer) IS NULL OR d.year >= CAST(:from_year AS integer))
  AND (CAST(:to_year AS integer) IS NULL OR d.year <= CAST(:to_year AS integer))
ORDER BY d.year, d.planets DESC, d.method
