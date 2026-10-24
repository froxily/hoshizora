# ADR 0002: Resumable, incremental ingestion without cursor tables

- Status: accepted
- Date: 2026-10-16
- Amended: 2026-10-17 (rejected responses are logged in `raw.fetch`); 2026-10-19 (superseded bodies of listed payloads are pruned, rows stay; held sources and bounded waits, [ADR 0009](0009-scheduled-ingestion-and-raw-retention.md))

## Context

The sources are slow, rate-limited or strict:
- Launch Library 2 allows 15 requests per hour, so a full backfill (about 82 pages) takes six hours.
- CelesTrak blocks IPs that download the same data twice in an update cycle or that ignore errors.
- JPL asks for one request at a time.
- SWPC publishes rolling windows that must be fetched often enough not to leave gaps.

A run can stop anywhere (Ctrl-C, a crash, a cron timeout, a `--max-requests` cap), and the next run must continue without losing or duplicating work. Re-running on unchanged data must not rewrite anything.

## Decision

1. **Raw is the source of truth for progress.**
   - Every response lands in `raw.payload`, append-only and content-addressed: unique on `(source, content_hash)`, so identical content is stored once.
   - Every request is logged in `raw.fetch`:
     - Accepted responses: a 200 with its payload (new or duplicate), or a 304 Not Modified.
     - Rejected responses: a 429, or any other 4xx or 5xx that ends a request. These rows have the real status and duration but no payload, so quota and outage problems can be diagnosed from the database.
     - When the HTTP client retries a status internally (5xx, and 429 for JPL and SWPC), only the response that ends the request is logged. The run's `requests` count works the same way.
   - There are no mutable cursor or state tables. Progress is derived from what has landed:
     - **Watermarks.** The LL2 launch watermark is the newest `last_updated` in landed launch payloads. Launches are fetched with `last_updated__gte=<watermark>`, ordered by `last_updated`, advancing the offset when a page shares one timestamp.
     - **Refetch intervals** come from the last accepted (200 or 304) `raw.fetch` of the same endpoint and params: CelesTrak GP 2 h, SATCAT 12 h, SWPC 1–6 h, JPL 12 h, LL2 agencies 7 days after a complete sweep.
     - **Conditional requests** reuse the stored `ETag` and `Last-Modified` from the last 200 in `raw.fetch`.
     - **One-off windows** (JPL decades) are fetched once ever, because their fetch is on record.
   - A rejection never counts as a fetch:
     - Interval and validator lookups filter to accepted statuses.
     - The LL2 agency-sweep and JPL Sentry-removal queries join `raw.fetch` to its payload.
     - `mart.source_status.last_fetched_at` counts only 200 and 304, so the Sources page never shows a 429 as the last fetch.
2. **One transaction per page.** Landing the payload, logging the fetch, upserting core rows and writing lineage commit together. An interrupted run therefore leaves no half-applied page, and the next run's derived progress is exact. Rejections are the exception: they're written at once on the autocommit run-log connection, like `raw.ingest_run`. A run that fails or stops for review rolls back its open page but keeps the rejection that stopped it. A rejection has no payload, so no page depends on it.
3. **Upserts write only real changes.**
   - Core upserts use `ON CONFLICT … DO UPDATE … WHERE ROW(current) IS DISTINCT FROM ROW(incoming)` and return only changed keys. Lineage (`core.source_record`) is written for those keys only.
   - Time guards stop stale data from overwriting newer data: launches compare LL2 `last_updated`, and orbit elements compare `epoch`.
   - Windowed sources (JPL close approaches) replace their own date window, so revised predictions never leave duplicates.
4. **Run log with explicit outcomes.** `raw.ingest_run` records requests, 304s, new payloads and rows changed, with a status:
   - `succeeded`, `partial` (the `--max-requests` budget was reached, or the source's quota ran out: HTTP 429 after the source's own waiting rules), `failed` (exception), or `needs_review` (a source policy says stop, e.g. any CelesTrak non-200).
   - It is the only raw table the writer may update, and only by column.
5. **One code path.** Backfill, crash recovery and incremental updates are the same loop. `hoshizora replay <source>` rebuilds core from raw with the same parse → normalize → store code.

## Consequences

- **A Ctrl-C at any point is safe.** This was demonstrated against production LL2: a run capped at 7 requests ended `partial`, and the next run resumed from the exact landed watermark (`2023-06-14T03:32:46Z`), skipping the already-complete agency sweep.
- **Re-runs are cheap and provable.** Immediate re-runs make zero requests where an interval applies, and report 0 rows changed otherwise. Tests assert both for every source.
- **Rejections are on record.** Production LL2 run 3 failed on 429s that left no trace in `raw.fetch`. Now every rejected request has a row. Anything new that reads `raw.fetch` as "the last fetch" must filter to `http_status IN (200, 304)` or join the payload.
- **Raw grows with every distinct response.** Bodies use lz4 compression. Since Phase 7, superseded bodies of the high-churn products are pruned after 48 hours while their rows stay ([ADR 0009](0009-scheduled-ingestion-and-raw-retention.md)).
- **Payloads from different hosts are kept apart.** Endpoints are stored as full URLs, so a dev-host load can't move the production watermark.
- **One origin per source.** Amended 2026-10-18 after dev-host runs mixed stale LL2 rows into a production-fed database. Every run records its origin. The first one pins the source, and ingest and replay refuse any other origin. A blocking data-quality check flags core rows that trace back to more than one origin. Replay rebuilds from the pinned origin, prunes rows only foreign payloads support, and drops foreign links. See [launch-library-2.md](../sources/launch-library-2.md#origins-and-the-backfill).
- **Deriving progress costs queries over raw** (e.g. the LL2 watermark scans landed launch pages). That's fine at this scale and indexable later if needed.
