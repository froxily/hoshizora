SELECT p.slug, p.name_en, p.name_ja
FROM core.program_member m
JOIN core.program p ON p.slug = m.program_slug
WHERE m.organization_id = :organization_id
ORDER BY p.slug
