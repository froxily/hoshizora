CREATE FUNCTION mart.url_origin(url text) RETURNS text
LANGUAGE sql IMMUTABLE STRICT PARALLEL SAFE
RETURN lower(substring(url FROM '^[A-Za-z][A-Za-z0-9+.-]*://[^/?#]+'));

COMMENT ON FUNCTION mart.url_origin(text) IS 'Scheme and host of a URL, lower-cased, or NULL for a value that is not an absolute URL (such as a reference file name).';

ALTER TABLE raw.ingest_run ADD COLUMN origin text;

COMMENT ON COLUMN raw.ingest_run.origin IS 'Scheme and host the run fetched from. A database holds each source from one origin only: the origin of its first run pins it, and ingest refuses any other.';

UPDATE raw.ingest_run r
SET origin = f.origin
FROM (
    SELECT run_id, min(mart.url_origin(endpoint)) AS origin
    FROM raw.fetch
    GROUP BY run_id
) AS f
WHERE f.run_id = r.id;

CREATE VIEW mart.dq_source_origin_mix AS
WITH linked AS (
    SELECT
        p.source,
        mart.url_origin(p.endpoint) AS origin,
        count(DISTINCT (s.entity, s.entity_key)) AS linked_rows
    FROM core.source_record s
    JOIN raw.payload p ON p.id = s.payload_id
    WHERE mart.url_origin(p.endpoint) IS NOT NULL
    GROUP BY p.source, mart.url_origin(p.endpoint)
)
SELECT source, origin, linked_rows
FROM linked
WHERE source IN (SELECT source FROM linked GROUP BY source HAVING count(*) > 1);

COMMENT ON VIEW mart.dq_source_origin_mix IS 'Sources whose core rows trace back to payloads from more than one origin, for example the Launch Library 2 dev and production hosts. Replaying the source rebuilds it from its pinned origin and clears the mix.';
