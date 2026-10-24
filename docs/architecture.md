# Architecture

```
 sources ──► ingest (Python) ──► PostgreSQL ──► api (Spring Boot) ──► web (React)
                                 raw → core → mart → facts
```

## Components

| Path | Role | Stack |
|---|---|---|
| `ingest/` | The only writer. Fetches sources, lands raw payloads, normalizes into `core`, refreshes `mart`, generates `facts`. | Python 3.14, uv, typer |
| `db/migration/` | The schema, owned by Flyway. Nothing else runs DDL. | PostgreSQL 18, Flyway 13 |
| `api/` | Read-only HTTP API under `/api/v1`, plus `/actuator/health`. | Java 25, Spring Boot 4.1, JdbcClient |
| `web/` | Bilingual (en / ja) single-page app with locale-prefixed routes, a react-three-fiber hero and ECharts figures. | TypeScript, Vite 8, React 19, React Router 8, TanStack Query 5, i18next, Tailwind 4, three.js, ECharts 6 |
| `infra/` | Local PostgreSQL and the Flyway runner (Docker Compose). | Docker |

## Data layers

| Schema | Contents | Written by | Read by |
|---|---|---|---|
| `raw` | Append-only source payloads, deduplicated by content hash | ingest (insert only) | ingest |
| `core` | Normalized entities with lineage to `raw` | ingest | ingest, api |
| `mart` | Materialized views for analytics | ingest (refresh) | ingest, api |
| `facts` | Fact params, scores and source references | ingest | ingest, api |

The database enforces the access rules with two group roles, `hoshizora_writer` and `hoshizora_reader`. See [ADR 0001](decisions/0001-read-write-split.md). The one exception to append-only `raw` is `raw.ingest_run`, whose status and counters the writer may update column by column. Superseded payload bodies listed in `raw.retention_policy` are pruned through owner-defined functions that never delete a row ([ADR 0009](decisions/0009-scheduled-ingestion-and-raw-retention.md)), and ingestion runs on a schedule on GitHub Actions ([deploy.md](deploy.md)).

## Ingestion

```
fetch ──► raw.fetch (every request) ──► raw.payload (distinct content) ──► parse ──► normalize ──► core (+ source_record)
  ▲                                                                                                   │
  └──────────── watermarks, refetch intervals and validators derived from raw ◄───────────────────────┘
```

- **Every source implements one protocol** (`ingest/hoshizora_ingest/sources/base.py`): `fetch` (async, plans requests through a shared context), `parse` (pydantic models), `normalize` (pure functions to typed rows) and `store` (SQL upserts with lineage).
- **The shared HTTP client** applies a per-source rate limit, tenacity retries that honor `Retry-After`, conditional requests from the fetch log, and a stop-for-review policy for sources that forbid retries.
- **Each page commits** landing, fetch log, core upserts and lineage in one transaction. Progress is derived from raw, so any interruption resumes cleanly. See [ADR 0002](decisions/0002-resumable-ingestion.md).
- **Payload models keep unknown fields** and declare the fields they ignore on purpose, so a new upstream field is reported once per run.
- **Organizations, aliases, countries and programs** follow [ADR 0003](decisions/0003-organization-model.md) and [sources/organizations.md](sources/organizations.md).

| Source | Slug | Core tables | Notes |
|---|---|---|---|
| Curated reference data | `reference` | country, program, organization_curation, external_code, aliases, data_source | [organizations.md](sources/organizations.md); the source catalog is `reference/sources.toml` |
| Launch Library 2 | `launch-library` | organization, launch, launch_vehicle, launch_pad, mission, mission_agency, launcher, landing | [launch-library-2.md](sources/launch-library-2.md) |
| CelesTrak | `celestrak` | space_object, orbit_element | [celestrak.md](sources/celestrak.md) |
| NASA/JPL SSD | `jpl` | small_body, close_approach, impact_risk | [jpl.md](sources/jpl.md) |
| NOAA SWPC | `swpc` | geomagnetic_index, space_weather_event, solar_wind_sample | [swpc.md](sources/swpc.md) |
| NASA Exoplanet Archive | `exoplanet-archive` | exoplanet | [exoplanet-archive.md](sources/exoplanet-archive.md) |

The CLI (`uv run hoshizora …`, or the `just` recipes):
- `sources` lists the registered sources.
- `ingest <slug> [--max-requests N]` and `ingest-all` run sources. Exit code 3 means a source asked for human review.
- `replay <slug>` rebuilds core from raw.
- `refresh-marts` refreshes every mart. `ingest`, `ingest-all` (once, at the end) and `replay` do it automatically after a run that changed rows, and after a failed run, since earlier pages may have committed.
- `dq [--strict]` prints the data-quality report.
- `docs` regenerates the organizations doc.

## Analytics marts

`db/migration/V8`–`V15` build the `mart` layer, one migration per module ([ADR 0005](decisions/0005-marts-and-lineage.md)). `V16` makes `source_status.last_fetched_at` count only accepted (200 and 304) fetches ([ADR 0002](decisions/0002-resumable-ingestion.md)).

