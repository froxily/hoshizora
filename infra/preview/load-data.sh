#!/bin/sh
set -eu

: "${PREVIEW_DATABASE_URL:?set PREVIEW_DATABASE_URL to the Neon connection string}"

target="$PREVIEW_DATABASE_URL"

existing=$(psql "$target" -Atc "SELECT count(*) FROM raw.payload")
if [ "$existing" != "0" ]; then
  echo "The preview database already holds $existing raw payloads; load only into a freshly migrated database." >&2
  exit 1
fi

PGPASSWORD="$SOURCE_PASSWORD" pg_dump -h postgres -U "$SOURCE_USER" -d "$SOURCE_DB" \
    --data-only --no-owner --no-privileges \
    --schema=raw --schema=core --schema=mart --schema=facts \
    --exclude-table-data=raw.retention_policy \
  | psql "$target" --quiet --single-transaction -v ON_ERROR_STOP=1

psql "$target" -Atc \
  "SELECT 'launches ' || (SELECT count(*) FROM core.launch) || ', facts ' || (SELECT count(*) FROM facts.fact) || ', size ' || pg_size_pretty(pg_database_size(current_database()))"

sh /preview/refresh-marts.sh
