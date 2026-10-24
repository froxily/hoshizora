SELECT *
FROM mart.close_approach_enriched
WHERE approach_utc >= :as_of AND approach_utc < :until
ORDER BY dist_au, designation
LIMIT 1