| Module | Materialized views | Shared plain views and functions |
|---|---|---|
| Meta | none | `record_lineage`, `source_status`, `source_quality` |
| Launches | `launch_cadence_yearly`, `launch_success_rolling`, `launch_pad_activity`, `organization_launch_summary` | `launch_outcome()`, `launch_classified`, `launch_group`, `launch_listing`, `launch_group_name`, `organization_key`, `organization_profile` |
| Orbits | `objects_in_orbit_by_owner`, `objects_in_orbit_by_country` | `space_object_classified` |
| Near-Earth | `close_approach_enriched`, `close_approach_monthly` | `tdb_to_utc()`, `diameter_from_h_km()` |
| Space weather | `kp_daily`, `flare_counts_monthly`, `solar_wind_hourly` | `g_scale()`, `r_scale()` |
| Facts | none | tables `facts.template` and `facts.fact` |

- Every materialized view has a unique index, reads only `core` and plain views, and buckets time explicitly in UTC (TDB months for close approaches). Ingest refreshes them `CONCURRENTLY` after a run that changed rows.
- Each mart row records its `source` and the group keys that reproduce the core rows behind it.

## Fact engine

Templates live in `facts/templates/<module>.yaml`, and the generator in `ingest/hoshizora_ingest/facts/` writes `facts.fact` ([ADR 0006](decisions/0006-fact-engine.md)). There are 40 templates across launches, booster reuse, near-Earth, space weather, orbits, exoplanets, agencies and sources.

1. **Load and validate.** Ingest reads the YAML and checks it: params match the en/ja placeholders and the API renderer's grammar, and queries read only `core` and `mart`.
2. **Gate.** Templates that `require` a source wait until its latest run succeeded. Launch Library 2 facts wait for a complete backfill.
3. **Read.** All queries run in one read-only snapshot at `as_of`, the start of the UTC hour. Each row yields params, scoring signals, `valid_until` and `source_refs`.
4. **Score and store.**
   - The score is the strongest signal among a base, a percentile against history, a record or a first, decayed by distance in time.
   - Facts below `min_score` are dropped. The rest are upserted with stable ids.
   - Stale and expired facts are deleted.
5. **Render.** The API renders text per `Accept-Language` from the stored params and links every source to its records.

Mart refreshes trigger the generator, and `just facts` runs it on demand.

## Read API

```
request ─► LocaleHeadersFilter ─► ShallowEtagHeaderFilter ─► controller ─► repository (@Cacheable) ─► SQL in resources/sql
                                                                 │                                       │
                                                                 └──── localized view (after cache) ◄──── locale-neutral rows
```

- **Package by feature** under `api/src/main/java/dev/hoshizora/api/`: `meta`, `launches`, `agencies`, `neo` (close approaches and Sentry), `spaceweather`, `stats`, `facts`. Shared pieces live in `web` (paging, ranges, problems, caching, OpenAPI conventions), `i18n` (`Lang`, `Bilingual`, `Vocabulary`), `db` and `common` (organization, country and program references, lineage).
- **SQL is a file per query** in `api/src/main/resources/sql/<feature>/`, read through `JdbcClient` into records. Paginated queries return their total in the same round trip.
- **Contract:** [ADR 0004](decisions/0004-api-contract.md). The source of truth is `api/openapi.yaml`, with 22 operations. `just api-spec` regenerates it and the web types.

| Route | What it serves | Cache TTL |
|---|---|---|
| `GET /api/v1/meta/sources` | Sources, credits, licenses, freshness, data-quality status | 5 min |
| `GET /api/v1/launches`, `/launches/{id}` | Launches with filters; detail with partners, catalogued objects, lineage | 1 h |
| `GET /api/v1/agencies`, `/agencies/{key}` | Organizations, programs, launch records, reliability | 1 h |
| `GET /api/v1/close-approaches` | Approaches with UTC times and size ranges | 12 h |
| `GET /api/v1/impact-risks`, `/impact-risks/{designation}` | Sentry objects and their approaches | 12 h |
| `GET /api/v1/space-weather/now`, `/kp`, `/flares`, `/solar-wind` | Current conditions and time series | 1 h |
| `GET /api/v1/stats/launches/cadence`, `/success`, `/pads` | Launch aggregates with `records_url` | 1 h |
| `GET /api/v1/stats/orbits/countries` | Objects by country and organization | 12 h |
| `GET /api/v1/stats/close-approaches/monthly` | Approaches per month | 12 h |
| `GET /api/v1/stats/space-weather/flares`, `/kp` | Flares per month, Kp per day | 1 h |
| `GET /api/v1/stats/overview` | The home ticker | 1 h |
| `GET /api/v1/facts`, `/facts/{id}` | Rendered facts and how we know them | 1 h |

- **Tests:** the suite runs the API as a `hoshizora_reader` login against one seeded Testcontainers database (`api/src/test/resources/seed/`, built from real core rows), with a fixed clock. Every response is validated against the committed spec.

## Database conventions

