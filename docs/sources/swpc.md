# NOAA Space Weather Prediction Center (SWPC)

Slug: `swpc` · Adapter: `ingest/hoshizora_ingest/sources/swpc/` · Verified against live responses on 2026-10-16.

## Purpose

The Sun page and the home ticker: the planetary Kp index, GOES X-ray flares, SWPC alerts, watches and warnings, and real-time solar wind at L1.

## Access

| | |
|---|---|
| Base | `https://services.swpc.noaa.gov/` (directory listings at `/json/` and `/products/`) |
| Auth | None |
| Caching | Every product sends `ETag`, `Last-Modified` and `Cache-Control: max-age=60`, so requests are conditional (unchanged → 304) |
| Format | Key-value JSON objects since Service Change Notice 26-21 (effective about 2026-03-31; old formats retired 2026-04-30) |
| License and credit | NOAA data is open; NOAA asks for attribution and forbids implying endorsement or affiliation. Credit shown: "Space weather data: NOAA Space Weather Prediction Center (SWPC)" |

## Products

| Product | URL | Content | Refresh |
|---|---|---|---|
| Planetary Kp | `/products/noaa-planetary-k-index.json` | 7 days of 3-hourly Kp with `a_running`, `station_count` | hourly |
| X-ray flares | `/json/goes/primary/xray-flares-7-day.json` | GOES primary flares for 7 days | hourly |
| Alerts | `/products/alerts.json` | Recent alerts, watches and warnings with full message text | hourly |
| Solar wind plasma | `/json/rtsw/rtsw_wind_1m.json` | 1 day of 1-minute proton speed, density and temperature | every 6 hours |
| Solar wind field | `/json/rtsw/rtsw_mag_1m.json` | 1 day of 1-minute Bt and Bz (GSM) | every 6 hours |
| Aurora forecast | `/json/ovation_aurora_latest.json` | OVATION Prime 30–90 minute forecast: probability of visible aurora on a 1° grid | hourly |

Each product is refetched only after its refresh interval (from the `raw.fetch` log) and always conditionally, so an unchanged product costs one 304. Retries cover 429 and 5xx with backoff, one request per second. A 429 that outlasts the retries ends the run `partial`.

### Aurora forecast (added in Phase 4, verified 2026-10-18)

- **Shape:** one object with `Observation Time`, `Forecast Time`, `Data Format` (`[Longitude, Latitude, Aurora]`), `type` (`MultiPoint`) and `coordinates`: 65,160 triples covering longitude 0–359 and latitude −90 to 90 in 1° steps. The third value is the probability of visible aurora in percent.
- **Model:** OVATION Prime, developed by P. Newell and colleagues at the Johns Hopkins University Applied Physics Laboratory and run operationally by SWPC (OVATION 2020). The lead time equals the solar wind travel time from L1. If L1 data are missing, the model falls back to Kp and has no lead time.
- **Size and cadence:** about 920 KB, `Last-Modified` about every 5 minutes, ETag supported. We fetch it hourly, conditionally.
- **Storage ([ADR 0007](../decisions/0007-aurora-storage.md)):** one stored payload is about 0.46 MB even with lz4. Superseded OVATION bodies are kept 48 hours (`raw.retention_policy`, ADR 0009); their rows stay for lineage. `core.aurora_forecast` keeps a summary row per forecast for the same window, and `core.aurora_cell` holds only the latest forecast's non-zero cells.

## Field mapping

| Source field | Core column |
|---|---|
| Kp `time_tag`, `Kp`, `a_running`, `station_count` | `core.geomagnetic_index` (`index = 'kp'`, `observed_at`, `value`, `a_running`, `station_count`) |
| Flare `begin_time` | `space_weather_event.external_id` (ISO) and `begin_at`, `kind = 'xray_flare'` |
| Flare `max_time`, `end_time`, `max_class`, `max_xrlong`, `satellite` | `peak_at`, `end_at`, `event_class`, `peak_flux_wm2`, `satellite` |
| Alert `product_id`, `issue_datetime`, `message` | `kind = 'alert'`, `external_id = product_id@issue time`, `product_id`, `begin_at`, `message` |
| Plasma `time_tag`, `source`, `proton_speed`, `proton_density`, `proton_temperature` | `core.solar_wind_sample.observed_at`, `plasma_spacecraft`, `speed_kms`, `density_cm3`, `temperature_k` |
| Field `time_tag`, `source`, `bt`, `bz_gsm` | `observed_at`, `mag_spacecraft`, `bt_nt`, `bz_gsm_nt` |
| OVATION `Observation Time`, `Forecast Time` | `core.aurora_forecast.observed_at`, `forecast_at` |
| OVATION highest northern and southern value | `north_max_percent`, `south_max_percent` |
| OVATION lowest latitude reaching 10 % in each hemisphere | `north_boundary_lat`, `south_boundary_lat` |
| OVATION non-zero `[lon, lat, aurora]` of the latest forecast | `core.aurora_cell` (`longitude`, `latitude`, `probability_percent`) |

## Quirks

- **The real-time solar wind files mix spacecraft** (ACE, IMAP and SOLAR1 at verification time), with one row per spacecraft per minute. `active: true` marks the one SWPC is using. Only active rows are stored. At the same minute in the fixture, inactive ACE reported Bz −2.27 nT and active SOLAR1 −0.67 nT, so this matters.
- **Plasma and magnetic-field data arrive in separate files.** They fill different columns of the same minute row and may come from different spacecraft.
- **Timestamps mix styles.** Kp and solar-wind times have no time zone (`2026-10-16T03:00:00`), flares end in `Z`, and alerts use a space and milliseconds (`2026-10-13 20:58:58.750`). All are UTC and stored as `timestamptz`.
- **A flare in progress has no `end_time` yet.** The row is updated in place when it ends. Kp estimates are revised in place too.
- **The solar wind files are large** (about 4 MB together) and cover only one day. A 6-hour refresh keeps the record continuous. Raw bodies use lz4 compression, and superseded bodies are pruned after 48 hours while their rows stay ([ADR 0009](../decisions/0009-scheduled-ingestion-and-raw-retention.md)).

## Fixtures

`ingest/tests/fixtures/swpc/`, one request per product on 2026-10-16, trimmed:

- `kp.json`: 8 Kp intervals.
- `flares.json`: 4 real flares plus one ongoing flare (edge case: no `end_time`), derived from a real row.
- `alerts.json`: 3 alerts.
- `rtsw_wind.json`, `rtsw_mag.json`: 3 minutes each with an inactive ACE row beside the active SOLAR1 row.
- `ovation.json`: the 2026-10-18 14:24 UTC grid trimmed to longitudes 0, 1, 140 and 141 at latitudes ≥ 40° N and ≤ 50° S (368 cells, 185 non-zero). Tests also derive a quiet all-zero grid (edge case: no boundary).
