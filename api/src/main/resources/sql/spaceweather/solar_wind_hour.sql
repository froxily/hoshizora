SELECT
    h.hour AS observed_at,
    h.speed_kms_mean AS speed_kms,
    h.density_cm3_mean AS density_cm3,
    h.temperature_k_mean AS temperature_k,
    h.bt_nt_mean AS bt_nt,
    h.bz_gsm_nt_mean AS bz_gsm_nt,
    h.speed_kms_max,
    h.bz_gsm_nt_min,
    h.samples
FROM mart.solar_wind_hourly h
WHERE h.hour >= :from AND h.hour < :to
ORDER BY h.hour
