CREATE TABLE facts.template (
    key text PRIMARY KEY,
    module text NOT NULL,
    text_en text NOT NULL,
    text_ja text NOT NULL,
    min_score double precision NOT NULL DEFAULT 0,
    updated_at timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE facts.template IS 'Fact templates synced from facts/templates/*.yaml. Text uses ICU MessageFormat arguments: {p}, {p, number}, {p, number, integer|percent|compact} and {p, date}.';

CREATE TABLE facts.fact (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    template_key text NOT NULL REFERENCES facts.template (key),
    entity_type text,
    entity_key text,
    params jsonb NOT NULL CHECK (jsonb_typeof(params) = 'object'),
    score double precision NOT NULL,
    kind text NOT NULL CHECK (kind IN ('computed', 'curated')),
    source_refs jsonb NOT NULL DEFAULT '[]' CHECK (jsonb_typeof(source_refs) = 'array'),
    citation_url text,
    generated_at timestamptz NOT NULL DEFAULT now(),
    valid_until timestamptz,
    CHECK (kind = 'computed' OR citation_url IS NOT NULL),
    CHECK ((entity_type IS NULL) = (entity_key IS NULL)),
    UNIQUE NULLS NOT DISTINCT (template_key, entity_type, entity_key)
);

CREATE INDEX fact_template_score_idx ON facts.fact (template_key, score DESC);

COMMENT ON TABLE facts.fact IS 'One fact per template and entity, stored as params rather than prose; the API renders text per Accept-Language. Regeneration upserts on (template_key, entity), so ids stay stable.';
COMMENT ON COLUMN facts.fact.params IS 'Template arguments. Numbers are already rounded; a localized string is an object {"en": ..., "ja": ...}.';
COMMENT ON COLUMN facts.fact.source_refs IS 'Core rows behind the fact: [{"entity": "core.close_approach", "key": "..."}], resolved to source requests through mart.record_lineage.';
