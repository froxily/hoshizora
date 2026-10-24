SELECT g.observed_at, g.value AS kp, mart.g_scale(g.value) AS g_scale
FROM core.geomagnetic_index g
WHERE g.index = 'kp' AND g.observed_at >= :from AND g.observed_at < :to
ORDER BY g.observed_at
