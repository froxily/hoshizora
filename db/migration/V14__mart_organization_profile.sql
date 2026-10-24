CREATE VIEW mart.organization_profile AS
SELECT
    o.id,
    k.key,
    o.name_en,
    o.name_ja,
    o.name_ja_source,
    o.abbrev,
    o.type,
    o.founding_year,
    o.parent_id,
    s.attempts,
    s.successes,
    s.failures,
    s.partial_failures,
    s.scheduled,
    s.first_launch_at,
    s.last_launch_at,
    ARRAY(
        SELECT c.code FROM core.organization_country oc JOIN core.country c ON c.code = oc.country_code
        WHERE oc.organization_id = o.id ORDER BY c.code
    ) AS country_codes,
    ARRAY(
        SELECT c.name_en FROM core.organization_country oc JOIN core.country c ON c.code = oc.country_code
        WHERE oc.organization_id = o.id ORDER BY c.code
    ) AS country_names_en,
    ARRAY(
        SELECT c.name_ja FROM core.organization_country oc JOIN core.country c ON c.code = oc.country_code
        WHERE oc.organization_id = o.id ORDER BY c.code
    ) AS country_names_ja,
    ARRAY(
        SELECT p.slug FROM core.program_member m JOIN core.program p ON p.slug = m.program_slug
        WHERE m.organization_id = o.id ORDER BY p.slug
    ) AS program_slugs,
    ARRAY(
        SELECT p.name_en FROM core.program_member m JOIN core.program p ON p.slug = m.program_slug
        WHERE m.organization_id = o.id ORDER BY p.slug
    ) AS program_names_en,
    ARRAY(
        SELECT p.name_ja FROM core.program_member m JOIN core.program p ON p.slug = m.program_slug
        WHERE m.organization_id = o.id ORDER BY p.slug
    ) AS program_names_ja
FROM core.organization o
JOIN mart.organization_key k ON k.organization_id = o.id
LEFT JOIN mart.organization_launch_summary s ON s.organization_id = o.id;

COMMENT ON VIEW mart.organization_profile IS 'One row per organization with its public key, names, type, countries and national programs (parallel arrays in code order), and its launch totals as a provider.';
