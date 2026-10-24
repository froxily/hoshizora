SELECT
    o.owner_code,
    e.label,
    p.key,
    p.name_en,
    p.name_ja,
    p.type,
    coalesce(sum(o.objects) FILTER (WHERE o.object_type = 'payload'), 0) AS payloads,
    coalesce(sum(o.objects) FILTER (WHERE o.object_type = 'rocket_body'), 0) AS rocket_bodies,
    coalesce(sum(o.objects) FILTER (WHERE o.object_type = 'debris'), 0) AS debris,
    coalesce(sum(o.objects) FILTER (WHERE o.object_type = 'unknown'), 0) AS unknown,
    sum(o.objects) AS total
FROM mart.objects_in_orbit_by_owner o
JOIN core.external_code e ON e.namespace = 'celestrak.owner' AND e.code = o.owner_code
LEFT JOIN core.organization_alias a ON a.namespace = 'celestrak.owner' AND a.code = o.owner_code
LEFT JOIN mart.organization_profile p ON p.id = a.organization_id
WHERE o.orbit_state = :orbit_state AND e.kind = 'organization'
GROUP BY o.owner_code, e.label, p.key, p.name_en, p.name_ja, p.type
ORDER BY total DESC, o.owner_code
LIMIT :limit
