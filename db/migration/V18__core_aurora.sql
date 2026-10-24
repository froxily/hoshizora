CREATE TABLE core.aurora_forecast (
    observed_at timestamptz PRIMARY KEY,
    forecast_at timestamptz NOT NULL,
    north_max_percent smallint NOT NULL CHECK (north_max_percent BETWEEN 0 AND 100),
    south_max_percent smallint NOT NULL CHECK (south_max_percent BETWEEN 0 AND 100),
    north_boundary_lat smallint CHECK (north_boundary_lat BETWEEN 1 AND 90),
    south_boundary_lat smallint CHECK (south_boundary_lat BETWEEN -90 AND -1)
);

COMMENT ON TABLE core.aurora_forecast IS 'One NOAA SWPC OVATION aurora forecast per observation time: the highest probability of visible aurora in each hemisphere and the latitude closest to the equator where it reaches 10 percent. Kept for the raw retention window (48 hours).';

CREATE TABLE core.aurora_cell (
    longitude smallint NOT NULL CHECK (longitude BETWEEN 0 AND 359),
    latitude smallint NOT NULL CHECK (latitude BETWEEN -90 AND 90),
    probability_percent smallint NOT NULL CHECK (probability_percent BETWEEN 1 AND 100),
    observed_at timestamptz NOT NULL REFERENCES core.aurora_forecast (observed_at) ON DELETE CASCADE,
    PRIMARY KEY (longitude, latitude)
);

COMMENT ON TABLE core.aurora_cell IS 'The non-zero 1-degree cells of the latest OVATION forecast only, replaced whenever a newer forecast is stored.';

CREATE TABLE raw.retention_policy (
    source text NOT NULL,
    endpoint text NOT NULL,
    keep interval NOT NULL CHECK (keep >= interval '1 hour'),
    reason text NOT NULL,
    PRIMARY KEY (source, endpoint)
);

COMMENT ON TABLE raw.retention_policy IS 'The only raw payloads that may ever be deleted, and how long each is kept. Everything else in raw stays append-only.';

INSERT INTO raw.retention_policy (source, endpoint, keep, reason)
VALUES (
    'swpc',
    'https://services.swpc.noaa.gov/json/ovation_aurora_latest.json',
    interval '48 hours',
    'A 65,160-cell grid of about 0.46 MB stored, refreshed hourly. Only the latest grid and a short history are shown.'
);

ALTER TABLE raw.fetch
    DROP CONSTRAINT fetch_payload_id_fkey,
    ADD CONSTRAINT fetch_payload_id_fkey
        FOREIGN KEY (payload_id) REFERENCES raw.payload (id) ON DELETE SET NULL;

ALTER TABLE core.source_record
    DROP CONSTRAINT source_record_payload_id_fkey,
    ADD CONSTRAINT source_record_payload_id_fkey
        FOREIGN KEY (payload_id) REFERENCES raw.payload (id) ON DELETE CASCADE;

CREATE FUNCTION raw.apply_retention(p_source text, p_endpoint text, p_reference timestamptz)
RETURNS integer
LANGUAGE sql
SECURITY DEFINER
SET search_path = pg_catalog, raw
AS $$
    WITH pruned AS (
        DELETE FROM raw.payload p
        USING raw.retention_policy r
        WHERE r.source = p_source
          AND r.endpoint = p_endpoint
          AND p.source = r.source
          AND p.endpoint = r.endpoint
          AND p.fetched_at < p_reference - r.keep
        RETURNING p.id
    )
    SELECT count(*)::integer FROM pruned;
$$;

COMMENT ON FUNCTION raw.apply_retention(text, text, timestamptz) IS 'Deletes payloads older than their retention_policy window before p_reference. Fetch log rows keep their request and lose the payload link; lineage rows go with the payload.';

REVOKE ALL ON FUNCTION raw.apply_retention(text, text, timestamptz) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION raw.apply_retention(text, text, timestamptz) TO hoshizora_writer;
