WITH series AS (
    SELECT r.*
    FROM mart.reusability_yearly r
    WHERE r.group_kind = :group_by
      AND (CAST(:key AS text) IS NULL OR r.group_key = CAST(:key AS text))
      AND (CAST(:from_year AS integer) IS NULL OR r.year >= CAST(:from_year AS integer))
      AND (CAST(:to_year AS integer) IS NULL OR r.year <= CAST(:to_year AS integer))
),
ranked AS (
    SELECT group_key, sum(stage_flights) AS total_stage_flights
    FROM series
    GROUP BY group_key
    ORDER BY total_stage_flights DESC, group_key
    LIMIT :limit
)
SELECT s.group_key, r.total_stage_flights, n.name_en, n.name_ja,
       s.year, s.launches, s.launches_reflown, s.stage_flights, s.stage_reflights,
       s.landing_attempts, s.landings
FROM series s
JOIN ranked r USING (group_key)
LEFT JOIN mart.launch_group_name n ON n.group_kind = s.group_kind AND n.group_key = s.group_key
ORDER BY r.total_stage_flights DESC, s.group_key, s.year
