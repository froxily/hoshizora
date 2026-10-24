SELECT
    (
        SELECT count(*)
        FROM mart.launch_classified c
        WHERE c.attempted AND c.net >= :year_start AND c.net < :as_of
    ) AS launches_this_year,
    (
        SELECT count(*)
        FROM mart.launch_classified c
        WHERE c.attempted AND c.net >= :last_year_start AND c.net < :last_year_as_of
    ) AS launches_same_period_last_year,
    kp.observed_at AS kp_observed_at,
    kp.value AS kp,
    mart.g_scale(kp.value) AS g_scale,
    (
        SELECT coalesce(sum(o.objects), 0)
        FROM mart.objects_in_orbit_by_owner o
        WHERE o.orbit_state = 'earth_orbit'
    ) AS objects_in_earth_orbit,
    (
        SELECT coalesce(sum(o.objects), 0)
        FROM mart.objects_in_orbit_by_owner o
        WHERE o.orbit_state = 'earth_orbit' AND o.object_type = 'payload'
    ) AS payloads_in_earth_orbit
FROM (SELECT 1) AS one
LEFT JOIN LATERAL (
    SELECT g.observed_at, g.value
    FROM core.geomagnetic_index g
    WHERE g.index = 'kp' AND g.observed_at <= :as_of
    ORDER BY g.observed_at DESC
    LIMIT 1
) AS kp ON true
