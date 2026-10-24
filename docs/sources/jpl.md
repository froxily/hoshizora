# NASA/JPL SSD: Close Approaches and Sentry

Slug: `jpl` · Adapter: `ingest/hoshizora_ingest/sources/jpl/` · Verified against the live documentation and responses on 2026-10-16.

## Purpose

Past and future close approaches of asteroids and comets to Earth (the Near-Earth page's timeline and size-vs-distance charts) and the Sentry impact-monitoring list (the risk table).

## Access

| | |
|---|---|
| Close approaches | `https://ssd-api.jpl.nasa.gov/cad.api`, API version 1.5. Docs: <https://ssd-api.jpl.nasa.gov/doc/cad.html> |
| Sentry | `https://ssd-api.jpl.nasa.gov/sentry.api`, API version 2.0 (summary mode, plus `removed=1`). Docs: <https://ssd-api.jpl.nasa.gov/doc/sentry.html> |
| Auth | None |
| Usage policy | <https://ssd-api.jpl.nasa.gov/>: **one request at a time**, back off on errors, and send a User-Agent with product, version and contact. No published numeric limit. The APIs must not be embedded in websites, so the browser never calls them; only ingestion does |
| User-Agent | `Hoshizora/<version> (+https://github.com/froxily)`, overridable with `HOSHIZORA_CONTACT` |
| Conditional requests | Not supported (no ETag or Last-Modified), so duplicates are skipped by content hash |
| Credit | No requirement is stated. Credit shown: "Small-body data: NASA/JPL Solar System Dynamics (SBDB Close Approach and Sentry APIs)" |

## What is fetched

| Request | Parameters | When |
|---|---|---|
| CAD backfill | `date-min`/`date-max` per decade 1900–2200, `dist-max=0.05`, `body=Earth`, `fullname=true`, `diameter=true` | Once per window, ever |
| CAD rolling window | 60 days back to 366 days ahead of today | At most every 12 hours |
| Sentry summary | none (mode S) | At most every 12 hours |
| Sentry removed | `removed=1` (mode R) | At most every 12 hours, after the summary |

Requests run one at a time (at most one every 2 seconds) and retry 429/5xx with backoff. A 429 that outlasts the retries ends the run `partial`; any other 4xx is a bug on our side and fails the run. Each response's `signature.version` is checked, so a format change fails loudly instead of loading wrong data.

## How windows stay correct

Orbit solutions improve with every observation, so a predicted approach time moves slightly between fetches. The key `(designation, body, approach_tdb)` would therefore leave stale duplicates. Instead, **each CAD response replaces its own date window**: rows inside `[date-min, date-max)` that are no longer in the response are deleted, and the rest are upserted. Payload params use absolute dates, so a replay reproduces the same windows.

Sentry objects that leave the list keep their row with `removed_at` from the removed list. An object is marked removed only if the most recently fetched summary no longer lists it, because the removed list also contains old removals of objects that were later re-added.

## Field mapping

| Source field | Core column |
|---|---|
| CAD `des`, `fullname` (trimmed), `h`, `diameter`, `diameter_sigma` | `core.small_body.designation`, `fullname`, `h_mag`, `diameter_km`, `diameter_sigma_km` |
| CAD `cd` | `core.close_approach.approach_tdb` (TDB, see below) |
| CAD `jd`, `orbit_id`, `dist`, `dist_min`, `dist_max`, `v_rel`, `v_inf`, `t_sigma_f`, `h` | `jd_tdb`, `orbit_id`, `dist_au`, `dist_min_au`, `dist_max_au`, `v_rel_kms`, `v_inf_kms`, `t_sigma`, `h_mag` |
| Sentry `des`, `id`, `fullname` | `core.impact_risk.designation`, `sentry_id`, `fullname` |
| Sentry `ip`, `ps_cum`, `ps_max`, `ts_max`, `n_imp` | `impact_probability`, `palermo_cumulative`, `palermo_max`, `torino_max`, `potential_impacts` |
| Sentry `range` (`2178-2290`) | `impact_year_first`, `impact_year_last` |
| Sentry `last_obs`, `diameter`, `h`, `v_inf` | `last_observed`, `diameter_km`, `h_mag`, `v_inf_kms` |
| Sentry removed `removed` | `impact_risk.removed_at` |

## Quirks

- **`cd` is Barycentric Dynamical Time (TDB), not UTC** (TDB − UTC ≈ 69 s), formatted like `2026-Oct-01 11:01`. It's stored as `timestamp` without time zone in `approach_tdb`, so nobody mistakes it for UTC.
- **CAD returns every value as a string**, positionally against the `fields` list. An empty window returns only `signature` and `count: 0`, with no `fields` or `data`.
- **`fullname` is left-padded with spaces** (`"       (2026 TZ)"`).
- **Sentry `last_obs` is usually `YYYY-MM-DD`**, but some entries use a fractional day without zero padding (`2020-10-3.80160`). The date part is kept.
- **Sentry `diameter`, `h`, `v_inf` and `ps_cum` are impact-probability-weighted means**, not catalogue values. `core.small_body` keeps the CAD values.
- **Errors come back as JSON**: `{"code": "400", "message": …}`.

## Fixtures

`ingest/tests/fixtures/jpl/`, captured with five sequential requests on 2026-10-16 and trimmed:

- `cad_window.json`: a one-week window (2026-10-01..08).
- `cad_empty.json`: an empty window (the edge case).
- `cad_error.json`: a 400 error body.
- `sentry_summary.json`: five objects, including (29075) 1950 DA and (101955) Bennu.
- `sentry_removed.json`: three removals.
