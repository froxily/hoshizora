CREATE TABLE core.exoplanet (
    name text PRIMARY KEY,
    host_name text NOT NULL,
    star_count smallint CHECK (star_count >= 1),
    planet_count smallint CHECK (planet_count >= 1),
    discovery_method text NOT NULL,
    discovery_year smallint,
    discovery_facility text,
    discovery_locale text,
    orbital_period_days double precision CHECK (orbital_period_days > 0),
    semi_major_axis_au double precision CHECK (semi_major_axis_au > 0),
    radius_earth double precision CHECK (radius_earth > 0),
    mass_earth double precision CHECK (mass_earth > 0),
    eccentricity double precision CHECK (eccentricity >= 0),
    equilibrium_temp_k double precision CHECK (equilibrium_temp_k > 0),
    insolation_earth double precision CHECK (insolation_earth >= 0),
    star_temp_k double precision,
    star_radius_sun double precision,
    star_mass_sun double precision,
    distance_pc double precision CHECK (distance_pc > 0),
    controversial boolean NOT NULL
);

CREATE INDEX exoplanet_discovery_idx ON core.exoplanet (discovery_year, discovery_method);
CREATE INDEX exoplanet_distance_idx ON core.exoplanet (distance_pc);

COMMENT ON TABLE core.exoplanet IS 'Confirmed exoplanets from the NASA Exoplanet Archive Planetary Systems Composite Parameters table (pscomppars): one row per planet with the archive''s best value for each parameter, which may come from different publications. Planets the archive drops are deleted; their lineage rows stay.';
COMMENT ON COLUMN core.exoplanet.mass_earth IS 'pl_bmasse: the best available mass, which is M sin i for most radial-velocity planets.';
COMMENT ON COLUMN core.exoplanet.controversial IS 'pl_controv_flag: the planet''s confirmation has been questioned in the literature.';

INSERT INTO raw.retention_policy (source, endpoint, keep, reason)
VALUES (
    'exoplanet-archive',
    'https://exoplanetarchive.ipac.caltech.edu/TAP/sync',
    interval '48 hours',
    'The whole composite table, about 3 MB of JSON, fetched daily and changed weekly. Core keeps the latest values per planet.'
);

CREATE MATERIALIZED VIEW mart.exoplanet_discoveries_yearly AS
SELECT
    e.discovery_year AS year,
    e.discovery_method AS method,
    count(*) AS planets,
    count(*) FILTER (WHERE e.discovery_locale = 'space') AS from_space,
    'exoplanet-archive'::text AS source
FROM core.exoplanet e
WHERE e.discovery_year IS NOT NULL
GROUP BY e.discovery_year, e.discovery_method;

CREATE UNIQUE INDEX exoplanet_discoveries_yearly_key ON mart.exoplanet_discoveries_yearly (year, method);

COMMENT ON MATERIALIZED VIEW mart.exoplanet_discoveries_yearly IS 'Confirmed exoplanets per discovery year and method, and how many were found from space.';

CREATE MATERIALIZED VIEW mart.exoplanet_size_orbit AS
SELECT
    floor(log(e.orbital_period_days) / 0.25)::integer AS period_bin,
    floor(log(e.radius_earth) / 0.125)::integer AS radius_bin,
    count(*) AS planets,
    'exoplanet-archive'::text AS source
FROM core.exoplanet e
WHERE e.discovery_method = 'Transit'
  AND e.orbital_period_days IS NOT NULL
  AND e.radius_earth IS NOT NULL
GROUP BY 1, 2;

CREATE UNIQUE INDEX exoplanet_size_orbit_key ON mart.exoplanet_size_orbit (period_bin, radius_bin);

COMMENT ON MATERIALIZED VIEW mart.exoplanet_size_orbit IS 'Transiting planets counted on a log grid: orbital period bins of 0.25 dex (10^(0.25 period_bin) days and up) by radius bins of 0.125 dex (10^(0.125 radius_bin) Earth radii and up). Transits measure the radius directly; other methods mostly estimate it.';
