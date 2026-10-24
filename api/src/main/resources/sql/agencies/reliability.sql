SELECT
    (array_agg(r.window_attempts ORDER BY r.attempt_no DESC))[1] AS recent_attempts,
    (array_agg(r.window_successes ORDER BY r.attempt_no DESC))[1] AS recent_successes,
    (array_agg(r.success_streak ORDER BY r.attempt_no DESC))[1] AS current_streak,
    max(r.success_streak) AS longest_streak
FROM mart.launch_success_rolling r
WHERE r.group_kind = 'provider' AND r.group_key = :key
