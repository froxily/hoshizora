SELECT
    v.ll2_id AS vehicle_id,
    coalesce(v.full_name, v.name) AS name,
    v.name_ja,
    v.family,
    count(*) FILTER (WHERE c.attempted) AS attempts,
    count(*) FILTER (WHERE c.outcome = 'success') AS successes
FROM mart.launch_classified c
JOIN core.launch_vehicle v ON v.ll2_id = c.vehicle_ll2_id
WHERE c.provider_org_id = :id
GROUP BY v.ll2_id
HAVING count(*) FILTER (WHERE c.attempted) > 0
ORDER BY attempts DESC, name
LIMIT 5
