SELECT k.key, o.name_en, o.name_ja, o.type
FROM core.mission_agency ma
JOIN core.organization o ON o.id = ma.organization_id
JOIN mart.organization_key k ON k.organization_id = o.id
WHERE ma.mission_ll2_id = :mission_id
ORDER BY o.name_en
