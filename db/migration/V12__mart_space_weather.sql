CREATE FUNCTION mart.g_scale(kp double precision) RETURNS smallint
LANGUAGE sql IMMUTABLE STRICT PARALLEL SAFE
RETURN CASE
    WHEN kp > 8.8 THEN 5
    WHEN kp >= 7.5 THEN 4
    WHEN kp >= 6.5 THEN 3
    WHEN kp >= 5.5 THEN 2
    WHEN kp >= 4.5 THEN 1
    ELSE 0
END;

COMMENT ON FUNCTION mart.g_scale(double precision) IS 'NOAA geomagnetic storm level G0 to G5 from planetary Kp in thirds: G1 is Kp 5- to 5+, G2 6, G3 7, G4 8- to 9-, G5 9o.';

CREATE FUNCTION mart.r_scale(peak_flux_wm2 double precision) RETURNS smallint
LANGUAGE sql IMMUTABLE STRICT PARALLEL SAFE
RETURN CASE
    WHEN peak_flux_wm2 >= 2e-3 THEN 5
    WHEN peak_flux_wm2 >= 1e-3 THEN 4
    WHEN peak_flux_wm2 >= 1e-4 THEN 3
    WHEN peak_flux_wm2 >= 5e-5 THEN 2
    WHEN peak_flux_wm2 >= 1e-5 THEN 1
    ELSE 0
END;

COMMENT ON FUNCTION mart.r_scale(double precision) IS 'NOAA radio blackout level R0 to R5 from GOES 0.1-0.8 nm peak flux: R1 M1, R2 M5, R3 X1, R4 X10, R5 X20.';

CREATE MATERIALIZED VIEW mart.kp_daily AS
SELECT
    (g.observed_at AT TIME ZONE 'UTC')::date AS day,
    max(g.value) AS kp_max,
    avg(g.value) AS kp_mean,
    count(*) AS intervals,
    mart.g_scale(max(g.value)) AS g_scale,
    'swpc'::text AS source
FROM core.geomagnetic_index g
WHERE g.index = 'kp'
GROUP BY 1;

CREATE UNIQUE INDEX kp_daily_key ON mart.kp_daily (day);

COMMENT ON MATERIALIZED VIEW mart.kp_daily IS 'Planetary Kp per UTC day: maximum, mean, the number of 3-hour intervals seen and the storm level of the maximum.';

CREATE MATERIALIZED VIEW mart.flare_counts_monthly AS
SELECT
    date_trunc('month', coalesce(e.peak_at, e.begin_at) AT TIME ZONE 'UTC')::date AS month,
    left(e.event_class, 1) AS class_letter,
    count(*) AS flares,
    max(e.peak_flux_wm2) AS max_peak_flux_wm2,
    (array_agg(e.event_class ORDER BY e.peak_flux_wm2 DESC NULLS LAST, e.external_id))[1] AS strongest_class,
    'swpc'::text AS source
FROM core.space_weather_event e
WHERE e.kind = 'xray_flare' AND e.event_class IS NOT NULL AND coalesce(e.peak_at, e.begin_at) IS NOT NULL
GROUP BY 1, 2;

CREATE UNIQUE INDEX flare_counts_monthly_key ON mart.flare_counts_monthly (month, class_letter);

COMMENT ON MATERIALIZED VIEW mart.flare_counts_monthly IS 'GOES X-ray flares per UTC month and class letter (A, B, C, M, X) with the strongest of each. Flares still in progress have no class yet and are left out.';

CREATE MATERIALIZED VIEW mart.solar_wind_hourly AS
SELECT
    date_trunc('hour', w.observed_at AT TIME ZONE 'UTC') AT TIME ZONE 'UTC' AS hour,
    avg(w.speed_kms) AS speed_kms_mean,
    max(w.speed_kms) AS speed_kms_max,
    avg(w.density_cm3) AS density_cm3_mean,
    avg(w.temperature_k) AS temperature_k_mean,
    avg(w.bt_nt) AS bt_nt_mean,
    avg(w.bz_gsm_nt) AS bz_gsm_nt_mean,
    min(w.bz_gsm_nt) AS bz_gsm_nt_min,
    count(*) AS samples,
    'swpc'::text AS source
FROM core.solar_wind_sample w
GROUP BY 1;

CREATE UNIQUE INDEX solar_wind_hourly_key ON mart.solar_wind_hourly (hour);

COMMENT ON MATERIALIZED VIEW mart.solar_wind_hourly IS 'Real-time solar wind at L1 averaged per UTC hour from one-minute samples; bz_gsm_nt_min is the most southward field, which drives geomagnetic storms.';
