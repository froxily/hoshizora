SELECT
    coalesce(sum(o.objects) FILTER (WHERE o.object_type = 'payload'), 0) AS payloads,
    coalesce(sum(o.objects) FILTER (WHERE o.object_type = 'rocket_body'), 0) AS rocket_bodies,
    coalesce(sum(o.objects) FILTER (WHERE o.object_type = 'debris'), 0) AS debris,
    coalesce(sum(o.objects) FILTER (WHERE o.object_type = 'unknown'), 0) AS unknown,
    coalesce(sum(o.objects), 0) AS total
FROM mart.objects_in_orbit_by_owner o
WHERE o.orbit_state = :orbit_state
