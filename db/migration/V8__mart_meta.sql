CREATE TABLE core.data_source (
    slug text PRIMARY KEY,
    name_en text NOT NULL,
    name_ja text NOT NULL,
    description_en text NOT NULL,
    description_ja text NOT NULL,
    credit_en text NOT NULL,
    credit_ja text NOT NULL,
    license_en text NOT NULL,
    license_ja text NOT NULL,
    license_url text,
    homepage_url text NOT NULL,
    cadence_en text NOT NULL,
    cadence_ja text NOT NULL,
    update_interval interval CHECK (update_interval > interval '0')
);

COMMENT ON TABLE core.data_source IS 'Every ingested source with its bilingual name, credit, license and cadence. Curated in the reference data and written by ingest.';
COMMENT ON COLUMN core.data_source.update_interval IS 'How often ingest refreshes the source. NULL when it changes only on demand.';

CREATE VIEW mart.record_lineage AS
SELECT r.entity, r.entity_key, p.source, p.endpoint, p.params, p.fetched_at, p.content_hash, r.recorded_at
FROM core.source_record r
JOIN raw.payload p ON p.id = r.payload_id;

COMMENT ON VIEW mart.record_lineage IS 'Which source response produced each version of a core row. Request metadata only, never payload bodies: the read API''s only window into raw.';

CREATE VIEW mart.source_status AS
SELECT
    d.slug AS source,
    last_run.status AS last_run_status,
    last_run.started_at AS last_run_started_at,
    last_run.finished_at AS last_run_finished_at,
    (
        SELECT max(r.finished_at)
        FROM raw.ingest_run r
        WHERE r.source = d.slug AND r.status = 'succeeded'
    ) AS last_succeeded_at,
    (
        SELECT max(f.requested_at)
        FROM raw.fetch f
        WHERE f.source = d.slug
    ) AS last_fetched_at
FROM core.data_source d
LEFT JOIN LATERAL (
    SELECT r.status, r.started_at, r.finished_at
    FROM raw.ingest_run r
    WHERE r.source = d.slug
    ORDER BY r.started_at DESC
    LIMIT 1
) AS last_run ON true;

COMMENT ON VIEW mart.source_status IS 'Latest run status and fetch times per source, without error text, for the public Sources page.';

CREATE VIEW mart.source_quality AS
WITH problem AS (
    SELECT namespace, true AS blocking FROM mart.dq_unmapped_code
    UNION ALL
    SELECT 'll2.agency', true FROM mart.dq_untyped_organization
    UNION ALL
    SELECT namespace, false FROM mart.dq_unapplied_curation
    UNION ALL
    SELECT 'll2.' || entity, false FROM mart.dq_missing_name_ja
)
SELECT
    CASE split_part(namespace, '.', 1)
        WHEN 'll2' THEN 'launch-library'
        WHEN 'celestrak' THEN 'celestrak'
        ELSE 'reference'
    END AS source,
    count(*) FILTER (WHERE blocking) AS blocking,
    count(*) FILTER (WHERE NOT blocking) AS warnings
FROM problem
GROUP BY 1;

COMMENT ON VIEW mart.source_quality IS 'Data-quality problem counts per source, using the same blocking rules as hoshizora dq.';
