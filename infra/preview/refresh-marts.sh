#!/bin/sh
set -eu

: "${PREVIEW_DATABASE_URL:?set PREVIEW_DATABASE_URL to the Neon connection string}"

psql "$PREVIEW_DATABASE_URL" -Atc \
  "SELECT format('REFRESH MATERIALIZED VIEW %I.%I;', schemaname, matviewname) FROM pg_matviews WHERE schemaname = 'mart' ORDER BY matviewname" \
  | psql "$PREVIEW_DATABASE_URL" --quiet --single-transaction -v ON_ERROR_STOP=1

psql "$PREVIEW_DATABASE_URL" -Atc \
  "SELECT 'marts refreshed ' || count(*) || ', organizations with launches ' || (SELECT count(*) FROM mart.organization_launch_summary) FROM pg_matviews WHERE schemaname = 'mart'"
