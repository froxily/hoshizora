CREATE VIEW mart.launch_group_name AS
SELECT 'program' AS group_kind, p.slug AS group_key, p.name_en, p.name_ja
FROM core.program p
UNION ALL
SELECT 'provider', k.key, o.name_en, o.name_ja
FROM core.organization o
JOIN mart.organization_key k ON k.organization_id = o.id
UNION ALL
SELECT 'site_country', c.code, c.name_en, c.name_ja
FROM core.country c
UNION ALL
SELECT DISTINCT 'vehicle_family', v.family, v.family, NULL::text
FROM core.launch_vehicle v
WHERE v.family IS NOT NULL AND v.family <> '';

COMMENT ON VIEW mart.launch_group_name IS 'English and Japanese names for every launch grouping key in mart.launch_group. Vehicle families have no Japanese names yet, and the all group is named by the API.';
