DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'hoshizora_ingest') THEN
        CREATE ROLE hoshizora_ingest LOGIN;
    END IF;
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'hoshizora_api') THEN
        CREATE ROLE hoshizora_api LOGIN;
    END IF;
END
$$;

ALTER ROLE hoshizora_ingest WITH LOGIN PASSWORD '${ingest_password}';
ALTER ROLE hoshizora_api WITH LOGIN PASSWORD '${api_password}';

GRANT hoshizora_writer TO hoshizora_ingest;
GRANT hoshizora_reader TO hoshizora_api;
