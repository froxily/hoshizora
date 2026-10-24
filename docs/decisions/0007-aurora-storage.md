# ADR 0007: Aurora forecast storage and the first raw retention policy

Status: accepted (Phase 4, 2026-10-18). Amended by [ADR 0009](0009-scheduled-ingestion-and-raw-retention.md): retention now prunes bodies, never rows, and runs once per run for every listed endpoint.

## Context

- The Sun page needs NOAA SWPC's OVATION aurora forecast: a 65,160-cell grid of the probability of visible aurora, refreshed about every 5 minutes.
- Every response lands in `raw.payload`, which has been append-only so every transform can be replayed.
- One OVATION payload stores at about 0.46 MB in `raw.payload` even with lz4. Hourly fetching kept for 7 days would be about 85 MB, two-thirds of the whole local database (128 MB) and a large share of the 0.5 GB free Postgres tier planned for the preview.
- The page shows the latest forecast and a short trend, not a long history. Kp and flares already cover the week.

## Decision

1. **Fetch hourly**, conditionally, as a sixth SWPC product.
2. **Retention by policy, not by habit.** `raw.retention_policy` lists the only payloads that may ever be deleted, with their window and reason. Its single row keeps OVATION payloads for 48 hours.
   - `raw.apply_retention(source, endpoint, reference)` is a `SECURITY DEFINER` function owned by the migration role. It deletes only payloads named in the policy that are older than the reference time minus the window. The writer may call it but still cannot delete from `raw` directly.
   - `raw.fetch` keeps every request; its `payload_id` becomes NULL when the payload is pruned. `core.source_record` rows go with their payload.
   - The store step calls it with the forecast's observation time, not the wall clock. A replay walks payloads oldest first, so it never prunes a payload it has not processed yet.
3. **Core tables.**
   - `core.aurora_forecast`: one summary row per forecast (observation and forecast time, the highest probability and the 10 % boundary latitude per hemisphere), kept for the same 48 hours.
   - `core.aurora_cell`: the non-zero cells of the latest forecast only (about 20,000 rows), replaced when a newer forecast is stored.
4. **API.** `GET /api/v1/space-weather/aurora` serves the latest cells as compact `[longitude, latitude, percent]` triples plus the 48-hour summary.

## Consequences

- Every aurora number on the site still traces to a stored payload, because summaries outlive neither their payload nor the window.
- Replays rebuild aurora only for the last 48 hours. That is the accepted cost.
- The policy table is the place to add Phase 7's planned retention for other large products, such as the real-time solar wind files.
- Test cleanup leaves `raw.retention_policy` in place, since it is configuration, not data.
