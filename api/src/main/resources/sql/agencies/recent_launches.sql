SELECT *
FROM mart.launch_listing
WHERE provider_org_id = :id AND outcome IN ('success', 'failure', 'partial_failure', 'in_flight')
ORDER BY net DESC NULLS LAST, launch_id
LIMIT 5
