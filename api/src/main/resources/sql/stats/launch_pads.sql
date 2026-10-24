SELECT
    a.pad_id,
    p.name AS pad_name,
    p.location_name AS pad_location,
    p.country_code,
    c.name_en AS country_en,
    c.name_ja AS country_ja,
    p.latitude,
    p.longitude,
    a.attempts,
    a.successes,
    a.failures,
    a.scheduled,
    a.first_launch_at,
    a.last_launch_at,
    a.busiest_year,
    a.busiest_year_attempts
FROM mart.launch_pad_activity a
JOIN core.launch_pad p ON p.ll2_id = a.pad_id
LEFT JOIN core.country c ON c.code = p.country_code
WHERE (CAST(:country AS text) IS NULL OR p.country_code = upper(CAST(:country AS text)))
ORDER BY a.attempts DESC, a.pad_id
LIMIT :limit
