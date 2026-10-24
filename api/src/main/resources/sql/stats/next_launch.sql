SELECT *
FROM mart.launch_listing
WHERE outcome = 'upcoming' AND net >= :as_of
ORDER BY net, launch_id
LIMIT 1
