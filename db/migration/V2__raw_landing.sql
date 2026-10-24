CREATE TABLE raw.ingest_run (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source text NOT NULL,
    started_at timestamptz NOT NULL DEFAULT now(),
    finished_at timestamptz,
    status text NOT NULL DEFAULT 'running'
        CHECK (status IN ('running', 'succeeded', 'partial', 'failed', 'needs_review')),
    requests integer NOT NULL DEFAULT 0,
    not_modified integer NOT NULL DEFAULT 0,
    payloads_new integer NOT NULL DEFAULT 0,
    rows_in integer NOT NULL DEFAULT 0,
    rows_upserted integer NOT NULL DEFAULT 0,
    error text
);

CREATE INDEX ingest_run_source_started_idx ON raw.ingest_run (source, started_at DESC);

COMMENT ON TABLE raw.ingest_run IS 'One row per ingestion run. The only raw table the writer may update, so a run can close itself.';

CREATE TABLE raw.payload (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source text NOT NULL,
    endpoint text NOT NULL,
    params jsonb NOT NULL DEFAULT '{}',
    fetched_at timestamptz NOT NULL DEFAULT now(),
    content_hash text NOT NULL,
    body jsonb NOT NULL,
    UNIQUE (source, content_hash)
);

ALTER TABLE raw.payload ALTER COLUMN body SET COMPRESSION lz4;

CREATE INDEX payload_source_endpoint_idx ON raw.payload (source, endpoint, id);

COMMENT ON TABLE raw.payload IS 'Append-only, content-addressed source responses. Identical content is stored once; every transform can be replayed from here.';

CREATE TABLE raw.fetch (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_id bigint NOT NULL REFERENCES raw.ingest_run (id),
    source text NOT NULL,
    endpoint text NOT NULL,
    params jsonb NOT NULL DEFAULT '{}',
    requested_at timestamptz NOT NULL DEFAULT now(),
    http_status smallint NOT NULL,
    etag text,
    last_modified text,
    payload_id bigint REFERENCES raw.payload (id),
    duration_ms integer NOT NULL
);

CREATE INDEX fetch_source_endpoint_requested_idx ON raw.fetch (source, endpoint, requested_at DESC);

COMMENT ON TABLE raw.fetch IS 'Append-only log of every HTTP request, including 304 Not Modified and duplicate content. Drives conditional requests and refetch intervals.';

GRANT UPDATE (finished_at, status, requests, not_modified, payloads_new, rows_in, rows_upserted, error)
    ON raw.ingest_run TO hoshizora_writer;

CREATE TABLE core.source_record (
    entity text NOT NULL,
    entity_key text NOT NULL,
    payload_id bigint NOT NULL REFERENCES raw.payload (id),
    recorded_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (entity, entity_key, payload_id)
);

CREATE INDEX source_record_payload_idx ON core.source_record (payload_id);

COMMENT ON TABLE core.source_record IS 'Lineage: which raw payload produced each version of a core row. Written only when the row actually changed.';
