SELECT
    ranked.id,
    ranked.template_key,
    ranked.module,
    ranked.text_en,
    ranked.text_ja,
    ranked.entity_type,
    ranked.entity_key,
    ranked.params,
    ranked.score,
    ranked.kind,
    ranked.source_refs,
    ranked.citation_url,
    ranked.generated_at,
    ranked.valid_until
FROM (
    SELECT
        f.id,
        f.template_key,
        t.module,
        t.text_en,
        t.text_ja,
        f.entity_type,
        f.entity_key,
        f.params::text AS params,
        f.score,
        f.kind,
        f.source_refs::text AS source_refs,
        f.citation_url,
        f.generated_at,
        f.valid_until,
        row_number() OVER (PARTITION BY t.module ORDER BY f.score DESC, f.id) AS module_rank
    FROM facts.fact f
    JOIN facts.template t ON t.key = f.template_key
    WHERE f.score >= t.min_score
      AND (CAST(:id AS bigint) IS NULL OR f.id = CAST(:id AS bigint))
      AND (CAST(:module AS text) IS NULL OR t.module = CAST(:module AS text))
      AND (CAST(:entity_type AS text) IS NULL OR f.entity_type = CAST(:entity_type AS text))
      AND (CAST(:entity_key AS text) IS NULL OR f.entity_key = CAST(:entity_key AS text))
) ranked
WHERE ranked.module_rank <= 40
ORDER BY ranked.score DESC, ranked.id
