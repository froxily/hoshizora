WITH series AS (
    SELECT c.*
    FROM mart.launch_cadence_yearly c
    WHERE c.group_kind = :group_by
      AND (CAST(:key AS text) IS NULL OR c.group_key = CAST(:key AS text))
      AND (CAST(:from_year AS integer) IS NULL OR c.year >= CAST(:from_year AS integer))
      AND (CAST(:to_year AS integer) IS NULL OR c.year <= CAST(:to_year AS integer))
),
ranked AS (
    SELECT group_key, sum(attempts) AS total_attempts
    FROM series
    GROUP BY group_key
    ORDER BY total_attempts DESC, group_key
    LIMIT :limit
)
SELECT s.group_key, r.total_attempts, n.name_en, n.name_ja,
       s.year, s.attempts, s.successes, s.failures, s.partial_failures, s.scheduled
FROM series s
JOIN ranked r USING (group_key)
LEFT JOIN mart.launch_group_name n ON n.group_kind = s.group_kind AND n.group_key = s.group_key
ORDER BY r.total_attempts DESC, s.group_key, s.year
