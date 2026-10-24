SELECT *
FROM mart.launch_listing
WHERE provider_org_id = :id AND outcome = 'upcoming'
ORDER BY net NULLS LAST, launch_id
LIMIT 1
