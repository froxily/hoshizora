WITH planet AS (
    SELECT e.*
    FROM core.exoplanet e
    WHERE (CAST(:name AS text) IS NULL OR e.name = CAST(:name AS text))
      AND (
          CAST(:method AS text) IS NULL
          OR trim(BOTH '_' FROM regexp_replace(lower(e.discovery_method), '[^a-z0-9]+', '_', 'g'))
              = CAST(:method AS text)
      )
      AND (CAST(:from_year AS integer) IS NULL OR e.discovery_year >= CAST(:from_year AS integer))
      AND (CAST(:to_year AS integer) IS NULL OR e.discovery_year <= CAST(:to_year AS integer))
      AND (
          CAST(:max_distance_ly AS double precision) IS NULL
          OR e.distance_pc * 3.26156 <= CAST(:max_distance_ly AS double precision)
      )
      AND (CAST(:include_controversial AS boolean) OR NOT e.controversial)
),
total AS (
    SELECT count(*) AS total_items FROM planet
)
SELECT total.total_items, page.*
FROM total
LEFT JOIN LATERAL (
    SELECT *
    FROM planet
    ORDER BY
        CASE WHEN CAST(:sort AS text) = 'distance' THEN distance_pc END ASC NULLS LAST,
        CASE WHEN CAST(:sort AS text) = '-discovery_year' THEN discovery_year END DESC NULLS LAST,
        CASE WHEN CAST(:sort AS text) = 'radius' THEN radius_earth END ASC NULLS LAST,
        name
    LIMIT :limit OFFSET :offset
) AS page ON true
