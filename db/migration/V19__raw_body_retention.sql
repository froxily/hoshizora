ALTER TABLE raw.payload
    ALTER COLUMN body DROP NOT NULL,
    ADD COLUMN pruned_at timestamptz,
    ADD CONSTRAINT payload_pruned_body CHECK ((body IS NULL) = (pruned_at IS NOT NULL));

COMMENT ON TABLE raw.payload IS 'Append-only, content-addressed source responses. Identical content is stored once; every transform can be replayed from the bodies kept here. Rows are never deleted; only bodies listed in raw.retention_policy are pruned, and their metadata stays for lineage.';
COMMENT ON COLUMN raw.payload.pruned_at IS 'When raw.apply_retention dropped the body. The row keeps its endpoint, params, fetched_at and content_hash, so lineage still resolves.';

ALTER TABLE raw.fetch
    DROP CONSTRAINT fetch_payload_id_fkey,
    ADD CONSTRAINT fetch_payload_id_fkey
        FOREIGN KEY (payload_id) REFERENCES raw.payload (id);

ALTER TABLE core.source_record
    DROP CONSTRAINT source_record_payload_id_fkey,
    ADD CONSTRAINT source_record_payload_id_fkey
        FOREIGN KEY (payload_id) REFERENCES raw.payload (id);

COMMENT ON TABLE raw.retention_policy IS 'The only raw payloads whose bodies may ever be pruned, and how long a superseded body is kept. Rows are never deleted, and everything else in raw keeps its body.';

INSERT INTO raw.retention_policy (source, endpoint, keep, reason)
VALUES
    (
        'celestrak',
        'https://celestrak.org/NORAD/elements/gp.php',
        interval '48 hours',
        'The active GP group, about 1.6 MB stored every 2 hours. Core keeps the latest elements per object.'
    ),
    (
        'celestrak',
        'https://celestrak.org/pub/satcat.csv',
        interval '48 hours',
        'The full catalog, about 2.5 MB stored every 12 hours. Core keeps the latest record per object.'
    ),
    (
        'swpc',
        'https://services.swpc.noaa.gov/json/rtsw/rtsw_mag_1m.json',
        interval '48 hours',
        'A rolling day of 1-minute magnetic field data, about 0.25 MB stored every 6 hours. Core keeps every sample.'
    ),
    (
        'swpc',
        'https://services.swpc.noaa.gov/json/rtsw/rtsw_wind_1m.json',
        interval '48 hours',
        'A rolling day of 1-minute plasma data, about 0.17 MB stored every 6 hours. Core keeps every sample.'
    ),
    (
        'jpl',
        'https://ssd-api.jpl.nasa.gov/sentry.api',
        interval '48 hours',
        'The full Sentry list and its removals, about 0.13 MB stored every 12 hours. Core keeps the latest state per object.'
    );

DROP FUNCTION raw.apply_retention(text, text, timestamptz);

CREATE FUNCTION raw.apply_retention(p_source text, p_reference timestamptz)
RETURNS integer
LANGUAGE sql
SECURITY DEFINER
SET search_path = pg_catalog, raw
AS $$
    WITH pruned AS (
        UPDATE raw.payload p
        SET body = NULL, pruned_at = p_reference
        FROM raw.retention_policy r
        WHERE r.source = p_source
          AND p.source = r.source
          AND p.endpoint = r.endpoint
          AND p.body IS NOT NULL
          AND p.fetched_at < p_reference - r.keep
          AND p.id <> (
              SELECT f.payload_id
              FROM raw.fetch f
              WHERE f.source = p.source
                AND f.endpoint = p.endpoint
                AND f.params = p.params
                AND f.payload_id IS NOT NULL
              ORDER BY f.requested_at DESC, f.id DESC
              LIMIT 1
          )
        RETURNING p.id
    )
    SELECT count(*)::integer FROM pruned;
$$;

COMMENT ON FUNCTION raw.apply_retention(text, timestamptz) IS 'Drops the bodies of a source''s listed payloads that are older than their keep window before p_reference and are not the payload of the latest fetch for the same endpoint and params. The current body per request always stays, and no row is deleted.';

REVOKE ALL ON FUNCTION raw.apply_retention(text, timestamptz) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION raw.apply_retention(text, timestamptz) TO hoshizora_writer;

CREATE FUNCTION raw.restore_body(p_source text, p_content_hash text, p_body jsonb)
RETURNS bigint
LANGUAGE sql
SECURITY DEFINER
SET search_path = pg_catalog, raw
AS $$
    UPDATE raw.payload
    SET body = p_body, pruned_at = NULL
    WHERE source = p_source AND content_hash = p_content_hash AND body IS NULL
    RETURNING id;
$$;

COMMENT ON FUNCTION raw.restore_body(text, text, jsonb) IS 'Puts a pruned body back when a source returns the same content again, so the payload of the latest fetch always has its body. Touches only pruned rows with that content hash.';

REVOKE ALL ON FUNCTION raw.restore_body(text, text, jsonb) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION raw.restore_body(text, text, jsonb) TO hoshizora_writer;

GRANT MAINTAIN ON raw.payload TO hoshizora_writer;

COMMENT ON TABLE core.orbit_element IS 'Latest CCSDS OMM mean elements per object from CelesTrak GP (SGP4-ready). Only newer epochs replace a row; raw keeps superseded GP bodies for 48 hours.';
