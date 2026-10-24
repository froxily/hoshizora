SELECT p.key, p.name_en, p.name_ja, p.type, coalesce(p.id = CAST(:parent_id AS bigint), false) AS is_parent
FROM mart.organization_profile p
WHERE p.id = CAST(:parent_id AS bigint) OR p.parent_id = :id
ORDER BY is_parent DESC, lower(p.name_en)
