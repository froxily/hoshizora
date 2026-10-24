CREATE TABLE core.country (
    code char(2) PRIMARY KEY,
    alpha3 char(3) NOT NULL UNIQUE,
    name_en text NOT NULL,
    name_ja text NOT NULL
);

COMMENT ON TABLE core.country IS 'ISO 3166-1 countries and territories with English and Japanese names from Unicode CLDR.';

CREATE TABLE core.organization (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    slug text UNIQUE,
    source_name text,
    curated_name_en text,
    name_en text GENERATED ALWAYS AS (coalesce(curated_name_en, source_name)) STORED NOT NULL,
    name_ja text,
    name_ja_source text,
    abbrev text,
    source_type text,
    type_override text CHECK (type_override IN ('agency', 'company', 'military', 'academic', 'international')),
    type text GENERATED ALWAYS AS (
        coalesce(
            type_override,
            CASE source_type
                WHEN 'Government' THEN 'agency'
                WHEN 'Commercial' THEN 'company'
                WHEN 'Private' THEN 'company'
                WHEN 'Multinational' THEN 'international'
                WHEN 'Educational' THEN 'academic'
            END
        )
    ) STORED,
    founding_year smallint,
    parent_id bigint REFERENCES core.organization (id),
    CHECK (name_ja IS NULL OR name_ja_source IS NOT NULL)
);

COMMENT ON TABLE core.organization IS 'Canonical organizations. Source fields come from Launch Library 2; curated fields win through the generated name_en and type columns.';
COMMENT ON COLUMN core.organization.name_ja_source IS 'Citation for the Japanese name: the organization''s Japanese site or Japanese Wikipedia.';

CREATE TABLE core.organization_alias (
    namespace text NOT NULL,
    code text NOT NULL,
    organization_id bigint NOT NULL REFERENCES core.organization (id),
    PRIMARY KEY (namespace, code)
);

CREATE INDEX organization_alias_organization_idx ON core.organization_alias (organization_id);

COMMENT ON TABLE core.organization_alias IS 'Maps every external organization code (namespaces ll2.agency, celestrak.owner, hoshizora) to one canonical organization.';

CREATE TABLE core.organization_country (
    organization_id bigint NOT NULL REFERENCES core.organization (id),
    country_code char(2) NOT NULL REFERENCES core.country (code),
    PRIMARY KEY (organization_id, country_code)
);

CREATE TABLE core.organization_curation (
    namespace text NOT NULL,
    code text NOT NULL,
    slug text UNIQUE,
    curated_name_en text,
    name_ja text,
    name_ja_source text,
    type_override text CHECK (type_override IN ('agency', 'company', 'military', 'academic', 'international')),
    countries char(2)[] NOT NULL DEFAULT '{}',
    programs text[] NOT NULL DEFAULT '{}',
    PRIMARY KEY (namespace, code),
    CHECK (name_ja IS NULL OR name_ja_source IS NOT NULL),
    CHECK (namespace <> 'hoshizora' OR (slug = code AND curated_name_en IS NOT NULL AND type_override IS NOT NULL))
);

COMMENT ON TABLE core.organization_curation IS 'Curated facts keyed by external code. Applied to organizations whenever either side changes, so curation and source data can arrive in any order.';

CREATE TABLE core.external_code (
    namespace text NOT NULL,
    code text NOT NULL,
    label text NOT NULL,
    kind text NOT NULL CHECK (kind IN ('country', 'multinational', 'organization', 'category', 'unknown')),
    organization_slug text,
    country_codes char(2)[] NOT NULL DEFAULT '{}',
    note text,
    PRIMARY KEY (namespace, code)
);

COMMENT ON TABLE core.external_code IS 'Curated vocabulary of every external code we know and what it means. Kind unknown marks acknowledged placeholders such as TBD.';

CREATE TABLE core.country_alias (
    namespace text NOT NULL,
    code text NOT NULL,
    country_code char(2) NOT NULL REFERENCES core.country (code),
    PRIMARY KEY (namespace, code, country_code)
);

COMMENT ON TABLE core.country_alias IS 'Maps external country codes to ISO countries. Joint codes such as celestrak.owner CHBZ map to several countries.';

CREATE TABLE core.observed_code (
    namespace text NOT NULL,
    code text NOT NULL,
    first_seen timestamptz NOT NULL DEFAULT now(),
    last_seen timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (namespace, code)
);

COMMENT ON TABLE core.observed_code IS 'External codes seen in ingested data that need a mapping, so unmapped values fail loudly in the data-quality report.';

CREATE TABLE core.program (
    slug text PRIMARY KEY,
    name_en text NOT NULL,
    name_ja text NOT NULL
);

COMMENT ON TABLE core.program IS 'Curated national programs, so the UI can honestly say "Japan''s launches" across agencies, companies and armed forces.';

CREATE TABLE core.program_member (
    program_slug text NOT NULL REFERENCES core.program (slug),
    organization_id bigint NOT NULL REFERENCES core.organization (id),
    PRIMARY KEY (program_slug, organization_id)
);

CREATE VIEW mart.dq_unmapped_code AS
SELECT o.namespace, o.code, 'not in vocabulary' AS problem, o.last_seen
FROM core.observed_code o
LEFT JOIN core.external_code e USING (namespace, code)
WHERE e.code IS NULL
UNION ALL
SELECT e.namespace, e.code, 'no alias for ' || e.kind AS problem, NULL::timestamptz
FROM core.external_code e
WHERE e.kind IN ('country', 'multinational', 'organization')
  AND NOT EXISTS (
      SELECT FROM core.organization_alias a WHERE a.namespace = e.namespace AND a.code = e.code
  )
  AND NOT EXISTS (
      SELECT FROM core.country_alias c WHERE c.namespace = e.namespace AND c.code = e.code
  );

CREATE VIEW mart.dq_unapplied_curation AS
SELECT c.namespace, c.code, c.slug
FROM core.organization_curation c
WHERE NOT EXISTS (
    SELECT FROM core.organization_alias a WHERE a.namespace = c.namespace AND a.code = c.code
);

CREATE VIEW mart.dq_untyped_organization AS
SELECT id, name_en, source_type
FROM core.organization
WHERE type IS NULL;

CREATE VIEW mart.dq_missing_name_ja AS
SELECT 'organization' AS entity, id::text AS key, name_en, 0::bigint AS relevance
FROM core.organization
WHERE name_ja IS NULL;

CREATE VIEW mart.dq_source_freshness AS
SELECT DISTINCT ON (source)
    source,
    status AS last_status,
    finished_at AS last_finished_at,
    (
        SELECT max(s.finished_at)
        FROM raw.ingest_run s
        WHERE s.source = r.source AND s.status = 'succeeded'
    ) AS last_succeeded_at,
    error AS last_error
FROM raw.ingest_run r
ORDER BY source, started_at DESC;
