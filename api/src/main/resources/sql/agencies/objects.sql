SELECT
    coalesce(array_agg(DISTINCT a.code ORDER BY a.code), '{}') AS owner_codes,
    coalesce(sum(o.objects) FILTER (WHERE o.orbit_state = 'earth_orbit'), 0) AS in_earth_orbit,
    coalesce(sum(o.objects) FILTER (WHERE o.orbit_state = 'earth_orbit' AND o.object_type = 'payload'), 0)
        AS payloads_in_earth_orbit,
    coalesce(sum(o.objects) FILTER (WHERE o.orbit_state = 'beyond_earth'), 0) AS beyond_earth,
    coalesce(sum(o.objects) FILTER (WHERE o.orbit_state = 'decayed'), 0) AS decayed
FROM core.organization_alias a
LEFT JOIN mart.objects_in_orbit_by_owner o ON o.owner_code = a.code
WHERE a.namespace = 'celestrak.owner' AND a.organization_id = :id
