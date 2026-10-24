SELECT s.period_bin, s.radius_bin, s.planets
FROM mart.exoplanet_size_orbit s
ORDER BY s.period_bin, s.radius_bin
