SELECT
    w.observed_at,
    w.speed_kms,
    w.density_cm3,
    w.temperature_k,
    w.bt_nt,
    w.bz_gsm_nt,
    NULL::double precision AS speed_kms_max,
    NULL::double precision AS bz_gsm_nt_min,
    NULL::bigint AS samples
FROM core.solar_wind_sample w
WHERE w.observed_at >= :from AND w.observed_at < :to
ORDER BY w.observed_at
