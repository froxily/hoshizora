# ADR 0005: Analytics marts, their refresh, and a metadata-only window into raw

- Status: accepted
- Date: 2026-10-16
- Amends: [ADR 0001](0001-read-write-split.md), whose consequences anticipated that lineage would need fetch times from `raw`

## Context

Phase 2 needs aggregates that several consumers share: API statistics, the fact engine (Phase 3) and the pages (Phase 4). Computing them in each request would repeat the same SQL in several places and do heavy scans on every call. Every number must also trace back to source records, yet the API role must stay unable to read `raw` payloads.

## Decision

1. **One migration per module** (`V8`–`V15`) owns the `mart` objects for meta, launches, orbits, near-Earth objects, space weather and facts.
   - **Materialized views** hold the aggregates: `launch_cadence_yearly`, `launch_success_rolling`, `launch_pad_activity`, `organization_launch_summary`, `objects_in_orbit_by_owner`, `objects_in_orbit_by_country`, `close_approach_enriched`, `close_approach_monthly`, `kp_daily`, `flare_counts_monthly` and `solar_wind_hourly`.
   - **Plain views** define shared shapes that are cheap to compute at read time: `launch_classified`, `launch_group`, `launch_listing`, `organization_key`, `organization_profile`, `launch_group_name` and `space_object_classified`.
2. **Domain rules are SQL functions, defined once:**
   - `launch_outcome()`: Launch Library 2 status ids to outcomes.
   - `tdb_to_utc()`: UTC = TDB − (32.184 s + TAI−UTC), with the IERS leap-second table through Bulletin C 72, valid to 2027-06-28; NULL before 1972.
   - `diameter_from_h_km()`: D = 1329 km / √albedo × 10^(−H/5), for albedos 0.05 to 0.25.
   - `g_scale()` and `r_scale()`: the NOAA storm and radio blackout levels.
   Marts and API queries call the same functions, so a chart and a fact can't disagree.
3. **Deterministic buckets.** Every timestamp is bucketed explicitly in UTC (`AT TIME ZONE 'UTC'`), whatever the session time zone of whoever refreshes. Close approaches are bucketed by TDB calendar month, as JPL publishes them.
4. **Refresh, owned by ingest.**
   - Each materialized view has a unique index, so ingest can run `REFRESH MATERIALIZED VIEW CONCURRENTLY` after any run that changed rows, while the API keeps reading. That needs only the `MAINTAIN` privilege ADR 0001 granted.
   - Materialized views read only `core` and plain views, never each other, so refresh order doesn't matter.
   - On a copy of the real data (3,904 launches, 71,073 objects, 51,960 approaches), all eleven refresh in about 2 seconds.
5. **Lineage.**
   - **Records:** `mart.record_lineage` joins `core.source_record` to `raw.payload` and exposes only request metadata (source, endpoint, params, fetched_at, content hash), never bodies. `mart.source_status` exposes run status and fetch times without error text. Both are owner-privileged views, so `hoshizora_reader` still can't select from `raw` itself, and the privilege test still proves it.
   - **Aggregates:** each mart row carries its `source` and the group keys that reproduce exactly the core rows behind it. The API turns those keys into `records_url` queries.
   - **Facts:** `facts.fact.source_refs` names the core or mart rows behind each fact, and the API resolves them to routes and lineage.
6. **Source metadata is data, not schema.** `core.data_source` (bilingual name, credit, license, cadence) is written by ingest from curated reference data, like countries and organizations. Flyway creates the table but never fills it, so ingest stays the only writer.

## Consequences

- The fact engine can build on the same marts the charts use, so a computed fact and the chart beside it agree by construction.
- A migration that adds a materialized view runs its query once at deploy time. That's fine at current sizes; very large marts would need `WITH NO DATA` and a first refresh by ingest.
- The marts lag core until the next refresh. Without the ingest hook, they stay as they were at migration time.
- SWPC publishes only about seven days of flares and Kp and one day of solar wind, so those marts grow with each ingestion rather than starting with history.
- The `raw` window is narrow and reviewable: two views, metadata only. Widening it needs another migration and an ADR.
