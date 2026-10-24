CREATE SCHEMA raw;
CREATE SCHEMA core;
CREATE SCHEMA mart;
CREATE SCHEMA facts;

COMMENT ON SCHEMA raw IS 'Append-only landing zone: every source payload exactly as fetched, deduplicated by content hash.';
COMMENT ON SCHEMA core IS 'Normalized entities keyed on stable external IDs, with lineage back to raw payloads.';
COMMENT ON SCHEMA mart IS 'Analytics materialized views, refreshed after each ingestion run.';
COMMENT ON SCHEMA facts IS 'Computed and curated facts stored as params, scores and source references.';

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'hoshizora_writer') THEN
        CREATE ROLE hoshizora_writer NOLOGIN;
    END IF;
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'hoshizora_reader') THEN
        CREATE ROLE hoshizora_reader NOLOGIN;
    END IF;
END
$$;

COMMENT ON ROLE hoshizora_writer IS 'Ingestion: appends raw payloads and writes core, mart and facts rows. Never changes the schema.';
COMMENT ON ROLE hoshizora_reader IS 'API: reads core, mart and facts. Nothing else.';

GRANT USAGE ON SCHEMA raw, core, mart, facts TO hoshizora_writer;
GRANT USAGE ON SCHEMA core, mart, facts TO hoshizora_reader;

ALTER DEFAULT PRIVILEGES IN SCHEMA raw
    GRANT SELECT, INSERT ON TABLES TO hoshizora_writer;

ALTER DEFAULT PRIVILEGES IN SCHEMA core, mart, facts
    GRANT SELECT, INSERT, UPDATE, DELETE, MAINTAIN ON TABLES TO hoshizora_writer;

ALTER DEFAULT PRIVILEGES IN SCHEMA raw, core, mart, facts
    GRANT USAGE, SELECT ON SEQUENCES TO hoshizora_writer;

ALTER DEFAULT PRIVILEGES IN SCHEMA core, mart, facts
    GRANT SELECT ON TABLES TO hoshizora_reader;
