WITH flare AS (
    SELECT
        e.external_id AS id,
        e.begin_at,
        e.peak_at,
        e.end_at,
        e.event_class AS xray_class,
        e.peak_flux_wm2,
        e.satellite,
        mart.r_scale(e.peak_flux_wm2) AS r_scale,
        coalesce(e.peak_at, e.begin_at) AS occurred_at
    FROM core.space_weather_event e
    WHERE e.kind = 'xray_flare'
      AND (CAST(:from AS timestamptz) IS NULL OR coalesce(e.peak_at, e.begin_at) >= CAST(:from AS timestamptz))
      AND (CAST(:to AS timestamptz) IS NULL OR coalesce(e.peak_at, e.begin_at) < CAST(:to AS timestamptz))
      AND (
          CAST(:min_flux AS double precision) IS NULL
          OR e.peak_flux_wm2 >= CAST(:min_flux AS double precision)
      )
),
total AS (
    SELECT count(*) AS total_items FROM flare
)
SELECT total.total_items, page.*
FROM total
LEFT JOIN LATERAL (
    SELECT *
    FROM flare
    ORDER BY
        CASE WHEN CAST(:sort AS text) = '-time' THEN occurred_at END DESC,
        CASE WHEN CAST(:sort AS text) = '-flux' THEN peak_flux_wm2 END DESC NULLS LAST,
        id
    LIMIT :limit OFFSET :offset
) AS page ON true
