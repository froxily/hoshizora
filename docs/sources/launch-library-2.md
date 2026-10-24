# Launch Library 2 (The Space Devs)

Slug: `launch-library` · Adapter: `ingest/hoshizora_ingest/sources/launch_library/` · Verified against live docs and responses on 2026-10-16. Throttle behaviour re-verified the same day, after the production backfill hit HTTP 429 (see [Quota handling](#quota-handling)). Launchers and landings verified against the live 2.3.0 schema and responses on 2026-10-19.

## Purpose

The backbone for launches, launch providers, vehicles, pads and missions, and the identity source for organizations (see [organizations.md](organizations.md)). Roscosmos and CNSA publish no general launch APIs, so their launch history comes from here.

## Access

| | |
|---|---|
| API version | 2.3.0 (marked "Supported" and current in the OpenAPI schema) |
| Production | `https://ll.thespacedevs.com/2.3.0/` |
| Development | `https://lldev.thespacedevs.com/2.3.0/`: "no rate limits, limited, stale data", for development only (515 launches, 350 agencies at verification time) |
| Auth | None. An API key raises the limit, but anonymous access is enough |
| Rate limit | 15 requests per hour per IP on production, over a sliding hour. `/2.3.0/api-throttle/` reports `your_request_limit`, `limit_frequency_secs`, `current_use`, `next_use_secs` and **does not count** toward the limit, but LL2's proxy caches its answer for about 60 s. The docs don't describe the 429 response or `Retry-After` |
| Page size | `limit` up to 100 |
| Conditional requests | Not supported (no ETag or Last-Modified) |
| License and credit | No license or attribution requirement is published. Credit shown: "Launch data: The Space Devs, Launch Library 2 (thespacedevs.com)" |
| Docs | <https://thespacedevs.com/llapi>, <https://ll.thespacedevs.com/docs/>, FAQ: <https://github.com/TheSpaceDevs/Tutorials/blob/main/faqs/faq_LL2.md>, schema: `/2.3.0/schema/` |

`HOSHIZORA_LL2_BASE_URL` selects the host, and `just` defaults to production. A database holds each source from one origin only (see [Origins and the backfill](#origins-and-the-backfill)), so use the dev host only with a separate database.

## Endpoints used

| Endpoint | Parameters | Why |
|---|---|---|
| `/2.3.0/agencies/` | `mode=normal&ordering=id&limit=100&offset=N` | Agency identity, type, countries, founding year, parent. Refreshed at most weekly |
| `/2.3.0/launches/` | `mode=normal&ordering=last_updated&last_updated__gte=W&limit=100&offset=N` | Launches with provider, vehicle, pad and mission inline |
| `/2.3.0/launchers/` | `mode=detailed&ordering=id&limit=100&offset=N` | Every tracked first stage: serial, status, configuration, flights, landings, first and latest launch, fastest turnaround. Swept at most daily |
| `/2.3.0/landings/` | `mode=list&ordering=-id&limit=100&offset=N` | Landing records, newest first: attempt, outcome, type, location, and the stage's flight number, previous flight and turnaround. See [Landings](#landings) |
| `/2.3.0/api-throttle/` | — | Quota check before every production request (free) |

## Incremental and resumable fetching

There is no cursor table. The **watermark** `W` is the newest `last_updated` among the launch payloads already landed in `raw.payload` for the same host. Each run requests launches with `last_updated__gte=W`, ordered by `last_updated`:

- A full page whose newest timestamp is beyond `W` moves `W` forward (offset 0).
- A full page where every launch shares `W` advances the offset instead, so a burst of identical timestamps cannot loop.
- A short page means the feed is caught up.

The first run on an empty database starts at 1950-01-01, so the backfill, a restart after a crash or Ctrl-C, and the hourly incremental update are all the same code path. Pages commit one by one, so nothing is lost when a run stops. On production a full backfill runs unattended at 15 pages per hour (see [Quota handling](#quota-handling)). `--max-requests N` caps one invocation for cron.

Raw endpoints are stored as full URLs, so dev-host and production payloads keep separate watermarks. Since 2026-10-18 one database never mixes the two hosts.

## Landings

`/landings/` has no `last_updated` filter and its records have no launch link or date ([ADR 0010](../decisions/0010-booster-reuse.md)).

- **Backfill:** the walk resumes at the highest offset already fetched and runs until `next` is null. That took 18 pages on 2026-10-19 (1,787 landings).
- **Incremental:** once a walk has reached the end, each run walks from offset 0 and stops after a page whose first-stage landings were all settled before the run (known outcome, or no attempt). Scheduled landings are always unsettled, so a run usually makes two requests.
- **Kept:** first-stage landings only. Spacecraft (Dragon, Starship ships, Soyuz) and payload landings are skipped.
- **Launch time:** `mart.landing_flight` derives it as `previous_flight_date + turn_around_time`, or as the stage's `first_launch_date` for its first flight, and matches the launch within a minute. `mart.dq_unmatched_landing` lists settled misses (none on 2026-10-19; all 845 settled landings matched).
- **Retention:** both `/landings/` and `/launchers/` are in `raw.retention_policy` (48 hours). Each landing page is about 0.38 MB of JSON and about 50 KB stored.

## Quota handling

What the live service showed on 2026-10-16:

- **The hour slides.** `next_use_secs` counts down to the moment the oldest request of the past hour expires, not to a fixed reset. Run 3's probe held one request back 65 s, until exactly an hour after an earlier request, at a point where a fixed window would already have reset.
- **The throttle answer is cached.** Repeated probes return `x-cache-status: HIT` for about 60 s, then `EXPIRED`. A probe can therefore report a `current_use` up to a minute old, and a request it lets through can still get 429.
- **Rejected requests appear to count.** Run 3 failed at 13:58 UTC with 4,958 of 8,126 launches landed. One request at the quota boundary got 429, and the generic retry sent three more attempts. Each went out the instant the local limiter freed a slot, and each was rejected, so the window never emptied and the exhausted retry failed the run.

The adapter follows these rules on production:

1. Before every request, probe `/api-throttle/`. If `current_use >= your_request_limit`, sleep `next_use_secs + 1`.
2. The local limiter (15 per 3,600 s) counts each request from when its response arrives, not when it was sent. LL2 can stamp a slow request at any point in between (one page took 34 s in run 3), so counting from the response never frees a slot before LL2 does. Every attempt counts, including a 429.
3. The shared HTTP client never retries a 429 for this source. The adapter catches it, waits `max(Retry-After, 60 s) + 1 s` so the next probe reads fresh counts, then probes again and follows that answer.
4. After 3 consecutive 429s for the same page, the run stops as `partial`. Every landed page is already committed, and the next `just ingest launch-library` resumes from the raw watermark at that same page.

A 429 is logged as a `quota exhausted` warning and, when it ends the run, in `raw.ingest_run.error`. Every 429 also gets its own `raw.fetch` row with `http_status = 429`, its duration and no payload. The client never retries a 429 for this source, so each row is one request LL2 counted. The row survives even when the run fails. To see the rejections of recent runs:

```sql
SELECT run_id, requested_at, http_status, duration_ms, params ->> 'offset' AS "offset"
FROM raw.fetch
WHERE source = 'launch-library' AND http_status NOT IN (200, 304)
ORDER BY requested_at DESC;
```

The `/api-throttle/` probes aren't written to `raw.fetch`.

## Origins and the backfill

On 2026-10-16, runs 12 to 15 fetched from the dev host because `just` defaulted to it. They added 515 launches, 511 missions, 66 vehicles and 42 pads with no production lineage, and rewrote 3 production organizations with dev-host values. Nothing flagged it, and `replay` replayed both hosts' payloads.

Since 2026-10-18:

- **Every run records its origin** (`raw.ingest_run.origin`, scheme and host). The first run that records one pins the source. `ingest` and `replay` refuse any other origin with exit code 2, before any request is sent.
- **`just dq --strict` fails on a mix.** The blocking check "Sources mixing origins" (`mart.dq_source_origin_mix`) lists every source whose core rows trace back to payloads from more than one origin.
- **`replay` rebuilds from the pinned origin only.** When foreign payloads exist, it:
  1. Replays the pinned origin's payloads and links every row they contain, not only the rows that changed.
  2. Deletes launches, missions, pads and vehicles that only foreign payloads support. Children go first.
  3. Removes every link to a foreign payload.
  - Organizations are never deleted, because curation and the reference source feed them too. Foreign-only organizations are reported as unlinked.
  - Raw payloads stay untouched; raw is append-only.
- **`just backfill`** always uses the production host, whatever `HOSHIZORA_LL2_BASE_URL` says. Each run covers one quota window:
  - It probes `/api-throttle/` and, if the quota is spent, logs "waiting N min for the LL2 quota" and sleeps until it frees.
  - It runs the ingest with a request budget equal to the quota still free, so the run ends `partial` when the window is used up instead of sleeping inside the run.
  - It appends one line per run to `logs/backfill.log`, then waits 61 s for LL2's cached throttle answer to expire before probing again.
  - It stops on `needs_review`, on a failed run, or after 2 runs in a row that landed nothing.
  - When a run succeeds with no launch pages left, it replays from production (which removes any dev-only rows production doesn't have), refreshes the marts and exits 0.
  - Ctrl-C is safe: the interrupted run closes as `partial`, and the next `just backfill` resumes from the raw watermark.
- **Bulk edits slow the walk.** LL2 has stretches where hundreds of launches share one `last_updated` (2023-06-14 17:40 UTC, for example). Each watermark move re-reads that tie group, so such pages bring about 50 new launches instead of 100, and the pages-left estimate is optimistic there.
- **`just backfill-status`** reads the database only.
  - **Launches:** "loaded" counts distinct launch ids in production pages. LL2's total is that count plus the launches its latest page still reports after itself.
  - **It also shows:** the pages left, the last run with its status and origin, and an ETA at 15 pages per hour.

## Field mapping

| LL2 field | Core column |
|---|---|
| `id` (uuid) | `core.launch.ll2_id` |
| `name`, `slug` | `launch.name`, `launch.slug` |
| `launch_designator` | `launch.launch_designator` (COSPAR `YYYY-NNN`; joins to CelesTrak `OBJECT_ID`) |
| `net`, `net_precision.abbrev` | `launch.net`, `launch.net_precision` |
| `window_start`, `window_end` | `launch.window_start`, `launch.window_end` |
| `status.id`, `status.abbrev`, `status.name` | `launch.status_id`, `launch.status`, `launch.status_name` |
| `failreason` | `launch.failure_reason` |
| `last_updated` | `launch.source_updated_at` (upserts only move forward) |
| `launch_service_provider.id` | `launch.provider_org_id` via alias `ll2.agency/<id>` |
| `rocket.configuration.{id,name,full_name,variant,families[0].name}` | `core.launch_vehicle` |
| `pad.{id,name,latitude,longitude,country.alpha_2_code,location.name}` | `core.launch_pad` |
| `mission.{id,name,type,description,orbit.abbrev,orbit.name}` | `core.mission` |
| `mission.agencies[].id` | `core.mission_agency` (customers and partners) |
| agency `{name, abbrev, type.name, founding_year}` | `core.organization.{source_name, abbrev, source_type, founding_year}` |
| agency `country[].alpha_2_code` | `core.organization_country` |
| agency `parent` | `core.organization.parent_id` (resolved by unique name) |
| launcher `id`, `serial_number`, `is_placeholder`, `flight_proven`, `status.name` | `core.launcher.{ll2_id, serial_number, is_placeholder, flight_proven, status}` |
| launcher `launcher_config.id` | `core.launcher.vehicle_ll2_id` (same id space as `core.launch_vehicle`; launcher sweep only) |
| launcher `flights`, `attempted_landings`, `successful_landings`, `first_launch_date`, `last_launch_date`, `fastest_turnaround` | `core.launcher.{flights, attempted_landings, successful_landings, first_launch_at, last_launch_at, fastest_turnaround}` |
| landing `id`, `attempt`, `success`, `downrange_distance` | `core.landing.{ll2_id, attempt, success, downrange_km}` |
| landing `type.{abbrev,name}`, `landing_location.{name,abbrev}` | `core.landing.{type_abbrev, type_name, location_name, location_abbrev}` |
| landing `firststage.{launcher.id, type, launcher_flight_number, reused, previous_flight_date, turn_around_time}` | `core.landing.{launcher_ll2_id, stage_type, launcher_flight_number, reused, previous_flight_at, turnaround}` |

## Quirks

- **An agency's `parent` is the parent's name, not its id.** It resolves only when exactly one organization has that name.
- **Agency `type` is coarse.** State-owned corporations (CASC, CASIC, Khrunichev) are listed as Government, and armed forces as Government too. Curated overrides correct both.
- **The placeholder agency "Unknown"** has type `Unknown`. It's acknowledged in the code vocabulary and not reported as untyped.
- **Landings have no launch link or date.** See [Landings](#landings).
- **Placeholder stages** ("Unknown F9") carry no flight number, so their landings have no derivable launch time. They are kept in core and left out of the marts.
- **`/launchers/` in normal mode omits the configuration**, so the sweep uses detailed mode. Landings embed the stage in its short form, which only sets the stage's identity columns.
- **The country code `??`** means unknown. Codes absent from CLDR are recorded in `core.observed_code` instead of failing the load.
- **Launch-embedded providers are partial** (no countries, no founding year), so they never overwrite fields that a full agency record set.
- **`launch_designator` is null** until a launch reaches orbit.
- **The API-throttle schema says "array", but the live response is a single object.**
- **The throttle endpoint is cached for about 60 s** by LL2's proxy (`x-cache-status: HIT`), so its counts can lag behind real use.
- **The quota follows the caller's IP.** `ident` echoes the address being counted (over IPv6, a /64 prefix such as `2001:db8:1:2::`). Other machines that share that egress address, for example behind a VPN, share the 15 requests.

## Fixtures

`ingest/tests/fixtures/launch-library/`, captured from the dev host on 2026-10-16:

- `launches_page.json`: 5 upcoming launches (no designators).
- `launches_history.json`: 4 successful launches with designators (CASC, SpaceX, CAS Space).
- `launches_empty.json`: an empty page (the edge case).
- `agencies_page.json`: 5 agencies, including one with a `parent`.
- `api_throttle.json`: a throttle response.
- `launchers_page.json`: 5 stages from production on 2026-10-19, including the placeholder "Unknown F9" (images removed).
- `landings_page.json`: 5 production landings in list mode: B1095's third flight (matches the Starlink Group 10-52 launch in `launches_history.json`), a first flight, an expended stage, a scheduled landing and a spacecraft landing (the skipped edge case).

No 429 response was captured, because capturing one means going over the production limit. Tests script the 429 (status plus optional `Retry-After`), and the adapter relies on nothing else from it.
