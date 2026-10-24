SELECT
    c.country_code,
    co.name_en,
    co.name_ja,
    coalesce(sum(c.objects) FILTER (WHERE c.object_type = 'payload'), 0) AS payloads,
    coalesce(sum(c.objects) FILTER (WHERE c.object_type = 'rocket_body'), 0) AS rocket_bodies,
    coalesce(sum(c.objects) FILTER (WHERE c.object_type = 'debris'), 0) AS debris,
    coalesce(sum(c.objects) FILTER (WHERE c.object_type = 'unknown'), 0) AS unknown,
    sum(c.objects) AS total,
    sum(c.shared_objects) AS shared
FROM mart.objects_in_orbit_by_country c
JOIN core.country co ON co.code = c.country_code
WHERE c.orbit_state = :orbit_state
GROUP BY c.country_code, co.name_en, co.name_ja
ORDER BY total DESC, c.country_code
LIMIT :limit
