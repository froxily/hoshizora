WITH match AS (
    SELECT o.id
    FROM core.organization o
    WHERE o.slug = :key
    UNION
    SELECT a.organization_id
    FROM core.organization_alias a
    WHERE a.namespace = 'll2.agency' AND 'll2-' || a.code = :key
)
SELECT p.*
FROM mart.organization_profile p
WHERE p.id IN (SELECT id FROM match)
