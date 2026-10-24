#!/bin/sh
set -eu

: "${PREVIEW_DATABASE_URL:?set PREVIEW_DATABASE_URL to the Neon connection string}"
: "${FLYWAY_PLACEHOLDERS_API_PASSWORD:?set PREVIEW_API_DB_PASSWORD}"
: "${FLYWAY_PLACEHOLDERS_INGEST_PASSWORD:?set PREVIEW_INGEST_DB_PASSWORD}"

authority=${PREVIEW_DATABASE_URL#*://}
credentials=${authority%@*}
location=${authority##*@}

export FLYWAY_URL="jdbc:postgresql://${location%%\?*}?sslmode=${PREVIEW_DB_SSLMODE:-require}"
export FLYWAY_USER="${credentials%%:*}"
export FLYWAY_PASSWORD="${credentials#*:}"

exec flyway "$@"
