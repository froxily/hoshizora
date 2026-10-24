CREATE TABLE core.small_body (
    designation text PRIMARY KEY,
    fullname text,
    h_mag double precision,
    diameter_km double precision,
    diameter_sigma_km double precision
);

COMMENT ON TABLE core.small_body IS 'Asteroids and comets seen in JPL close-approach or Sentry data, keyed by primary designation.';
COMMENT ON COLUMN core.small_body.h_mag IS 'Absolute magnitude H. Diameter estimates from H depend on an assumed albedo and must be shown as a range.';

CREATE TABLE core.close_approach (
    designation text NOT NULL REFERENCES core.small_body (designation),
    body text NOT NULL,
    approach_tdb timestamp NOT NULL,
    orbit_id text,
    jd_tdb double precision NOT NULL,
    dist_au double precision NOT NULL,
    dist_min_au double precision,
    dist_max_au double precision,
    v_rel_kms double precision,
    v_inf_kms double precision,
    t_sigma text,
    h_mag double precision,
    PRIMARY KEY (designation, body, approach_tdb)
);

CREATE INDEX close_approach_time_idx ON core.close_approach (approach_tdb);

COMMENT ON TABLE core.close_approach IS 'Close approaches within 0.05 au from the JPL SBDB Close Approach Data API. Each fetched date window replaces its rows, so revised predictions never leave stale duplicates.';
COMMENT ON COLUMN core.close_approach.approach_tdb IS 'Time of closest approach in TDB (Barycentric Dynamical Time), not UTC; TDB - UTC is about 69 s.';

CREATE TABLE core.impact_risk (
    designation text PRIMARY KEY REFERENCES core.small_body (designation),
    sentry_id text,
    fullname text,
    impact_probability double precision,
    palermo_cumulative double precision,
    palermo_max double precision,
    torino_max smallint,
    potential_impacts integer,
    impact_year_first smallint,
    impact_year_last smallint,
    last_observed date,
    diameter_km double precision,
    h_mag double precision,
    v_inf_kms double precision,
    removed_at timestamptz
);

COMMENT ON TABLE core.impact_risk IS 'JPL Sentry impact monitoring. Objects removed from Sentry keep their row with removed_at set; diameter, h and v_inf are impact-probability-weighted means.';