- `initdb` uses the `builtin` locale provider with `C.UTF-8`. Collation is deterministic, and an OS upgrade can't silently invalidate indexes through glibc collation changes. Japanese-aware sorting uses the ICU `ja-x-icu` collation per query.
- Flyway keeps its history table in `public`. The data layers live only in their own schemas.

## Build and runtime conventions

- The API runs in UTC. Tests and `bootRun` pin `user.timezone=UTC`. On Windows hosts in India the JVM otherwise reports the legacy zone ID `Asia/Calcutta`, which PostgreSQL 18 on Debian trixie rejects at connect time. Locale-specific dates are formatted in the browser with `Intl`.
- Gradle provisions the Java 25 toolchain through the foojay resolver when no local JDK 25 exists.
- pnpm installs only package versions that are at least a day old (`minimumReleaseAge: 1440`, strict), which guards against freshly compromised releases.
- CI runs once per commit. Pushes to `main` and `phase/**` run `just up`, `just migrate` and `just check`. A pull request from a `phase/` branch skips its own run, because the push run already checked that commit. Pull requests from any other branch run the check themselves.
- Every dependency is pinned: `uv.lock`, `pnpm-lock.yaml`, the Gradle version catalog and Boot BOM, and exact Docker image tags.
- uv, like pnpm, refuses releases younger than a day (`exclude-newer = "1 day"`).
- On Windows, psycopg's async mode needs a selector event loop. The CLI and the test backend both pass `loop_factory`.

## Locales

- Every route is prefixed with a locale: `/en/…` or `/ja/…`.
  - `/` and unprefixed paths redirect to the stored preference, otherwise the browser language, otherwise English.
- The layout sets `<html lang>`, the localized title and description, and `hreflang` alternates for every language plus `x-default`.
- UI strings live in `web/src/locales/{en,ja}/*.json`. A parity test fails the build when a key, a namespace or an interpolation parameter exists in one locale but not the other.

## Web app

See [ADR 0008](decisions/0008-frontend-architecture.md) for the reasoning.

- **Design tokens.** Every color, type size, duration and easing is a CSS custom property on `[data-theme='deep-space']` (`web/src/styles/tokens.css`), mapped into Tailwind with `@theme inline`. Components never use raw hex. Chart colors, the categorical series and the aurora ramp are tokens too, read at runtime by the chart theme and the scenes.
- **Data layer.** `web/src/api/client.ts` wraps the generated `openapi-fetch` client. Every request sends `Accept-Language` and has a 25-second timeout.
  - A small store (`dataLink.ts`) tracks the API as `idle`, `connected`, `waking` or `offline`. Network errors, timeouts, 502/503/504 and non-JSON bodies (a host's wake page) count as waking.
  - TanStack Query retries those errors with capped backoff. After three minutes the link reads `offline` and retries every 30 s, with a manual retry button. The first success refetches everything that stalled.
  - Route loaders start each page's first queries while the page's chunk downloads.
- **Waking and errors.** The shell, hero and headings never wait for the API. Each data region keeps its final height and shows the designed "waking up the data link" state, or a localized error with a retry. A crash shows a designed route error, never a raw stack.
- **Hero.** A react-three-fiber scene (procedural starfield in three depth layers, fbm nebula, a textured rotating planet with an atmosphere shell) loads lazily after the page's `load` event and idle time, over a static SVG poster with the same composition.
  - It renders only when WebGL2 runs on a hardware renderer. Software renderers (SwiftShader, llvmpipe, Microsoft Basic Render) keep the poster.
  - Quality steps down by device: star count, noise octaves and a DPR cap of 1.5 / 1.25 / 1.
  - It pauses off-screen and in background tabs. Under reduced motion it renders a single still frame and ignores pointer and scroll parallax.
- **Facts.** Fact cards come from `/facts`. `web/src/facts/presentation.ts` maps every template key to its key figure and an optional comparison scale. A unit test fails when a template has no presentation, or a presentation has no template.
- **Charts.** ECharts loads lazily with the first chart: core, the SVG renderer and only the bar, line and scatter charts. Every figure has a chart/table toggle, an aria description and a source note dated by that source's last successful fetch.
- **Motion.** `prefers-reduced-motion` plus a persisted toggle set `data-motion` on `<html>`. CSS animations are token-driven, so reduced motion turns rises into nothing and fades into plain fades. Content already on screen at load is never animated from transparent.
- **Fonts.** M PLUS 1 (display) and IBM Plex Sans JP (text) are unicode-range-sliced woff2, loaded after the first frame with `font-display: swap`.
- **Tests.** Vitest covers formatters, scales, presentations, projection and preferences. Playwright runs every page in en and ja on a desktop and a phone, with the API answered from the OpenAPI examples. It also covers the waking state, the table views, the language and motion toggles, and the no-WebGL poster.

## Local workflow

`just up` starts PostgreSQL. `just migrate` applies the migrations and the local login roles. `just check` runs exactly what CI runs, including the Playwright smoke tests. `just web-preview` serves a production build on :4173 with `/api` proxied to `just api`, and `just lighthouse` scores every page against it.
