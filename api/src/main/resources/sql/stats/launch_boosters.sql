SELECT
    b.launcher_id,
    b.serial_number,
    b.status,
    b.vehicle_ll2_id,
    b.vehicle_name,
    b.vehicle_name_ja,
    b.vehicle_family,
    b.flights,
    b.attempted_landings,
    b.successful_landings,
    b.first_launch_at,
    b.last_launch_at,
    extract(epoch FROM b.fastest_turnaround) / 86400 AS fastest_turnaround_days,
    b.flights_rank
FROM mart.booster_ranking b
LEFT JOIN mart.organization_key k ON k.organization_id = b.provider_org_id
WHERE (CAST(:provider AS text) IS NULL OR k.key = CAST(:provider AS text))
  AND (CAST(:active AS boolean) IS NULL OR (b.status = 'active') = CAST(:active AS boolean))
ORDER BY b.flights DESC, b.last_launch_at DESC NULLS LAST, b.launcher_id
LIMIT :limit
