WITH latest AS (
    SELECT DISTINCT ON (r.group_key)
        r.group_key, r.attempt_no, r.successes_to_date, r.window_attempts, r.window_successes, r.success_streak
    FROM mart.launch_success_rolling r
    WHERE r.group_kind = :group_by AND (CAST(:key AS text) IS NULL OR r.group_key = CAST(:key AS text))
    ORDER BY r.group_key, r.attempt_no DESC
),
ranked AS (
    SELECT * FROM latest ORDER BY attempt_no DESC, group_key LIMIT :limit
),
longest AS (
    SELECT r.group_key, max(r.success_streak) AS longest_streak
    FROM mart.launch_success_rolling r
    JOIN ranked USING (group_key)
    WHERE r.group_kind = :group_by
    GROUP BY r.group_key
),
yearly AS (
    SELECT DISTINCT ON (r.group_key, r.year)
        r.group_key, r.year, r.attempt_no, r.successes_to_date, r.window_attempts, r.window_successes
    FROM mart.launch_success_rolling r
    JOIN ranked USING (group_key)
    WHERE r.group_kind = :group_by
    ORDER BY r.group_key, r.year, r.attempt_no DESC
)
SELECT
    ranked.group_key,
    ranked.attempt_no AS attempts,
    ranked.successes_to_date AS successes,
    ranked.window_attempts AS recent_attempts,
    ranked.window_successes AS recent_successes,
    ranked.success_streak AS current_streak,
    longest.longest_streak,
    n.name_en,
    n.name_ja,
    y.year,
    y.attempt_no AS year_attempts_to_date,
    y.successes_to_date AS year_successes_to_date,
    y.window_attempts AS year_recent_attempts,
    y.window_successes AS year_recent_successes
FROM ranked
JOIN longest USING (group_key)
JOIN yearly y USING (group_key)
LEFT JOIN mart.launch_group_name n ON n.group_kind = :group_by AND n.group_key = ranked.group_key
ORDER BY ranked.attempt_no DESC, ranked.group_key, y.year
