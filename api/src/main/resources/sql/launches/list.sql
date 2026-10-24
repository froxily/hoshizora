WITH provider AS (
    SELECT o.id
    FROM core.organization o
    WHERE o.slug = CAST(:provider AS text)
    UNION
    SELECT a.organization_id
    FROM core.organization_alias a
    WHERE a.namespace = 'll2.agency' AND 'll2-' || a.code = CAST(:provider AS text)
),
launch AS (
    SELECT l.*
    FROM mart.launch_listing l
    WHERE (CAST(:from AS timestamptz) IS NULL OR l.net >= CAST(:from AS timestamptz))
      AND (CAST(:to AS timestamptz) IS NULL OR l.net < CAST(:to AS timestamptz))
      AND (CAST(:status AS text) IS NULL OR l.outcome = CAST(:status AS text))
      AND (CAST(:provider AS text) IS NULL OR l.provider_org_id IN (SELECT id FROM provider))
      AND (
          CAST(:program AS text) IS NULL
          OR EXISTS (
              SELECT FROM core.program_member m
              WHERE m.organization_id = l.provider_org_id AND m.program_slug = CAST(:program AS text)
          )
      )
      AND (CAST(:vehicle_family AS text) IS NULL OR lower(l.vehicle_family) = lower(CAST(:vehicle_family AS text)))
      AND (CAST(:site_country AS text) IS NULL OR l.pad_country_code = upper(CAST(:site_country AS text)))
      AND (CAST(:pad AS integer) IS NULL OR l.pad_id = CAST(:pad AS integer))
),
total AS (
    SELECT count(*) AS total_items FROM launch
)
SELECT total.total_items, page.*
FROM total
LEFT JOIN LATERAL (
    SELECT *
    FROM launch
    ORDER BY
        CASE WHEN CAST(:sort AS text) = 'net' THEN net END ASC NULLS LAST,
        CASE WHEN CAST(:sort AS text) = '-net' THEN net END DESC NULLS LAST,
        launch_id
    LIMIT :limit OFFSET :offset
) AS page ON true
