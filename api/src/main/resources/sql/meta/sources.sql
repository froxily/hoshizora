WITH source AS (
    SELECT
        d.slug,
        d.name_en,
        d.name_ja,
        d.description_en,
        d.description_ja,
        d.credit_en,
        d.credit_ja,
        d.license_en,
        d.license_ja,
        d.license_url,
        d.homepage_url,
        d.cadence_en,
        d.cadence_ja,
        extract(epoch FROM d.update_interval)::bigint AS update_interval_seconds,
        s.last_run_status,
        s.last_run_started_at,
        s.last_run_finished_at,
        s.last_succeeded_at,
        s.last_fetched_at,
        coalesce(q.blocking, 0) AS blocking,
        coalesce(q.warnings, 0) AS warnings
    FROM core.data_source d
    LEFT JOIN mart.source_status s ON s.source = d.slug
    LEFT JOIN mart.source_quality q ON q.source = d.slug
),
total AS (
    SELECT count(*) AS total_items FROM source
)
SELECT total.total_items, page.*
FROM total
LEFT JOIN LATERAL (
    SELECT * FROM source ORDER BY slug LIMIT :limit OFFSET :offset
) AS page ON true
