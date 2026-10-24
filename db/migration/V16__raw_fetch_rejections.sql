COMMENT ON TABLE raw.fetch IS 'Append-only log of every HTTP request, including 304 Not Modified, duplicate content and rejected responses (4xx and 5xx, which have no payload). Accepted 200 and 304 rows drive conditional requests and refetch intervals.';

CREATE OR REPLACE VIEW mart.source_status AS
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
        WHERE f.source = d.slug AND f.http_status IN (200, 304)
    ) AS last_fetched_at
FROM core.data_source d
LEFT JOIN LATERAL (
    SELECT r.status, r.started_at, r.finished_at
    FROM raw.ingest_run r
    WHERE r.source = d.slug
    ORDER BY r.started_at DESC
    LIMIT 1
) AS last_run ON true;

COMMENT ON VIEW mart.source_status IS 'Latest run status and fetch times per source, without error text, for the public Sources page. The last fetch counts only accepted 200 and 304 responses, never rejections.';
