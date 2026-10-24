# NASA Exoplanet Archive

Slug: `exoplanet-archive` · Adapter: `ingest/hoshizora_ingest/sources/exoplanets/` · Verified against the live documentation and responses on 2026-10-19.

## Purpose

The Exoplanets page: discoveries per year and method, sizes against orbits, the nearest known planets, and the exoplanet facts.

## Access

| | |
|---|---|
| Endpoint | `https://exoplanetarchive.ipac.caltech.edu/TAP/sync` (Table Access Protocol, synchronous). Docs: <https://exoplanetarchive.ipac.caltech.edu/docs/TAP/usingTAP.html> |
| Table | `pscomppars`, the Planetary Systems Composite Parameters table (DOI 10.26133/NEA13): one row per confirmed planet with the archive's best value for each parameter. Columns: <https://exoplanetarchive.ipac.caltech.edu/docs/API_PS_columns.html> |
| Auth | None |
| Rate limit | None published. We make one request a day, at most one every 5 seconds, with retries on 429 and 5xx |
| Update cadence | Weekly, per the table's DOI listing (the day of the week isn't published) |
| Conditional requests | Not supported (no ETag or Last-Modified), so unchanged tables are skipped by content hash |
| Format | `format=json`: a JSON array of objects, one per planet. Missing values are `null` |
| License and credit | Public NASA data. The archive asks for its acknowledgment in published material: "This research has made use of the NASA Exoplanet Archive, which is operated by the California Institute of Technology, under contract with the National Aeronautics and Space Administration under the Exoplanet Exploration Program." Citation: Christiansen et al. (2025), *Planetary Science Journal*; service DOI 10.26133/NEA45. <https://exoplanetarchive.ipac.caltech.edu/docs/acknowledge.html>. The acknowledgment is shown on the Exoplanets page and the Sources page |

## What is fetched

One ADQL query, once a day:

```sql
select pl_name,hostname,sy_snum,sy_pnum,discoverymethod,disc_year,disc_facility,disc_locale,
       pl_orbper,pl_orbsmax,pl_rade,pl_bmasse,pl_orbeccen,pl_eqt,pl_insol,st_teff,st_rad,st_mass,
       sy_dist,pl_controv_flag
from pscomppars order by pl_name
```

On 2026-10-19 it returned 6,451 planets in 3.0 MB of JSON (4.4 s). The payload stores at 0.6 MB, and `core.exoplanet` takes 1.8 MB with indexes. The request's params never change, so the endpoint is in `raw.retention_policy` (48 hours) and a superseded table loses its body.

## How the table stays correct

- **The table is a snapshot.** Each new payload upserts every planet and deletes planets the archive no longer lists (retracted planets). Their `core.source_record` rows stay.
- **A shrinking table fails the run.** If a response holds fewer than 90 % of the stored planets, the run fails and nothing changes (`ShrunkTableError`). A partial or broken response cannot wipe the table.

## Field mapping

| Source field | Core column |
|---|---|
| `pl_name`, `hostname` | `core.exoplanet.name` (key), `host_name` |
| `sy_snum`, `sy_pnum` | `star_count`, `planet_count` |
| `discoverymethod`, `disc_year`, `disc_facility` | `discovery_method`, `discovery_year`, `discovery_facility` |
| `disc_locale` | `discovery_locale`, lowercased (`ground`, `space`, `multiple locales`) |
| `pl_orbper`, `pl_orbsmax`, `pl_orbeccen` | `orbital_period_days`, `semi_major_axis_au`, `eccentricity` |
| `pl_rade`, `pl_bmasse` | `radius_earth`, `mass_earth` |
| `pl_eqt`, `pl_insol` | `equilibrium_temp_k`, `insolation_earth` |
| `st_teff`, `st_rad`, `st_mass` | `star_temp_k`, `star_radius_sun`, `star_mass_sun` |
| `sy_dist` | `distance_pc` (the API also gives light-years, 1 pc = 3.26156 ly) |
| `pl_controv_flag` | `controversial` |

Discovery methods appear in English in core and are translated by the API's `discovery_method` vocabulary (トランジット法, 視線速度法, …).

## Marts

- `mart.exoplanet_discoveries_yearly`: planets per discovery year and method, and how many were found from space.
- `mart.exoplanet_size_orbit`: transiting planets counted on a log grid (0.25 dex of period by 0.125 dex of radius), for the size-against-orbit chart without sending 6,000 points to the browser.

## Quirks

- **Composite values mix sources.** Each column holds the archive's preferred value, which may come from a different paper than the next column.
- **Radii are often estimates.** For planets not seen transiting, `pl_rade` usually comes from a mass–radius relation (Proxima Cen b shows 1.02). The size chart and the Earth-sized fact use transiting planets only, and the nearest-planets table says so.
- **`pl_bmasse` is the best available mass**: M sin i for most radial-velocity planets, a lower limit.
- **`disc_locale` is not normalized at the source.** Two rows had `ground` in lowercase on 2026-10-19; the transform lowercases every value.
- **Microlensing planets often have no distance or period.**
- **`rowupdate`, `pl_pubdate` and `releasedate` exist only in the `ps` table,** not in `pscomppars`. Asking for them returns HTTP 400.
- **`HAT-P-47 b` shows `disc_year` 2026** although its star was catalogued earlier; the archive dates a planet by its confirmation paper.

## Fixtures

`ingest/tests/fixtures/exoplanet-archive/planets.json`: 8 real rows from 2026-10-19. They cover the nearest planet (Proxima Cen b), the lowercase `ground` locale, two controversial planets, a radial-velocity planet without a radius, a microlensing planet without a distance, a 2026 discovery, TRAPPIST-1 e (`multiple locales`) and Kepler-452 b.
