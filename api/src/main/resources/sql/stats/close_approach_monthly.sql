SELECT
    m.month,
    m.approaches,
    m.within_1_ld,
    m.closest_dist_ld,
    m.closest_designation,
    m.min_h_mag,
    m.largest_designation
FROM mart.close_approach_monthly m
WHERE m.body = 'Earth' AND m.month >= :from AND m.month < :to
ORDER BY m.month
