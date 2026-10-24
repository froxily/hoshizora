SELECT k.day, k.kp_max, k.kp_mean, k.intervals, k.g_scale
FROM mart.kp_daily k
WHERE k.day >= :from AND k.day < :to
ORDER BY k.day
