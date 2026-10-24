WITH risk AS (
    SELECT
        r.designation,
        coalesce(r.fullname, b.fullname) AS fullname,
        r.sentry_id,
        r.impact_probability,
        r.palermo_cumulative,
        r.palermo_max,
        r.torino_max,
        r.potential_impacts,
        r.impact_year_first,
        r.impact_year_last,
        r.last_observed,
        r.diameter_km,
        r.h_mag,
        r.v_inf_kms,
        r.removed_at,
        mart.diameter_from_h_km(r.h_mag, 0.25) AS diameter_min_km,
        mart.diameter_from_h_km(r.h_mag, 0.05) AS diameter_max_km
    FROM core.impact_risk r
    JOIN core.small_body b USING (designation)
    WHERE (CAST(:designation AS text) IS NULL OR r.designation = CAST(:designation AS text))
      AND (CAST(:include_removed AS boolean) OR r.removed_at IS NULL)
      AND (
          CAST(:min_palermo AS double precision) IS NULL
          OR r.palermo_cumulative >= CAST(:min_palermo AS double precision)
      )
      AND (CAST(:min_torino AS integer) IS NULL OR r.torino_max >= CAST(:min_torino AS integer))
),
total AS (
    SELECT count(*) AS total_items FROM risk
)
SELECT total.total_items, page.*
FROM total
LEFT JOIN LATERAL (
    SELECT *
    FROM risk
    ORDER BY
        CASE WHEN CAST(:sort AS text) = '-palermo' THEN palermo_cumulative END DESC NULLS LAST,
        CASE WHEN CAST(:sort AS text) = '-probability' THEN impact_probability END DESC NULLS LAST,
        CASE WHEN CAST(:sort AS text) = '-torino' THEN torino_max END DESC NULLS LAST,
        designation
    LIMIT :limit OFFSET :offset
) AS page ON true
