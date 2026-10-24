SELECT
    r.source,
    r.endpoint || coalesce(
        '?' || (SELECT string_agg(p.key || '=' || p.value, '&' ORDER BY p.key) FROM jsonb_each_text(r.params) AS p),
        ''
    ) AS url,
    r.fetched_at,
    r.content_hash
FROM mart.record_lineage r
WHERE r.entity = :entity AND r.entity_key = :key
ORDER BY r.fetched_at DESC, r.content_hash
LIMIT 20
