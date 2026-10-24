SELECT
    kp.observed_at AS kp_observed_at,
    kp.value AS kp,
    mart.g_scale(kp.value) AS g_scale,
    wind.observed_at AS wind_observed_at,
    wind.speed_kms,
    wind.density_cm3,
    wind.temperature_k,
    wind.bt_nt,
    wind.bz_gsm_nt,
    NULL::double precision AS speed_kms_max,
    NULL::double precision AS bz_gsm_nt_min,
    NULL::bigint AS samples,
    flare.external_id AS flare_id,
    flare.begin_at AS flare_begin_at,
    flare.peak_at AS flare_peak_at,
    flare.end_at AS flare_end_at,
    flare.event_class AS flare_xray_class,
    flare.peak_flux_wm2 AS flare_peak_flux_wm2,
    flare.satellite AS flare_satellite,
    mart.r_scale(flare.peak_flux_wm2) AS flare_r_scale,
    counted.flares AS flares_last_day
FROM (SELECT CAST(:as_of AS timestamptz) AS as_of) AS asked
LEFT JOIN LATERAL (
    SELECT g.observed_at, g.value
    FROM core.geomagnetic_index g
    WHERE g.index = 'kp' AND g.observed_at <= asked.as_of
    ORDER BY g.observed_at DESC
    LIMIT 1
) AS kp ON true
LEFT JOIN LATERAL (
    SELECT w.*
    FROM core.solar_wind_sample w
    WHERE w.observed_at <= asked.as_of
    ORDER BY w.observed_at DESC
    LIMIT 1
) AS wind ON true
LEFT JOIN LATERAL (
    SELECT e.*
    FROM core.space_weather_event e
    WHERE e.kind = 'xray_flare'
      AND e.event_class IS NOT NULL
      AND coalesce(e.peak_at, e.begin_at) > asked.as_of - interval '24 hours'
      AND coalesce(e.peak_at, e.begin_at) <= asked.as_of
    ORDER BY e.peak_flux_wm2 DESC NULLS LAST, e.external_id
    LIMIT 1
) AS flare ON true
CROSS JOIN LATERAL (
    SELECT count(*) AS flares
    FROM core.space_weather_event e
    WHERE e.kind = 'xray_flare'
      AND coalesce(e.peak_at, e.begin_at) > asked.as_of - interval '24 hours'
      AND coalesce(e.peak_at, e.begin_at) <= asked.as_of
) AS counted
