CREATE FUNCTION mart.tdb_to_utc(tdb timestamp) RETURNS timestamptz
LANGUAGE sql IMMUTABLE STRICT PARALLEL SAFE
RETURN (
    SELECT (tdb - make_interval(secs => 32.184 + l.tai_minus_utc)) AT TIME ZONE 'UTC'
    FROM (
        VALUES
            (timestamp '1972-01-01', 10), (timestamp '1972-07-01', 11), (timestamp '1973-01-01', 12),
            (timestamp '1974-01-01', 13), (timestamp '1975-01-01', 14), (timestamp '1976-01-01', 15),
            (timestamp '1977-01-01', 16), (timestamp '1978-01-01', 17), (timestamp '1979-01-01', 18),
            (timestamp '1980-01-01', 19), (timestamp '1981-07-01', 20), (timestamp '1982-07-01', 21),
            (timestamp '1983-07-01', 22), (timestamp '1985-07-01', 23), (timestamp '1988-01-01', 24),
            (timestamp '1990-01-01', 25), (timestamp '1991-01-01', 26), (timestamp '1992-07-01', 27),
            (timestamp '1993-07-01', 28), (timestamp '1994-07-01', 29), (timestamp '1996-01-01', 30),
            (timestamp '1997-07-01', 31), (timestamp '1999-01-01', 32), (timestamp '2006-01-01', 33),
            (timestamp '2009-01-01', 34), (timestamp '2012-07-01', 35), (timestamp '2015-07-01', 36),
            (timestamp '2017-01-01', 37)
    ) AS l (effective_utc, tai_minus_utc)
    WHERE tdb - make_interval(secs => 32.184 + l.tai_minus_utc) >= l.effective_utc
    ORDER BY l.effective_utc DESC
    LIMIT 1
);

COMMENT ON FUNCTION mart.tdb_to_utc(timestamp) IS 'UTC = TDB - (32.184 s + TAI-UTC), with TAI-UTC from IERS Bulletin C (Leap_Second.dat, valid through 2027-06-28). TDB and TT differ by under 2 ms. NULL before 1972, when UTC had no leap seconds.';

CREATE FUNCTION mart.diameter_from_h_km(h double precision, albedo double precision) RETURNS double precision
LANGUAGE sql IMMUTABLE STRICT PARALLEL SAFE
RETURN 1329.0 / sqrt(albedo) * power(10.0, -h / 5.0);

COMMENT ON FUNCTION mart.diameter_from_h_km(double precision, double precision) IS 'Diameter estimate from absolute magnitude H and an assumed geometric albedo: D = 1329 km / sqrt(albedo) * 10^(-H/5).';

CREATE MATERIALIZED VIEW mart.close_approach_enriched AS
SELECT
    c.designation,
    b.fullname,
    c.body,
    c.approach_tdb,
    mart.tdb_to_utc(c.approach_tdb) AS approach_utc,
    c.t_sigma,
    c.dist_au,
    c.dist_au * 149597870.7 AS dist_km,
    c.dist_au * 149597870.7 / 384400.0 AS dist_ld,
    c.dist_min_au * 149597870.7 AS dist_min_km,
    c.dist_max_au * 149597870.7 AS dist_max_km,
    c.v_rel_kms,
    c.v_inf_kms,
    c.h_mag,
    b.diameter_km,
    b.diameter_sigma_km,
    mart.diameter_from_h_km(c.h_mag, 0.25) AS diameter_min_km,
    mart.diameter_from_h_km(c.h_mag, 0.05) AS diameter_max_km,
    (r.designation IS NOT NULL AND r.removed_at IS NULL) AS sentry,
    'jpl'::text AS source
FROM core.close_approach c
JOIN core.small_body b USING (designation)
LEFT JOIN core.impact_risk r USING (designation);

CREATE UNIQUE INDEX close_approach_enriched_key ON mart.close_approach_enriched (designation, body, approach_tdb);
CREATE INDEX close_approach_enriched_time ON mart.close_approach_enriched (approach_tdb);
CREATE INDEX close_approach_enriched_dist ON mart.close_approach_enriched (dist_au);

COMMENT ON MATERIALIZED VIEW mart.close_approach_enriched IS 'Close approaches with distances in km and lunar distances (1 au = 149,597,870.7 km, 1 LD = 384,400 km), the approach time in UTC, a diameter range from H for albedos 0.25 to 0.05, and whether the object is on the Sentry impact-risk list.';

CREATE MATERIALIZED VIEW mart.close_approach_monthly AS
SELECT
    c.body,
    date_trunc('month', c.approach_tdb)::date AS month,
    count(*) AS approaches,
    count(*) FILTER (WHERE c.dist_au * 149597870.7 <= 384400.0) AS within_1_ld,
    min(c.dist_au) * 149597870.7 / 384400.0 AS closest_dist_ld,
    (array_agg(c.designation ORDER BY c.dist_au, c.designation))[1] AS closest_designation,
    min(c.h_mag) AS min_h_mag,
    (array_agg(c.designation ORDER BY c.h_mag, c.designation) FILTER (WHERE c.h_mag IS NOT NULL))[1] AS largest_designation,
    'jpl'::text AS source
FROM core.close_approach c
GROUP BY c.body, date_trunc('month', c.approach_tdb);

CREATE UNIQUE INDEX close_approach_monthly_key ON mart.close_approach_monthly (body, month);

COMMENT ON MATERIALIZED VIEW mart.close_approach_monthly IS 'Close approaches within 0.05 au per TDB calendar month: count, how many came within one lunar distance, the closest, and the likely largest (lowest H).';
