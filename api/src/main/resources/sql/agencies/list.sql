WITH organization AS (
    SELECT p.*
    FROM mart.organization_profile p
    WHERE (CAST(:type AS text) IS NULL OR p.type = CAST(:type AS text))
      AND (CAST(:country AS text) IS NULL OR upper(CAST(:country AS text)) = ANY (p.country_codes))
      AND (CAST(:program AS text) IS NULL OR CAST(:program AS text) = ANY (p.program_slugs))
      AND (
          CAST(:has_launches AS boolean) IS NULL
          OR (coalesce(p.attempts, 0) + coalesce(p.scheduled, 0) > 0) = CAST(:has_launches AS boolean)
      )
      AND (
          CAST(:q AS text) IS NULL
          OR strpos(lower(p.name_en), lower(CAST(:q AS text))) > 0
          OR strpos(p.name_ja, CAST(:q AS text)) > 0
          OR strpos(lower(p.abbrev), lower(CAST(:q AS text))) > 0
      )
),
total AS (
    SELECT count(*) AS total_items FROM organization
)
SELECT total.total_items, page.*
FROM total
LEFT JOIN LATERAL (
    SELECT *
    FROM organization
    ORDER BY
        CASE WHEN CAST(:sort AS text) = '-launches' THEN coalesce(attempts, 0) END DESC,
        CASE WHEN CAST(:sort AS text) = 'name' THEN lower(name_en) END ASC,
        key
    LIMIT :limit OFFSET :offset
) AS page ON true
