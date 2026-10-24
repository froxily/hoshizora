# CelesTrak (SATCAT and GP)

Slug: `celestrak` · Adapter: `ingest/hoshizora_ingest/sources/celestrak/` · Verified against the live documentation and responses on 2026-10-16.

## Purpose

Every catalogued object (payloads, rocket bodies, debris) with its owner, launch and decay dates, and the current mean elements of active satellites for SGP4 propagation (the 3D globe in Phase 6). This is the only source that covers every nation's objects, including Russia's and China's.

## Access

| | |
|---|---|
| SATCAT | `https://celestrak.org/pub/satcat.csv`: the full catalog (~6.8 MB). Updated manually once or twice a day. Sends `ETag` and `Last-Modified` |
| GP | `https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=json`: CCSDS OMM mean elements for active satellites. Updated every 2 hours |
| Auth | None |
| Usage policy | <https://celestrak.org/usage-policy.php> (updated 2026-05-22): download GP data **once per update**, enforced for the Active and Starlink groups (repeats return 403). Software must **stop on any non-200 response** and report it to a person. Ignoring errors gets the IP firewalled. CelesTrak also counts 301/403/404 responses (about 50 per 2 hours) toward a block |
| License and credit | No attribution requirement is stated; the data is freely available. Credit shown: "Orbital data: CelesTrak (celestrak.org)" |
| Formats | SATCAT CSV per <https://celestrak.org/satcat/satcat-format.php>. GP OMM keywords per CCSDS 502.0-B-3 (<https://celestrak.org/NORAD/documentation/gp-data-formats.php>) |

## How the adapter respects the policy

- **No retries at all.** Any status other than 200 or 304 ends the run as `needs_review` (CLI exit code 3) and nothing in that page is committed.
- **Refetch intervals** come from the `raw.fetch` log (which also records 304s): SATCAT at most every 12 hours, GP at most every 2 hours. An immediate re-run makes **zero requests**.
- **SATCAT is requested conditionally** (`If-None-Match`/`If-Modified-Since`), so an unchanged catalog costs one 304.
- **Redirects are not followed.** A 301 means an outdated URL and is a review-stopping error, as the policy asks.
- **Catalog numbers are 6 digits since 2026-07-11**, so only JSON and CSV are used, never TLE.

## Field mapping

| Source field | Core column |
|---|---|
| `NORAD_CAT_ID` | `core.space_object.norad_id`, `core.orbit_element.norad_id` |
| `OBJECT_ID` | `space_object.object_id`; its `YYYY-NNN` prefix is `launch_designator` (joins `core.launch`) |
| `OBJECT_NAME`, `OBJECT_TYPE`, `OPS_STATUS_CODE` | `name`, `object_type` (PAY, R/B, DEB, UNK), `ops_status` |
| `OWNER` | `owner_code`, resolved through `core.space_object_country` / `core.space_object_organization` |
| `LAUNCH_DATE`, `LAUNCH_SITE`, `DECAY_DATE` | `launch_date`, `launch_site`, `decay_date` |
| `PERIOD`, `INCLINATION`, `APOGEE`, `PERIGEE`, `RCS` | `period_min`, `inclination_deg`, `apogee_km`, `perigee_km`, `rcs_m2` |
| `DATA_STATUS_CODE`, `ORBIT_CENTER`, `ORBIT_TYPE` | `data_status`, `orbit_center`, `orbit_type` |
| GP `EPOCH`, `MEAN_MOTION`, `ECCENTRICITY`, `INCLINATION`, `RA_OF_ASC_NODE`, `ARG_OF_PERICENTER`, `MEAN_ANOMALY`, `BSTAR`, `MEAN_MOTION_DOT`, `MEAN_MOTION_DDOT`, `ELEMENT_SET_NO`, `REV_AT_EPOCH`, `CLASSIFICATION_TYPE`, `EPHEMERIS_TYPE` | `core.orbit_element` (latest epoch per object) |

## Quirks

- **Owner codes are not agencies.** They're countries, joint ventures (`CHBZ`), international bodies (`ESA`, `EUME`) or companies (`IRID`). A `US` object may belong to NASA, the military or a company. All about 140 codes are mapped in [organizations.md](organizations.md), and a new code fails `hoshizora dq --strict`.
- **`CIS` covers Soviet and Russian objects** and resolves to Russia. ISS modules use the owner code `ISS`.
- **Docked objects put the host's catalog number in `ORBIT_CENTER`** (e.g. POISK → `25544`, orbit type `DOC`).
- **Empty CSV fields mean "no data"** (e.g. no RCS for Sputnik 1) and are stored as NULL.
- **GP `EPOCH` has no time zone.** It's UTC and stored as `timestamptz`.
- **GP can list objects that SATCAT hasn't catalogued yet.** They get a minimal row (id, designator, name), and the next SATCAT load completes it.
- **Older epochs never replace newer elements.** The element history stays in `raw.payload`.

## Fixtures

`ingest/tests/fixtures/celestrak/`, captured with three small requests on 2026-10-16 so that the large files are not downloaded twice:

- `gp_stations.json`: GP OMM JSON for the `stations` group.
- `satcat_stations.csv`: the same CSV schema as `pub/satcat.csv`, for the `stations` group (ISS modules, docked objects, several owner codes).
- `satcat_sputnik.csv`: launch 1957-001, the edge case (decayed objects, owner `CIS`, missing RCS).
