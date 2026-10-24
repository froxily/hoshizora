WITH approach AS (
    SELECT c.*
    FROM mart.close_approach_enriched c
    WHERE (CAST(:from AS date) IS NULL OR c.approach_tdb >= CAST(:from AS date))
      AND (CAST(:to AS date) IS NULL OR c.approach_tdb < CAST(:to AS date))
      AND (CAST(:max_dist_ld AS double precision) IS NULL OR c.dist_ld <= CAST(:max_dist_ld AS double precision))
      AND (CAST(:max_h AS double precision) IS NULL OR c.h_mag <= CAST(:max_h AS double precision))
      AND (CAST(:designation AS text) IS NULL OR c.designation = CAST(:designation AS text))
      AND (CAST(:sentry AS boolean) IS NULL OR c.sentry = CAST(:sentry AS boolean))
),
total AS (
    SELECT count(*) AS total_items FROM approach
)
SELECT total.total_items, page.*
FROM total
LEFT JOIN LATERAL (
    SELECT *
    FROM approach
    ORDER BY
        CASE WHEN CAST(:sort AS text) = 'date' THEN approach_tdb END ASC,
        CASE WHEN CAST(:sort AS text) = '-date' THEN approach_tdb END DESC,
        CASE WHEN CAST(:sort AS text) = 'distance' THEN dist_au END ASC,
        designation,
        approach_tdb
    LIMIT :limit OFFSET :offset
) AS page ON true
