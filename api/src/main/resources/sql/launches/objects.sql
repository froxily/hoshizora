SELECT
    s.norad_id,
    s.object_id,
    s.name,
    c.object_type,
    c.orbit_state,
    s.owner_code,
    s.decay_date,
    count(*) OVER () AS total
FROM core.space_object s
JOIN mart.space_object_classified c USING (norad_id)
WHERE s.launch_designator = :designator
ORDER BY CASE c.object_type WHEN 'payload' THEN 0 WHEN 'rocket_body' THEN 1 ELSE 2 END, s.norad_id
LIMIT :limit
